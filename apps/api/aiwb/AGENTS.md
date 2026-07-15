<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AI Development Rules for AIWB API

> **Note**: This file extends rules from parent directories. Read these files first:
>
> - `/AGENTS.md` - General repository rules (git, Jira, PRs)
> - `/apps/api/AGENTS.md` - FastAPI rules (async, Pydantic, transactions)

AIWB (AI Workbench) is a backend RESTful API that manages AIMs and AI Workloads.

## Data Architecture

AIWB is a **Kubernetes-first API**. Understand these rules:

1. **Kubernetes is the source of truth.** All live resource state (AIMs, Secrets, Namespaces) is fetched directly from the k8s cluster via the gateway layer. Do NOT store live state in the database.

2. **The database stores only persisted data.** Use PostgreSQL for audit logs, usage history, and metadata that Kubernetes does not track. When in doubt, fetch from k8s.

3. **Gateway is the primary data layer.** When implementing a new domain, use `gateway.py` to read/write k8s resources. Only add `repository.py` if you need to persist records.

4. **Do NOT duplicate k8s state in the database.** If a resource exists in Kubernetes, read it from there. Database synchronization creates stale data and bugs.

5. **Push filters to the K8s API.** Use `label_selector=` or `field_selector=` on the list call rather than fetching everything and filtering in Python. Server-side filtering keeps payload and parse cost proportional to what the caller actually needs — fetch-all-then-filter is a smell worth flagging in review. `rg 'label_selector|field_selector' apps/api/aiwb` for current usages. Python-side filtering is only justified for predicates K8s cannot express (e.g. `ownerReferences` walks, computed predicates over multiple fields). Server-side `field_selector` also requires the CRD to enable `selectableFields` for that field; when that's not the case the API rejects the selector and falling back to client-side filtering is correct.

6. **Backfill cross-field defaults at the schema boundary.** When a Pydantic field can be sourced from a sibling field as a fallback, use `model_validator(mode="after")` on the model to fill it in once — don't push the fallback (`x.foo or x.bar`) into every caller. The validator becomes the single source of truth for the field's effective value; consumers always read the canonical field. _(Paired FE rule in `apps/ui/aiwb/AGENTS.md` § Data Fetching & Forms: don't shadow this field with a computed wrapper at consumers — they should read the canonical field directly.)_

### Exception: Workloads Module

The `workloads` module is **legacy code** from AIRM. It uses heavy database storage instead of live k8s data. Do NOT use it as a reference for new implementations. This module is scheduled for removal.

## Architecture

Each domain module (e.g., aims, secrets, namespaces) contains:

| File            | Purpose                                         |
| --------------- | ----------------------------------------------- |
| `crds.py`       | Pydantic models for Kubernetes Custom Resources |
| `gateway.py`    | Data access layer for k8s (primary)             |
| `models.py`     | SQLAlchemy models for database (if needed)      |
| `repository.py` | Data access layer for database (if needed)      |
| `service.py`    | Business logic                                  |
| `router.py`     | HTTP interface                                  |
| `schemas.py`    | Request/response Pydantic models                |

### Data Flow

```
LIVE DATA (primary):     crds.py → gateway.py → service.py → router.py
PERSISTED DATA:          models.py → repository.py → service.py → router.py
```

Most domains use only the live data path.

### Layer Responsibilities

1. **Gateway (`gateway.py`)** - PRIMARY DATA LAYER
   - Fetches live data from Kubernetes
   - CRUD on Custom Resources: get, list, create, update, delete
   - **Returns:** CRD objects from `crds.py`
   - NO business logic

2. **Repository (`repository.py`)** - PERSISTED DATA ONLY
   - Reads/writes to PostgreSQL
   - Use ONLY for records that don't exist in k8s
   - **Returns:** SQLAlchemy models from `models.py`
   - Most domains will NOT need this

3. **Service (`service.py`)** - BUSINESS LOGIC
   - Validation, orchestration, error handling
   - Calls gateway and/or repository
   - **Returns:** CRD objects or models (may return schemas when convenient)
   - Raises `api_common.exceptions` (NotFoundException, ValidationException)
   - May use FastAPI types (Request, StreamingResponse)

4. **Router (`router.py`)** - HTTP INTERFACE
   - Converts service results to schema responses
   - Handles HTTP concerns
   - **Returns:** Schema objects (Pydantic response models)

## Common Commands

```bash
cd apps/api/aiwb
```

### Using Make (preferred)

```bash
make init      # First-time setup: sync deps, start docker
make run       # Run the application (or just `make`)
make test      # Run tests
make dc-up     # Start docker services
make dc-down   # Stop docker services
make reset     # Full reset: docker down, init, run
make ai-rules  # Generate CLAUDE.md symlinks and copilot-instructions.md
```

### Manual Commands

```bash
docker compose up -d    # Start PostgreSQL
uv run dev              # Run application
uv run pytest           # Run tests
```

Swagger UI: http://localhost:8000/docs

## Testing

| Layer      | Real DB | Mock K8s                 | Mock External |
| ---------- | ------- | ------------------------ | ------------- |
| Repository | ✅      | -                        | -             |
| Gateway    | -       | ✅ unit / ❌ integration | -             |
| Service    | ✅      | ✅                       | ✅            |
| Router     | ✅      | ✅                       | ✅            |

- **Always use real database** for repository tests
- **Mock Kubernetes client** for gateway unit tests
- **Never mock SQLAlchemy** - it masks integration issues

### Dependency Override Pattern

Router tests use centralized dependency overrides from `tests/dependency_overrides.py`:

**Override patterns** (use decorator):

```python
from tests.dependency_overrides import override_dependencies, BASE_OVERRIDES

@override_dependencies(BASE_OVERRIDES)
def test_get_aims():
    with patch("app.aims.router.list_aims") as mock:
        mock.return_value = [...]
        with TestClient(app) as client:
            response = client.get("/v1/aims")
```

Available patterns: `BASE_OVERRIDES`, `SESSION_OVERRIDES`, `CLUSTER_AUTH_OVERRIDES`

**Dynamic overrides** (for single-test customization):

```python
from app.dispatch.kube_client import get_kube_client

# Spread base overrides and customize one dependency
@override_dependencies({**BASE_OVERRIDES, get_kube_client: lambda: None})
def test_kube_client_missing():
    ...

# Or use context manager with fixture injection
from tests.dependency_overrides import runtime_dependency_overrides

def test_with_custom_client(mock_kube_client):
    with runtime_dependency_overrides({**BASE_OVERRIDES, get_kube_client: lambda: mock_kube_client}):
        with TestClient(app) as client:
            ...
```

If multiple tests need the same custom override, add a new pattern to `dependency_overrides.py`.

**Guidelines:**

- Import overrides at top of file (never inside test functions)
- Use decorator for static dependencies
- Use context manager when injecting fixtures

## Working with Kubernetes

### Verify K8s API behavior against a live cluster

When in doubt about how a K8s call behaves — `selectableFields` enablement on a CRD, whether a CEL validation rule fires for a given `spec.*` shape, URL-decode behavior on `/` in path segments, whether an annotation reaches the controller — `kubectl` against a live dev cluster and find out. Doc generations lag, CRD schemas vary across installations, and validation/admission rules ship independently of the controllers that consume them. Don't rely on doc memory for assumptions that affect production code.

### CRD field presence is not field honored

A field appearing in a CRD's OpenAPI schema only means the API server will accept it — not that any controller acts on it. Controllers select their reconcile path by annotation, label, spec shape, or installed version, so the same CRD can honor very different subsets of `spec` across installations — and backward-compat fields often linger in the schema long after the controller stops reading them. Before assuming a field has effect, trace the controller's dispatch path, or set the field on a live cluster and confirm it changes the resulting resource state.

## Quick Reference

When implementing a new domain module:

1. **Start with `gateway.py`** - fetch live data from k8s
2. **Add `crds.py`** - define Pydantic models for k8s resources
3. **Add `service.py`** - business logic
4. **Add `router.py`** - HTTP interface, returns schemas
5. **Add `repository.py` ONLY if needed** - for persisted data not in k8s

Remember:

- Kubernetes is the source of truth for live state
- Service returns models/CRDs, router returns schemas
- All I/O operations must be async
