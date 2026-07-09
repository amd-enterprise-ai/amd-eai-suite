# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API workspace endpoints.
...                 Provides direct API operation wrappers for the /workspaces endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource
Resource            resources/deployment.resource


*** Variables ***
${HEADERS}    Content-Type=application/json


*** Keywords ***
Workspaces endpoint
    [Documentation]    Return the workspaces collection endpoint URL for a project.
    ...    Pattern: /projects/{project}/workspaces
    [Arguments]    ${namespace}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${namespace}/workspaces
    RETURN    ${endpoint}

Workspace endpoint by id
    [Documentation]    Return the per-instance workspace endpoint URL.
    ...    Pattern: /projects/{project}/workspaces/{workload_id}
    [Arguments]    ${workload_id}    ${namespace}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${namespace}/workspaces/${workload_id}
    RETURN    ${endpoint}

Delete workspace
    [Documentation]    Delete a specific workspace via AIWB API
    ...    Uses: DELETE /projects/{project}/workspaces/{workload_id}
    [Arguments]    ${workload_id}    ${namespace}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Workspace endpoint by id    ${workload_id}    ${namespace}
    Log    DELETE ${endpoint}    DEBUG
    ${response}=    Safe Delete Request    ${endpoint}    expected_status=${expected_status}
    Log    Delete workspace response: status=${response.status_code}    DEBUG
    RETURN    ${response}

Create workspace
    [Documentation]    Create a new workspace of specified type via AIWB API
    ...
    ...    Args:
    ...    workspace_type (str): Type of workspace (jupyterlab, mlflow, vscode, comfyui) — sent as
    ...    workspaceType in the request body
    ...    workspace_data (dict): Workspace configuration including:
    ...    - image: Container image to use
    ...    - gpus: Number of GPUs (0-8)
    ...    - memoryPerGpu: Memory per GPU in Gi
    ...    - cpuPerGpu: CPU per GPU in vCPUs
    ...    projectId (str): UUID of the project
    ...    displayName (str): Display name for the workspace
    ...    expected_status (int): Expected HTTP status code (default: any)
    ...
    ...    Returns:
    ...    response: API response containing the created workspace (ChartWorkloadResponse)
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]    ${workspace_type}    ${workspace_data}    ${project_id}    ${display_name}    ${namespace}    ${expected_status}=any
    Create api session    aiwb

    TRY
        # Build query parameters - projectId is required, displayName is optional
        VAR    &{params}    projectId=${project_id}

        IF    "${display_name}" != "${None}"
            Set To Dictionary    ${params}    displayName=${display_name}
        END

        # Merge workspaceType into the request body (workspace type goes in body, not path)
        VAR    &{full_data}    workspaceType=${workspace_type}    &{workspace_data}

        # Get endpoint - uses AIWB /projects/{project}/workspaces
        ${endpoint}=    Workspaces endpoint    namespace=${namespace}

        Log    POST ${endpoint} with params=${params}, data=${full_data}    DEBUG

        ${response}=    Safe Post Request    ${endpoint}
        ...    json=${full_data}
        ...    params=${params}
        ...    expected_status=${expected_status}

        Log    Response status: ${response.status_code}    DEBUG

        # Only log workspace ID if response was successful (2xx)
        IF    ${response.status_code} >= 200 and ${response.status_code} < 300
            ${workspace_id}=    Get From Dictionary    ${response.json()}    id
            Log    Created workspace ID: ${workspace_id}    DEBUG
        END

        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        VAR    ${error_msg}    Failed to create ${workspace_type} workspace: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END
