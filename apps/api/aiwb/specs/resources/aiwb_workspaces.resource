# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level workspace testing keywords.
...                 Provides business-logic level keywords for testing workspace operations.
...                 Uses the low-level API keywords from api/workspaces.resource to implement
...                 higher-level testing scenarios for JupyterLab, MLflow, VS Code, and ComfyUI workspaces.
Resource            api/workspaces.resource
Resource            api/workloads.resource
Resource            resources/airm_projects.resource
Resource            resources/common/resource_tracking.resource
Resource            resources/common/resource_lifecycle.resource
Resource            aiwb_common.resource
Library             Collections
Library             String
Library             RequestsLibrary


*** Variables ***
${TEST_WORKSPACE_ID}        ${None}
@{CREATED_WORKLOAD_IDS}     # List to track created workspace IDs for cleanup (workspaces are workloads)


*** Keywords ***
JupyterLab workspace is deployed
    [Documentation]    Deploys a JupyterLab workspace via AIWB API
    ...    Uses default configuration: 1 GPU, standard image
    [Arguments]    ${display_name}=test-jupyter    ${gpus}=1    ${image}=${None}

    IF    "${image}" == "${None}"
        VAR    ${workspace_image}    rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ELSE
        VAR    ${workspace_image}    ${image}
    END

    ${workspace_data}=    Create Dictionary
    ...    image=${workspace_image}
    ...    gpus=${gpus}
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=jupyterlab
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    namespace=${namespace}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    Log    Created JupyterLab workspace ${workspace_id} with name: ${display_name}    INFO

JupyterLab workspace is deployed with custom image
    [Documentation]    Deploys JupyterLab workspace with specified container image
    [Arguments]    ${image}    ${gpus}=0

    JupyterLab workspace is deployed    image=${image}    gpus=${gpus}

JupyterLab workspace is deployed with GPU allocation
    [Documentation]    Deploys JupyterLab workspace with specified GPU count
    [Arguments]    ${gpus}

    JupyterLab workspace is deployed    gpus=${gpus}

MLflow workspace is deployed
    [Documentation]    Deploys an MLflow workspace via AIWB API
    ...    MLflow is project-scoped - only one can be Running/Pending per project
    [Arguments]    ${display_name}=test-mlflow

    ${workspace_data}=    Create Dictionary
    ...    gpus=0
    ...    memory_per_gpu=20
    ...    cpu_per_gpu=1

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=mlflow
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    namespace=${namespace}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    Log    Created MLflow workspace ${workspace_id} with name: ${display_name}    INFO

VSCode workspace is deployed
    [Documentation]    Deploys a VSCode workspace via AIWB API
    ...    Uses default configuration: 1 GPU, standard image
    [Arguments]    ${display_name}=test-vscode    ${gpus}=1    ${image}=${None}

    IF    "${image}" == "${None}"
        VAR    ${workspace_image}    rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ELSE
        VAR    ${workspace_image}    ${image}
    END

    ${workspace_data}=    Create Dictionary
    ...    image=${workspace_image}
    ...    gpus=${gpus}
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=vscode
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    namespace=${namespace}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    Log    Created VSCode workspace ${workspace_id} with name: ${display_name}    INFO

ComfyUI workspace is deployed
    [Documentation]    Deploys a ComfyUI workspace via AIWB API
    ...    Uses default configuration: 0 GPUs (CPU-only), standard image
    [Arguments]    ${display_name}=test-comfyui    ${gpus}=0    ${image}=${None}

    IF    "${image}" == "${None}"
        VAR    ${workspace_image}    rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ELSE
        VAR    ${workspace_image}    ${image}
    END

    ${workspace_data}=    Create Dictionary
    ...    image=${workspace_image}
    ...    gpus=${gpus}
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=comfyui
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    namespace=${namespace}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    Log    Created ComfyUI workspace ${workspace_id} with name: ${display_name}    INFO

Attempting to deploy second MLflow workspace
    [Documentation]    Attempts to deploy a second MLflow workspace (should fail with 409)
    ${workspace_data}=    Create Dictionary
    ...    gpus=0
    ...    memory_per_gpu=20
    ...    cpu_per_gpu=1

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=mlflow
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=test-mlflow-2
    ...    namespace=${namespace}
    ...    expected_status=409

    Set Test Variable    ${TEST_RESPONSE}    ${response}

Attempting to deploy second JupyterLab workspace
    [Documentation]    Attempts to deploy a second JupyterLab workspace (should fail with 409)
    ${workspace_data}=    Create Dictionary
    ...    image=rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    gpus=0
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=jupyterlab
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=jupyter-2
    ...    namespace=${namespace}
    ...    expected_status=any

    Set Test Variable    ${TEST_RESPONSE}    ${response}

Attempting to deploy second VSCode workspace
    [Documentation]    Attempts to deploy a second VSCode workspace (should fail with 409)
    ${workspace_data}=    Create Dictionary
    ...    image=rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    gpus=0
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=vscode
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=vscode-2
    ...    namespace=${namespace}
    ...    expected_status=any

    Set Test Variable    ${TEST_RESPONSE}    ${response}

Attempting to deploy second ComfyUI workspace
    [Documentation]    Attempts to deploy a second ComfyUI workspace (should fail with 409)
    ${workspace_data}=    Create Dictionary
    ...    image=rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    gpus=0
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${namespace}=    Get Project Namespace
    ${response}=    Create workspace
    ...    workspace_type=comfyui
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=comfyui-2
    ...    namespace=${namespace}
    ...    expected_status=any

    Set Test Variable    ${TEST_RESPONSE}    ${response}

Workspace should be visible via API
    [Documentation]    Verifies that the workspace is visible via AIWB workloads API
    ...    Polls for workspace to appear in database to handle async operations
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    Wait Until Keyword Succeeds    10 sec    1 sec
    ...    Workspace is in database

    Log    Workspace ${TEST_WORKSPACE_ID} is visible via API    INFO

Workspace is in database
    [Documentation]    Verifies workspace exists in database via AIWB workloads API
    ...    Used with polling to wait for async workspace creation
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workload    ${TEST_WORKSPACE_ID}    namespace=${namespace}    expected_status=200
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Workspace should have valid ID and status
    [Documentation]    Verifies workspace response contains valid id and status fields
    Should Not Be Equal    ${TEST_RESPONSE}    ${None}    msg=Response not set. Call 'workspace should be visible via API' first.

    ${json}=    Set Variable    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${json}    id
    Dictionary Should Contain Key    ${json}    status

    ${workspace_id}=    Get From Dictionary    ${json}    id
    ${status}=    Get From Dictionary    ${json}    status

    Log    Workspace has valid ID: ${workspace_id}, Status: ${status}    INFO

Workspace status should be "${expected_status}"
    [Documentation]    Verifies the workspace has the expected status by fetching fresh state
    ...    Always fetches current workspace state using TEST_WORKSPACE_ID
    ...    For checking immediate API response, use 'Workspace status should be "${status}" in response'
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}
    ...    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    ${namespace}=    Get Project Namespace
    Verify Resource Status    Get AIWB workload    ${TEST_WORKSPACE_ID}    ${expected_status}    namespace=${namespace}

Workspace transitions to "${expected_status}"
    [Documentation]    Waits for workspace to transition to expected status
    ...    Polls the workspace endpoint until status becomes expected value
    ...    Timeout: 20 min (ComfyUI and MLflow download large models and install dependencies)
    ${namespace}=    Get Project Namespace
    Wait For Resource Status    Get AIWB workload    ${TEST_WORKSPACE_ID}    ${expected_status}    timeout=20 min    interval=10 sec    namespace=${namespace}

Verify workspace has status "${expected_status}"
    [Documentation]    Helper keyword to verify workspace status (used with polling)
    ${namespace}=    Get Project Namespace
    Verify Resource Status    Get AIWB workload    ${TEST_WORKSPACE_ID}    ${expected_status}    namespace=${namespace}

Workspace should have access URL
    [Documentation]    Verifies workspace has external_host and internal_host set
    ...    Polls for URLs to be populated as they may take a few seconds after Running status
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}
    ...    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    # Poll for URLs to be populated (may take a few seconds after Running)
    Wait Until Keyword Succeeds    30 sec    2 sec
    ...    Verify workspace has URLs populated

Verify workspace has URLs populated
    [Documentation]    Helper keyword to verify workspace URLs are set (used with polling)
    ...    AIWB uses computed 'endpoints' field with 'external' and 'internal' keys
    ${namespace}=    Get Project Namespace
    ${workspace_response}=    Get AIWB workload    ${TEST_WORKSPACE_ID}    namespace=${namespace}    expected_status=200
    ${json}=    Set Variable    ${workspace_response.json()}

    # URLs are in the 'endpoints' computed field
    Dictionary Should Contain Key    ${json}    endpoints    msg=Workload should have endpoints field
    ${endpoints}=    Get From Dictionary    ${json}    endpoints
    Should Not Be Equal    ${endpoints}    ${None}    msg=Workload endpoints should not be None

    Dictionary Should Contain Key    ${endpoints}    internal    msg=Endpoints should contain internal URL
    ${internal_url}=    Get From Dictionary    ${endpoints}    internal
    Should Not Be Empty    ${internal_url}    msg=internal endpoint should not be empty

    # External URL may not be present if HTTPRoute is not yet created
    ${has_external}=    Evaluate    'external' in $endpoints
    IF    ${has_external}
        ${external_url}=    Get From Dictionary    ${endpoints}    external
        Log    Workspace access URLs - External: ${external_url}, Internal: ${internal_url}    INFO
    ELSE
        Log    Workspace access URLs - Internal: ${internal_url} (external not yet available)    INFO
    END

Workspace external URL should be accessible
    [Documentation]    Verifies that the workspace external URL is accessible via HTTP
    ...    Accepts any non-error response (200-499) as success since auth is expected
    ...    Only fails on connection errors or server errors (500+)
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}
    ...    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    # Get the external URL from workspace endpoints
    ${namespace}=    Get Project Namespace
    ${workspace_response}=    Get AIWB workload    ${TEST_WORKSPACE_ID}    namespace=${namespace}    expected_status=200
    ${json}=    Set Variable    ${workspace_response.json()}
    ${endpoints}=    Get From Dictionary    ${json}    endpoints
    Dictionary Should Contain Key    ${endpoints}    external    msg=Workspace should have external endpoint URL
    ${external_url}=    Get From Dictionary    ${endpoints}    external

    # Make HTTP request - allow redirects and don't verify SSL for internal testing
    ${http_response}=    GET    ${external_url}    expected_status=any    verify=${False}

    # Accept any non-server-error response (200-499 are all valid)
    # This includes: 200 OK, 301/302 redirects, 401/403 auth challenges
    ${status}=    Set Variable    ${http_response.status_code}
    Should Be True    ${status} < 500
    ...    msg=Workspace URL returned server error ${status}, expected < 500

    Log    Workspace external URL is accessible: ${external_url} (HTTP ${status})    INFO

Workspace is deleted
    [Documentation]    Deletes the workspace via AIWB DELETE /namespaces/{namespace}/workloads/{id}
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    ${namespace}=    Get Project Namespace
    ${response}=    Delete AIWB workload    ${TEST_WORKSPACE_ID}    namespace=${namespace}    expected_status=204

    Log    Deleted workspace ${TEST_WORKSPACE_ID} via API    INFO

Workspace should not be visible via API
    [Documentation]    Verifies that the workspace has status "Deleted" via AIWB workloads API
    ...    Polls until workspace deletion is complete (soft delete with status=Deleted)
    ...    Timeout: 10 min (workspaces involve Kubernetes resource cleanup)
    ...
    ...    Note: Workspaces use soft delete - records remain in database with status=Deleted
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set.

    Log    Waiting for workspace ${TEST_WORKSPACE_ID} deletion to complete    INFO
    ${namespace}=    Get Project Namespace
    Wait For Resource Status    Get AIWB workload    ${TEST_WORKSPACE_ID}    Deleted    timeout=10 min    interval=10 sec    namespace=${namespace}
    Log    Workspace ${TEST_WORKSPACE_ID} has status Deleted    INFO

Verify workspace is fully deleted
    [Documentation]    Helper to verify workspace has status "Deleted" (soft delete)
    ${namespace}=    Get Project Namespace
    Verify Resource Status    Get AIWB workload    ${TEST_WORKSPACE_ID}    Deleted    namespace=${namespace}

Workspace creation should fail with conflict
    [Documentation]    Verifies that workspace creation failed with 409 Conflict
    ${status_code}=    Set Variable    ${TEST_RESPONSE.status_code}
    Should Be Equal As Integers    ${status_code}    409
    ...    msg=Expected 409 Conflict, but got ${status_code}

    Log    Workspace creation correctly failed with 409 Conflict    INFO

"${count}" workspaces of type "${workspace_type}" should be visible in project
    [Documentation]    Verifies that the specified number of workspaces are visible in the namespace
    ...    Only counts non-deleted workspaces (excludes Deleting/Deleted status)
    ${count_int}=    Convert To Integer    ${count}

    # Get all workloads filtered by type via AIWB API
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workloads
    ...    namespace=${namespace}
    ...    workload_type=${workspace_type}
    ...    expected_status=200

    # Extract data field from response (ListResponse has 'data' key)
    ${response_json}=    Set Variable    ${response.json()}
    ${all_workspaces}=    Get From Dictionary    ${response_json}    data

    # Filter out workspaces with Deleting or Deleted status
    ${active_workspaces}=    Create List
    FOR    ${workspace}    IN    @{all_workspaces}
        ${status}=    Get From Dictionary    ${workspace}    status
        IF    "${status}" not in ["Deleting", "Deleted"]
            Append To List    ${active_workspaces}    ${workspace}
        END
    END

    ${actual_count}=    Get Length    ${active_workspaces}

    Should Be Equal As Integers    ${actual_count}    ${count_int}
    ...    msg=Expected ${count_int} ${workspace_type} workspaces, found ${actual_count}

    Log    Found ${actual_count} ${workspace_type} workspaces in namespace    INFO

Clean Up Workspace Test Resources
    [Documentation]    Clean up all resources created during workspace tests.
    ...    Uses AIWB workload endpoint for workspace cleanup, then cleans up projects.
    ${tracking_list}=    Get Variable Value    ${CREATED_WORKLOAD_IDS}    ${EMPTY}
    ${count}=    Get Length    ${tracking_list}
    IF    ${count} > 0
        Log    Cleaning up ${count} workspace(s) via AIWB API    INFO
        ${namespace}=    Get Project Namespace
        FOR    ${workload_id}    IN    @{CREATED_WORKLOAD_IDS}
            TRY
                Delete AIWB workload    ${workload_id}    namespace=${namespace}    expected_status=any
                Log    Deleted workspace ${workload_id}    INFO
            EXCEPT    AS    ${error}
                Log    Failed to delete workspace ${workload_id}: ${error}    WARN
            END
        END
        @{empty_list}=    Create List
        Set Suite Variable    ${CREATED_WORKLOAD_IDS}    ${empty_list}
    END
    Clean Up All Created Projects
