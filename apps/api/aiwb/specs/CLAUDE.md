<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# Claude Code Guide: AIWB E2E Tests

This document provides context and guidance for Claude Code when working with AI Workbench (AIWB) E2E tests.

## AIRM Dependency

AIWB (AI Workbench) depends on AIRM (AI Resource Manager). AIRM manages infrastructure — projects, clusters, quotas, authentication, and workloads. AIWB builds on top of AIRM to provide the AI/ML user experience (AIMs, datasets, models, workspaces).

AIWB E2E tests reuse AIRM's test infrastructure for all infrastructure operations. When writing AIWB tests, you use AIRM keywords for project setup, authentication, workload management, and HTTP request handling. AIWB-specific keywords only cover AI/ML features.

**For complete test infrastructure documentation, see: `../../airm/specs/CLAUDE.md`**

That guide covers: layered test architecture, resource tracking/cleanup, token refresh after permission changes, safe HTTP request wrappers, and common anti-patterns.

## Resource Resolution

`arguments.txt` configures two pythonpaths, searched in order:

1. `.` — local AIWB specs (`apps/api/aiwb/specs/`)
2. `../../airm/specs` — shared AIRM specs

When a test imports `Resource resources/foo.resource`, Robot Framework searches both paths. Local AIWB files take precedence. There are no file name overlaps between AIWB and AIRM resources by design — AIRM infrastructure resources use `airm_` prefixes and generic names, while AIWB resources use feature-specific names.

**AIRM shared resources** (resolved via pythonpath): `airm_projects.resource` for project/quota setup, `api/common.resource` for safe HTTP wrappers, `authorization.resource` for OIDC auth, `deployment.resource` for endpoint resolution, and others. Search with `grep -r "keyword" ../../airm/specs/resources/`.

**AIWB-specific resources** (local): `aiwb_*.resource` files for business logic (aims, charts, datasets, models, workspaces), `api/*.resource` for HTTP operations, and `aims/api_keys.resource` for AIMS API key management. List with `ls resources/`.

**Generic test infrastructure** (resolved via `../../../../testing` on pythonpath): `resources/resource_tracking.resource` provides `Track * For Cleanup` and `Clean Up All Tracked Resources` keywords. These are shared across all apps. AIWB resources import this for lazy-initialized resource tracking -- no `Initialize * Tracking` calls needed.

## Suite Setup

`__init__.robot` provides a suite-level setup that runs before all test suites:

- Validates kubectl OIDC configuration
- Verifies AIWB service health with retry

Individual `.robot` files do **not** need their own suite setup for health checks.

## Test Suites

Test suites cover AIMs, API keys, charts, datasets, finetuning, models, workspaces, and AIM catalog testing. Each feature has its own `.robot` file. List with `ls *.robot`.

## Test Setup Patterns

Every test must explicitly state its infrastructure preconditions — never hide project setup inside other keywords.

```robot
*** Test Cases ***
# Non-GPU test
My AIWB Test
    Given a ready project with user access exists
    When <perform AIWB operation>
    Then <verify result>

# GPU test (AIM deployment, workspaces, etc.)
My GPU Test
    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    When <perform GPU operation>
    Then <verify result>
```

## Running Tests

**IMPORTANT**: Always use `--argumentfile arguments.txt` when running tests.

All commands must be run from the `apps/api/aiwb/specs` directory.

```bash
cd apps/api/aiwb/specs

# Quick validation (smoke only, no GPU)
uv run --project .. robot --argumentfile arguments.txt --include smoke --exclude gpu .

# Run specific suite or test
uv run --project .. robot --argumentfile arguments.txt aims.robot
uv run --project .. robot --argumentfile arguments.txt --test "Deploy AIM successfully" .

# Rerun failures
uv run --project .. robot --argumentfile arguments.txt --rerunfailed results/output.xml .
```

**Note the difference from AIRM:**

- AIWB: `uv run --project ..` (pyproject.toml is one level up)
- AIRM: `uv run --project ../api` (pyproject.toml is in api/ subdirectory)

## Test Concurrency

AIWB E2E tests use prefixed resource names to allow concurrent execution. See `services/airm/specs/CLAUDE.md` "Test Concurrency" section for details on the `TestPrefix` library and prefix resolution.

## AIM Catalog Testing

The `aim_catalog.robot` suite uses dynamic test generation via `libraries/AimCatalogGenerator.py`.

**Model Discovery:** Models are auto-discovered from the cluster API (`GET /v1/inference/models`), filtered to `Ready` status, and deduplicated by `image_name` (keeping the highest version). Authentication uses the OIDC token from kubectl (override with `AIWB_API_TOKEN` env var). The API URL resolves from `${AIM_CATALOG_API_URL}` → `${AIWB_BASE_URL}` → `AIWB_API_URL` env var → cluster Gateway auto-discovery. To test only a subset, create a text file with one model name per line and pass `--variable AIM_CATALOG_FILTER:config/aim_models.txt`.

**Tag Filtering:** Use variables in `arguments.txt`:

- `INCLUDE_TAGS:model:aim-name` — test specific model
- `INCLUDE_TAGS:gpus:1` — only 1-GPU models
- `INCLUDE_TAGS:version:0.8.5` — only tests for version 0.8.5
- `EXCLUDE_TAGS:requires-hf-token` — skip models needing `HF_TOKEN`

**Version Filtering:** Use `AIM_VERSION` to filter models before test generation:

- `AIM_VERSION:0.8.5` — exact version match
- `AIM_VERSION:>=0.9.0` — minimum version (also supports `>`, `<=`, `<`)
- `AIM_VERSION:latest` — keep only the latest version per model (default behavior)

## Writing and Reviewing Tests

### Layered Architecture

The test framework uses three layers:

1. **Test files (.robot)** — BDD-style Given-When-Then test cases
2. **AIWB resources (aiwb\_\*.resource)** — High-level business logic keywords
3. **API resources (api/\*.resource)** — Low-level HTTP operations

Test files should NEVER call API resources directly. Always go through AIWB resources.

### BDD Pattern

Structure all tests with Given-When-Then. Given = preconditions, When = action, Then = verification. Each test must be completely independent.

### Modern Syntax

Use RF 5.0+ syntax: `VAR` for variables, `IF/ELSE/END` for conditionals, `TRY/EXCEPT/FINALLY/END` for error handling. Avoid legacy `Set Variable`, `Run Keyword If`, `Run Keyword And Ignore Error`.

### Anti-Patterns

- **Don't use Sleep** — use `Wait Until Keyword Succeeds` instead
- **Don't create test dependencies** — each test creates its own data
- **Don't hide infrastructure preconditions** — project setup, GPU quota must be visible at test level
- **Don't bypass layered architecture** — tests call AIWB layer, not API layer directly
- **Don't define keywords in .robot files** — keep them in `.resource` files

### Safe HTTP Request Wrappers

Always use safe wrappers (`Safe Get Request`, `Safe Post Request`, etc.) in resource files — they handle port forwarding failures and SSL verification automatically. Never use direct RequestsLibrary calls (`Get On Session`, etc.). Implementation: `resources/api/common.resource` (from AIRM). For direct HTTP calls (e.g., multipart uploads), add `verify=${VERIFY_SSL}` explicitly. See `testing/CLAUDE.md` for SSL verification details.

### Test Variable Communication

Keywords communicate through `TEST_*` variables. Example: `A ready project with user access exists` sets `${TEST_PROJECT_ID}` and `${TEST_PROJECT}` (full dict). Access attributes via `${TEST_PROJECT}[name]`. Later keywords reference these automatically.

**API-layer keywords must not access `TEST_*` variables.** Business-logic keywords (`aiwb_*.resource`) resolve values from test state and pass them as explicit arguments to API keywords. See AIRM CLAUDE.md for the full layered architecture rules.

**Namespace access:** Business-logic keywords must use `Get Project Namespace` to resolve the namespace and pass it explicitly to API-layer keywords. API-layer keywords must not default to `${TEST_PROJECT}[name]`.

### Token Refresh After Permission Changes

**CRITICAL:** After adding users to projects or changing permissions, call `Refresh kubectl and API tokens` — JWT group claims are embedded at authentication time. The `A ready project with user access exists` keyword handles this automatically.

### Reuse Existing Keywords

Always search for existing keywords before writing new ones:

1. Find similar tests for reference
2. Search: `grep -r "keyword_name" resources/`
3. Reuse AIWB-level keywords whenever possible

### Tags

| Tag       | When to Use                                                      |
| --------- | ---------------------------------------------------------------- |
| `smoke`   | Fast tests (<1 min), no heavy resources                          |
| `gpu`     | Tests deploying GPU workloads (AIMs, finetuning, GPU workspaces) |
| `kubectl` | Tests interacting with Kubernetes resources directly             |

Feature tags: `aims`, `datasets`, `models`, `workspace`, `api-keys`, `namespaces`, `health`, `cross-service`. Operation tags: `create`, `delete`, `list`, `deploy`.

## Never Read Test Output Files

**NEVER** read Robot Framework output files directly (`results/output.xml`, `results/log.html`). They are extremely large and will crash sessions. Use `robot-extract` instead:

```bash
robot-extract --name "Test Name Here" --log-level trace results/output.xml
```

## Common Debugging

```bash
# View test logs with full debug
uv run --project .. robot --argumentfile arguments.txt --loglevel TRACE aims.robot

# Run single test
uv run --project .. robot --argumentfile arguments.txt --test "Deploy AIM successfully" .

# Check workbench service
kubectl get pods -n airm | grep workbench
kubectl logs -n airm deployment/aiwb-api
```

---

_This guide is maintained for Claude Code assistance. Human developers should refer to specs/README.md._
