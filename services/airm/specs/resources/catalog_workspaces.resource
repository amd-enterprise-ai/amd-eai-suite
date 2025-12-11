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
Resource            airm_projects.resource
Resource            common/resource_tracking.resource
Library             Collections
Library             String
Library             RequestsLibrary


*** Variables ***
${TEST_WORKSPACE_ID}        ${None}
@{CREATED_WORKLOAD_IDS}     # List to track created workspace IDs for cleanup (workspaces are workloads)
${response}                 ${None}


*** Keywords ***
JupyterLab workspace is deployed
    [Documentation]    Deploys a JupyterLab workspace via AIRM API
    ...    Uses default configuration: 1 GPU, standard image
    [Arguments]    ${display_name}=test-jupyter    ${gpus}=1    ${image}=${None}

    ${workspace_image}=    Set Variable If    "${image}" == "${None}"
    ...    rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    ${image}

    ${workspace_data}=    Create Dictionary
    ...    image=${workspace_image}
    ...    gpus=${gpus}
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${response}=    Create workspace
    ...    workspace_type=jupyterlab
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    # Store response for assertions
    Set Test Variable    ${response}    ${response}

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
    [Documentation]    Deploys an MLflow workspace via AIRM API
    ...    MLflow is project-scoped - only one can be Running/Pending per project
    [Arguments]    ${display_name}=test-mlflow

    ${workspace_data}=    Create Dictionary
    ...    image=rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    gpus=0
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${response}=    Create workspace
    ...    workspace_type=mlflow
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    # Store response for assertions
    Set Test Variable    ${response}    ${response}

    Log    Created MLflow workspace ${workspace_id} with name: ${display_name}    INFO

VSCode workspace is deployed
    [Documentation]    Deploys a VSCode workspace via AIRM API
    ...    Uses default configuration: 1 GPU, standard image
    [Arguments]    ${display_name}=test-vscode    ${gpus}=1    ${image}=${None}

    ${workspace_image}=    Set Variable If    "${image}" == "${None}"
    ...    rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    ${image}

    ${workspace_data}=    Create Dictionary
    ...    image=${workspace_image}
    ...    gpus=${gpus}
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${response}=    Create workspace
    ...    workspace_type=vscode
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    # Store response for assertions
    Set Test Variable    ${response}    ${response}

    Log    Created VSCode workspace ${workspace_id} with name: ${display_name}    INFO

VSCode workspace is deployed with custom image
    [Documentation]    Deploys VSCode workspace with specified container image
    [Arguments]    ${image}

    VSCode workspace is deployed    image=${image}

VSCode workspace is deployed with GPU allocation
    [Documentation]    Deploys VSCode workspace with specified GPU count
    [Arguments]    ${gpus}

    VSCode workspace is deployed    gpus=${gpus}

ComfyUI workspace is deployed
    [Documentation]    Deploys a ComfyUI workspace via AIRM API
    ...    Uses default configuration: 0 GPUs (CPU-only), standard image
    [Arguments]    ${display_name}=test-comfyui    ${gpus}=0    ${image}=${None}

    ${workspace_image}=    Set Variable If    "${image}" == "${None}"
    ...    rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    ${image}

    ${workspace_data}=    Create Dictionary
    ...    image=${workspace_image}
    ...    gpus=${gpus}
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${response}=    Create workspace
    ...    workspace_type=comfyui
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=${display_name}
    ...    expected_status=201

    ${workspace_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_WORKSPACE_ID}    ${workspace_id}

    Append To List    ${CREATED_WORKLOAD_IDS}    ${workspace_id}
    Log    Added workspace ${workspace_id} to cleanup list    DEBUG

    # Store response for assertions
    Set Test Variable    ${response}    ${response}

    Log    Created ComfyUI workspace ${workspace_id} with name: ${display_name}    INFO

ComfyUI workspace is deployed with custom image
    [Documentation]    Deploys ComfyUI workspace with specified container image
    [Arguments]    ${image}

    ComfyUI workspace is deployed    image=${image}

ComfyUI workspace is deployed with GPU allocation
    [Documentation]    Deploys ComfyUI workspace with specified GPU count
    [Arguments]    ${gpus}

    ComfyUI workspace is deployed    gpus=${gpus}

Attempting to deploy second MLflow workspace
    [Documentation]    Attempts to deploy a second MLflow workspace (should fail with 409)
    ${workspace_data}=    Create Dictionary
    ...    image=rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0
    ...    gpus=0
    ...    memory_per_gpu=128
    ...    cpu_per_gpu=4

    ${response}=    Create workspace
    ...    workspace_type=mlflow
    ...    workspace_data=${workspace_data}
    ...    project_id=${TEST_PROJECT_ID}
    ...    display_name=test-mlflow-2
    ...    expected_status=409

    Set Test Variable    ${response}    ${response}

Workspace should be visible via API
    [Documentation]    Verifies that the workspace is visible via GET /managed-workloads/{id}
    ...    Polls for workspace to appear in database to handle async operations
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    Wait Until Keyword Succeeds    10 sec    1 sec
    ...    Workspace is in database

    Log    Workspace ${TEST_WORKSPACE_ID} is visible via API    INFO

Workspace is in database
    [Documentation]    Verifies workspace exists in database via API
    ...    Used with polling to wait for async workspace creation
    ${response}=    Get managed workload    ${TEST_WORKSPACE_ID}    expected_status=200
    Set Test Variable    ${response}    ${response}

Workspace should have valid ID and status
    [Documentation]    Verifies workspace response contains valid id and status fields
    Should Not Be Equal    ${response}    ${None}    msg=Response not set. Call 'workspace should be visible via API' first.

    ${json}=    Set Variable    ${response.json()}
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

    ${workspace_response}=    Get managed workload    ${TEST_WORKSPACE_ID}    expected_status=200
    ${json}=    Set Variable    ${workspace_response.json()}
    ${status}=    Get From Dictionary    ${json}    status
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Expected workspace status to be ${expected_status}, but got ${status}
    Set Test Variable    ${response}    ${workspace_response}
    Log    Workspace status: ${status}    INFO

Workspace status should be "${expected_status}" in response
    [Documentation]    Verifies the workspace status in the cached ${response} variable
    ...    Use this immediately after an API call to check the response without extra fetch
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    status
    ${status}=    Get From Dictionary    ${json}    status
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Expected workspace status to be ${expected_status} in response, but got ${status}
    Log    Workspace status in response: ${status}    INFO

# Backward compatibility keywords (can be removed later)
Workspace status should be pending
    [Documentation]    DEPRECATED: Use 'Workspace status should be "Pending"' instead
    Workspace status should be "Pending"

Workspace status should be running
    [Documentation]    DEPRECATED: Use 'Workspace status should be "Running"' instead
    Workspace status should be "Running"

Workspace transitions to "${expected_status}"
    [Documentation]    Waits for workspace to transition to expected status
    ...    Polls the workspace endpoint until status becomes expected value
    ...    Timeout: 20 min (ComfyUI and MLflow download large models and install dependencies)
    Wait Until Keyword Succeeds    20 min    10 sec
    ...    Verify workspace has status "${expected_status}"

Verify workspace has status "${expected_status}"
    [Documentation]    Helper keyword to verify workspace status (used with polling)
    ${workspace_response}=    Get managed workload    ${TEST_WORKSPACE_ID}    expected_status=200
    ${json}=    Set Variable    ${workspace_response.json()}
    ${status}=    Get From Dictionary    ${json}    status
    Log    Polling workspace ${TEST_WORKSPACE_ID}: current status=${status}, expected=${expected_status}    TRACE
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Workspace status is ${status}, expected ${expected_status}
    Set Test Variable    ${response}    ${workspace_response}
    Log    Workspace ${TEST_WORKSPACE_ID} transitioned to ${expected_status}    INFO

# Backward compatibility keywords (can be removed later)
Workspace transitions to running
    [Documentation]    DEPRECATED: Use 'Workspace transitions to "Running"' instead
    Workspace transitions to "Running"

Verify workspace is running
    [Documentation]    DEPRECATED: Use 'Verify workspace has status "Running"' instead
    Verify workspace has status "Running"

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
    ${workspace_response}=    Get managed workload    ${TEST_WORKSPACE_ID}    expected_status=200
    ${json}=    Set Variable    ${workspace_response.json()}

    # URLs are in the 'output' object
    Dictionary Should Contain Key    ${json}    output
    ${output}=    Get From Dictionary    ${json}    output

    Dictionary Should Contain Key    ${output}    external_host
    Dictionary Should Contain Key    ${output}    internal_host

    ${external_host}=    Get From Dictionary    ${output}    external_host
    ${internal_host}=    Get From Dictionary    ${output}    internal_host

    Should Not Be Equal    ${external_host}    ${None}    msg=external_host not yet populated
    Should Not Be Equal    ${internal_host}    ${None}    msg=internal_host not yet populated

    Set Test Variable    ${response}    ${workspace_response}
    Log    Workspace access URLs - External: ${external_host}, Internal: ${internal_host}    INFO

Workspace external URL should be accessible
    [Documentation]    Verifies that the workspace external URL is accessible via HTTP
    ...    Accepts any non-error response (200-499) as success since auth is expected
    ...    Only fails on connection errors or server errors (500+)
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}
    ...    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    # Get the external URL from workspace
    ${workspace_response}=    Get managed workload    ${TEST_WORKSPACE_ID}    expected_status=200
    ${json}=    Set Variable    ${workspace_response.json()}
    ${output}=    Get From Dictionary    ${json}    output
    ${external_host}=    Get From Dictionary    ${output}    external_host

    # Make HTTP request - allow redirects and don't verify SSL for internal testing
    ${http_response}=    GET    ${external_host}    expected_status=any    verify=${False}

    # Accept any non-server-error response (200-499 are all valid)
    # This includes: 200 OK, 301/302 redirects, 401/403 auth challenges
    ${status}=    Set Variable    ${http_response.status_code}
    Should Be True    ${status} < 500
    ...    msg=Workspace URL returned server error ${status}, expected < 500

    Log    Workspace external URL is accessible: ${external_host} (HTTP ${status})    INFO

Workspace is deleted
    [Documentation]    Deletes the workspace via DELETE /workloads/{id}
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set. Deploy workspace first.

    ${response}=    Delete workload    ${TEST_WORKSPACE_ID}    expected_status=204

    Log    Deleted workspace ${TEST_WORKSPACE_ID} via API    INFO

Workspace should not be visible via API
    [Documentation]    Verifies that the workspace has status "Deleted" via GET /managed-workloads/{id}
    ...    Polls until workspace deletion is complete (soft delete with status=Deleted)
    ...    Timeout: 10 min (workspaces involve Helm releases, Kubernetes cleanup, and dispatcher processing)
    ...
    ...    Note: Workspaces use soft delete - records remain in database with status=Deleted
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set.

    Log    Waiting for workspace ${TEST_WORKSPACE_ID} deletion to complete    INFO
    Wait Until Keyword Succeeds    10 min    10 sec
    ...    Verify workspace is fully deleted

    Log    Workspace ${TEST_WORKSPACE_ID} has status Deleted    INFO

Verify workspace is fully deleted
    [Documentation]    Helper to verify workspace has status "Deleted" (soft delete)
    ${response}=    Get managed workload    ${TEST_WORKSPACE_ID}    expected_status=200
    ${status}=    Get From Dictionary    ${response.json()}    status
    Should Be Equal As Strings    ${status}    Deleted
    ...    msg=Expected workspace to have status Deleted, but got ${status}
    Log    Polling: workspace ${TEST_WORKSPACE_ID} status is ${status}    TRACE

Workspace creation should fail with conflict
    [Documentation]    Verifies that workspace creation failed with 409 Conflict
    ${status_code}=    Set Variable    ${response.status_code}
    Should Be Equal As Integers    ${status_code}    409
    ...    msg=Expected 409 Conflict, but got ${status_code}

    Log    Workspace creation correctly failed with 409 Conflict    INFO

"${count}" workspaces of type "${workspace_type}" should be visible in project
    [Documentation]    Verifies that the specified number of workspaces are visible in the project
    ...    Only counts non-deleted workspaces (excludes Deleting/Deleted status)
    ${count_int}=    Convert To Integer    ${count}

    # Get all managed workloads filtered by type
    ${response}=    Get managed workloads
    ...    project_id=${TEST_PROJECT_ID}
    ...    type=${workspace_type}
    ...    expected_status=200

    ${all_workspaces}=    Set Variable    ${response.json()}

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

    Log    Found ${actual_count} ${workspace_type} workspaces in project ${TEST_PROJECT_ID}    INFO

Workspace HTTPRoute should exist in cluster
    [Documentation]    Verifies that workspace has created HTTPRoute in Kubernetes
    ...    Uses TEST_WORKSPACE_ID to find the HTTPRoute
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set.

    # HTTPRoutes are created in the project namespace
    ${result}=    Run Process    kubectl    get    httproute
    ...    -n    ${TEST_PROJECT_SLUG}
    ...    -l    workload.airm.io/workload-id\=${TEST_WORKSPACE_ID}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get HTTPRoute for workspace ${TEST_WORKSPACE_ID}. Error: ${result.stderr}

    ${httproutes_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    ${httproutes}=    Get From Dictionary    ${httproutes_json}    items
    ${count}=    Get Length    ${httproutes}

    Should Be True    ${count} > 0
    ...    msg=No HTTPRoute found for workspace ${TEST_WORKSPACE_ID}

    Log    HTTPRoute exists for workspace ${TEST_WORKSPACE_ID} in namespace ${TEST_PROJECT_SLUG}    INFO

Workspace HTTPRoute should not exist in cluster
    [Documentation]    Verifies that workspace HTTPRoute has been deleted from Kubernetes
    Should Not Be Equal    ${TEST_WORKSPACE_ID}    ${None}    msg=TEST_WORKSPACE_ID not set.

    # Poll for HTTPRoute deletion
    Wait Until Keyword Succeeds    2 min    2 sec
    ...    Verify workspace HTTPRoute is deleted

Verify workspace HTTPRoute is deleted
    [Documentation]    Helper keyword to verify HTTPRoute doesn't exist (used with polling)
    ${result}=    Run Process    kubectl    get    httproute
    ...    -n    ${TEST_PROJECT_SLUG}
    ...    -l    workload.airm.io/workload-id\=${TEST_WORKSPACE_ID}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=kubectl command failed. Error: ${result.stderr}

    ${httproutes_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    ${httproutes}=    Get From Dictionary    ${httproutes_json}    items
    ${count}=    Get Length    ${httproutes}
    Log    Polling HTTPRoute deletion for workspace ${TEST_WORKSPACE_ID}: found ${count} routes    TRACE

    Should Be Equal As Integers    ${count}    0
    ...    msg=HTTPRoute still exists for workspace ${TEST_WORKSPACE_ID}

    Log    HTTPRoute deleted for workspace ${TEST_WORKSPACE_ID}    INFO
