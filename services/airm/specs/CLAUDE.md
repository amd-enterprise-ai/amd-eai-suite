<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# Claude Code Guide: AIRM E2E Tests

This document provides context and troubleshooting guidance for Claude Code when working with AIRM E2E tests.

## ⚠️ CRITICAL WARNING: Do NOT Read Test Output Files

**NEVER attempt to read Robot Framework output files directly**. These files are extremely large (often >100MB) and will:

- Consume excessive tokens
- Cause performance issues
- Potentially crash the session
- Provide no useful debugging information

**Files to NEVER read:**

- `results/output.xml` - Main test execution results (can be 100MB+)
- `results/log.html` - HTML test log (very large, use browser instead)
- `results/report.html` - HTML test report (very large, use browser instead)
- Any file in `results/` directory without explicit confirmation from user

**Instead, use these approaches:**

1. **Ask the user** to share specific error messages or test failures
2. **Run specific tests** to see failures in real-time: `uv run --project ../api/ robot --argumentfile arguments.txt --test "Test Name" .`
3. **Use grep** to search for specific patterns in output files if absolutely necessary
4. **View HTML reports** in a browser (users can share screenshots if needed)

## Quick Start: Running E2E Tests

All test commands must be run from the `services/airm/specs` directory and use `--argumentfile arguments.txt`.

**Most common commands:**

```bash
# Navigate to specs directory first
cd services/airm/specs

# Quick validation (smoke tests only, no GPU)
uv run --project ../api/ robot --argumentfile arguments.txt --include smoke --exclude gpu .

# Run all tests
uv run --project ../api/ robot --argumentfile arguments.txt .

# Run specific test suite
uv run --project ../api/ robot --argumentfile arguments.txt workbench/aims.robot

# Run specific test by name
uv run --project ../api/ robot --argumentfile arguments.txt --test "Create project and verify status" .

# Rerun only failed tests
uv run --project ../api/ robot --argumentfile arguments.txt --rerunfailed results/output.xml .
```

**Test output location:** `services/airm/specs/results/`

- View `log.html` and `report.html` in a browser for detailed results
- **Never read these files directly in Claude Code**

See "Running Tests" section below for complete command reference.

## Connection Resilience

### Port Forwarding Architecture

**Problem**: kubectl port-forward can die during long test runs, causing connection reset errors.

**Solution**: Automatic port forward validation and recreation via safe HTTP request wrappers.

### How It Works

```
Test Keyword → Safe HTTP Request → Ensure Port Forward Alive → Catalog endpoint
→ Service endpoint → KubeConnection.external_host_for() → Validate/Recreate Port Forward
→ Update Session → Execute HTTP Request
```

### Troubleshooting Port Forwarding Issues

#### Symptom: "Connection reset by peer" errors

**Diagnosis**:

```bash
# Check if kubectl port-forward processes are running
ps aux | grep "kubectl port-forward.*airm"

# Check if ports are accessible
curl http://localhost:31274/health  # Replace port as needed
```

**Resolution**: Tests should auto-recover via safe wrappers. If not:

1. Check resource files are using safe wrappers (not direct RequestsLibrary calls)
2. Verify `Ensure Port Forward Alive` keyword is called before HTTP requests
3. Check KubeConnection.py cache isn't corrupted (restart Python process)

#### Symptom: Port forward validation taking too long

**Cause**: Socket checks timing out repeatedly.

**Resolution**:

- Check cluster connectivity: `kubectl get pods -n airm`
- Verify service is healthy: `kubectl get svc airm-api -n airm`
- Check firewall/network isn't blocking localhost ports

### Writing New Test Keywords

**Always use safe wrappers for HTTP requests**:

```robot
# ✅ CORRECT - Uses safe wrapper
My New Keyword
    ${response}=    Safe Get Request    /v1/my-endpoint
    RETURN    ${response}

# ❌ WRONG - Direct RequestsLibrary call
My New Keyword
    ${response}=    Get On Session    ${API_SESSION}    /v1/my-endpoint
    RETURN    ${response}
```

**Safe wrappers available**:

- `Safe Get Request` - GET requests
- `Safe Post Request` - POST requests
- `Safe Put Request` - PUT requests
- `Safe Delete Request` - DELETE requests
- `Safe Patch Request` - PATCH requests

All are defined in `resources/api/common.resource`.

## Quota System

### Understanding Quotas

**Quotas are minimum guarantees, not upper limits:**

- Zero quota = valid (no guarantee, but can use available resources)
- System validates total allocations ≤ cluster capacity
- Projects can exceed quota if resources available (borrowing/preemption)

### Quota Validation Logic

**Location**: `services/airm/api/app/quotas/utils.py:19-55`

**Validates**:

- Sum of all project quotas doesn't exceed cluster CPU capacity
- Sum of all project quotas doesn't exceed cluster memory capacity
- Sum of all project quotas doesn't exceed cluster storage capacity
- Sum of all project quotas doesn't exceed cluster GPU count

**Returns**: HTTP 400 with `ValidationException` if validation fails, HTTP 201 if successful.

### Quota Test Keywords

**IMPORTANT**: Do NOT change quota-specific keywords to use zero values:

```robot
# ✅ CORRECT - Quota-specific keywords have non-zero values
Prepare Minimum Quota
    ${quota_data}=    Prepare Quota    cpu_milli_cores=1000    memory_bytes=1073741824    ...

# ✅ CORRECT - General-purpose keywords can use zero defaults
Prepare Default Quota
    ${quota_data}=    Prepare Quota    cpu_milli_cores=0    memory_bytes=0    ...
```

**Quota-specific keywords** (must have non-zero values):

- `Prepare Minimum Quota` - For quota tests (1 CPU core, 1GB RAM)
- `Prepare Custom Quota Data` - For custom quota tests (4 CPU cores, 4GB RAM, 2 GPUs)
- `Minimum Quota Data Is Prepared` - Uses proper minimum values

**General-purpose keywords** (can have zero defaults):

- `Prepare Quota` - Base keyword with flexible defaults
- `Prepare Default Quota` - Convenience wrapper for zero quotas
- `Valid project data*` keywords - Fallback quotas for project creation

### Troubleshooting Quota Test Failures

#### Symptom: Tests expect 200 but fail with "Expected status: 400"

**Diagnosis**: Check if quota keywords are using zero values incorrectly.

**Resolution**:

1. Verify `Prepare Minimum Quota` has `cpu_milli_cores=1000`, not `0`
2. Verify `Prepare Custom Quota Data` has proper defaults (4000 CPU, 4GB RAM, 2 GPUs)
3. Check git diff for uncommitted changes to quota keywords

#### Symptom: Quota exceeds cluster capacity errors

**Cause**: Cluster doesn't have enough resources for requested quota.

**Resolution**:

- Check cluster capacity: `kubectl describe node`
- Verify other projects aren't consuming all resources
- Reduce quota values in test or increase cluster size

## Common Patterns

### Creating Projects with Quotas

```robot
# Pattern 1: Project with minimum quota
Given a cluster exists in system
And minimum quota data is prepared
And valid project data with quota is prepared
When create project request is sent
Then response status should be 200

# Pattern 2: Project with custom quota
Given a cluster exists in system
And custom quota data is prepared
And valid project data with quota is prepared
When create project request is sent
Then response status should be 200

# Pattern 3: Project with zero quota (for non-quota tests)
Given a cluster exists in system
And valid project data is prepared  # Uses zero quota fallback
When create project request is sent
Then response status should be 200
```

### Updating Quotas

```robot
# Always provide all quota fields when updating
Given a project exists with minimum quota
And quota update data is prepared
    ...    cpu_milli_cores=2000
    ...    memory_bytes=2147483648
    ...    ephemeral_storage_bytes=2147483648
    ...    gpu_count=1
When update project request is sent
Then response status should be 200
```

## Resource File Organization

### Layered Architecture

The test framework uses a three-layer architecture:

1. **Test Files (.robot)** - Test cases with BDD-style Given-When-Then
2. **Catalog Resources (catalog\_\*.resource)** - High-level business logic keywords
3. **API Resources (api/\*.resource)** - Low-level API operation keywords

**Key Principle**: Test files should NEVER call API resources directly. Always go through catalog resources.

### API Layer (resources/api/)

**Purpose**: Low-level HTTP operations and endpoint construction.

**Key Files**:

- `common.resource` - Safe HTTP wrappers, session management, endpoint resolution
- `aims.resource` - AIM-specific API operations (deploy, undeploy, list)
- `projects.resource` - Project CRUD operations
- `datasets.resource` - Dataset upload/download/management
- `models.resource` - Model operations

**Characteristics**:

- Direct RequestsLibrary wrapper calls (via Safe wrappers)
- No business logic or validation
- Returns raw HTTP responses
- Handles endpoint URL construction

### Catalog Layer (resources/catalog\_\*.resource)

**Purpose**: Business logic, validation, and test orchestration.

**Key Files**:

- `catalog_aims.resource` - AIM deployment workflows, status validation
- `catalog_projects.resource` - Project lifecycle management
- `catalog_keywords.resource` - Shared test utilities

**Characteristics**:

- Calls API resources for HTTP operations
- Performs response validation
- Implements business logic (wait for status, retry logic)
- Provides BDD-friendly keyword names

### Example Flow

```robot
# Test file (aims.robot)
Test Case: Deploy AIM
    Given a project exists
    When deploying AIM "${AIM_ID}"
    Then AIM should reach Running state

# Catalog layer (catalog_aims.resource)
Deploying AIM "${aim_id}"
    ${response}=    Deploy AIM    ${aim_id}
    Should Be Equal As Integers    ${response.status_code}    202

# API layer (api/aims.resource)
Deploy AIM
    [Arguments]    ${aim_id}
    ${endpoint}=    Set Variable    /v1/aims/${aim_id}/deploy
    ${response}=    Safe Post Request    ${endpoint}    json={}
    RETURN    ${response}
```

## Port Forwarding Implementation Details

### KubeConnection.py Cache

**File**: `libraries/KubeConnection.py`

**Cache Structure**:

```python
_PORT_FORWARD_CACHE = {
    "airm:airm-api": ("localhost:31274", 1733147382.5),
    "keycloak:keycloak": ("localhost:30521", 1733147390.1)
}
```

**Cache Key Format**: `{namespace}:{service_name}`

**Cache Entry**: `(host_string, timestamp)`

**TTL**: 3600 seconds (1 hour)

### Validation Flow

```python
def external_host_for(service, micro_service, prefix=None):
    # 1. Check cache + validate port is accessible
    if cache_key in _PORT_FORWARD_CACHE:
        cached_host, timestamp = _PORT_FORWARD_CACHE[cache_key]
        if current_time - timestamp < _CACHE_TTL:
            if _check_port_ready(port, timeout=1):
                return cached_host  # Cache hit - port still alive

    # 2. Search for existing kubectl port-forward process
    existing_port = _find_existing_port_forward(...)
    if existing_port and _check_port_ready(existing_port):
        # Reuse existing process
        _PORT_FORWARD_CACHE[cache_key] = (f"localhost:{existing_port}", time.time())
        return f"localhost:{existing_port}"

    # 3. Create new port forward
    local_port = random.randint(30000, 32767)
    _start_port_forward(micro_service, namespace, local_port, service_port)

    # 4. Cache and return
    host = f"localhost:{local_port}"
    _PORT_FORWARD_CACHE[cache_key] = (host, time.time())
    return host
```

### Socket Validation

```python
def _check_port_ready(port, timeout=10):
    """Validate port is accessible via socket connection."""
    for attempt in range(timeout):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()

        if result == 0:  # Port is accessible
            return True

        time.sleep(1)

    return False
```

## Session Management

### Token Refresh Strategy

**File**: `resources/api/common.resource`

**Problem**: Long test runs (>55 minutes) cause JWT tokens to expire.

**Solution**: Automatic session token refresh every 4 minutes.

### Implementation

```robot
Create api session
    # If session exists, refresh token if needed
    IF    $API_SESSION is not None
        Ensure Fresh Session Token
        RETURN
    END

    # Create new session
    ${base_url}=    Catalog endpoint
    ${access_token}=    Authorization token
    Create session    catalog_api    ${base_url}    headers=...
    Set suite variable    ${API_SESSION}    catalog_api

Ensure Fresh Session Token
    # Check session age
    ${current_time}=    Get Current Date
    ${time_diff}=    Subtract Date From Date    ${current_time}    ${SESSION_LAST_REFRESH}

    # Refresh if older than 4 minutes (240 seconds)
    IF    ${time_diff} >= ${SESSION_TOKEN_REFRESH_INTERVAL}
        ${fresh_token}=    Authorization token
        &{headers}=    Create Dictionary    Authorization=Bearer ${fresh_token}
        Update Session    ${API_SESSION}    headers=${headers}
        Set Suite Variable    ${SESSION_LAST_REFRESH}    ${current_time}
    END
```

### When to Recreate Session

**Use `Recreate api session` when**:

- User is added to a project (JWT group claims changed)
- Project permissions are modified
- Authorization context needs to be refreshed

**Use `Create api session` when**:

- First API call in a suite
- Session doesn't exist yet
- Session variable is None

## Investigation Documents

When troubleshooting test failures, refer to:

- `/home/teemu/repos/core/PORT_FORWARDING_RELIABILITY_INVESTIGATION.md` - Port forwarding deep dive
- `/home/teemu/repos/core/QUOTA_TEST_INVESTIGATION.md` - Quota system architecture and validation

## Test Tags and Tagging Guidelines

### Understanding Test Tags

Robot Framework tags enable filtering tests by functionality, speed, or resource requirements. Tags appear in the `[Tags]` setting of each test case.

**General-Purpose Tags:**

| Tag       | Purpose                               | When to Use                                                                                   |
| --------- | ------------------------------------- | --------------------------------------------------------------------------------------------- |
| `smoke`   | Fast tests for quick validation       | Tests that complete in <1 minute and validate core functionality without heavy resource usage |
| `gpu`     | Tests requiring GPU resources         | Any test that deploys GPU workloads (AIMs, finetuning) or explicitly requests GPU allocation  |
| `kubectl` | Tests using kubectl/helm verification | Tests that interact directly with Kubernetes resources beyond API calls                       |

**Feature-Specific Tags:**

Tests should include relevant feature tags:

- `aims` - AIM deployment and management tests
- `projects` - Project CRUD operations
- `datasets` - Dataset upload/download/management
- `models` - Model catalog operations
- `workload` - Workload lifecycle tests
- `workspace` - Workspace deployment tests

**Operation Tags:**

Include operation type where applicable:

- `create`, `delete`, `list`, `get` - CRUD operations
- `deploy`, `undeploy` - Deployment operations
- `status`, `lifecycle` - Status transition tests

### Tagging New Tests

When adding new test cases, follow these guidelines:

**1. Always include feature tag:**

```robot
*** Test Cases ***
Create new project
    [Tags]    projects    create
```

**2. Add `smoke` tag for fast validation tests:**

```robot
List all projects
    [Documentation]    Quick validation that project listing works
    [Tags]    projects    list    smoke
```

**3. Add `gpu` tag for tests that deploy GPU workloads:**

```robot
Deploy AIM workload
    [Documentation]    Verify AIM deployment creates running workload
    [Tags]    aims    deploy    gpu
    # Test deploys an AIM which requires GPU
```

**4. Add `kubectl` tag when verifying Kubernetes resources:**

```robot
Verify workload pod exists
    [Documentation]    Check that workload created pod in namespace
    [Tags]    workload    kubectl
    # Test uses kubectl to verify pod existence
```

**5. Combine multiple relevant tags:**

```robot
Deploy AIM and verify running
    [Documentation]    Full AIM deployment workflow validation
    [Tags]    aims    deploy    smoke    gpu    kubectl
    # Smoke test (quick), requires GPU, verifies via kubectl
```

### When to Use `gpu` Tag

**Always add `gpu` tag to tests that:**

- Deploy AIMs (all AIM deployment tests)
- Run finetuning workflows (finetuning tests)
- Create workspaces with explicit GPU allocation
- Submit workloads that request GPU resources
- Wait for GPU workloads to reach Running state
- Access or verify GPU workload endpoints

**Don't add `gpu` tag to tests that:**

- Only list/query AIM metadata (no deployment)
- Perform CRUD operations on projects, secrets, storage
- Test API validation without resource allocation
- Deploy CPU-only workloads or workspaces

**Example - `aims.robot`:**

```robot
List available AIMs
    [Tags]    aims    list    smoke
    # ✅ NO gpu tag - only lists metadata

Deploy AIM creates workload
    [Tags]    aims    deploy    smoke    gpu
    # ✅ HAS gpu tag - deploys GPU workload
```

### Filtering Tests by Tags

See "Tag Filtering Examples" in the "Running Tests" section above for detailed tag filtering commands.

## Test Organization

Tests are organized into logical subdirectories for better maintainability:

- **`workbench/`** - AI/ML user-facing features (AIMs, datasets, models, workspaces, charts, finetuning)
- **`airm/`** - Infrastructure management (projects, quotas, secrets, storage, workloads, API keys)
- **Root level** - Special suites (aim_catalog.robot, health.robot, test_tracking.robot)

## Running Tests

**IMPORTANT**: Always use `--argumentfile arguments.txt` when running tests. This file is safe to use with all test suites.

The `arguments.txt` file contains a listener for dynamic test generation that automatically activates only for `aim_catalog.robot` and has no effect on other test suites.

### Basic Test Commands

```bash
# Navigate to specs directory
cd services/airm/specs

# Run all smoke tests (recommended for quick validation)
uv run --project ../api/ robot --argumentfile arguments.txt --include smoke .

# Run all tests
uv run --project ../api/ robot --argumentfile arguments.txt .

# Run tests from specific category
uv run --project ../api/ robot --argumentfile arguments.txt workbench/  # Workbench tests
uv run --project ../api/ robot --argumentfile arguments.txt airm/       # AIRM tests

# Run smoke tests by category
uv run --project ../api/ robot --argumentfile arguments.txt --include smoke workbench/
uv run --project ../api/ robot --argumentfile arguments.txt --include smoke airm/

# Run specific suite
uv run --project ../api/ robot --argumentfile arguments.txt workbench/aims.robot
uv run --project ../api/ robot --argumentfile arguments.txt airm/projects.robot

# Run specific test by name
uv run --project ../api/ robot --argumentfile arguments.txt --test "Create project and verify status" .

# Exclude GPU tests
uv run --project ../api/ robot --argumentfile arguments.txt --include smoke --exclude gpu .
```

### Tag Filtering Examples

```bash
# Quick validation without GPU
uv run --project ../api/ robot --argumentfile arguments.txt --include smoke --exclude gpu .

# All tests except GPU-intensive ones
uv run --project ../api/ robot --argumentfile arguments.txt --exclude gpu .

# Only AIM-related tests
uv run --project ../api/ robot --argumentfile arguments.txt --include aims .

# Only project-related tests
uv run --project ../api/ robot --argumentfile arguments.txt --include projects .

# Smoke tests for specific feature
uv run --project ../api/ robot --argumentfile arguments.txt --include smokeANDprojects .
```

**Tag combination syntax:**

- `--include tagA` - Tests with tagA
- `--exclude tagB` - Tests without tagB
- `--include tagAANDtagB` - Tests with both tags
- `--include tagAORtagB` - Tests with either tag
- `--include tagANOTtagB` - Tests with tagA but not tagB

## Best Practices

1. **Always use `--argumentfile arguments.txt`** when running tests (safe for all suites)
2. **Always use safe HTTP request wrappers** in resource files
3. **Never change quota-specific keywords to zero values**
4. **Add documentation** when creating new keywords
5. **Test in isolation** when debugging failures (run single suite/test)
6. **Check investigation docs** before creating new tickets
7. **Follow layered architecture** - tests → catalog → api
8. **Use appropriate log levels** - TRACE for polling, DEBUG for API calls, INFO for milestones

## Common Debugging Commands

```bash
# Check port forwards
ps aux | grep "kubectl port-forward"

# Test port accessibility
nc -zv localhost 31274

# Check cluster connectivity
kubectl get pods -n airm
kubectl get svc -n airm

# View test logs with full debug
uv run --project ../api/ robot --argumentfile arguments.txt --loglevel TRACE workbench/aims.robot

# Run single test
uv run --project ../api/ robot --argumentfile arguments.txt --test "Deploy AIM successfully" .

# Rerun only failed tests
uv run --project ../api/ robot --argumentfile arguments.txt --rerunfailed results/output.xml .
```

---

_This guide is maintained for Claude Code assistance. Human developers should refer to specs/README.md._
