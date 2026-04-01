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
    [Documentation]    Return the full workspaces endpoint URL for a specific workspace type
    ...    Pattern: /namespaces/{namespace}/workspaces/{workspace_type}
    [Arguments]    ${workspace_type}    ${namespace}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=namespaces/${namespace}/workspaces/${workspace_type}
    RETURN    ${endpoint}

Create workspace
    [Documentation]    Create a new workspace of specified type via AIWB API
    ...
    ...    Args:
    ...    workspace_type (str): Type of workspace (jupyterlab, mlflow, vscode, comfyui)
    ...    workspace_data (dict): Workspace configuration including:
    ...    - image: Container image to use
    ...    - gpus: Number of GPUs (0-8)
    ...    - memory_per_gpu: Memory per GPU in Gi
    ...    - cpu_per_gpu: CPU per GPU in vCPUs
    ...    project_id (str): UUID of the project
    ...    display_name (str): Display name for the workspace
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
        # Build query parameters - project_id is required, display_name is optional
        &{params}=    Create Dictionary
        ...    project_id=${project_id}

        IF    "${display_name}" != "${None}"
            Set To Dictionary    ${params}    display_name=${display_name}
        END

        # Get endpoint - uses AIWB /namespaces/{namespace}/workspaces/{workspace_type}
        ${endpoint}=    Workspaces endpoint    ${workspace_type}    namespace=${namespace}

        Log    POST ${endpoint} with params=${params}, data=${workspace_data}    DEBUG

        ${response}=    Safe Post Request    ${endpoint}
        ...    json=${workspace_data}
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
        ${error_msg}=    Set Variable    Failed to create ${workspace_type} workspace: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END
