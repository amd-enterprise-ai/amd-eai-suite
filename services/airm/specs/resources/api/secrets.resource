# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API secrets endpoints.
...                 Provides direct API operation wrappers for the /secrets endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            common.resource


*** Variables ***
${HEADERS}    Content-Type=application/json


*** Keywords ***
Secrets endpoint
    [Documentation]    Return the full secrets endpoint URL
    ${endpoint}=    Catalog endpoint    secrets
    RETURN    ${endpoint}

Create secret
    [Documentation]    Create a new secret
    ...
    ...    Args:
    ...    secret_data (dict): Secret configuration including:
    ...    - name: Secret name (DNS subdomain format)
    ...    - type: Secret type (External)
    ...    - scope: Secret scope (Organization)
    ...    - manifest: ExternalSecret YAML manifest
    ...    - project_ids: List of project UUIDs to assign to (optional)
    ...
    ...    Returns:
    ...    response: API response containing the created secret
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]    ${secret_data}    ${expected_status}=200
    Create api session

    TRY
        ${endpoint}=    Secrets endpoint
        ${secret_name}=    Get From Dictionary    ${secret_data}    name
        ${project_ids}=    Get From Dictionary    ${secret_data}    project_ids    ${EMPTY}

        Log    API request: POST ${endpoint}    DEBUG
        Log    Request body: ${secret_data}    DEBUG

        ${response}=    POST On Session    ${API_SESSION}    ${endpoint}
        ...    json=${secret_data}
        ...    expected_status=${expected_status}

        Log    API response: status=${response.status_code}    DEBUG
        Log    Response body: ${response.json()}    DEBUG

        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set Variable    Failed to create secret: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END

Get secret
    [Documentation]    Retrieve a specific secret by ID
    ...    Note: The API doesn't have GET /secrets/{id}, so we list all and filter
    ...
    ...    Args:
    ...    secret_id (str): UUID of the secret to retrieve
    ...
    ...    Returns:
    ...    response: Mock response object with .json() method returning the secret
    ...
    ...    Raises:
    ...    Exception: If the secret is not found
    [Arguments]    ${secret_id}    ${expected_status}=200

    Log    API request: GET secrets (filtering for ID=${secret_id})    DEBUG

    ${list_response}=    Get secrets    expected_status=200
    ${secrets_data}=    Set Variable    ${list_response.json()}
    ${secrets_list}=    Get From Dictionary    ${secrets_data}    secrets
    ${list_length}=    Get Length    ${secrets_list}

    Log    Searching for secret ${secret_id} in ${list_length} secrets    DEBUG

    FOR    ${secret}    IN    @{secrets_list}
        ${id}=    Get From Dictionary    ${secret}    id
        IF    "${id}" == "${secret_id}"
            ${status_code}=    Set Variable If    "${expected_status}" == "any"    200    ${expected_status}
            ${mock_response}=    Evaluate    type('MockResponse', (), {'json': lambda self: ${secret}, 'status_code': ${status_code}})()
            Log    API response: status=${status_code}, secret found    DEBUG
            Log    Response body: ${secret}    DEBUG
            RETURN    ${mock_response}
        END
    END

    # Secret not found in list
    IF    "${expected_status}" == "404" or "${expected_status}" == "any"
        ${empty_dict}=    Create Dictionary
        ${mock_response}=    Evaluate    type('MockResponse', (), {'json': lambda self: ${empty_dict}, 'status_code': 404})()
        Log    API response: status=404, secret not found    DEBUG
        RETURN    ${mock_response}
    END

    FAIL    Secret with ID ${secret_id} not found in list

Get secrets
    [Documentation]    List secrets for organization
    ...
    ...    Returns:
    ...    response: API response containing list of secrets
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]    ${expected_status}=200
    Create api session

    TRY
        ${endpoint}=    Secrets endpoint

        Log    API request: GET ${endpoint}    DEBUG

        ${response}=    GET On Session    ${API_SESSION}    ${endpoint}
        ...    expected_status=${expected_status}

        Log    API response: status=${response.status_code}    DEBUG
        ${secrets_data}=    Set Variable    ${response.json()}
        ${secrets_list}=    Get From Dictionary    ${secrets_data}    secrets
        ${count}=    Get Length    ${secrets_list}
        Log    Response contains ${count} secrets    DEBUG

        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set Variable    Failed to list secrets: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END

Delete secret
    [Documentation]    Delete a secret by ID
    ...
    ...    Args:
    ...    secret_id (str): UUID of the secret to delete
    ...
    ...    Returns:
    ...    response: API response (204 No Content on success)
    ...
    ...    Raises:
    ...    HTTPError: If the secret is not found or deletion fails
    [Arguments]    ${secret_id}    ${expected_status}=204
    Create api session

    TRY
        ${endpoint}=    Secrets endpoint

        Log    API request: DELETE ${endpoint}/${secret_id}    DEBUG

        ${response}=    DELETE On Session    ${API_SESSION}    ${endpoint}/${secret_id}
        ...    expected_status=${expected_status}

        Log    API response: status=${response.status_code}    DEBUG

        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set Variable    Failed to delete secret ${secret_id}: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END

Assign secret to projects
    [Documentation]    Assign a secret to one or more projects
    ...
    ...    Args:
    ...    secret_id (str): UUID of the secret
    ...    project_ids (list): List of project UUIDs to assign to
    ...
    ...    Returns:
    ...    response: API response containing updated secret with assignments
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]    ${secret_id}    ${project_ids}    ${expected_status}=200
    Create api session

    TRY
        ${endpoint}=    Secrets endpoint
        &{assignment_data}=    Create Dictionary    project_ids=${project_ids}

        Log    API request: PUT ${endpoint}/${secret_id}/assign    DEBUG
        Log    Request body: ${assignment_data}    DEBUG

        ${response}=    PUT On Session    ${API_SESSION}    ${endpoint}/${secret_id}/assign
        ...    json=${assignment_data}
        ...    expected_status=${expected_status}

        Log    API response: status=${response.status_code}    DEBUG
        Log    Response body: ${response.json()}    DEBUG

        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set Variable    Failed to assign secret ${secret_id}: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END
