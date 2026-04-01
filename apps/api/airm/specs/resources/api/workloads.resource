# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIRM API workloads endpoints.
...                 Provides direct API operation wrappers for the /workloads endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Library             OperatingSystem
Resource            resources/api/common.resource


*** Variables ***
${HEADERS}      Content-Type=application/json


*** Keywords ***
Workloads endpoint
    [Documentation]    Return the full workloads endpoint url
    ${endpoint}=            Service API Endpoint    airm    endpoint=workloads
    RETURN                  ${endpoint}

Create workload
    [Documentation]    Create a new workload using the provided data
    ...
    ...    Args:
    ...    workload_data (dict): Workload submission parameters including:
    ...    - chart_id: ID of the chart to use
    ...    - model_id: Optional ID of the model to use
    ...    - user_inputs: Optional user inputs to override chart defaults
    ...
    ...    Return:
    ...    response: API response containing the created workload
    ...
    ...    Raise:
    ...    HTTPError: If the API request fails
    [Arguments]             ${workload_data}        ${expected_status}=any
    Create api session    airm
    ${chart_id}=            Get From Dictionary     ${workload_data}        chart_id

    ${endpoint}=            Service API Endpoint    airm    endpoint=charts/${chart_id}/submit

    ${workload_copy}=       Copy Dictionary         ${workload_data}
    Remove From Dictionary                          ${workload_copy}        chart_id

    ${user_inputs}=         Get From Dictionary     ${workload_copy}        user_inputs             default=None

    IF    $user_inputs is not None and isinstance($user_inputs, str) and $user_inputs.startswith('{')
        ${user_inputs_dict}=    Evaluate                json.loads('''${user_inputs}''')                json
        Set To Dictionary       ${workload_copy}        user_inputs=${user_inputs_dict}
    END

    Log                     POST ${endpoint}    DEBUG
    Log                     Request body: ${workload_copy}    DEBUG

    ${response}=            Safe Post Request       ${endpoint}             json=${workload_copy}                           expected_status=${expected_status}
    Log                     Response status: ${response.status_code}    DEBUG
    RETURN                  ${response}

Submit workload with manifest
    [Documentation]    Submit a workload directly with a Kubernetes manifest file
    ...
    ...    This uses the POST /workloads endpoint to submit workloads without requiring charts.
    ...    The manifest file should contain valid Kubernetes YAML (max 2MB).
    ...
    ...    Args:
    ...    manifest_path (str): Path to the Kubernetes manifest YAML file
    ...    project_id (str): UUID of the project to submit the workload to
    ...    display_name (str): Display name for the workload (2-256 chars, alphanumeric + _-.,:()+@#)
    ...    workload_type (str): Type of workload (CUSTOM, INFERENCE, TRAINING, WORKSPACE, etc.)
    ...
    ...    Returns:
    ...    response: API response containing the created workload
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]             ${manifest_path}        ${project_id}           ${display_name}         ${workload_type}=CUSTOM                         ${expected_status}=any
    Create api session    airm
    TRY
        ${manifest_content}=    Get Binary File         ${manifest_path}

        @{manifest_file}=       Create list             manifest.yaml           ${manifest_content}
        &{files}=               Create dictionary       manifest=${manifest_file}

        &{params}=              Create dictionary
        ...                     project_id=${project_id}
        ...                     workload_type=${workload_type}
        ...                     display_name=${display_name}

        ${endpoint}=            Workloads endpoint
        Log                     POST ${endpoint} with manifest    DEBUG
        Log                     Request params: ${params}    DEBUG

        ${access_token}=        Authorization token
        &{headers}=             Create Dictionary       Authorization=Bearer ${access_token}

        ${response}=            POST                    ${endpoint}             headers=${headers}      files=${files}          params=${params}                                expected_status=${expected_status}
        Log                     Response status: ${response.status_code}    DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to submit workload with manifest ${manifest_path}: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

Get workload
    [Documentation]    Retrieve a specific workload by ID
    ...
    ...    Args:
    ...    workload_id (str): UUID of the workload to retrieve
    ...
    ...    Return:
    ...    response: API response containing the workload details
    ...
    ...    Raise:
    ...    HTTPError: If the workload is not found or request fails
    [Arguments]             ${workload_id}          ${expected_status}=any                          ${params}=${None}
    Create api session    airm
    ${endpoint}=            Workloads endpoint
    Log                     GET ${endpoint}/${workload_id}    DEBUG
    ${response}=            Safe Get Request        ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
    Log                     Response status: ${response.status_code}    DEBUG
    RETURN                  ${response}

Get workloads
    [Documentation]    List workloads with optional filtering.
    ...
    ...    Args:
    ...    type (list, optional): Filter by workload type(s)
    ...    status (list, optional): Filter by workload status(es)
    ...
    ...    Returns:
    ...    response: API response containing list of workloads
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]             ${type}=${None}         ${status}=${None}       ${expected_status}=any
    Create api session    airm
    ${params}=              Create dictionary

    IF    "${type}" != "${None}"    Set to dictionary    ${params}    type=${type}
    IF    "${status}" != "${None}"    Set to dictionary    ${params}    status=${status}

    ${endpoint}=            Workloads endpoint
    Log                     GET ${endpoint} with params: ${params}    DEBUG
    ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=${expected_status}
    Log                     Response status: ${response.status_code}    DEBUG
    RETURN                  ${response}

Delete workload
    [Documentation]    Delete a specific workload.
    ...
    ...    Args:
    ...    workload_id (str): UUID of the workload to delete
    ...
    ...    Returns:
    ...    response: API response (empty on success)
    ...
    ...    Raises:
    ...    HTTPError: If the workload is not found or deletion fails
    [Arguments]             ${workload_id}          ${expected_status}=any                          ${params}=${None}
    Create api session    airm
    ${endpoint}=            Workloads endpoint
    Log                     DELETE ${endpoint}/${workload_id}    DEBUG
    ${response}=            Safe Delete Request     ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
    Log                     Response status: ${response.status_code}    DEBUG
    RETURN                  ${response}

Batch delete workloads
    [Documentation]    Delete multiple workloads in a batch.
    ...
    ...    Args:
    ...    workload_ids (list): List of workload UUIDs to delete
    ...
    ...    Returns:
    ...    response: API response containing deletion status
    ...
    ...    Raises:
    ...    HTTPError: If the request fails
    [Arguments]             ${workload_ids}         ${expected_status}=any
    Create api session    airm
    ${endpoint}=            Workloads endpoint
    ${data}=                Create dictionary       ids=${workload_ids}
    Log                     POST ${endpoint}/delete    DEBUG
    Log                     Request body: ${data}    DEBUG
    ${response}=            Safe Post Request       ${endpoint}/delete      json=${data}            expected_status=${expected_status}
    Log                     Response status: ${response.status_code}    DEBUG
    RETURN                  ${response}

Get workload logs
    [Documentation]    Retrieve logs for a specific workload
    ...
    ...    Args:
    ...    workload_id (str): UUID of the workload to get logs for
    ...    limit (int, optional): Maximum number of log entries to retrieve (default: 100)
    ...    level (str, optional): Log level filter (trace, debug, info, warning, error, critical)
    ...    direction (str, optional): Direction of log retrieval - 'forward' or 'backward' (default: forward)
    ...
    ...    Returns:
    ...    response: API response containing logs and pagination metadata
    ...
    ...    Raises:
    ...    HTTPError: If the workload is not found or request fails
    [Arguments]             ${workload_id}          ${limit}=100            ${level}=${None}        ${direction}=forward    ${expected_status}=any
    Create API Session    airm
    ${params}=              Create Dictionary       limit=${limit}          direction=${direction}
    IF    "${level}" != "${None}"
        Set To Dictionary       ${params}               level=${level}
    END
    ${endpoint}=            Service API Endpoint    airm    endpoint=workloads/${workload_id}/logs
    ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=${expected_status}
    RETURN                  ${response}
