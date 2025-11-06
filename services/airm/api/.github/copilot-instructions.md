<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AI Development Rules for AIRM API

This document outlines the coding standards, architectural patterns, and development guidelines for the AIRM API service. These rules ensure consistency, maintainability, and quality across the codebase.

## Overview

This codebase is for the AMD Resource Manager (AIRM) API, a backend RESTful API service that manages AI resources like user groups, clusters, datasets, and workloads.

## Technology Stack

- **Python 3.13+** with asynchronous programming
- **FastAPI** for API framework
- **SQLAlchemy** for ORM with asyncio support
- **PostgreSQL** for database
- **Liquibase** for database migrations
- **Uvicorn** for ASGI server
- **Keycloak** for authentication/authorization
- **RabbitMQ** for messaging
- **Minio** for S3-compatible object storage
- **Docker/Docker Compose** for containerization

## Architecture

The codebase follows a modular architecture with domain-specific packages:

- Each domain module (e.g., users, organizations, clusters) typically contains:
  - `models.py` - Database models using SQLAlchemy
  - `repository.py` - Data access layer
  - `router.py` - API endpoint definitions
  - `schemas.py` - Request/response Pydantic models
  - `service.py` - Business logic
  - `utils.py` - Utility functions

- Cross-cutting concerns:
  - Authentication via OAuth2/Keycloak
  - Asynchronous messaging via RabbitMQ
  - Object storage via Minio

## Common Commands

### Setup and Running

```bash
# Copy environment variables template
cp .env.local .env

# Start supporting services (PostgreSQL, RabbitMQ, Minio, Keycloak)
docker compose up -d

# Run the application locally
uv run -m app
```

### Testing

```bash
# Run all tests in parallel (recommended default - faster execution)
uv run pytest -n auto

# Run tests for a specific module (single process for focused testing)
uv run pytest tests/users/

# Run with coverage
uv run pytest --cov=app -n auto

# Run tests with specific worker count
uv run pytest -n 2
```

#### Parallel Testing

The test suite supports parallel execution using pytest-xdist with database-per-worker isolation:

- **Database isolation**: Each worker process gets its own PostgreSQL database (`airm_test_gw0`, `airm_test_gw1`, etc.)
- **Automatic cleanup**: Worker databases are created/dropped automatically
- **Load balancing**: Tests are distributed using `loadscope` strategy (modules distributed across workers)
- **Default recommendation**: Use `-n auto` for optimal performance (automatically detects CPU cores)
- **Single process compatibility**: All existing tests continue to work without modification

**When to use different approaches:**

- **`-n auto`**: Default for full test suite runs (fastest, ~1-2 minutes)
- **Single process**: When debugging specific modules or tests
- **Manual worker count** (`-n 2`): For CI environments or when auto detection isn't optimal

**Automated cleanup**: Orphaned Docker containers are automatically cleaned up before tests start using process-based detection. Manual cleanup with `uv run python3 tests/cleanup_test_docker.py` is available if needed.

### Development Workflow

- Database migrations are managed in the `/migrations` directory using Liquibase
- Swagger UI is available at http://localhost:8001/docs when running locally
- RabbitMQ Management UI is accessible at http://localhost:15672
- Default development credentials are in the README.md and docker-compose.yaml

#### Issue Tracking and Naming Conventions

- **Jira**: Used for all internal work and project management. All development tasks should have corresponding Jira tickets
- **GitHub Issues**: Used for external issue tracking and open-source related discussions
- **Naming Convention**: When a Jira ticket exists, include the ticket ID as a prefix in:
  - Branch names: `<ticket-id>-<type>-<name>` (no slashes allowed) - Example: `SDA-2161-sync-python-docstrings`
  - Commit messages: `SDA-2161: Sync Python docstrings with implementation`
  - PR titles: `SDA-2161: Sync Python docstrings with implementation`

## Development Philosophy

### Code Change Approach

The approach to making code changes should balance maintainability with change scope. **Primary indicator: Listen to what the user is asking for** - if they ask to "simplify", "clean up", "refactor", or "improve" code, be comprehensive within that scope.

**Secondary indicators:** Check branch name, commit history, and current file changes to understand context.

1. **Files Already Modified in Current Branch:**
   - **Check with**: `git diff main...HEAD --name-only` to see what's already changed
   - **Be Bold**: Feel free to refactor, simplify, and improve code quality in files already being modified
   - **Consolidate Functions**: If functions can be simplified or combined, do so
   - **Clean Up**: Remove redundant code, improve naming, and enhance readability
   - **Don't Leave Ugly Code**: Prioritize maintainability over minimal changes in files you're already touching
   - **Rationale**: These files are already part of the PR scope, so additional improvements add value without expanding review scope

2. **New Files Being Created:**
   - **Write Clean Code**: Always write new code following best practices from the start
   - **Use Modern Patterns**: Apply current architectural patterns and conventions
   - **Don't Compromise**: New code should exemplify good practices, not inherit technical debt

3. **Untouched Files:**
   - **Be Conservative**: Avoid modifying files not related to the current feature
   - **Ask First**: If improvements in other files would benefit the feature, ask before making changes
   - **Focus**: Keep changes scoped to the current task unless explicitly asked to refactor

4. **Refactoring Branches:**
   - **Identify Scope**: Check branch name and commit history to understand if this is a refactoring-focused branch
   - **Be Comprehensive**: Apply changes consistently across the entire codebase, not just to files already modified
   - **Follow Patterns**: If refactoring a pattern (e.g., error handling, naming conventions), find and update ALL instances
   - **Use Search Tools**: Leverage grep/glob to find all occurrences of patterns being refactored
   - **Stay in Scope**: Only refactor what's specified in the task, but do it thoroughly across all relevant files
   - **Document Impact**: When making broad changes, explain the scope and reasoning

5. **Explicit Refactoring Tasks:**
   - **Follow the Scope**: When explicitly asked to refactor, clean up, or improve code quality, be thorough
   - **Question Broad Changes**: If refactoring would touch many files, confirm scope with the user first

## Best Practices

### Layer Responsibilities

1. **Repository Layer:**
   - Should focus on data access operations only
   - Should NOT contain business logic beyond basic CRUD operations
   - Should NOT raise HTTP exceptions or implement validation logic
   - Should use SQLAlchemy queries and handle database-specific errors

2. **Service Layer:**
   - Should implement all business logic and validation rules
   - Should NOT raise HTTP exceptions directly - instead raise domain-specific exceptions
   - Should orchestrate repository calls and handle transaction boundaries
   - Should be independent of the API framework (FastAPI)

3. **API Layer (Routers):**
   - Should handle HTTP concerns (status codes, responses, etc.)
   - Should map domain exceptions to appropriate HTTP responses, preferring FastAPI's exception handlers over try/except blocks
   - Should validate input data using Pydantic models
   - Should manage dependency injection and request/response formatting

### FastAPI-Specific Best Practices

#### Async/Await Usage

- **Prefer `async` for I/O operations**: Database calls, external API requests, file operations
- **Use `sync` functions for CPU-intensive tasks**: Heavy calculations, data processing (FastAPI runs these in threadpool)
- **Never mix blocking I/O in async functions**: Avoid `time.sleep()`, sync database calls in async routes
- **Example**: Use `await asyncio.sleep()` instead of `time.sleep()` in async functions

#### Dependencies and Dependency Injection

- **Use dependencies for validation beyond Pydantic**: Database constraint checks, complex business rules
- **Chain dependencies for reusability**: Break complex validation into smaller, composable functions
- **Prefer `async` dependencies**: Avoid unnecessary threadpool overhead for simple non-I/O operations
- **Example**: Use dependencies to validate entity existence, ownership, and permissions

#### Pydantic Configuration

- **Use custom base models for consistency**: Standardize datetime formatting, add common methods
- **Decouple settings by domain**: Split BaseSettings into module-specific configs rather than one monolithic config
- **Leverage Pydantic validators**: Use built-in validators for emails, URLs, enums, and custom business rules

#### Configuration Management

- **Split configuration by module**: Each domain should have its own config class inheriting from BaseSettings
- **Example**: `messaging/config.py` for messaging-specific settings, separate from global app config
- **Use environment-specific defaults**: Provide sensible defaults while allowing environment overrides

### Error Handling

- **Domain exceptions**: Defined in `app/utilities/exceptions.py` (inherit from `BaseAirmException` or appropriate subclass)
- **HTTP mapping**: FastAPI exception handlers in `app/utilities/fastapi.py` automatically map domain exceptions to appropriate HTTP responses
- **Service layers**: Raise domain-specific exceptions, never HTTP exceptions
- **API layers**: Let FastAPI exception handlers manage HTTP responses rather than try/catch blocks

### Transaction Handling

1. **API Layer (Routers) Should Manage Transactions:**
   - API endpoints using `Depends(get_session)` get a session with transaction handling via `session_scope()`
   - The transaction lifecycle (begin, commit on success, rollback on error, close) is managed by the API layer

2. **Service/Repository Layer Should Be Transaction-Agnostic:**
   - These layers should receive an active `AsyncSession` from the API layer
   - They should NOT call `session.commit()` or `session.rollback()` themselves
   - Use `session.flush()` when needed to get generated IDs or enforce constraints
   - Let exceptions propagate up to the API layer's transaction handler

3. **Examples of Good Practice:**
   - In `app/utilities/database.py`, the `session_scope()` context manager properly handles transactions
   - In `tests/datasets/test_repository.py`, there are good examples of testing transaction safety

### Database Conventions

1. **Organization Scoping:**
   - **Always scope SQL queries with organization_id when possible** for security and performance
   - This ensures proper data isolation between organizations and improves query performance
   - Add organization_id filters to WHERE clauses and JOIN conditions where applicable

2. **Constraint Naming:**
   - Use consistent naming patterns for database constraints and indexes
   - Follow the format: `{table_name}_{column(s)}_{type}_key`
   - Examples: `datasets_name_cluster_id_key`, `overlays_chart_id_canonical_name_key`
   - Use case-insensitive constraints where appropriate with `lower(field::text)` in the index definition

3. **Unique Constraints:**
   - When implementing unique constraints across multiple tables, use consistent naming
   - For case-insensitive unique constraints, use the SQL function `lower()` in the index definition
   - Add appropriate error handling in repositories to catch and translate constraint violations

4. **SQL-First Approach:**
   - **Prefer database operations over Python processing**: Use SQL for joins, aggregations, and data transformations
   - **Aggregate data in SQL**: Build JSON objects and arrays in queries rather than in Python
   - **Use database functions**: Leverage `func.json_build_object()`, `func.coalesce()`, and other SQL functions for efficient data processing

5. **Transaction Handling:**
   - **Production uses automatic transaction management** via `session_scope()` context manager in API layer
   - **Tests mirror production behavior** with `test_session_scope()` providing automated commit/rollback
   - **No manual rollback needed** in constraint violation tests - handled automatically by test infrastructure
   - **Each test gets clean transaction boundaries** ensuring proper isolation and state management

### Schema Naming Conventions

To avoid naming conflicts between SQLAlchemy models and Pydantic schemas, follow these consistent naming patterns:

1. **API Response Schemas:**
   - Use `{Entity}Response` suffix for schemas returned by API endpoints
   - Examples: `UserResponse`, `ProjectResponse`, `ClusterResponse`
   - These represent the complete data structure returned to clients

2. **Input Schemas:**
   - Use `{Entity}In` for schemas where create and update validation are identical
   - Use `{Entity}Create` and `{Entity}Edit` when different validation rules apply
   - Examples: `UserCreate`, `ProjectEdit`, `ClusterIn`

3. **Naming Conflicts Resolution:**
   - SQLAlchemy models use simple names: `User`, `Project`, `Cluster`
   - Pydantic schemas use descriptive suffixes to avoid conflicts
   - This eliminates the need for import aliases that obscure code meaning

4. **Import Organization:**
   - Import models and schemas directly without aliases when names don't conflict
   - Avoid aliases like `from app.users.schemas import User as UserSchema`
   - Clear naming conventions make code more readable and maintainable

**Example Implementation:**

```python
# models.py
class User(Base):
    __tablename__ = "users"
    # ... model definition

# schemas.py
class UserResponse(BaseModel):
    # Schema for API responses

class UserCreate(BaseModel):
    # Schema for user creation

# router.py
from app.users.models import User
from app.users.schemas import UserResponse, UserCreate

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    # No naming conflicts, clear imports
```

This approach ensures code clarity while maintaining clean separation between database models and API schemas.

### Testing Strategy by Layer

1. **Repository Layer Tests:**
   - **Always use real database** with `db_session` fixture for data access testing
   - **Never mock SQLAlchemy operations** - this masks integration issues and constraint violations
   - **Test database constraints** including unique constraints, foreign keys, and check constraints
   - **Verify transaction behavior** including rollbacks and constraint enforcement
   - **Use centralized test data factories** from `tests/factory.py` for consistent test data

2. **Service Layer Tests:**
   - **Use real database** for repository operations and business logic testing
   - **Mock external services only** - Keycloak, email services, S3/Minio, RabbitMQ, etc.
   - **Focus on business logic** rather than mock coordination
   - **Test error propagation** from repository to service layer with real constraints
   - **Verify transaction boundaries** and proper exception handling

   **Advanced Pattern - Service Boundary Mocking:**
   - **Mock service function calls but return real database objects** for optimal unit test isolation
   - **Example**: Mock `insert_workload()` but return actual `ManagedWorkload` created with factories
   - **Benefits**: Isolates unit tests from other service bugs while maintaining real SQLAlchemy behavior
   - **Use case**: Complex services that call multiple other services (e.g., workspace service calling managed_workloads service)

   ```python
   # Good: Mock service boundary but return real DB object
   with patch("app.workspaces.service.insert_workload") as mock_insert:
       real_workload = await create_chart_workload(db_session, project=project, ...)
       mock_insert.return_value = real_workload
       # Now session.refresh(workload) works naturally
   ```

3. **API Layer Tests:**
   - **Integration tests** with real database and mocked external services
   - **Mock external dependencies** but keep database operations real
   - **Test request/response handling** and HTTP status codes
   - **Verify dependency injection** and authentication/authorization

### When to Use Real Database vs Mocking

**✅ Use Real Database When:**

- Testing repository layer (always)
- Testing service layer business logic
- Testing database constraints and relationships
- Testing transaction rollback scenarios
- Testing data integrity and consistency
- Testing complex queries and aggregations

**✅ Use Mocking When:**

- Testing external service integrations (Keycloak, email, S3)
- Testing error scenarios where external services fail
- Testing API layer HTTP concerns without business logic
- Testing pure business logic without data persistence
- Performance testing where database setup is overhead
- **Service boundary isolation**: Mock service calls but return real DB objects for unit test isolation

**❌ Avoid Mocking:**

- SQLAlchemy session operations in repository/service tests
- Database constraints and validation logic
- Transaction management behavior
- Query result processing and data transformation
- **Inconsistent mocking**: Don't mock service calls and then mock session operations to fix the resulting issues

### Test Data Factories

**Philosophy:** Centralized, reusable factory functions provide consistent test data and reduce maintenance overhead when models change.

**Factory Hierarchy:**

- **Environment Factories:** `create_basic_test_environment()`, `create_full_test_environment()`, `create_multi_organization_environment()`
- **Entity Factories:** `create_organization()`, `create_user()`, `create_project()`, etc.
- **Workload Factories:** `create_workload()`, `create_chart_workload()`, `create_aim_workload()`

**Benefits:**

- **Consistency:** All tests use the same data patterns and relationships
- **Maintainability:** Single point of change when models evolve
- **Readability:** Tests focus on business logic rather than data setup
- **Reliability:** Factory-created data respects all constraints and relationships

**Usage Guidelines:**

- **Prefer factories over inline object creation** in all repository and service tests
- **Use environment factories** for standard test scenarios (organization → cluster → project)
- **Use individual factories** for specific entity testing
- **Combine factories** for complex multi-entity scenarios

### Test Coverage Requirements

**Critical Test Categories:**

- **Happy path scenarios** - core functionality working as expected
- **Error handling** - external service failures, constraint violations, invalid input
- **Edge cases** - empty results, boundary conditions, null values
- **Security scenarios** - cross-organization access, permission boundaries
- **Transaction safety** - rollback behavior, constraint enforcement

**Layer-Specific Coverage:**

- **Repository:** CRUD operations, constraints, query logic, transaction handling
- **Service:** Business rules, error handling, external service integration, validation
- **API:** HTTP handling, authentication, request/response formatting, dependency injection

### Mock Specification Best Practices

**External Service Mocking:**

- **Use `spec=` parameter** to catch interface mismatches: `AsyncMock(spec=KeycloakAdmin)`
- **Mock return values realistically** to match actual service responses
- **Test both success and failure scenarios** for external service calls
- **Verify mock interactions** to ensure correct service integration

**Database Session Mocking (Limited Use):**

- **Only for pure business logic tests** where database interaction is not the focus
- **Always use `AsyncMock(spec=AsyncSession)`** for interface validation
- **Verify transaction calls** (commit/rollback) when mocking sessions
- **Prefer real database over mocking** in most cases for better integration testing

**Detailed Mock Guidelines:**

Use the `spec` parameter with mock objects to improve test reliability and catch interface mismatches early:

1. **Simple Interface Mocks - Use `spec=` (not `spec_set=True`):**
   - **Database sessions**: `AsyncMock(spec=AsyncSession)` - complex interfaces that need flexibility
   - **External clients**: `AsyncMock(spec=KeycloakAdmin)` - complex third-party interfaces
   - **Model objects**: `MagicMock(spec=Project)` - when tests need to set attributes dynamically

2. **Pydantic Schema Mocks - Consider `spec_set=True`:**
   - **Simple data models**: `Mock(spec=UserSchema, spec_set=True)` - when strict validation is beneficial
   - **Only use when you don't need to set attributes on the mock**

3. **General Guidelines:**
   - **Always use `spec=` for basic interface validation** - catches typos in method names
   - **Use `spec_set=True` sparingly** - only when strict attribute validation adds significant value
   - **Avoid `spec_set=True` for complex objects** that need dynamic attribute assignment in tests
   - **Mock return values can remain generic** unless they represent specific interfaces

**Example:**

```python
# Good - provides interface validation without being overly restrictive
session = AsyncMock(spec=AsyncSession)
kc_admin = AsyncMock(spec=KeycloakAdmin)
project = MagicMock(spec=Project)

# Use with caution - only when strict validation is needed
user_schema = Mock(spec=UserSchema, spec_set=True)  # Only if no attribute assignment needed
```

### Global Variables and Resource Management

- **Minimize globals**: Constants are fine. For shared, stateful resources like clients, use framework-managed state (e.g., in FastAPI) and dependency injection
- **Avoid mutable global variables** that are modified from various parts of the application
- Use FastAPI's dependency injection system to manage shared resources like database sessions, external clients, and configuration
- **External service clients**: Store in `app.state` and access via dependencies (see `utilities/minio.py` for Minio client example)
- **Prefer dependency injection over global imports**: This improves testability and follows FastAPI patterns

### Code Comments and Documentation

**Core Principles:**

- **Explain "why" not "what"** - comments should provide reasoning, context, or non-obvious constraints
- **Write for future maintainers** - assume readers understand the language but not the business logic
- **Never document past changes** - use git history for change tracking, comments should reflect current state

**When to Comment:**

- **Business rules and constraints** that aren't obvious from code structure
- **Complex algorithms or calculations** where the approach isn't immediately clear
- **Non-obvious workarounds** for API limitations or external service quirks
- **Important assumptions** about data state or system behavior
- **Security considerations** or permission boundaries

**What NOT to Comment:**

- **Obvious operations** - don't restate what function calls clearly show
- **Code structure** - well-named functions and variables should be self-documenting
- **Repetitive patterns** - avoid duplicating the same comment across similar functions
- **Implementation details** that are clear from reading the code

**Test File Comments:**

- **Test docstrings** should explain the scenario being tested, not just restate the function name
- **Setup comments** should explain WHY specific test data is needed, not just what's being created
- **Assertion comments** should clarify non-obvious expectations or business rules
- **Avoid factory setup comments** - `factory.create_user()` is self-explanatory

**Maintenance:**

- **Update comments when code changes** - outdated comments are worse than no comments
- **Remove rather than fix** unclear comments - if a comment needs explanation, the code probably needs improvement
- **Review comment necessity** during refactoring - code improvements often eliminate the need for explanatory comments

### Import Organization

- **Place all imports at the top of the file** - avoid embedded imports inside functions unless absolutely necessary for circular import resolution
- Group imports logically: standard library, third-party packages, then local application imports
- **Avoid embedded imports**: Don't place `from .repository import function` inside function bodies without a compelling reason (like circular imports)
- **Avoid import aliases unless absolutely necessary**: Import aliases make code harder to understand and can create naming conflicts. Prefer explicit imports or reorganizing code structure over aliases.
  - **Good**: `from tests import factory` then `factory.create_user()`
  - **Bad**: `from app.users.repository import create_user as repo_create_user`
  - **Exception**: Only use aliases when there are genuine naming conflicts that cannot be resolved by module organization
- If you must use embedded imports for circular import resolution, add a comment explaining why

### API Documentation Best Practices

- **Use comprehensive endpoint documentation**: Include `response_model`, `status_code`, `description`, `summary`, and `tags`
- **Document different response scenarios**: Use the `responses` parameter to document various status codes and their models
- **Environment-specific documentation**: Hide docs in production environments, show only in development/staging

#### Endpoint Descriptions for MCP Integration

Endpoint descriptions should be optimized for both human developers and LLM consumption via MCP. Keep descriptions concise but contextually rich:

**Include for LLM understanding:**

- **Business domain context** - What the resource/operation represents in the AI/ML domain
- **Prerequisites and constraints** - Authorization requirements, resource limits, validation rules
- **Key relationships** - How this endpoint relates to other resources (clusters, projects, etc.)
- **Authorization semantics** - Role-based access patterns and membership requirements

**Avoid verbose content:**

- Detailed code examples or YAML snippets (use schema examples instead)
- Step-by-step workflows (LLMs can reason through multi-step processes)
- UI-specific guidance ("populate dropdowns", "display in dashboards")
- "Response includes" sections (redundant with response models)

This approach provides LLMs with semantic context to make informed API calls while keeping documentation clean for human users.

## Important Notes

- The application uses asynchronous programming extensively with asyncio
- Authentication is handled via OAuth2 with Keycloak integration
- **Database transactions are handled at the route level** - lower-level code (services/repositories) should focus on business logic and let exceptions propagate for automatic rollback
- **External resource cleanup**: When working with external resources (S3, Keycloak, RabbitMQ), implement proper cleanup/compensation logic since these are not covered by database transactions
- New modules should follow the existing structure pattern
- Tests use async fixtures and pytest-asyncio

## GitHub PR Review Management

For detailed GitHub CLI commands for managing PR reviews, see [GitHub PR Management Guide](../../../docs/internal-docs/guidelines/github-pr-management.md).
