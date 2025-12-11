# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level API keywords for AIRM storage management.
...                 Provides direct HTTP operations for storage endpoints.
...                 These keywords wrap the REST API calls with minimal business logic.
Resource            common.resource
Library             Collections


*** Keywords ***
Storage endpoint
    [Documentation]    Returns the base storage endpoint path
    ${endpoint}=    Catalog endpoint    storages
    RETURN    ${endpoint}

Storage by id endpoint
    [Documentation]    Returns the endpoint path for a specific storage
    [Arguments]    ${storage_id}
    ${base_endpoint}=    Storage endpoint
    RETURN    ${base_endpoint}/${storage_id}

Storage assign endpoint
    [Documentation]    Returns the endpoint path for storage project assignment
    [Arguments]    ${storage_id}
    ${base_endpoint}=    Storage by id endpoint    ${storage_id}
    RETURN    ${base_endpoint}/assign

Get storages
    [Documentation]    Retrieve all storage resources for the organization
    ...
    ...    Returns:
    ...    Response object with .json() containing {"storages": [...]}
    [Arguments]    ${expected_status}=200
    Create API session

    ${endpoint}=    Storage endpoint
    Log    GET ${endpoint}    DEBUG
    ${response}=    GET on session    ${API_SESSION}    ${endpoint}
    ...    expected_status=${expected_status}
    Log    Response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Get storage
    [Documentation]    Retrieve a specific storage by ID
    ...    Note: The API doesn't have GET /storages/{id}, so we list all and filter
    ...
    ...    Args:
    ...    storage_id (str): UUID of the storage to retrieve
    ...
    ...    Returns:
    ...    response: Mock response object with .json() method returning the storage
    ...
    ...    Raises:
    ...    Exception: If the storage is not found
    [Arguments]    ${storage_id}    ${expected_status}=200

    Log    Getting storage ${storage_id} by filtering list    DEBUG

    # Retry GET /storages up to 3 times to handle async cleanup 400 errors
    ${max_retries}=    Set Variable    3
    ${max_range}=    Evaluate    ${max_retries} + 1
    FOR    ${attempt}    IN RANGE    1    ${max_range}
        ${list_response}=    Get storages    expected_status=any

        IF    ${list_response.status_code} == 200
            # Success - break out of retry loop
            BREAK
        ELSE IF    ${list_response.status_code} == 400
            Log    GET /storages returned 400 (attempt ${attempt}/${max_retries}), likely during async cleanup    WARN
            IF    ${attempt} < ${max_retries}
                Sleep    3s
                CONTINUE
            ELSE
                # Last attempt failed - log and handle below
                Log    GET /storages still returning 400 after ${max_retries} attempts    ERROR
            END
        ELSE
            # Unexpected status code
            Log    GET /storages returned unexpected status ${list_response.status_code}    ERROR
            BREAK
        END
    END

    # Handle final response status
    IF    ${list_response.status_code} != 200
        Log    GET /storages failed with ${list_response.status_code}: ${list_response.text}    ERROR
        IF    ${expected_status} == 404
            ${empty_dict}=    Create Dictionary
            ${mock_response}=    Evaluate    type('MockResponse', (), {'json': lambda self: ${empty_dict}, 'status_code': 404})()
            RETURN    ${mock_response}
        END
        FAIL    Failed to list storages after ${max_retries} attempts: ${list_response.status_code} - ${list_response.text}
    END

    ${storages_data}=    Set Variable    ${list_response.json()}
    ${storages_list}=    Get From Dictionary    ${storages_data}    storages

    FOR    ${storage}    IN    @{storages_list}
        ${id}=    Get From Dictionary    ${storage}    id
        IF    "${id}" == "${storage_id}"
            Log    Found storage ${storage_id}    DEBUG
            ${mock_response}=    Evaluate    type('MockResponse', (), {'json': lambda self: ${storage}, 'status_code': ${expected_status}})()
            RETURN    ${mock_response}
        END
    END

    IF    ${expected_status} == 404
        Log    Storage ${storage_id} not found (expected 404)    DEBUG
        ${empty_dict}=    Create Dictionary
        ${mock_response}=    Evaluate    type('MockResponse', (), {'json': lambda self: ${empty_dict}, 'status_code': 404})()
        RETURN    ${mock_response}
    END

    FAIL    Storage with ID ${storage_id} not found in list

Create storage
    [Documentation]    Create a new storage resource
    ...
    ...    Args:
    ...    storage_data (dict): Storage configuration including:
    ...    - name: Storage name (DNS subdomain format)
    ...    - type: Storage type (e.g., "S3")
    ...    - scope: Storage scope (e.g., "Organization")
    ...    - secret_id: UUID of secret containing credentials
    ...    - project_ids: List of project UUIDs to assign to (optional)
    ...    - spec: Storage-specific configuration (e.g., S3 bucket details)
    ...
    ...    Returns:
    ...    Response object with .json() containing created storage with project_storages
    [Arguments]    ${storage_data}    ${expected_status}=200
    Create API session

    TRY
        ${endpoint}=    Storage endpoint
        ${name}=    Get from dictionary    ${storage_data}    name
        Log    POST ${endpoint} - Creating storage '${name}'    DEBUG
        Log    Request body: ${storage_data}    DEBUG
        ${response}=    POST on session    ${API_SESSION}    ${endpoint}
        ...    json=${storage_data}
        ...    expected_status=${expected_status}
        Log    Response status: ${response.status_code}    DEBUG
        IF    ${response.status_code} == 200
            ${storage_id}=    Get from dictionary    ${response.json()}    id
            Log    Created storage ${storage_id} (${name})    INFO
        END
        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set variable    Failed to create storage: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END

Delete storage
    [Documentation]    Delete a storage resource
    ...
    ...    Args:
    ...    storage_id (str): UUID of the storage to delete
    ...    expected_status (int): Expected HTTP status code (204 for success)
    ...
    ...    Returns:
    ...    Response object
    [Arguments]    ${storage_id}    ${expected_status}=204
    Create API session

    TRY
        ${endpoint}=    Storage by id endpoint    ${storage_id}
        Log    DELETE ${endpoint}    DEBUG
        ${response}=    DELETE on session    ${API_SESSION}    ${endpoint}
        ...    expected_status=${expected_status}
        Log    Response status: ${response.status_code}    DEBUG
        IF    ${response.status_code} == 204
            Log    Deleted storage ${storage_id}    INFO
        END
        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set variable    Failed to delete storage ${storage_id}: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END

Assign storage to projects
    [Documentation]    Assign storage to a list of projects
    ...
    ...    Args:
    ...    storage_id (str): UUID of the storage
    ...    project_ids (list): List of project UUIDs to assign storage to
    ...    expected_status (int): Expected HTTP status code
    ...
    ...    Returns:
    ...    Response object with .json() containing updated storage with project_storages
    [Arguments]    ${storage_id}    ${project_ids}    ${expected_status}=200
    Create API session

    ${assignment_data}=    Create dictionary    project_ids=${project_ids}

    TRY
        ${endpoint}=    Storage assign endpoint    ${storage_id}
        ${project_count}=    Get length    ${project_ids}
        Log    PUT ${endpoint} - Assigning ${project_count} project(s)    DEBUG
        Log    Request body: ${assignment_data}    DEBUG
        ${response}=    PUT on session    ${API_SESSION}    ${endpoint}
        ...    json=${assignment_data}
        ...    expected_status=${expected_status}
        Log    Response status: ${response.status_code}    DEBUG
        IF    ${response.status_code} == 200
            Log    Assigned storage ${storage_id} to ${project_count} project(s)    INFO
        END
        RETURN    ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=    Set variable    Failed to assign storage ${storage_id}: ${error}
        Log    ${error_msg}    ERROR
        FAIL    ${error_msg}
    END
