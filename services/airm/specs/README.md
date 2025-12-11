<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AIRM End-to-End Tests

End-to-end tests for the AMD Enterprise AI Suite, covering the AI Resource Manager (AIRM) backend service and AI Workbench functionality via API endpoints, workload management, and AIM catalog testing using Robot Framework.

## Quick Start

### Prerequisites

1. **Install development tools**:

   See the **dev-tooling repository** for installation instructions:
   - **Redflame** (recommended): Complete development environment
   - **silodev**: Standalone CLI for testing and deployment

2. **Configure Kubernetes authentication** in your kubeconfig (`~/.kube/config`):

   The test infrastructure automatically handles authentication using OIDC credentials from your kubeconfig. Configure the `users` section with OIDC login:

   ```yaml
   users:
     - name: your-context-name
       user:
         exec:
           apiVersion: client.authentication.k8s.io/v1beta1
           args:
             - oidc-login
             - get-token
             - --oidc-issuer-url=https://kc.your-domain.silogen.ai/realms/airm
             - --oidc-client-id=k8s
             - --oidc-client-secret=<insert client secret>
             - --grant-type=password
             - --username=<keycloak user with admin privileges>
             - --password=<very secret password>
           command: kubectl
           env: null
           interactiveMode: IfAvailable
           provideClusterInfo: false
   ```

   **Important**: Replace placeholder values with your actual credentials:
   - `--oidc-issuer-url`: Your Keycloak realm URL
   - `--oidc-client-secret`: Client secret from Keycloak
   - `--username`: Keycloak user with admin privileges
   - `--password`: User's password

3. **Set active Kubernetes context**:
   ```bash
   kubectl config use-context your-context-name
   ```

### Running Tests

Tests are run using Robot Framework via `uv run robot`. The specs directory includes an `arguments.txt` file with recommended settings (pythonpath, output directory, log level, etc.).

**Note:** The `arguments.txt` file is **safe to use with all test suites**. It includes a listener for dynamic test generation that automatically activates only for `aim_catalog.robot` and has no effect on other test suites.

#### Setup

```bash
# Install AIRM dev dependencies (includes Robot Framework and all required libraries)
cd services/airm/api
uv sync --dev

# Navigate to the specs directory
cd ../specs
```

#### Running Tests

**Important:** Since the `pyproject.toml` is in `services/airm/api/` but tests are in `services/airm/specs/`, you must use the `--project` flag to tell `uv` which virtual environment to use.

```bash
# Run all tests using arguments.txt (recommended)
uv run --project ../api robot --argumentfile arguments.txt .

# Run smoke tests (quick validation)
uv run --project ../api robot --argumentfile arguments.txt --include smoke .

# Exclude GPU-intensive tests
uv run --project ../api robot --argumentfile arguments.txt --exclude gpu .

# Run a single test suite
uv run --project ../api robot --argumentfile arguments.txt projects.robot

# Run a specific test by name
uv run --project ../api robot --argumentfile arguments.txt --test "Create project and verify status" .

# Override output directory if needed
uv run --project ../api robot --argumentfile arguments.txt --outputdir /custom/path .

# Rerun only failed tests
uv run --project ../api robot --argumentfile arguments.txt --rerunfailed results/output.xml .
```

**Common tag filtering patterns:**

```bash
# Quick smoke test (no GPU required)
uv run --project ../api robot --argumentfile arguments.txt --include smoke --exclude gpu .

# Run all tests except GPU-intensive ones
uv run --project ../api robot --argumentfile arguments.txt --exclude gpu .

# Run only AIM-related tests
uv run --project ../api robot --argumentfile arguments.txt --include aims .

# Run only project-related tests
uv run --project ../api robot --argumentfile arguments.txt --include projects .

# Run tests that are BOTH smoke AND projects
uv run --project ../api robot --argumentfile arguments.txt --include smokeANDprojects .

# Run tests from specific subdirectory
uv run --project ../api robot --argumentfile arguments.txt workbench/  # Workbench tests only
uv run --project ../api robot --argumentfile arguments.txt airm/       # AIRM tests only
```

**Test Organization:**

Tests are organized into logical subdirectories:

- **`workbench/`** - AI/ML user-facing features (AIMs, datasets, models, workspaces, charts, finetuning)
- **`airm/`** - Infrastructure management (projects, quotas, secrets, storage, workloads, API keys)
- **Root level** - Special suites (aim_catalog.robot, health.robot, test_tracking.robot)

### Configuration

The `arguments.txt` file contains common Robot Framework settings. You can override any argument:

```bash
# Override log level for debugging
uv run --project ../api robot --argumentfile arguments.txt --loglevel TRACE .

# Set timeout for long-running tests
uv run --project ../api robot --argumentfile arguments.txt --test-timeout 30m .

# Change output directory
uv run --project ../api robot --argumentfile arguments.txt --outputdir /tmp/results .
```

See `arguments.txt` for available options and AIM catalog filtering.

### Analyzing Test Results

After running tests, Robot Framework generates HTML reports in `specs/results/`:

- **`log.html`** - Detailed execution log with expandable keyword tree (open in browser)
- **`report.html`** - High-level test report with statistics and pass/fail summary
- **`output.xml`** - Machine-readable results used by extract commands

#### Browser-Based Analysis

```bash
firefox specs/results/log.html
```

#### Terminal-Based Analysis (Recommended for Internal Development)

**When silodev is available**, use `silodev services e2e extract` for powerful command-line analysis:

```bash
# RECOMMENDED: Focus on first failure with full context
silodev services e2e extract airm --failed --first --max-depth 3

# High-level summary of all tests
silodev services e2e extract airm --summary

# Show all failed tests with full structure
silodev services e2e extract airm --failed --max-depth 3

# Show only failed keywords (when you have many failures)
silodev services e2e extract airm --failed --failed-keywords-only --max-depth 3

# Extract specific test by name
silodev services e2e extract airm --name "Create project"

# Extract tests from specific suite
silodev services e2e extract airm --suite "Projects"

# Show only slow operations (>1 second)
silodev services e2e extract airm --min-duration 1.0

# Filter by log level (hide verbose TRACE/DEBUG)
silodev services e2e extract airm --failed --log-level WARN

# Get JSON output for programmatic analysis
silodev services e2e extract airm --failed --output json
```

**Why use extract commands?**

- Essential for terminal-based workflows
- Perfect for LLM analysis (focused, text-based output)
- Powerful filtering and querying capabilities
- Programmatic access via JSON output

### AI-Assisted Testing with Redflame

**When Redflame is available**, you can use the `/e2e-report` slash command to run E2E tests and get AI-powered analysis with issue categorization and infrastructure analysis:

```bash
# Run tests with AI-powered reporting (requires Redflame)
redflame chat --yolo "/e2e-report skip gpu usage"

# The command will:
# 1. Execute the E2E test suite
# 2. Analyze test failures with AI
# 3. Categorize issues (test bugs, infrastructure problems, etc.)
# 4. Provide actionable suggestions for fixes
```

The `/e2e-report` command provides comprehensive analysis beyond standard test output, making it easier to diagnose and resolve test failures.

### Test Tags

Tests use Robot Framework tags for filtering and test selection. Use tags to run subsets of tests based on functionality, speed, or resource requirements.

**General-Purpose Tags:**

| Tag       | Purpose                               | Usage                                                                                                      |
| --------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `smoke`   | Fast tests for quick validation       | Quick smoke testing without waiting. Typically completes in <1 minute per test. Use: `--include smoke`     |
| `gpu`     | Tests requiring GPU resources         | Excludes GPU-intensive tests (AIM deployments, finetuning). Use: `--exclude gpu` for CPU-only environments |
| `kubectl` | Tests using kubectl/helm verification | Tests that interact directly with Kubernetes resources. Useful for isolating K8s-specific tests            |

**Feature-Specific Tags:**

Tests are also tagged by feature area (`aims`, `projects`, `datasets`, `models`, `workload`, `workspace`) and operation type (`create`, `delete`, `list`, `deploy`, etc.). See individual test files for complete tag lists.

## Test Suites

The test suites are organized into logical directories for better maintainability:

### Workbench Tests (`workbench/`)

AI/ML user-facing features and workflows:

| Suite              | Description                                                          |
| ------------------ | -------------------------------------------------------------------- |
| `aims.robot`       | AIM deployment, listing, and management                              |
| `charts.robot`     | Helm chart deployment testing                                        |
| `datasets.robot`   | Dataset upload, download, and management                             |
| `finetuning.robot` | Model fine-tuning workflows                                          |
| `models.robot`     | Model catalog operations                                             |
| `workspaces.robot` | Development workspace management (Jupyter, VS Code, MLflow, ComfyUI) |

**Running Workbench tests:**

```bash
# All Workbench tests
uv run --project ../api robot --argumentfile arguments.txt workbench/

# Specific Workbench suite
uv run --project ../api robot --argumentfile arguments.txt workbench/aims.robot
```

### AIRM Tests (`airm/`)

Infrastructure and platform management features:

| Suite                         | Description                              |
| ----------------------------- | ---------------------------------------- |
| `api_keys.robot`              | API key creation and authentication      |
| `projects.robot`              | Project CRUD operations and management   |
| `quotas.robot`                | Resource quota validation and allocation |
| `secrets.robot`               | Secret management and project assignment |
| `storage.robot`               | Storage configuration and operations     |
| `workloads_api.robot`         | Workload API operations                  |
| `workloads_kubectl.robot`     | Kubernetes workload verification         |
| `workloads_integration.robot` | End-to-end workload scenarios            |
| `workload_quotas.robot`       | Workload resource limits and enforcement |
| `workload_preemption.robot`   | Workload scheduling and preemption       |

**Running AIRM tests:**

```bash
# All AIRM tests
uv run --project ../api robot --argumentfile arguments.txt airm/

# Specific AIRM suite
uv run --project ../api robot --argumentfile arguments.txt airm/projects.robot
```

### Root Level Tests

Special-purpose test suites at the root level:

| Suite                 | Description                                            |
| --------------------- | ------------------------------------------------------ |
| `aim_catalog.robot`   | Comprehensive testing of all 24 AIM models (see below) |
| `health.robot`        | Health check endpoints                                 |
| `test_tracking.robot` | Test infrastructure and tracking                       |

### AIM Catalog Testing

`aim_catalog.robot` validates all 24 AIM models end-to-end:

1. Deploys each AIM
2. Verifies Running state
3. Runs inference requests
4. Validates metrics availability
5. Undeploys and cleans up

**Running AIM Catalog Tests:**

```bash
# Run all AIM catalog tests
uv run --project ../api robot --argumentfile arguments.txt aim_catalog.robot

# Test specific model
uv run --project ../api robot --argumentfile arguments.txt \
  --variable INCLUDE_TAGS:model:aim-tinyllama-tinyllama-1-1b-chat-v1-0 \
  aim_catalog.robot

# Test only 1-GPU models
uv run --project ../api robot --argumentfile arguments.txt \
  --variable INCLUDE_TAGS:gpus:1 \
  aim_catalog.robot

# Exclude models requiring HuggingFace token
uv run --project ../api robot --argumentfile arguments.txt \
  --variable EXCLUDE_TAGS:requires-hf-token \
  aim_catalog.robot
```

**Note:** `silodev services e2e run` does not pass `--pythonpath` and `--listener` arguments correctly for AIM catalog tests. Use `uv run --project ../api robot` directly with `--argumentfile arguments.txt`.

See [workspace/AIM_CATALOG_TESTING.md](workspace/AIM_CATALOG_TESTING.md) for detailed documentation.

## Test Architecture

### Directory Structure

```
specs/
├── *.robot                              # Test suite files
├── aim_catalog_generator.py             # Dynamic test generator for AIM catalog
├── config/
│   └── aim_models.csv                   # AIM model catalog configuration
├── libraries/
│   └── KubeConnection.py                # Port forwarding and cluster connection
└── resources/
    ├── aim_catalog_templates.resource   # AIM catalog test templates
    ├── catalog_*.resource               # Business logic keywords (high-level)
    ├── api/                             # API operation keywords (low-level)
    │   ├── aims.resource
    │   ├── common.resource              # Safe HTTP request wrappers
    │   ├── datasets.resource
    │   ├── models.resource
    │   └── ...
    ├── common/                          # Shared utilities
    │   ├── resource_tracking.resource
    │   └── response_validation.resource
    ├── authorization.resource
    ├── cluster_auth.resource
    ├── deployment.resource              # Service endpoint resolution
    ├── kubectl_verification.resource
    └── test_data.resource
```

### Three-Layer Architecture

Tests follow a layered approach for maintainability:

1. **Test Files (.robot)** - BDD-style Given-When-Then test cases
2. **Catalog Resources (catalog\_\*.resource)** - Business logic keywords
3. **API Resources (api/\*.resource)** - Low-level HTTP operations

**Important:** Test files should NEVER call API resources directly. Always use catalog resources.

**Example Flow:**

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

### Connection Resilience

Tests access cluster services via automatic port forwarding with built-in resilience:

- **Automatic Port Forwarding**: Created on-demand for required services (airm-api, cluster-auth)
- **Caching**: Port forwards cached for 1 hour via `libraries/KubeConnection.py`
- **Health Checks**: Socket validation before each HTTP request
- **Auto-Recovery**: Automatic recreation on failure ensures test reliability

**Safe HTTP Request Keywords** (defined in `resources/api/common.resource`):

- `Safe Get Request` - GET with port forward validation
- `Safe Post Request` - POST with port forward validation
- `Safe Put Request` - PUT with port forward validation
- `Safe Delete Request` - DELETE with port forward validation
- `Safe Patch Request` - PATCH with port forward validation

**Always use safe wrappers** when adding new resource keywords:

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

## Writing and Maintaining Tests

### Test Structure Best Practices

**1. Use BDD-Style Keywords**

```robot
Test Case: Create and delete project
    [Tags]    smoke    projects
    Given a cluster exists in system
    And valid project data is prepared
    When create project request is sent
    Then response status should be 200
    And project should exist in system
    When delete project request is sent
    Then response status should be 204
```

**2. Test Independence**

- Each test should be self-contained
- Use test-scoped variables for test data
- Clean up only test-created resources
- Don't assume environment state

**3. Resource Management**

- Track created resources in `@{CREATED_RESOURCE_IDS}`
- Use suite teardown for cleanup
- Rely on project deletion CASCADE for orphaned resources

**4. Logging Levels**

```robot
# TRACE - Repetitive polling/status checks
Log    Waiting for workload status...    TRACE

# DEBUG - API requests/responses, resource IDs
Log    Created project ID: ${PROJECT_ID}    DEBUG

# INFO - Key milestones, state transitions
Log    Project reached Running state    INFO

# WARN - Recoverable issues, fallbacks
Log    Port forward died, recreating...    WARN
```

### Adding New Test Suites

1. **Create test file** following naming convention: `<feature>.robot`

2. **Add appropriate tags** for filtering:

   ```robot
   *** Test Cases ***
   My Test Case
       [Tags]    smoke    <feature>    <category>
       ...
   ```

3. **Reuse existing keywords** from catalog resources:

   ```robot
   *** Settings ***
   Resource    resources/catalog_projects.resource
   Resource    resources/catalog_aims.resource
   ```

4. **Document test purpose**:

   ```robot
   *** Test Cases ***
   Create project with custom quota
       [Documentation]    Verify project creation with custom resource quota
       [Tags]    projects    quotas
       ...
   ```

5. **Ensure proper cleanup**:
   ```robot
   *** Settings ***
   Suite Teardown    Cleanup Created Resources
   ```

### Adding New Resource Keywords

When extending test capabilities:

1. **Follow the layer architecture**:
   - API keywords in `resources/api/<feature>.resource`
   - Business logic in `resources/catalog_<feature>.resource`

2. **Use safe HTTP wrappers**:

   ```robot
   # In resources/api/my_feature.resource
   Get My Resource
       [Arguments]    ${resource_id}
       ${endpoint}=    Set Variable    /v1/my-resource/${resource_id}
       ${response}=    Safe Get Request    ${endpoint}
       RETURN    ${response}
   ```

3. **Add documentation**:

   ```robot
   My Keyword
       [Documentation]    Brief description of what this keyword does
       [Arguments]    ${arg1}    ${arg2}=default
       ...
   ```

4. **Return values consistently**:

   ```robot
   # Return response objects from API keywords
   Create Resource
       ${response}=    Safe Post Request    /v1/resources    json=${data}
       RETURN    ${response}

   # Return domain objects from catalog keywords
   Resource Should Be Created
       ${response}=    Create Resource
       Should Be Equal As Integers    ${response.status_code}    201
       ${resource_id}=    Set Variable    ${response.json()['id']}
       RETURN    ${resource_id}
   ```

### Common Patterns

**Creating Projects with Quotas:**

```robot
# Minimum quota for quota-specific tests
Given a cluster exists in system
And minimum quota data is prepared
And valid project data with quota is prepared
When create project request is sent
Then response status should be 200

# Zero quota for other tests
Given a cluster exists in system
And valid project data is prepared  # Uses zero quota fallback
When create project request is sent
Then response status should be 200
```

**Waiting for Workload Status:**

```robot
# Use built-in wait keywords
Wait For Workload Status    ${WORKLOAD_ID}    Running    timeout=300s

# For custom conditions
Wait Until Keyword Succeeds    5 min    10 sec
...    Workload Should Have Status    ${WORKLOAD_ID}    Running
```

**Resource Tracking and Cleanup:**

```robot
*** Settings ***
Suite Setup       Initialize Test Suite
Suite Teardown    Cleanup Created Resources

*** Keywords ***
Track Created Resource
    [Arguments]    ${resource_id}
    Append To List    ${CREATED_RESOURCE_IDS}    ${resource_id}

Cleanup Created Resources
    FOR    ${resource_id}    IN    @{CREATED_RESOURCE_IDS}
        Run Keyword And Ignore Error    Delete Resource    ${resource_id}
    END
```

## Troubleshooting

### Common Issues

**Authentication failures:**

- Verify kubeconfig OIDC settings are correct
- Check that kubectl context is set to the correct cluster
- Ensure OIDC credentials in kubeconfig are valid

**Port forwarding issues:**

- Tests should auto-recover via safe HTTP wrappers
- Check stuck processes: `ps aux | grep "kubectl port-forward"`
- Verify cluster connectivity: `kubectl get pods -n airm`
- See [CLAUDE.md](CLAUDE.md) for detailed troubleshooting

**Resource conflicts:**

- Check for orphaned resources from previous runs
- Verify project cleanup is working
- Use unique resource names with timestamps

**Timeout issues:**

- Adjust wait timeouts for your environment
- Check cluster resources: `kubectl describe nodes`
- Verify workload logs: `kubectl logs -n <namespace> <pod-name>`

### Debug Commands

```bash
# RECOMMENDED: Focus on first failure with full context
silodev services e2e extract airm --failed --first --max-depth 3

# Run with verbose logging
uv run --project ../api robot --argumentfile arguments.txt --loglevel TRACE .

# Dry run to validate test structure
uv run --project ../api robot --argumentfile arguments.txt --dryrun .

# Extract all failed tests with full structure
silodev services e2e extract airm --failed --max-depth 3

# Check specific test execution
silodev services e2e extract airm --name "My Test Name" --log-level DEBUG
```

### Getting Help

- View test results: `specs/results/log.html`
- Check Robot Framework logs for detailed execution trace
- Use `silodev services e2e extract` to filter and analyze results
- See [CLAUDE.md](CLAUDE.md) for AI assistant guidance
- Refer to [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)

## Related Documentation

- **[CLAUDE.md](CLAUDE.md)** - AI assistant troubleshooting guide (port forwarding, quota system, common patterns)
- **[workspace/AIM_CATALOG_TESTING.md](workspace/AIM_CATALOG_TESTING.md)** - Comprehensive AIM catalog testing guide
- **[Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)** - Official Robot Framework documentation
- **[RequestsLibrary Documentation](https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html)** - HTTP request library reference
