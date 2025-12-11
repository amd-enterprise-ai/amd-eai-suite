# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API workloads endpoints.
...                 Provides direct API operation wrappers for the /workloads endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Library             OperatingSystem
Resource            common.resource


*** Variables ***
${HEADERS}      Content-Type=application/json


*** Keywords ***
Workloads endpoint
    [Documentation]    Return the full workloads endpoint url
    ${endpoint}=            Catalog endpoint        workloads
    RETURN                  ${endpoint}

Menaged workloads endpoint
    [Documentation]    Return the full workloads endpoint url
    ${endpoint}=            Catalog endpoint        managed-workloads
    RETURN                  ${endpoint}

Chat endpoint
    [Documentation]    Return the full workloads endpoint url
    [Arguments]             ${workload_id}
    ${endpoint}=            Catalog endpoint        managed-workloads/${workload_id}/chat
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
    Create api session
    TRY
        ${chart_id}=            Get From Dictionary     ${workload_data}        chart_id

        ${endpoint}=            Catalog endpoint        charts/${chart_id}/submit

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
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to create workload for chart ${workload_data['chart_id']}: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

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
    Create api session
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

Chat workload
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
    [Arguments]             ${chat_data}            ${expected_status}=any
    Create api session
    TRY
        ${endpoint}=            Chat endpoint           ${TEST_WORKLOAD_ID}
        Log To Console          message=Chatting workload for chart ${TEST_WORKLOAD_ID} with data: ${chat_data}
        Log To Console          message=Endpoint = ${endpoint}
        ${response}=            Safe Post Request       ${endpoint}             json=${chat_data}       expected_status=${expected_status}              params=${QUERY_PARAMS}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to chat with workload: ${error}
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
    Create api session
    TRY
        ${endpoint}=            Workloads endpoint
        Log                     GET ${endpoint}/${workload_id}    DEBUG
        ${response}=            Safe Get Request        ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
        Log                     Response status: ${response.status_code}    DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_detail}=        Set variable            ${EMPTY}

        TRY
            ${error_text}=          Set variable            ${error.response.text}
            ${error_detail}=        Set variable            \nStatus code: ${error.response.status_code}\nResponse: ${error_text}
        EXCEPT
            ${error_detail}=        Set variable            \nNo additional error details available.
        END

        ${error_msg}=           Set variable            Failed to get workload ${workload_id}: ${error}${error_detail}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

Get menaged workload
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
    Create api session
    TRY
        ${endpoint}=            Menaged workloads endpoint
        ${response}=            Safe Get Request        ${endpoint}/${workload_id}                      expected_status=${expected_status}              params=${params}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_detail}=        Set variable            ${EMPTY}

        # Extract more detailed error info when available
        TRY
            ${error_text}=          Set variable            ${error.response.text}
            ${error_detail}=        Set variable            \nStatus code: ${error.response.status_code}\nResponse: ${error_text}
        EXCEPT
            ${error_detail}=        Set variable            \nNo additional error details available.
        END

        ${error_msg}=           Set variable            Failed to get workload ${workload_id}: ${error}${error_detail}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

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
    Create api session
    ${params}=              Create dictionary

    IF    "${type}" != "${None}"    Set to dictionary    ${params}    type=${type}
    IF    "${status}" != "${None}"    Set to dictionary    ${params}    status=${status}

    TRY
        ${endpoint}=            Workloads endpoint
        Log                     GET ${endpoint} with params: ${params}    DEBUG
        ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=${expected_status}
        Log                     Response status: ${response.status_code}    DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to list workloads with params ${params}: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

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
    Create api session
    TRY
        ${endpoint}=            Workloads endpoint
        Log                     DELETE ${endpoint}/${workload_id}    DEBUG
        ${response}=            Safe Delete Request     ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
        Log                     Response status: ${response.status_code}    DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to delete workload ${workload_id}: ${error}.
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

Delete menaged workload
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
    Create api session
    TRY
        ${endpoint}=            Menaged workloads endpoint
        Log                     DELETE ${endpoint}/${workload_id}    DEBUG
        Log                     Request params: ${params}    DEBUG
        ${response}=            Safe Delete Request     ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
        Log                     Response status: ${response.status_code}    DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to delete workload ${workload_id}: ${error}.
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

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
    Create api session
    TRY
        ${endpoint}=            Workloads endpoint
        ${data}=                Create dictionary       ids=${workload_ids}
        Log                     POST ${endpoint}/delete    DEBUG
        Log                     Request body: ${data}    DEBUG
        ${response}=            Safe Post Request       ${endpoint}/delete      json=${data}            expected_status=${expected_status}
        Log                     Response status: ${response.status_code}    DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to batch delete workloads (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

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
    Create API Session
    ${params}=              Create Dictionary       limit=${limit}          direction=${direction}
    IF    "${level}" != "${None}"
        Set To Dictionary       ${params}               level=${level}
    END
    TRY
        ${endpoint}=            Catalog endpoint        workloads/${workload_id}/logs
        ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to get logs for workload ${workload_id}: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END
