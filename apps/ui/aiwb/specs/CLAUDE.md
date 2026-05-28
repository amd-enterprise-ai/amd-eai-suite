<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AIWB UI Frontend E2E Tests

Browser-based end-to-end tests for the AIWB UI application using Robot Framework + Browser Library (Playwright).

## Architecture

Three-layer structure keeps tests readable and maintainable:

- **Test suites** (`*.robot`) — BDD scenarios using Given/When/Then keywords. One file per feature area.
- **Feature resources** (`resources/*.resource`) — compose page interactions into business keywords with assertions. One file per feature area, matching the test suite.
- **Page resources** (`resources/pages/*.resource`) — selectors and atomic browser interactions only. No assertions, no business logic. One file per UI page/view.
- **Common resources** (`resources/common/`) — shared infrastructure: browser setup, Keycloak login, project navigation, UI endpoint resolution.
- **Libraries** (`libraries/`) — Python helpers (e.g., OIDC credential extraction from kubeconfig).

## Running Tests

```bash
cd apps/ui/aiwb/specs

# First time setup
uv sync --project ..
uv run --project .. rfbrowser init chromium

# Run all tests (excluding GPU-dependent ones)
uv run --project .. robot --argumentfile arguments.txt --exclude gpu .

# Run specific test file
uv run --project .. robot --argumentfile arguments.txt aim_versions.robot

# Run with specific tag
uv run --project .. robot --argumentfile arguments.txt --include deploy .

# Verbose output for debugging
uv run --project .. robot --argumentfile arguments.txt --loglevel TRACE .
```

## Pythonpath Resolution

The `arguments.txt` configures five pythonpath entries:

1. **`.`** — local specs directory (resources/, libraries/)
2. **`../../../api/aiwb/specs`** — AIWB API resources (aiwb_aims.resource for API-level preconditions)
3. **`../../../api/airm/specs`** — AIRM specs (airm_projects.resource, authorization, deployment)
4. **`../../../../testing`** — shared testing infrastructure (common.resource, resource lifecycle)
5. **`../../../../testing/libraries`** — shared Python libraries (KubeconfigAuth, TestPrefix)

## Browser Library Conventions

- Browser Library manages Playwright under the hood — no direct Playwright API usage
- `auto_closing_level=TEST` ensures browser context closes after each test
- Tracing is enabled by default; traces are saved on failure for debugging via [Playwright Trace Viewer](https://trace.playwright.dev/)
- Screenshots are captured automatically on test failure

## Tags

All tests are tagged `ui`. Additional tags follow these conventions (see `apps/CLAUDE.md` for the full tagging guide):

- **Resource tags** — `gpu`, `smoke` for hardware/speed classification
- **Feature tags** — match the feature area (e.g., `aims`, `workloads`, `secrets`, `chat`)
- **Operation tags** — match the action tested (e.g., `deploy`, `delete`, `create`)
