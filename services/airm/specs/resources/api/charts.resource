# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keywords for interacting with the Catalog API charts endpoints.
...                 Provides low-level keywords for managing Helm charts through the API.
...                 Includes operations for creating, listing, and deleting charts.
Library             RequestsLibrary
Library             Collections
Library             OperatingSystem
Resource            common.resource
Resource            ../airm_projects.resource


*** Variables ***
&{HEADERS}      Content-Type=multipart/form-data
# Default value for signature file - can be overridden by test suites
${SIGNATURE_FILE}   ${CURDIR}/../../test_data/charts/signature.yaml


*** Keywords ***
Charts endpoint
    [Documentation]    Returns the full charts endpoint URL
    ${endpoint}=            Catalog endpoint        charts
    RETURN                  ${endpoint}


*** Keywords ***
Create chart without files
    [Documentation]    Create a new chart via API without uploading template files
    ...    Uses the POST /v1/charts endpoint with just name, type, and user_inputs (no files)
    ...
    ...    Args:
    ...    name (str): Name of the chart
    ...    type (str): Chart type (INFERENCE, FINE_TUNING, etc.)
    ...    user_inputs (dict): Default user inputs for the chart
    ...
    ...    Returns:
    ...    response: API response containing the created chart
    [Arguments]             ${name}                 ${type}=INFERENCE       ${user_inputs}=${None}  ${expected_status}=any

    # Prepare user_inputs
    ${inputs}=              Set Variable If         ${user_inputs} is not None              ${user_inputs}          {}

    # Create the request data (multipart/form-data format)
    ${data}=                Create dictionary       name=${name}            type=${type}            project_id=${TEST_PROJECT_ID}                user_inputs=${inputs}

    ${endpoint} =           Charts endpoint
    ${access_token}=        Authorization token
    &{headers}=             Create Dictionary       Authorization=Bearer ${access_token}

    Log                     POST ${endpoint} with data: ${data}             DEBUG
    ${response}=            POST                    ${endpoint}             headers=${headers}      data=${data}            expected_status=${expected_status}
    Log                     Chart creation response: status=${response.status_code}                 DEBUG
    IF    ${response.status_code} in [200, 201]
        ${response_json}=       Set Variable            ${response.json()}
        ${chart_id}=        Get From Dictionary     ${response_json}        id
        ${chart_name}=      Get From Dictionary     ${response_json}        name
        Log                     Created chart ${chart_id} (${chart_name})      INFO
    END
    RETURN                  ${response}

Create chart request
    [Documentation]    Create a new chart with the provided files.
    ...
    ...    Args:
    ...    name (str): Name of the chart
    ...    template_file (str): Path to chart template file
    ...    values_file (str): Path to values YAML file
    ...    values_schema_file (str): Path to values schema JSON file
    ...    signature_file (str): Path to signature YAML file (optional, defaults to test data)
    ...    additional_files (list): Optional additional chart files
    ...
    ...    Returns:
    ...    response: API response containing the created chart
    ...
    ...    Raises:
    ...    HTTPError: If chart creation fails
    ...    IOError: If any of the required files cannot be read
    [Arguments]             ${name}                 ${template_file}        ${values_file}          ${values_schema_file}       ${signature_file}=${SIGNATURE_FILE}     @{additional_files}     ${expected_status}=any
    ${template_content}=    Get Binary File         ${template_file}
    ${values_content}=      Get Binary File         ${values_file}
    ${schema_content}=      Get Binary File         ${values_schema_file}
    ${signature_content}=   Get Binary File         ${signature_file}

    # Format: {'field_name': ('filename', filedata, 'content-type')}
    ${data}=                Create dictionary       name=${name}            type=INFERENCE          project_id=${TEST_PROJECT_ID}
    @{template}=            Create list             template.yaml           ${template_content}
    @{values}=              Create list             values.yaml             ${values_content}
    @{schema}=              Create list             schema.json             ${schema_content}
    @{signature}=           Create list             signature.yaml          ${signature_content}
    &{files}=               Create dictionary
    ...                     files=${template}
    ...                     user_inputs=${values}
    ...                     signature=${signature}

    ${endpoint} =           Charts endpoint
    ${access_token}=        Authorization token
    &{headers}=             Create Dictionary       Authorization=Bearer ${access_token}

    Log                     POST ${endpoint} with data: ${data}             DEBUG
    ${response}=            POST                    ${endpoint}             headers=${headers}      data=${data}            files=${files}          expected_status=${expected_status}
    Log                     Chart creation response: status=${response.status_code}                 DEBUG
    IF    ${response.status_code} in [200, 201]
        ${response_json}=       Set Variable            ${response.json()}
        ${chart_id}=        Get From Dictionary     ${response_json}        id
        ${chart_name}=      Get From Dictionary     ${response_json}        name
        Log                     Created chart ${chart_id} (${chart_name})      INFO
    END
    RETURN                  ${response}

List charts request
    [Documentation]    List charts with pagination and sorting.
    ...
    ...    Args:
    ...    page_number (int): Page number for pagination (default: 1)
    ...    page_size (int): Number of items per page (default: 10)
    ...    sort_by (str): Field to sort by (default: created_at)
    ...    sort_order (str): Sort direction - asc or desc (default: desc)
    ...
    ...    Returns:
    ...    response: API response containing list of charts
    [Arguments]             ${page_number}=1        ${page_size}=10         ${sort_by}=created_at                           ${sort_order}=desc      ${expected_status}=any
    ${params}=              Create dictionary
    ...                     page_number=${page_number}
    ...                     page_size=${page_size}
    ...                     sort_by=${sort_by}
    ...                     sort_order=${sort_order}

    Create api session
    ${endpoint} =           Charts endpoint
    Log                     GET ${endpoint} with params: ${params}          DEBUG
    ${response}=            Safe Get Request          ${endpoint}             params=${params}        expected_status=${expected_status}
    Log                     List charts response: status=${response.status_code}                    DEBUG
    RETURN                  ${response}

Delete chart
    [Documentation]    Delete a specific chart.
    ...
    ...    Args:
    ...    chart_id (str): UUID of the chart to delete
    ...
    ...    Returns:
    ...    response: API response (empty on success)
    ...
    ...    Raises:
    ...    HTTPError: If the chart is not found or deletion fails
    [Arguments]             ${chart_id}             ${expected_status}=any
    Create api session
    TRY
        ${endpoint} =           Charts endpoint
        Log                     DELETE ${endpoint}/${chart_id}  DEBUG
        ${response}=            Safe Delete Request       ${endpoint}/${chart_id}                         expected_status=${expected_status}
        Log                     Delete chart response: status=${response.status_code}                   DEBUG
        IF    ${response.status_code} == 204
            Log                     Deleted chart ${chart_id}       INFO
        END
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to delete chart ${chart_id} (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

Get charts
    [Documentation]    Get list of all charts
    [Arguments]             ${expected_status}=any
    Create api session
    ${endpoint}=            Charts endpoint
    Log                     GET ${endpoint}         DEBUG
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             expected_status=${expected_status}
    Log                     Get charts response: status=${response.status_code}                     DEBUG
    RETURN                  ${response}

Create chart request is sent
    [Documentation]    Sends a request to create a new chart and stores the ID
    [Arguments]             ${name}=${TEST_CHART_NAME}                      ${template}=${TEMPLATE_FILE}                    ${values}=${VALUES_FILE}                        ${schema}=${SCHEMA_FILE}       ${signature}=${SIGNATURE_FILE}
    ${response}=            Create chart request    ${name}                 ${template}             ${values}               ${schema}       ${signature}
    Set test variable       ${response}             ${response}

    # Initialize TEST_CHART_ID variable
    Set test variable       ${TEST_CHART_ID}        unknown-chart-id

    # Check status first
    Response status should be 201

    # Extract chart ID from successful response
    ${json}=                Set variable            ${response.json()}

    ${chart_id}=            Get from dictionary     ${json}                 id
    Set test variable       ${TEST_CHART_ID}        ${chart_id}

    Append To List          ${CREATED_CHART_IDS}    ${chart_id}
    Log                     Added chart ${chart_id} to cleanup list: ${CREATED_CHART_IDS}           DEBUG

List charts request is sent
    [Documentation]    Sends a request to list charts with optional pagination
    [Arguments]             ${page_number}=1        ${page_size}=10
    ${response}=            List Charts Request     page_number=${page_number}                      page_size=${page_size}
    Set Test Variable       ${response}             ${response}

Delete chart request is sent
    [Documentation]    Sends a request to delete a chart
    ${response}=            Delete chart            ${TEST_CHART_ID}
    Set test variable       ${response}             ${response}

Get chart
    [Documentation]    Get a specific chart by ID
    [Arguments]             ${chart_id}             ${expected_status}=any
    Create api session
    ${endpoint}=            Catalog endpoint        charts/${chart_id}
    Log                     GET ${endpoint}         DEBUG
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             expected_status=${expected_status}
    Log                     Get chart response: status=${response.status_code}                      DEBUG
    RETURN                  ${response}
