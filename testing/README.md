<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# Shared Testing Infrastructure

This document introduces the key concepts behind our E2E testing infrastructure. It covers how test suites are structured, how concurrent execution works, and how resources flow through a test.

For app-specific details -- how to run tests, available commands, which test suites exist, and what tags are available -- see the `CLAUDE.md` file in each app's `specs/` directory. Those files also contain the full test writing and review guidelines.

## Writing and Maintaining Tests

The recommended way to write, maintain, and debug E2E tests is with AI assistance using Redflame. The `CLAUDE.md` files in each app's `specs/` directory contain comprehensive instructions that the AI follows for test writing, keyword design, and code review. When using AI for test work, these instructions are loaded automatically.

## How Apps Use This

Each app has a `specs/` directory with its test suites. Apps live under `apps/` in the repository (e.g., `apps/api/aiwb/specs/`), though some services under `services/` also have their own test suites. Each app's `arguments.txt` adds this `testing/` directory and the app's own specs to Robot Framework's pythonpath:

```
--pythonpath .                             # App's own specs
--pythonpath <relative>/testing            # Shared resources
--pythonpath <relative>/testing/libraries  # Shared Python libraries
```

When an app's tests depend on another app (e.g., to create prerequisite infrastructure), it adds that app's specs directory to the pythonpath too. File names are prefixed by app (e.g., `appname_projects.resource`) to avoid ambiguity. Robot Framework resolves imports in path order, so local resources take precedence.

## Three Layers

Test suites follow a strict three-layer architecture:

- **Test layer** (`.robot` files) -- BDD Given-When-Then test cases. Only calls the business logic layer.
- **Business logic layer** (`appname_*.resource` files) -- high-level keywords that compose operations, track resources, and set test variables. Calls the API layer.
- **API layer** (`api/*.resource` files) -- low-level HTTP operations using safe request wrappers that handle authentication and connectivity.

## Concurrent Test Execution

Multiple developers and CI runners execute tests against the same cluster simultaneously. The `TestPrefix` library makes this work by generating a unique per-runner prefix that gets embedded in every resource name.

**Prefix resolution (all start with `e2e-`):**

| Priority | Source                                | Example        |
| -------- | ------------------------------------- | -------------- |
| 1        | `E2E_TEST_PREFIX` env var             | `e2e-{value}-` |
| 2        | `GITHUB_RUN_ID` / `CI_RUN_ID` env var | `e2e-ci{id}-`  |
| 3        | OS username (default)                 | `e2e-jdoe-`    |

The `Test Name` keyword combines the prefix with a suffix and sanitizes it for Kubernetes (lowercase, alphanumeric and hyphens, max 63 chars). The prefix is resolved once per session and cached. Locally it uses your OS username automatically; in CI you override it via the `E2E_TEST_PREFIX` environment variable.

### What Can Run in Parallel

- **Different developers** -- always safe. Each gets a unique prefix from their username.
- **Different suites by the same developer** -- generally safe. Each suite uses distinct resource name suffixes by default, so names don't collide even with the same prefix.
- **Same suite twice by the same developer** -- not safe. Both runs produce identical resource names, causing conflicts. Override with `E2E_TEST_PREFIX` to differentiate.

### Limitations

Names may be truncated at 63 characters. If a run crashes before teardown, prefixed resources stay in the cluster and need manual cleanup since cleanup relies on tracking lists, not prefix matching.

## Resource Lifecycle

This is how a resource flows through a test -- from naming to cleanup:

1. **Naming** -- `Test Name` generates a prefixed name (e.g., `e2e-jdoe-my-project`).
2. **Creation** -- A business logic keyword creates the resource via the API and stores identifiers in test-scoped `TEST_*` variables (e.g., `${TEST_PROJECT_ID}`, `${TEST_PROJECT_NAME}`).
3. **Reference** -- Subsequent keywords retrieve the current resource using `The ${resource_type}` resolver (e.g., `The project` returns `${TEST_PROJECT_ID}`). This avoids passing IDs around explicitly.
4. **Cleanup** -- Suite teardown deletes tracked resources. Track the **widest-scope resource** that cascades to its children -- deleting a project removes its workloads, secrets, and namespaces, so there's no need to track those individually.

```robot
# Test case -- the test just declares intent
Given project "my-project" exists in system    # Steps 1-2: names, creates, stores ID
Then project should be ready                   # Step 3: resolves ID, verifies status

# Behind the scenes in business logic keywords
Project "${name}" exists in system
    ${prefixed}=    Test Name    ${name}             # e2e-jdoe-my-project
    ${response}=    Create project    ${prefixed}     # API call
    Set Test Variable    ${TEST_PROJECT_ID}    ${response.json()['id']}

Project should be ready
    ${id}=    The project                             # Resolves ${TEST_PROJECT_ID}
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify project status    ${id}    Ready
```

## Test Results and Debugging

Robot Framework produces three output files after each run:

- `output.xml` -- machine-readable results with full execution details
- `log.html` -- detailed step-by-step execution log, viewable in a browser
- `report.html` -- high-level summary with pass/fail statistics

These files can exceed 100MB for large test suites. To query specific tests or failures from `output.xml` without loading the entire file, use the `robot-extract` CLI tool.

The recommended way to debug test failures is with AI assistance using Redflame, which includes specialized skills and tools for test result analysis, failure diagnosis, and manual verification against live clusters.

## Frontend E2E Tests

Frontend end-to-end tests use [Robot Framework](https://robotframework.org/) with
[Browser Library](https://robotframework-browser.org/), which manages
[Playwright](https://playwright.dev/) under the hood. Tests run headless Chromium
against a live environment and verify UI behavior through browser automation.

### Debugging Failures

Tests automatically capture diagnostics on failure:

- **Screenshots** are taken when a test fails, saved to `results/`.
- **Playwright traces** are recorded for every test. Trace files (`.zip`) are saved
  to `results/browser/traces/` and capture DOM snapshots, network requests, and
  console logs at each step.

To inspect a trace locally:

```bash
npx playwright show-trace results/browser/traces/trace_context=<id>.zip
```

This opens an interactive timeline — no external services needed.

## Authentication

Tests run against the Kubernetes cluster of the current kubectl context. Authentication works by extracting OIDC credentials from that context in `~/.kube/config`. The context's user must have an `exec` block with these arguments:

```yaml
users:
  - name: my-user
    user:
      exec:
        command: kubectl
        args:
          - --oidc-issuer-url=https://keycloak.example.com/realms/myrealm
          - --oidc-client-id=my-client
          - --oidc-client-secret=my-secret # Required for client_credentials grant
          - --username=user@example.com # Required for password grant
          - --password=mypassword # Required for password grant
```

`--oidc-issuer-url` and `--oidc-client-id` are required. Grant type is inferred: if `--username` and `--password` are present, `password` grant is used; if only `--oidc-client-secret` is present, `client_credentials` is used.

The token is cached to avoid excessive requests, and the API session refreshes it periodically to prevent 401 errors during long runs.

## CI/CD Pipeline

E2E tests run in CI via the **Main** pipeline (`.github/workflows/main-pipeline.yml`), which orchestrates all service builds and gates E2E on their success.

### How it works

1. **Push to `main`** triggers the Main pipeline automatically.
2. Pre-commit checks (`common.yml`) run first.
3. All 5 service builds run in parallel after pre-commit passes (AIRM UI, AIRM API, AIRM Agent, AIWB API, AIWB UI).
4. E2E tests run after all builds succeed.

The pipeline uses a fan-in pattern with native `needs:` dependencies — no polling or third-party actions.

### Running manually

Run the full pipeline (builds + E2E) on any branch:

```bash
gh workflow run "Main" -R silogen/core --ref <branch-name>
```

Run E2E tests directly (skipping builds, uses existing images):

```bash
# Auto-compute image tag from branch + SHA
gh workflow run "E2E Tests" -R silogen/core --ref <branch-name>

# With a specific image tag
gh workflow run "E2E Tests" -R silogen/core --ref <branch-name> -f image_tag=main-abc1234
```

### Trigger methods

| Method            | How                                          | What runs    |
| ----------------- | -------------------------------------------- | ------------ |
| Main push         | Automatic on merge to `main`                 | Builds + E2E |
| Manual (Main)     | `gh workflow run "Main" --ref <branch>`      | Builds + E2E |
| Manual (E2E only) | `gh workflow run "E2E Tests" --ref <branch>` | E2E only     |
| PR comment        | `/e2e-test` comment on PR                    | E2E only     |
