<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# Claude Code Guide: E2E Tests

This document provides context and guidance for Claude Code when working with AIRM and Workbench E2E tests.

## ⚠️ CRITICAL: Never Read Test Output Files

**NEVER attempt to read Robot Framework output files directly**. These files are extremely large (often >100MB) and will consume excessive tokens and crash sessions.

**Files to NEVER read:**

- `results/output.xml`, `results/log.html`, `results/report.html`
- Any file in `results/` directory without explicit user confirmation

**Instead, use `robot-extract` command:**

The `robot-extract` tool is the **preferred method** for analyzing test failures. It allows querying specific test details from output.xml without loading the entire file.

**After each test run**, a helpful message automatically prints the recommended robot-extract commands based on whether tests passed or failed.

**Key principles:**

1. **Focus on one test at a time** - More details about one test is better than less details about many
2. **Use `--log-level trace`** to see all log messages, HTTP requests/responses, and variable values
3. **Use `--failed-keywords-only`** to focus on the failure path and reduce noise

**Recommended pattern:**

```bash
# Get detailed info about a specific failed test
robot-extract --name "Test Name Here" --log-level trace results/output.xml
```

**Log levels:** Use `--log-level trace` to see HTTP requests/responses, variable assignments, and keyword arguments.

**Other useful options:** `--failed` (list failures), `--failed-keywords-only` (focus on failure path), `--max-depth N` (limit nesting), `--output json`

**Other alternatives (if robot-extract unavailable):**

1. Ask the user to share specific error messages
2. Run specific tests to see failures in real-time

## Test Organization

Tests are organized into logical subdirectories:

- **`workbench/`** - AI/ML user-facing features (AIMs, datasets, models, workspaces, charts, finetuning)
- **`airm/`** - Infrastructure management (projects, quotas, secrets, storage, workloads, API keys)
- **Root level** - Special suites (aim_catalog.robot, health.robot, test_tracking.robot)

## Layered Architecture

The test framework uses a three-layer architecture:

1. **Test Files (.robot)** - Test cases with BDD-style Given-When-Then syntax
2. **Catalog Resources (catalog\_\*.resource)** - High-level business logic keywords
3. **API Resources (api/\*.resource)** - Low-level HTTP operations

**Key Principle**: Test files should NEVER call API resources directly. Always go through catalog resources.

### API Layer (resources/api/)

Low-level HTTP operations and endpoint construction.

**Key files:**

- `common.resource` - Safe HTTP wrappers, session management
- `aims.resource`, `projects.resource`, `datasets.resource`, `models.resource` - Feature-specific operations

**Characteristics:**

- Uses Safe HTTP request wrappers (not direct RequestsLibrary calls)
- Returns raw HTTP responses
- No business logic or validation

### Catalog Layer (resources/catalog\_\*.resource)

Business logic, validation, and test orchestration.

**Key files:**

- `catalog_aims.resource`, `catalog_projects.resource`, `catalog_keywords.resource`

**Characteristics:**

- Calls API resources for HTTP operations
- Performs response validation
- Implements business logic (wait for status, retry logic)
- Provides BDD-friendly keyword names

**Example:** See `workbench/aims.robot` (test cases) → `resources/catalog_aims.resource` (business logic) → `resources/api/aims.resource` (HTTP operations)

## Test Infrastructure

### Reuse Existing Keywords

**Always look for existing keywords before writing new ones.** The test framework provides comprehensive infrastructure for resource management, authentication, and test setup.

**When writing new tests:**

1. Find similar tests for reference
2. Search for existing keywords: `grep -r "keyword_name" resources/`
3. Reuse catalog-level keywords whenever possible
4. Only create new keywords if functionality truly doesn't exist

### Built-in Infrastructure Features

The test framework provides powerful infrastructure that handles common concerns automatically:

**1. Resource Tracking and Cleanup**

- Resources are automatically tracked when created
- Cleanup happens in teardown phases
- Use `The <resource_type>` keyword pattern to access tracked resources

**2. Authentication and Token Management**

- Automatic token refresh every 4 minutes for long test runs
- Session recreation when user permissions change
- Port forwarding validation and auto-recovery on connection failures

**3. Test Variable Communication**

- Keywords communicate through `TEST_*` variables
- Example: `Project "my-project" exists in system` sets:
  - `${TEST_PROJECT_ID}` - The project UUID
  - `${TEST_PROJECT_NAME}` - The project name
  - `${TEST_PROJECT_SLUG}` - The project slug
- Later keywords can reference these variables automatically

### The Resource Resolver Pattern

Use `The <resource_type>` to access tracked resources: `${workload_id}= The workload` gets ID from `${TEST_WORKLOAD_ID}` (set by previous keywords).

Works for any resource type (project, dataset, model, etc.). Validates the resource exists and provides clear errors if not created.

**Implementation:** `resources/common/resource_resolver.resource`

### Keyword Composition and Extension

Keywords build on each other: basic → extended → further extended. Use the most complete keyword that fits your needs.

**Example progression:** `Project "name" exists` → `A Ready Project With User Access Exists` → `A Ready Project With GPU Quota Exists`

**See:** `resources/airm_projects.resource` for the full hierarchy and implementation examples

### Token Refresh After Permission Changes

**CRITICAL:** After adding users to projects or changing permissions, call `Refresh kubectl and API tokens` because JWT group claims are embedded at authentication time.

**When to refresh:** After adding/removing users, changing roles/permissions.

**See:** `resources/airm_projects.resource` keyword `User is added to project` for implementation example

### Common Setup Patterns

Most tests use: `a project exists` (basic), `a ready project with user access exists` (most common), or `a ready project with GPU quota exists` (GPU tests).

**See examples:** `workbench/aims.robot`, `airm/projects.robot`

## Writing and Reviewing Tests

### Test Structure

**Use BDD pattern (Given-When-Then):** Given = setup, When = action, Then = verification. Each test must be completely independent.

**See examples:** Any test in `workbench/` or `airm/` directories

### Modern Syntax

**Use RF 5.0+ syntax:** `VAR` for variables, `IF/ELSE/END` for conditionals, `TRY/EXCEPT/FINALLY/END` for error handling.

**Avoid legacy:** `Set Variable`, `Run Keyword If`, `Run Keyword And Ignore Error`

**See examples:** Search for `VAR`, `IF`, `TRY` in any recent test file

### Common Anti-Patterns to Avoid

**❌ Don't use Sleep** - Use `Wait Until Keyword Succeeds` instead

**❌ Don't create test dependencies** - Each test must create its own data

**❌ Don't test implementation details** - Test via API, not database queries

**❌ Don't bypass layered architecture** - Tests call catalog layer, not API layer directly

**See good examples:** Look at any test in `workbench/aims.robot` or `airm/projects.robot`

### Test Data Management

**Each test creates and cleans up its own data.** Use test-scoped variables (`scope=TEST`), not suite variables.

**See:** `workbench/datasets.robot` for good data isolation examples

### Safe HTTP Request Wrappers

**Always use safe wrappers** (`Safe Get Request`, `Safe Post Request`, etc.) in resource files - they handle port forwarding failures automatically.

**Never use** direct RequestsLibrary calls (`Get On Session`, etc.).

**Implementation:** `resources/api/common.resource`

## Test Tags

Robot Framework tags enable filtering tests by functionality, speed, or resource requirements.

### General-Purpose Tags

| Tag       | Purpose                               | When to Use                                                      |
| --------- | ------------------------------------- | ---------------------------------------------------------------- |
| `smoke`   | Fast tests for quick validation       | Tests completing in <1 minute, no heavy resources                |
| `gpu`     | Tests requiring GPU resources         | Tests deploying GPU workloads (AIMs, finetuning, GPU workspaces) |
| `kubectl` | Tests using kubectl/helm verification | Tests interacting with Kubernetes resources directly             |

### Feature-Specific Tags

- `aims`, `projects`, `datasets`, `models`, `workload`, `workspace`
- `create`, `delete`, `list`, `get` (CRUD operations)
- `deploy`, `undeploy`, `status`, `lifecycle`

### Tagging Guidelines

Include feature tag + `smoke` (fast tests) + `gpu` (GPU workloads) + `kubectl` (k8s verification) as appropriate.

**See examples:** Any test in `workbench/` or `airm/` directories

## Running Tests

**IMPORTANT**: Always use `--argumentfile arguments.txt` when running tests.

All commands must be run from the `services/airm/specs` directory.

```bash
# All commands from services/airm/specs directory
cd services/airm/specs

# Quick validation (smoke only, no GPU)
uv run --project ../api/ robot --argumentfile arguments.txt --include smoke --exclude gpu .

# Run specific suite or test
uv run --project ../api/ robot --argumentfile arguments.txt workbench/aims.robot
uv run --project ../api/ robot --argumentfile arguments.txt --test "Test name" .

# Rerun failures
uv run --project ../api/ robot --argumentfile arguments.txt --rerunfailed results/output.xml .

# Tag filtering: --include aims, --include smokeANDprojects, --exclude gpu
```

## Best Practices

1. **Always use `--argumentfile arguments.txt`** when running tests
2. **Define keywords in `.resource` files, never in `.robot` files** - keeps test files readable and focused on test cases
3. **Always use safe HTTP request wrappers** in resource files
4. **Follow layered architecture** - tests → catalog → api
5. **Use modern syntax** - VAR, IF/ELSE/END, TRY/EXCEPT/FINALLY/END
6. **Ensure test independence** - each test creates its own data
7. **Reuse existing keywords** - search before creating new ones
8. **Add documentation** when creating new keywords
9. **Test in isolation** when debugging (run single suite/test)

## Common Debugging Commands

```bash
# View test logs with full debug
uv run --project ../api/ robot --argumentfile arguments.txt --loglevel TRACE workbench/aims.robot

# Run single test
uv run --project ../api/ robot --argumentfile arguments.txt --test "Deploy AIM successfully" .

# Check cluster connectivity
kubectl get pods -n airm
kubectl get svc -n airm

# Check port forwards
ps aux | grep "kubectl port-forward"
```

---

_This guide is maintained for Claude Code assistance. Human developers should refer to specs/README.md._
