<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AI Development Rules - FastAPI APIs

These rules apply to all Python FastAPI services in `apps/api/`.

## Development Approach: Learn from Existing Code

**Before implementing any feature or writing tests, always examine existing code for established patterns.**

### Planning Phase Pattern Recognition

When planning implementation:

1. **Search for similar functionality** - Look for existing endpoints, services, or features that are similar to what you're building
2. **Identify architectural patterns** - Understand how the app structures routers, services, repositories, and dependencies
3. **Review existing tests** - See how similar features are tested to maintain consistency
4. **Follow established conventions** - Use the same naming, structure, and patterns already in use

### Use Codebase as Primary Reference

**This document provides essential rules and guidelines. For implementation details and examples, always consult the actual codebase:**

- **Implementation patterns**: Examine similar routers, services, and repositories in the app
- **Testing patterns**: Review existing test files to understand the app's testing conventions
- **Naming conventions**: Follow patterns from existing code for consistency
- **Architecture decisions**: Understand and follow the app's established structure

**Consistency is critical** - both implementation code and test code should follow patterns already established in the codebase. Don't introduce new patterns when existing patterns solve the problem.

## Technology Stack

- **Python 3.13+** with asynchronous programming
- **FastAPI** for API framework
- **SQLAlchemy** for ORM with asyncio support
- **PostgreSQL** for database
- **Liquibase** for database migrations
- **Uvicorn** for ASGI server
- **uv** for package management

## FastAPI Best Practices

### Async/Await Usage

- **Prefer `async` for I/O operations**: Database calls, external API requests, file operations, k8s API calls
- **Use `sync` functions for CPU-intensive tasks**: Heavy calculations, data processing (FastAPI runs these in threadpool)
- **Never mix blocking I/O in async functions**: Avoid `time.sleep()`, sync database calls in async routes
- Use `await asyncio.sleep()` instead of `time.sleep()` in async functions
- **Fan out independent I/O with `asyncio.gather`.** A `for x in xs: await io(x)` loop over a caller-driven list serializes N round-trips; rewrite as `await asyncio.gather(*(io(x) for x in xs))` so latency is bounded by the slowest call, not the sum. This is the established pattern across `apps/api/` — `rg 'asyncio\.gather' apps/api` for current usages. Only keep sequential iteration when a later call depends on an earlier result.

### Deduplicating inputs

When fanning out N K8s calls keyed off a user-supplied list, dedupe the input with `dict.fromkeys(xs)` (order-preserving) at the top of the function — before the `asyncio.gather`. When each call is uniquely keyed by its input (get-by-name, or an equality field selector on a single-valued field), the per-call result sets don't overlap, so duplicate results can only come from duplicate inputs — dedupe the input and the results are clean. Deduping results after the fact is solving a problem you created by not deduping the input. (This doesn't hold for label-selector fan-outs where one object can match several calls; there, the merged results genuinely need a `metadata.name` dedupe.)

### Dependencies and Dependency Injection

- Use dependencies for validation beyond Pydantic: database constraint checks, complex business rules
- Chain dependencies for reusability: break complex validation into smaller, composable functions
- Prefer `async` dependencies to avoid unnecessary threadpool overhead

### Pydantic Configuration

- Use custom base models for consistency: standardize datetime formatting, add common methods
- Decouple settings by domain: split BaseSettings into module-specific configs
- Leverage Pydantic validators for emails, URLs, enums, and custom business rules

### CamelCase API Convention

All API endpoints accept and return **camelCase** field names only. This is enforced at three layers:

1. **Code**: `api_common.schemas.BaseModel` adds `alias_generator=to_camel` to auto-generate camelCase aliases
2. **Runtime**: `CamelCaseMiddleware` rejects snake_case keys in request bodies and query params with 422
3. **CI**: Spectral lints the OpenAPI spec to catch snake_case property/parameter names before merge

Python code (services, repositories, tests) always uses snake_case internally. The translation happens automatically.

**Exception:** Chat endpoints (paths ending in `/chat`, e.g. `/workloads/{id}/chat`) follow OpenAI's snake_case convention and are excluded from the middleware.

#### Base class

`api_common.schemas.BaseModel` replaces `pydantic.BaseModel` for all API schemas. It provides `alias_generator=to_camel`, `populate_by_name=True`, and `from_attributes=True` out of the box. Always import from `api_common.schemas`:

```python
from api_common.schemas import BaseModel  # NOT from pydantic

class ClusterIn(BaseModel):
    workloads_base_url: str | None = None  # snake_case in Python, camelCase in API

class ClusterResponse(BaseModel):
    ...  # from_attributes=True is inherited, no need to set it
```

#### Query parameters

Define query params as a Pydantic model inheriting from `BaseModel` and use `QueryParam[...]` in the router signature. `QueryParam` is a type alias for `Annotated[T, Query()]` provided by `api_common.schemas`. This is required because `Depends()` does not resolve `alias_generator` for query params. Do NOT use manual `Query(alias="...")`.

```python
from api_common.schemas import QueryParam

class ListItemsQuery(BaseModel):
    page_size: int = Field(default=20, ge=1, le=100)
    sort_order: SortDirection = Field(default=SortDirection.desc)

@router.get("/items")
async def list_items(query: QueryParam[ListItemsQuery]):
    ...  # access query.page_size in Python
    # API accepts ?pageSize=20&sortOrder=desc
```

**Why not `Depends()`?** `Depends()` matches query params by field name (snake_case), ignoring aliases. `QueryParam` uses `Annotated[T, Query()]` so FastAPI resolves camelCase aliases.

**Bound caller-driven repeatable params at the Pydantic boundary.** Any repeatable query param the caller controls — `aim_id: list[str] = Field(default_factory=list)`, `status: list[Status] = Field(...)` — needs `max_length=` on the `Field` the same way `page_size` uses `le=100`. Without it, a single client can submit thousands of values and force fan-out (`asyncio.gather` over the list, N K8s calls, etc.) the service was never sized for. Fail-fast in Pydantic returns a clean 422; pushing the cap into a runtime semaphore in the service layer hides the problem from the API contract.

**Known bug:** `QueryParam` breaks when the endpoint also has `Depends()` params with `Query()`. FastAPI stops flattening the model fields. Fix pending: [fastapi#12481](https://github.com/fastapi/fastapi/pull/12481). In that case, fall back to `Depends()` with `alias=to_camel("field_name")` on each param:

```python
page_size: int = Query(default=10, alias=to_camel("page_size"))
```

#### Rules

- All API schemas inherit from `api_common.schemas.BaseModel`
- Query params use `QueryParam[MyQuery]`; fall back to `Depends()` + `alias=to_camel(...)` only when hitting the bug above
- Router tests send bodies with `model.model_dump(by_alias=True)`; service/repo tests use `model.model_dump()`

#### Exceptions (fields that stay snake_case)

- **OpenAI-compatible endpoints** (`/chat`): Follow OpenAI spec — `stream_options`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `frequency_penalty`, `presence_penalty`. The CamelCaseMiddleware excludes `/chat` paths.
- **OAuth2/OIDC fields**: `client_id`, `client_secret`, `grant_type`, `refresh_token`, `access_token`, `id_token` — external protocol spec.
- **RabbitMQ messaging schemas**: Internal inter-service messages use `pydantic.BaseModel` (not `api_common.schemas.BaseModel`) to preserve snake_case wire format.
- **Metric name values**: Strings like `'total_tokens'`, `'gpu_device_utilization'` passed as values (not JSON keys) to metric endpoints.
- **Kubernetes annotations/labels**: `airm.silogen.ai/project-id` etc. follow K8s conventions.
- **URL path parameters**: `{workload_id}` in route paths — these are URL segments, not JSON fields.
- **Helm template values**: `{{ .Values.metadata.project_id }}` follow Helm conventions.

### Error Handling

- **Domain exceptions**: Use `api_common.exceptions` (NotFoundException, ValidationException, etc.)
- **HTTP mapping**: FastAPI exception handlers automatically map domain exceptions to HTTP responses
- **Service layers**: Raise domain-specific exceptions
- **API layers**: Let FastAPI exception handlers manage HTTP responses

### Transaction Handling

- **Router layer manages transactions**: Endpoints using `Depends(get_session)` get automatic transaction handling
- **Service/Repository layers are transaction-agnostic**: Receive active `AsyncSession`, don't call `commit()` or `rollback()`
- Use `session.flush()` when needed to get generated IDs or enforce constraints

## Database Conventions

- **Constraint naming**: `{table_name}_{column(s)}_{type}_key`
- **SQL-first approach**: Prefer database operations over Python processing for joins, aggregations, transformations
- **Use database functions**: `func.json_build_object()`, `func.coalesce()`, etc.

## Schema Naming Conventions

Avoid naming conflicts between SQLAlchemy models and Pydantic schemas:

- **Response schemas**: `{Entity}Response` suffix (e.g., `UserResponse`, `AimResponse`)
- **Input schemas**: `{Entity}Create`, `{Entity}Edit`, or `{Entity}In`
- **Query param models**: `{Action}{Entity}Query` suffix (e.g., `ListModelsQuery`, `WorkloadStreamQuery`). Do NOT use `*Request` for query param models, as `*Request` is reserved for body/action schemas.
- **Models**: Simple names (`User`, `AimService`)
- **Avoid import aliases**: Clear naming eliminates the need for `import X as Y`

### List Response Pattern

For endpoints returning lists, use the generic `ListResponse[T]` from `api_common.schemas` instead of creating custom wrapper classes:

```python
# GOOD - use generic ListResponse
from api_common.schemas import ListResponse

@router.get("/users", response_model=ListResponse[UserResponse])
async def list_users() -> ListResponse[UserResponse]:
    users = await get_users()
    return ListResponse(data=users)

# BAD - don't create custom list wrappers
class UsersResponse(BaseModel):
    data: list[UserResponse]  # Unnecessary duplication
```

**When to use `ListResponse[T]`:**

- Simple list endpoints with `data: list[T]` structure

**When to use custom response classes:**

- Responses with multiple fields (e.g., `ChattableResponse` with `aim_services` and `workloads`)
- Paginated responses with metadata (see `### Pagination` below)
- Responses requiring computed fields or validators

### Pagination

Paginated list endpoints use a nested envelope: `data` carries the typed page, and a sibling `pagination` object carries page metadata.

**Envelope shape (wire):**

```json
{
  "data": [...],
  "pagination": { "page": 1, "pageSize": 10, "total": 137 }
}
```

**Response schema** — subclass `api_common.collections.BasePaginationList` and declare only the typed `data` field. The `pagination` field is inherited.

```python
from api_common.collections import BasePaginationList, PaginationMetadata

class InferenceDeploymentsList(BasePaginationList):
    data: list[InferenceDeploymentResponse]

# In the router:
return InferenceDeploymentsList(
    data=[InferenceDeploymentResponse.model_validate(s, from_attributes=True) for s in paginated.items],
    pagination=PaginationMetadata(
        page=paginated.page,
        page_size=paginated.page_size,
        total=paginated.total,
    ),
)
```

**Query parameters** — subclass `PaginationConditions` and override `page_size` to bind the cap. Default page size is 10; max is 100. Surface other filters as fields on the same model.

```python
from pydantic import Field
from api_common.collections import PaginationConditions

class ListInferenceDeploymentsQuery(PaginationConditions):
    page: int = Field(default=1, ge=1)
    # Bound page_size so a single client cannot fetch arbitrarily large pages.
    page_size: int = Field(default=10, ge=1, le=100)
    capability: InferenceCapability | None = None
    status_filter: list[AIMServiceStatus] | None = None
```

**When to paginate:** list endpoints where the result set scales with organization / project / cluster size. Small fixed enumerations (e.g., workload chart templates at `GET /v1/charts`) stay as `ListResponse[T]`.

**Composing with filter and sort:** `BaseFilterableList` and `BaseSortableList` are _query-input_ mixins, independent of the response envelope. Compose them on the query model when needed; the response model still subclasses only `BasePaginationList`.

**In-memory vs SQL pagination:**

- In-memory page slicing — `paginate_list()` from `api_common.collections` (used by AIWB inference endpoints that work over a fetched list).
- SQL pagination — `apply_pagination_to_query()` in `apps/api/airm/app/utilities/collections/queries.py` (issues a separate `COUNT(*)` to get `total`).

**`totalPages` is client-derived.** The envelope intentionally omits it. Clients that need it compute `Math.ceil(total / pageSize)`.

**Cursor pagination exception.** Time-series / log streams use cursor pagination, not offset-based: `PaginationMetadataResponse` + `TimeRangePaginationRequest`. See `apps/api/aiwb/app/logs/` for the reference implementation. Do not retrofit the offset envelope onto those endpoints.

**Naming:** snake_case in Python (`page_size`), camelCase on the wire (`pageSize`) via the alias generator. Tests construct query params as `params={"pageSize": 10}` for requests, and assert response shape as `body["pagination"]["pageSize"]`.

## Import Organization

Use module imports to avoid redundancy:

```python
# GOOD - module prefix makes origin clear
from . import gateway
from . import repository

aim = await gateway.get_aim_by_id(...)
history = await repository.get_aim_history(...)
```

**Rules:**

- Do NOT rename imports with `as`. The module prefix provides context.
- Place all imports at the top of the file
- Group: standard library → third-party → local imports

## API Documentation

- Use comprehensive endpoint documentation: `response_model`, `status_code`, `description`, `summary`, `tags`
- Document different response scenarios with the `responses` parameter
- Keep descriptions concise but contextually rich for LLM consumption

## Testing Strategy

**Examine existing test files before writing new tests.** This document provides essential rules - the codebase demonstrates how to apply them in practice. Maintain consistency with established testing patterns.

### Test Structure

**Always use function-based tests, never class-based tests.** Function-based tests are simpler and more composable with pytest fixtures.

**Always place ALL imports at the top of test files.** Never add imports inside test functions or fixtures.

### Testing by Layer

| Layer      | Real DB   | Mock External Services  |
| ---------- | --------- | ----------------------- |
| Repository | ✅ Always | -                       |
| Service    | ✅        | ✅ (Keycloak, S3, etc.) |
| Router/API | ✅        | ✅                      |

### When to Use Real Database vs Mocking

**✅ Use Real Database:**

- Repository layer tests (always)
- Service layer business logic
- Database constraints and relationships
- Transaction rollback scenarios

**✅ Use Mocking:**

- External services (Keycloak, S3, email)
- Error scenarios for external services
- Service boundary isolation (mock service calls, return real DB objects)

**❌ Avoid Mocking:**

- SQLAlchemy session operations
- Database constraints and validation
- Transaction management

### Test Data Factories

Use centralized factory functions from `tests/factory.py`:

- **Environment Factories**: `create_basic_test_environment()`, `create_full_test_environment()`
- **Entity Factories**: `create_organization()`, `create_user()`, `create_project()`, etc.
- Prefer factories over inline object creation

### Mock Specification

Always use `spec=` parameter to catch interface mismatches:

```python
session = AsyncMock(spec=AsyncSession)
kc_admin = AsyncMock(spec=KeycloakAdmin)
project = MagicMock(spec=Project)
```

Use `AsyncMock` for async dependencies, not `MagicMock`.

### AsyncMock call-order assertions under gather

Treat the order of mock calls made by tasks dispatched through `asyncio.gather` as non-contractual. The event loop can interleave concurrent tasks for reasons unrelated to your mock (an `await` anywhere before the mocked call is enough), so `assert_has_calls([...])` on gather-dispatched tasks is flaky by construction — a synchronous `side_effect` may make it pass today, but that's incidental, not a guarantee. Default to order-independent assertions (`assert {c.args[0] for c in mock.call_args_list} == {...}`). Only assert ordering when the production code explicitly sequences the calls — and then the sequencing belongs in the code, not in the test.

## App-Specific Testing Patterns

**Individual apps in `/apps/api/` have different testing implementations based on their architecture.** Always check your app's `tests/dependency_overrides.py` for available override patterns before writing tests. For app-specific guidance, see your app's AI rules file (if it exists).

## FastAPI Dependency Override Mechanics

### Core Concept

FastAPI's `app.dependency_overrides` dictionary allows replacing dependency implementations during testing. This enables mocking authentication, external services, and controlling test scenarios.

### Critical: Proper Cleanup

**Always use decorator or context manager** - they restore overrides automatically. Direct `app.dependency_overrides` manipulation causes test pollution.

## Override Patterns: Decorator vs Context Manager

### `@override_dependencies` Decorator

**Test-level scope** - applies overrides to the entire test function. Use for single-scenario tests.

```python
from tests.dependency_overrides import override_dependencies, BASE_OVERRIDES

@override_dependencies(BASE_OVERRIDES)
async def test_endpoint_access(client: AsyncClient):
    response = await client.get("/v1/resources/123")
    assert response.status_code == 200
```

### `runtime_dependency_overrides` Context Manager

**Block-level scope** - applies overrides to specific code blocks. Use for testing multiple scenarios in one test.

```python
from tests.dependency_overrides import runtime_dependency_overrides, BASE_OVERRIDES

async def test_authorization_boundaries(client: AsyncClient):
    admin_overrides = {**BASE_OVERRIDES, get_user_role: lambda: "admin"}
    user_overrides = {**BASE_OVERRIDES, get_user_role: lambda: "user"}

    with runtime_dependency_overrides(admin_overrides):
        response = await client.delete("/v1/resources/123")
        assert response.status_code == 204

    with runtime_dependency_overrides(user_overrides):
        response = await client.delete("/v1/resources/123")
        assert response.status_code == 403
```

### Combining Patterns

Combine decorator and context manager when you need base overrides for the entire test with specific overrides per scenario.

## Reusable Override Dictionaries

Apps define pre-configured override patterns in `tests/dependency_overrides.py` for common test scenarios.

### Pattern: Building Blocks

Create minimal overrides for specific dependencies, then combine using dictionary unpacking:

```python
# Building blocks (example - check your app's actual patterns)
MINIMAL_SESSION_OVERRIDES = {
    get_session: lambda: AsyncMock(spec=AsyncSession),
}

# Composition
USER_EMAIL_WITH_SESSION_OVERRIDES = {
    **MINIMAL_SESSION_OVERRIDES,
    get_user_email: lambda: "test@example.com",
}
```

**Note**: Pattern names vary by app. Check your app's `tests/dependency_overrides.py` for actual available patterns.

## Dictionary Composition Best Practices

- **Reuse existing patterns** from `tests/dependency_overrides.py` rather than creating inline overrides
- **Create named patterns** in `tests/dependency_overrides.py` if multiple tests need the same overrides
- **Override order matters**: Later entries override earlier ones in dictionary composition
- **Always specify mock types** with `spec` or `spec_set` to catch type errors early

## When to Use Each Pattern

- **Use `@override_dependencies`** when entire test needs same dependencies (single scenario)
- **Use `runtime_dependency_overrides`** when testing multiple scenarios in one test (authorization boundaries, different roles)
- **Avoid direct `app.dependency_overrides` manipulation** - legacy pattern, causes test pollution

## Common Pitfalls

- **Never manipulate `app.dependency_overrides` directly** - use decorator or context manager
- **Put specific overrides last in dictionary composition** - later entries override earlier ones
- **Always specify mock types** with `spec` or `spec_set`
- **Use `AsyncMock` for async dependencies** - not `MagicMock`
- **Global overrides from `conftest.py` are preserved** - `runtime_dependency_overrides` adds to them

## Test Coverage Requirements

**Critical Test Categories:**

- Happy path scenarios
- Error handling (external service failures, constraint violations, invalid input)
- Edge cases (empty results, boundary conditions, null values)
- Security scenarios (cross-organization access, permission boundaries)
- Transaction safety (rollback behavior, constraint enforcement)

**Layer-Specific Coverage:**

- **Repository:** CRUD operations, constraints, query logic, transaction handling
- **Service:** Business rules, error handling, external service integration, validation
- **API:** HTTP handling, authentication, request/response formatting, dependency injection

## Advanced Testing Patterns

### Service Boundary Mocking

Mock service function calls but return real database objects for optimal unit test isolation. This isolates unit tests from other service bugs while maintaining real SQLAlchemy behavior.

**Use case:** Complex services that call multiple other services (e.g., workspace service calling workloads service).

### Mock Specification Details

1. **Simple Interface Mocks - Use `spec=`:**
   - Database sessions: `AsyncMock(spec=AsyncSession)`
   - External clients: `AsyncMock(spec=KeycloakAdmin)`
   - Model objects: `MagicMock(spec=Project)`

2. **Pydantic Schema Mocks - Consider `spec_set=True`:**
   - Only when strict validation is beneficial and you don't need to set attributes on the mock

3. **General Guidelines:**
   - Always use `spec=` for basic interface validation
   - Use `spec_set=True` sparingly - only when strict attribute validation adds significant value
   - Avoid `spec_set=True` for complex objects that need dynamic attribute assignment in tests

## Testing Infrastructure Location

**Check your specific app's `tests/` directory** for available utilities.

**`tests/dependency_overrides.py`** - Core override utilities:

- `runtime_dependency_overrides` - Context manager for block-level scoped overrides
- `override_dependencies` - Decorator for test-level overrides
- **App-specific override dictionaries** - pattern names vary by app

**`tests/conftest.py`** - Global test fixtures and configuration:

- Test client fixtures
- Database setup and teardown
- Global dependency overrides applied to all tests
- Shared test utilities and helpers

**`tests/factory.py`** - Test data factory functions (if it exists):

- Environment factories for complete test setups
- Entity factories for individual objects
- Domain-specific factories

**Always inspect your app's `tests/` directory** to understand available utilities and patterns. Use existing test files as examples rather than creating new patterns unnecessarily.
