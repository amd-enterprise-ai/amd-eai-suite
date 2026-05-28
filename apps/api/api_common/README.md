<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# API Common

Shared boilerplate code for AMD FastAPI services (e.g. **AIRM**, **AIWB**): database/session helpers, base models + schemas, auth helpers, and common domain exceptions/handlers.

## Install (from a sibling app)

```toml
[tool.uv.sources]
api_common = { path = "../api_common", editable = true }

[project]
dependencies = ["api_common", ...]
```

## What to import

- **Database**: `api_common.database` (`create_engine`, `session_scope`, `get_session`, `engine`, `session_maker`)
- **Models**: `api_common.models` (`BaseEntity`, audit fields helpers)
- **Schemas**: `api_common.schemas` (`ListResponse`, `BaseEntityPublic`, pagination helpers)
- **Exceptions**: `api_common.exceptions` (domain exceptions)
- **FastAPI handlers**: `api_common.fastapi` (exception handlers for `app.add_exception_handler(...)`)
- **Health router**: `api_common.health.router` (`GET /health`)
- **Auth**: `api_common.auth.security` (Keycloak/OpenID helpers)

Notes:

- Prefer **explicit imports** from submodules (no top-level re-exports).
- Kubernetes `ApiException` handling stays app-specific (e.g. AIWB).
