# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       End-to-end testing of full AIM catalog.
...
...                 # Overview
...
...                 This test suite validates the complete AIM catalog by testing each model:
...                 - Deploying an AIM
...                 - Verifying it reaches Running state
...                 - Running inference requests
...                 - Verifying metrics are available
...                 - Undeploying the AIM
...
...                 # Architecture
...
...                 The suite uses dynamic test generation via Robot Framework Listener API.
...                 Test cases are generated at runtime based on the model list in config/aim_models.csv.
...
...                 Components:
...                 - aim_catalog.robot: Main test suite (this file)
...                 - aim_catalog_generator.py: Python listener for dynamic test generation
...                 - config/aim_models.csv: Model catalog configuration
...                 - resources/aim_catalog_templates.resource: Test templates with all logic
...
...                 For each AIM model, a sequence of tests is created:
...                 1. Deploy <model> - Deploys the AIM and verifies workload creation
...                 2. Verify <model> reaches Running state - Waits for deployment to be ready
...                 3. Run inference with <model> - Tests inference via external endpoint
...                 4. Verify metrics for <model> - Checks that metrics are available
...                 5. Undeploy <model> - Removes deployment and verifies cleanup
...
...                 This approach ensures:
...                 - Each AIM is deployed once, all tests run, then undeployed (resource efficient)
...                 - Models are tested sequentially due to GPU constraints
...                 - Test logic stays in .resource files (readable, maintainable)
...                 - Python handles only orchestration (which models, what sequence)
...                 - All 24 models can be tested systematically
...
...                 # Cleanup Strategy
...
...                 The suite uses a multi-layered cleanup approach:
...                 1. Each model has an explicit Undeploy test (frees GPUs for next model)
...                 2. Suite Teardown performs best-effort cleanup of any remaining deployments
...                 3. Project deletion CASCADE ensures complete cleanup of all resources
...
...                 IMPORTANT: There is NO test-level teardown. Individual tests do not
...                 perform cleanup. Only the explicit Undeploy test and Suite Teardown
...                 handle cleanup. This ensures the project remains available throughout
...                 the entire test run.
...
...                 # Usage
...
...                 Basic execution (all 24 models in full test mode):
...                 | robot aim_catalog.robot
...
...                 ## Tag Filtering
...
...                 IMPORTANT: Command-line --include and --exclude do NOT work with dynamically
...                 generated tests! Instead, use Robot Framework variables to pass tag filters.
...
...                 Run specific model using tag variable:
...                 | robot --variable INCLUDE_TAGS:model:aim-qwen-qwen2-5-0-5b-instruct aim_catalog.robot
...
...                 Run only models that don't require HuggingFace token:
...                 | robot --variable EXCLUDE_TAGS:requires-hf-token aim_catalog.robot
...
...                 Run only small models (1 GPU):
...                 | robot --variable INCLUDE_TAGS:gpus:1 aim_catalog.robot
...
...                 Combine include and exclude:
...                 | robot --variable INCLUDE_TAGS:gpus:1 --variable EXCLUDE_TAGS:requires-hf-token aim_catalog.robot
...
...                 Run with different test mode (full, smoke, or quick):
...                 | robot --variable TEST_MODE:smoke aim_catalog.robot
...
...                 # Available Tags
...
...                 Each test is tagged for flexible filtering:
...                 - model:<image_name> - Specific model (e.g., model:aim-tinyllama-tinyllama-1-1b-chat-v1-0)
...                 - gpus:<count> - GPU requirement (e.g., gpus:1, gpus:4, gpus:8)
...                 - requires-hf-token - HuggingFace token required
...                 - aim-catalog - All catalog tests
...                 - deploy, deployment - Deployment tests
...                 - status - Running state verification
...                 - inference, external - Inference tests
...                 - metrics, analytics - Metrics verification
...                 - undeploy, cleanup - Undeployment tests
...
...                 # Documentation
...
...                 See AIM_CATALOG_TESTING.md for comprehensive documentation

Resource            resources/aim_catalog_templates.resource
Resource            resources/airm_projects.resource
Resource            resources/api/models.resource
Resource            resources/api_keys.resource
Suite Setup         Setup AIM catalog testing
Suite Teardown      Cleanup AIM catalog testing
Test Timeout        15 minutes


*** Variables ***
${TEST_MODE}        full        # Test mode: full, smoke, or quick
${HF_TOKEN_SECRET_NAME}    huggingface-token    # Name of the HF token secret in the cluster
${INCLUDE_TAGS}     ${None}     # Tags to include (set via --variable INCLUDE_TAGS:model:aim-xxx)
${EXCLUDE_TAGS}     ${None}     # Tags to exclude (set via --variable EXCLUDE_TAGS:requires-hf-token)


*** Test Cases ***
Placeholder - Will be replaced by generated tests
    [Documentation]    This placeholder test will be removed when dynamic tests are generated
    ...                It has a special tag to prevent RF from filtering it out before the listener runs
    [Tags]    DYNAMIC_TEST_PLACEHOLDER    smoke
    No Operation


*** Keywords ***
Setup AIM catalog testing
    [Documentation]    Suite setup for AIM catalog testing.
    ...                Deletes all existing projects to ensure clean state before testing.
    ...                Individual tests handle their own Given prerequisites.

    Log    Starting AIM catalog testing suite    INFO
    Log    Test mode: ${TEST_MODE}    INFO

    # Clean up any existing projects from previous test runs
    # This frees up GPU resources and ensures clean state
    TRY
        Log    Cleaning up existing projects from previous test runs    INFO
        ${response}=    Get projects    expected_status=any
        IF    ${response.status_code} == 200
            ${projects}=    Set Variable    ${response.json()}
            ${project_count}=    Get Length    ${projects}
            Log    Found ${project_count} existing projects to clean up    INFO

            IF    ${project_count} > 0
                FOR    ${project}    IN    @{projects}
                    TRY
                        ${project_id}=    Set Variable    ${project}[id]
                        ${project_name}=    Set Variable    ${project}[name]
                        Log    Deleting existing project: ${project_name} (${project_id})    INFO
                        ${del_response}=    Delete project    ${project_id}    expected_status=any
                        IF    ${del_response.status_code} in [200, 204]
                            Log    Successfully deleted project ${project_id}    DEBUG
                        ELSE
                            Log    Failed to delete project ${project_id}: ${del_response.status_code}    WARN
                        END
                    EXCEPT    AS    ${error}
                        Log    Error deleting project: ${error}    WARN
                    END
                END
                Log    Existing projects cleanup complete    INFO
                # Wait a moment for resources to be freed
                Sleep    5s
            ELSE
                Log    No existing projects found, starting with clean state    INFO
            END
        ELSE
            Log    Could not list projects (status ${response.status_code}), continuing anyway    WARN
        END
    EXCEPT    AS    ${cleanup_error}
        Log    Pre-test cleanup encountered error: ${cleanup_error}    WARN
        Log    Continuing with test suite    INFO
    END

    # Initialize tracking lists (for cleanup)
    @{empty_list}=    Create List
    Set Suite Variable    @{DEPLOYED_AIMS_LIST}    @{empty_list}
    Set Suite Variable    @{CREATED_PROJECT_IDS}    @{empty_list}
    Set Suite Variable    @{TEST_API_KEYS}    @{empty_list}    # Required by tested API key keywords

    # Create the project for testing (this will set TEST_PROJECT_ID and related variables)
    A ready project "e2e-aim-catalog" with user access exists

    Log    AIM catalog testing suite initialized    INFO

Cleanup AIM catalog testing
    [Documentation]    Suite teardown for AIM catalog testing.
    ...                Performs best-effort cleanup of any remaining deployments.
    ...                Deletes all created projects (which cascades cleanup of workloads).

    Log    Cleaning up AIM catalog testing suite    INFO

    TRY
        # Check if we have a project
        ${project_exists}=    Run Keyword And Return Status
        ...    Variable Should Exist    ${TEST_PROJECT_ID}

        IF    ${project_exists}
            ${aims_count}=    Get Length    ${DEPLOYED_AIMS_LIST}
            Log    Found ${aims_count} deployed AIMs to clean up    DEBUG

            IF    ${aims_count} > 0
                # Undeploy all tracked AIMs (best effort, don't fail on errors)
                FOR    ${aim_id}    IN    @{DEPLOYED_AIMS_LIST}
                    TRY
                        ${response}=    Undeploy AIM
                        ...    ${aim_id}
                        ...    ${TEST_PROJECT_ID}
                        ...    expected_status=any
                        Log    Undeploy request sent for AIM ${aim_id}    DEBUG
                    EXCEPT
                        Log    Failed to undeploy AIM ${aim_id} (may already be undeployed)    DEBUG
                    END
                END

                Log    AIM undeploy requests completed    INFO

                # Clear the list
                @{empty_list}=    Create List
                Set Suite Variable    @{DEPLOYED_AIMS_LIST}    @{empty_list}
            END
        END
    EXCEPT
        Log    AIM cleanup completed with warnings (expected)    DEBUG
    END

    # Clean up all created projects (this will cascade delete any remaining workloads and API keys)
    TRY
        Clean Up All Created Projects With Wait
    EXCEPT    AS    ${cleanup_error}
        Log    Project cleanup completed with warnings: ${cleanup_error}    DEBUG
    END

    Log    AIM catalog testing suite cleanup complete    INFO
