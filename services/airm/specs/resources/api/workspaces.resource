# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API workspace endpoints.
...                 Provides direct API operation wrappers for the /workspaces endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            common.resource


*** Variables ***
${HEADERS}    Content-Type=application/json


*** Keywords ***
Workspaces endpoint
    [Documentation]    Return the full workspaces endpoint URL for a specific workspace type
    [Arguments]    ${workspace_type}
    ${endpoint}=    Catalog endpoint    workspaces/${workspace_type}
    RETURN    ${endpoint}

Managed workloads endpoint
    [Documentation]    Return the full managed-workloads endpoint URL
    ${endpoint}=    Catalog endpoint    managed-workloads
    RETURN    ${endpoint}

Create workspace
    [Documentation]    Create a new workspace of specified type
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
    ...
    ...    Returns:
    ...    response: API response containing the created workspace
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]    ${workspace_type}    ${workspace_data}    ${project_id}    ${display_name}    ${expected_status}=any
    Create api session

    TRY
        # Build query parameters
        &{params}=    Create Dictionary
        ...    project_id=${project_id}

        IF    "${display_name}" != "${None}"
            Set To Dictionary    ${params}    display_name=${display_name}
        END

        # Get endpoint
        ${endpoint}=    Workspaces endpoint    ${workspace_type}

        Log    POST ${endpoint} with params=${params}, data=${workspace_data}    DEBUG

        ${response}=    POST On Session    ${API_SESSION}    ${endpoint}
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

Get managed workload
    [Documentation]    Retrieve a specific managed workload by ID
    ...
    ...    Args:
    ...    workload_id (str): UUID of the workload to retrieve
    ...
    ...    Returns:
    ...    response: API response containing the workload details
    ...
    ...    Raises:
    ...    HTTPError: If the workload is not found or request fails
    [Arguments]    ${workload_id}    ${expected_status}=any
    Create api session

    TRY
        ${endpoint}=    Managed workloads endpoint
        Log    GET ${endpoint}/${workload_id}    DEBUG
        ${response}=    GET On Session    ${API_SESSION}    ${endpoint}/${workload_id}
        ...    expected_status=${expected_status}
        Log    Response status: ${response.status_code}    DEBUG
        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_detail}=    Set Variable    ${EMPTY}

        # Extract more detailed error info when available
        TRY
            ${error_text}=    Set Variable    ${error.response.text}
            ${error_detail}=    Set Variable    \nStatus code: ${error.response.status_code}\nResponse: ${error_text}
        EXCEPT
            ${error_detail}=    Set Variable    \nNo additional error details available.
        END

        ${error_msg}=    Set Variable    Failed to get managed workload ${workload_id}: ${error}${error_detail}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END

Get managed workloads
    [Documentation]    List managed workloads with optional filtering
    ...
    ...    Args:
    ...    project_id (str): Filter by project ID
    ...    type (str, optional): Filter by workload type
    ...    status (str, optional): Filter by workload status
    ...
    ...    Returns:
    ...    response: API response containing list of workloads
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]    ${project_id}    ${type}=${None}    ${status}=${None}    ${expected_status}=any
    Create api session

    &{params}=    Create Dictionary    project_id=${project_id}

    IF    "${type}" != "${None}"
        Set To Dictionary    ${params}    type=${type}
    END
    IF    "${status}" != "${None}"
        Set To Dictionary    ${params}    status=${status}
    END

    TRY
        ${endpoint}=    Managed workloads endpoint
        Log    GET ${endpoint} with params=${params}    DEBUG
        ${response}=    GET On Session    ${API_SESSION}    ${endpoint}
        ...    params=${params}
        ...    expected_status=${expected_status}
        Log    Response status: ${response.status_code}, found ${response.json().__len__()} workloads    DEBUG
        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set Variable    Failed to list managed workloads with params ${params}: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END
