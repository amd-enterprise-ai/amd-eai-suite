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
Resource            ../catalog_projects.resource


*** Variables ***
&{HEADERS}      Content-Type=multipart/form-data


*** Keywords ***
Charts endpoint
    [Documentation]    Returns the full charts endpoint URL
    ${endpoint}=            Catalog endpoint        charts
    RETURN                  ${endpoint}


*** Keywords ***
Create chart request
    [Documentation]    Create a new chart with the provided files.
    ...
    ...    Args:
    ...    name (str): Name of the chart
    ...    template_file (str): Path to chart template file
    ...    values_file (str): Path to values YAML file
    ...    values_schema_file (str): Path to values schema JSON file
    ...    additional_files (list): Optional additional chart files
    ...
    ...    Returns:
    ...    response: API response containing the created chart
    ...
    ...    Raises:
    ...    HTTPError: If chart creation fails
    ...    IOError: If any of the required files cannot be read
    [Arguments]             ${name}                 ${template_file}        ${values_file}          ${values_schema_file}                           @{additional_files}     ${expected_status}=any
    ${template_content}=    Get Binary File         ${template_file}
    ${values_content}=      Get Binary File         ${values_file}
    ${schema_content}=      Get Binary File         ${values_schema_file}

    # Following the example from StackOverflow for multipart/form-data with files
    # Format: {'field_name': ('filename', filedata, 'content-type')}
    ${data}=                Create dictionary       name=${name}            type=INFERENCE          project_id=${CURRENT_PROJECT_ID}
    @{template}=            Create list             template.yaml           ${template_content}
    @{values}=              Create list             values.yaml             ${values_content}
    @{schema}=              Create list             schema.json             ${schema_content}
    &{files}=               Create dictionary
    ...                     files=${template}
    ...                     user_inputs=${values}

    ${endpoint} =           Charts endpoint
    ${access_token}=        Authorization token
    &{headers}=             Create Dictionary       Authorization=Bearer ${access_token}

    ${response}=            POST                    ${endpoint}             headers=${headers}      data=${data}            files=${files}          expected_status=${expected_status}
    # Log response for debugging, but not to console
    ${debug_resp}=          Set Variable            Chart creation response: Status=${response.status_code}, Body=${response.text}
    Log                     ${debug_resp}
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
    ${response}=            Get on session          ${API_SESSION}          ${endpoint}             params=${params}        expected_status=${expected_status}
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
    Create API Session
    TRY
        ${endpoint} =           Charts endpoint
        ${response}=            Delete on session       ${API_SESSION}          ${endpoint}/${chart_id}                         expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to delete chart ${chart_id} (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

Get charts
    [Documentation]    Get list of all charts
    [Arguments]             ${expected_status}=any
    Create API Session
    ${endpoint}=            Charts endpoint
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             expected_status=${expected_status}
    RETURN                  ${response}

Create chart request is sent
    [Documentation]    Sends a request to create a new chart and stores the ID
    [Arguments]             ${name}=${TEST_CHART_NAME}                      ${template}=${TEMPLATE_FILE}                    ${values}=${VALUES_FILE}                        ${schema}=${SCHEMA_FILE}
    ${response}=            Create chart request    ${name}                 ${template}             ${values}               ${schema}
    Set test variable       ${response}             ${response}

    # Initialize TEST_CHART_ID variable
    Set test variable       ${TEST_CHART_ID}        unknown-chart-id

    # Check status first
    Response status should be 201

    # Extract chart ID from successful response
    ${json}=                Set variable            ${response.json()}
    Log                     Chart created successfully

    # Set TEST_CHART_ID from response - this is crucial
    ${chart_id}=            Get from dictionary     ${json}                 id
    Set test variable       ${TEST_CHART_ID}        ${chart_id}
    Log                     Successfully extracted chart ID: ${chart_id}

    # Track created chart ID for cleanup (import the tracking list from catalog_charts.resource)
    Append To List          ${CREATED_CHART_IDS}    ${chart_id}
    Log                     Added chart ${chart_id} to cleanup list: ${CREATED_CHART_IDS}           level=DEBUG

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
    [Documentation]    Get a specific chart by
    [Arguments]             ${chart_id}             ${expected_status}=any
    Create API Session
    ${endpoint}=            Catalog endpoint        charts/${chart_id}
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             expected_status=${expected_status}
    RETURN                  ${response}
