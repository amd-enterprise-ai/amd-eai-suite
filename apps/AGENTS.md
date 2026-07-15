<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# E2E Testing Rules

> **Note**: Read `/AGENTS.md` first for the E2E testing philosophy and general repository rules.

End-to-end tests use **Robot Framework 5.0+** with BDD-style Given/When/Then syntax. Tests live in `specs/` directories within each app.

## Layered Architecture

All E2E tests follow a strict layered architecture. Never bypass layers.

### API Tests (four layers)

1. **Test layer** (`*.robot`) — BDD scenarios using Given/When/Then keywords. Imports only business-logic resources.
2. **Business-logic layer** (`aiwb_*.resource`, `airm_*.resource`) — domain-specific keywords that own test state (`TEST_*` variables). Calls API-layer keywords.
3. **API layer** (`resources/api/*.resource`) — stateless HTTP operations. All inputs as explicit arguments, no `TEST_*` variable access. Uses Safe HTTP wrappers.
4. **Infrastructure layer** (`testing/resources/`) — shared utilities (session management, authorization, safe HTTP wrappers).

### UI Tests (three layers)

1. **Test layer** (`*.robot`) — BDD scenarios.
2. **Feature layer** (`resources/*.resource`) — business-meaningful keywords composing page interactions.
3. **Page layer** (`resources/pages/*.resource`) — selectors and atomic browser interactions. No business logic.

## Scenarios to Tests

**Tests copy the scenario words. Keywords make the words work.**

The `.robot` file is a near-verbatim copy of the behavioral scenario. The keyword library (`.resource` or Python) is the only place where behavioral language gets translated into technical actions. This keeps tests readable by the same three audiences that read the scenarios.

```robot
# Scenario (spec):
#   Given a ready project with user access exists
#   When AIM is deployed
#   Then AIM should be running

# .robot file (same words):
Deploy AIM successfully
    Given a ready project with user access exists
    When AIM is deployed
    Then AIM should be running
```

## Resource Files vs Python Libraries

| Use              | For                                                                                            |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| `.resource` file | Composite keywords that combine other keywords, shared variables, re-exporting library imports |
| Python library   | Anything with real logic — HTTP calls, assertions, state management, fixture loading           |

**Rule of thumb:** if the keyword body is just calling other keywords, it belongs in a `.resource` file. If it contains any logic, it belongs in Python.

## Black-Box Testing

Keyword libraries treat the system under test as a black box. **Never import from the codebase being tested.** Keywords interact only through external interfaces: HTTP, CLI, browser, or Kubernetes API. This ensures tests verify the contract the system keeps with its users, not its internal arrangement.

## Modern Robot Framework Syntax

Use RF 5.0+ syntax exclusively. Do not use legacy syntax in new code.

| Modern (required)              | Legacy (do not use)            |
| ------------------------------ | ------------------------------ |
| `VAR`                          | `Set Variable`                 |
| `IF / ELSE / END`              | `Run Keyword If`               |
| `TRY / EXCEPT / FINALLY / END` | `Run Keyword And Ignore Error` |
| `RETURN`                       | `[Return]`                     |

## Test Independence

- Every test is completely independent — creates its own data, no execution-order dependencies
- Tests can run in any order or concurrently
- Use the `Test Prefix` library for unique resource names (`Test Name    my-resource`)

## State Management

- **`TEST_*` variables** (e.g., `${TEST_PROJECT_ID}`, `${TEST_RESPONSE}`) are owned exclusively by the business-logic layer
- API-layer and page-layer keywords must receive values as explicit arguments
- Use the **resource resolver pattern** (`The ${resource_type}`) to access created resources with validation — do not access `TEST_*` variables directly from test cases

## Polling, Not Sleeping

**Always** use `Wait Until Keyword Succeeds` with appropriate timeout and interval. **Never** use `Sleep`.

```robot
# GOOD
Wait Until Keyword Succeeds    5 min    10 sec    Project should be ready

# BAD
Sleep    5m
Project should be ready
```

## Resource Cleanup

- Track created resources in suite-scoped lists (e.g., `@{CREATED_PROJECT_IDS}`)
- Clean up in Suite Teardown using idempotent keywords that tolerate partial failures
- Initialize tracking in Suite Setup

## Keyword Naming

| Type              | Pattern                  | Example                        |
| ----------------- | ------------------------ | ------------------------------ |
| Action            | Verb + object            | `Create project`, `Deploy AIM` |
| Verification      | Subject + should + state | `Project should be ready`      |
| Precondition      | A/an + condition         | `A ready project exists`       |
| Resource resolver | The + resource           | `The project`, `The workload`  |

## Tags

Use tags for test selection. Common tags across apps:

- `smoke` — fast tests, no heavy resources
- `gpu` — requires GPU hardware
- Feature tags: `aims`, `projects`, `workloads`, `secrets`, `api-keys`, `datasets`, etc.
- Operation tags: `create`, `delete`, `list`, `deploy`, `lifecycle`

```bash
# Include/exclude tags
uv run --project .. robot --argumentfile arguments.txt --include smoke --exclude gpu .
```

## Running Tests

Always use `arguments.txt` — never run Robot Framework without it:

```bash
cd apps/<api|ui>/<app>/specs
uv run --project .. robot --argumentfile arguments.txt .
```

## Anti-Patterns

- **Sleep in tests** — use `Wait Until Keyword Succeeds`
- **Test dependencies** — each test creates its own data
- **Hidden preconditions** — declare all setup in Given steps
- **Bypassing layers** — tests call business-logic keywords, not API/page-layer directly
- **Inline keywords in .robot files** — define keywords in `.resource` files
- **TEST\_\* in API/page layer** — these layers must be stateless
- **Legacy RF syntax** — use modern `VAR`, `IF/END`, `TRY/EXCEPT`, `RETURN`
- **Direct RequestsLibrary calls** — use Safe HTTP wrappers
- **Reading output.xml directly** — use `robot-extract` tool instead (output files are 100MB+)
