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
Resource            resources/api/common.resource


*** Variables ***
&{HEADERS}      Content-Type=multipart/form-data
# Default value for signature file - can be overridden by test suites
${SIGNATURE_FILE}   ${CURDIR}/../../test_data/charts/signature.yaml


*** Keywords ***
Charts endpoint
    [Documentation]    Returns the full charts endpoint URL
    ${endpoint}=            Service API Endpoint    aiwb    endpoint=charts
    RETURN                  ${endpoint}

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
    # No project_id needed for AIWB charts API
    ${data}=                Create dictionary       name=${name}            type=INFERENCE
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

    Create api session    aiwb
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
    Create api session    aiwb
    ${endpoint} =           Charts endpoint
    Log                     DELETE ${endpoint}/${chart_id}  DEBUG
    ${response}=            Safe Delete Request       ${endpoint}/${chart_id}                         expected_status=${expected_status}
    Log                     Delete chart response: status=${response.status_code}                   DEBUG
    IF    ${response.status_code} == 204
        Log                     Deleted chart ${chart_id}       INFO
    END
    RETURN                  ${response}

Get chart
    [Documentation]    Get a specific chart by ID
    [Arguments]             ${chart_id}             ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            Service API Endpoint    aiwb    endpoint=charts/${chart_id}
    Log                     GET ${endpoint}         DEBUG
    ${response}=            Safe Get Request         ${endpoint}             expected_status=${expected_status}
    Log                     Get chart response: status=${response.status_code}                      DEBUG
    RETURN                  ${response}
