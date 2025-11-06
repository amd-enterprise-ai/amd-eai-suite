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
    ${endpoint}=            Catalog endpoint        chat/${workload_id}
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
        # Verify chart_id exists in workload_data
        ${chart_id}=            Get From Dictionary     ${workload_data}        chart_id

        # Use the charts/{chart_id}/submit endpoint
        ${endpoint}=            Catalog endpoint        charts/${chart_id}/submit

        # Create a copy of workload_data without chart_id (it's in the URL path)
        ${workload_copy}=       Copy Dictionary         ${workload_data}
        Remove From Dictionary                          ${workload_copy}        chart_id

        # Check if user_inputs is a string that looks like JSON and convert to dictionary
        ${user_inputs}=         Get From Dictionary     ${workload_copy}        user_inputs             default=None

        # If user_inputs exists and is a string that looks like JSON
        IF    $user_inputs is not None and isinstance($user_inputs, str) and $user_inputs.startswith('{')
            ${user_inputs_dict}=    Evaluate                json.loads('''${user_inputs}''')                json
            Set To Dictionary       ${workload_copy}        user_inputs=${user_inputs_dict}
        END

        # Log the request data for debugging
        Log                     Creating workload for chart ${chart_id} with data: ${workload_copy}     level=DEBUG

        ${response}=            Post on session         ${API_SESSION}          ${endpoint}             json=${workload_copy}                           expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to create workload for chart ${workload_data['chart_id']}: ${error}
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
        ${response}=            Post on session         ${API_SESSION}          ${endpoint}             json=${chat_data}       expected_status=${expected_status}              params=${QUERY_PARAMS}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to caht workload for ${}: ${error}
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
        ${response}=            Get on session          ${API_SESSION}          ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
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
        ${response}=            Get on session          ${API_SESSION}          ${endpoint}/${workload_id}                      expected_status=${expected_status}              params=${params}
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

    # Add optional filters if provided
    IF    "${type}" != "${None}"    Set to dictionary    ${params}    type=${type}
    IF    "${status}" != "${None}"    Set to dictionary    ${params}    status=${status}

    TRY
        ${endpoint}=            Workloads endpoint
        ${response}=            Get on session          ${API_SESSION}          ${endpoint}             params=${params}        expected_status=${expected_status}
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
    Create API Session
    TRY
        ${endpoint}=            Workloads endpoint
        ${response}=            Delete on session       ${API_SESSION}          ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
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
    Create API Session
    TRY
        ${endpoint}=            Menaged workloads endpoint
        ${response}=            Delete on session       ${API_SESSION}          ${endpoint}/${workload_id}                      params=${params}        expected_status=${expected_status}
        Log To Console          message=Deleting workload ${workload_id} with params ${params} :${response}
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
    Create API Session
    TRY
        ${endpoint}=            Workloads endpoint
        ${data}=                Create dictionary       ids=${workload_ids}
        ${response}=            Post on session         ${API_SESSION}          ${endpoint}/delete      json=${data}            expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to batch delete workloads (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    ${error_msg}
    END
