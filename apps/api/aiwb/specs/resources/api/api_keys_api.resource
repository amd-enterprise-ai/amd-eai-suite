# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keywords for interacting with the API Keys API endpoints (AIWB API).
...                 Provides low-level keywords for managing API keys through the AIWB API.
...                 AIWB uses project-based routing: /projects/{project}/api-keys
...                 This differs from AIRM which uses projectId query parameter.
...                 Includes operations for creating, reading, updating, and deleting API keys.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource


*** Keywords ***
Api keys endpoint
    [Documentation]    Returns the full API keys endpoint URL for AIWB
    ...                AIWB uses project-based routing: /projects/{project}/api-keys
    [Arguments]    ${project}    ${key_id}=${None}
    ${base_endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/api-keys
    IF    $key_id is not None
        RETURN    ${base_endpoint}/${key_id}
    END
    RETURN    ${base_endpoint}

Create api key
    [Documentation]    Create a new API key via AIWB API
    [Arguments]    ${key_data}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    Api keys endpoint    ${project}
    Log    API Request: POST ${endpoint} - Body: ${key_data}    DEBUG
    ${response}=    Safe Post Request
    ...    ${endpoint}
    ...    json=${key_data}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

List api keys
    [Documentation]    List API keys for a project via AIWB API
    [Arguments]    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    Api keys endpoint    ${project}
    Log    API Request: GET ${endpoint}    DEBUG
    ${response}=    Safe Get Request
    ...    ${endpoint}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Get api key
    [Documentation]    Get API key details by ID via AIWB API
    [Arguments]    ${key_id}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    Api keys endpoint    ${project}    key_id=${key_id}
    Log    API Request: GET ${endpoint}    DEBUG
    ${response}=    Safe Get Request
    ...    ${endpoint}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Update api key
    [Documentation]    Update an API key via AIWB API (PATCH)
    [Arguments]    ${key_id}    ${update_data}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    Api keys endpoint    ${project}    key_id=${key_id}
    Log    API Request: PATCH ${endpoint} - Body: ${update_data}    DEBUG
    ${response}=    Safe Patch Request
    ...    ${endpoint}
    ...    json=${update_data}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Delete api key
    [Documentation]    Delete an API key via AIWB API
    [Arguments]    ${key_id}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    Api keys endpoint    ${project}    key_id=${key_id}
    Log    API Request: DELETE ${endpoint}    DEBUG
    ${response}=    Safe Delete Request
    ...    ${endpoint}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code}    DEBUG
    RETURN    ${response}

Renew api key
    [Documentation]    Renew an API key's lease via AIWB API
    [Arguments]    ${key_id}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${base_endpoint}=    Api keys endpoint    ${project}    key_id=${key_id}
    ${endpoint}=    Set variable    ${base_endpoint}/renew
    Log    API Request: POST ${endpoint}    DEBUG
    ${response}=    Safe Post Request
    ...    ${endpoint}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

List api key groups
    [Documentation]    List the cluster-auth groups an API key belongs to via AIWB API
    [Arguments]    ${api_key_id}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${base_endpoint}=    Api keys endpoint    ${project}    key_id=${api_key_id}
    VAR    ${endpoint}    ${base_endpoint}/groups
    Log    API Request: GET ${endpoint}    DEBUG
    ${response}=    Safe Get Request
    ...    ${endpoint}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Add api key to group
    [Documentation]    Add an API key to a cluster-auth group via AIWB API
    [Arguments]    ${api_key_id}    ${group_id}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${base_endpoint}=    Api keys endpoint    ${project}    key_id=${api_key_id}
    VAR    ${endpoint}    ${base_endpoint}/groups
    ${body}=    Create dictionary    groupId=${group_id}
    Log    API Request: POST ${endpoint} - Body: ${body}    DEBUG
    ${response}=    Safe Post Request
    ...    ${endpoint}
    ...    json=${body}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Remove api key from group
    [Documentation]    Remove an API key from a cluster-auth group via AIWB API
    [Arguments]    ${api_key_id}    ${group_id}    ${project}    ${expected_status}=any
    Create api session    aiwb

    ${base_endpoint}=    Api keys endpoint    ${project}    key_id=${api_key_id}
    VAR    ${endpoint}    ${base_endpoint}/groups/${group_id}
    Log    API Request: DELETE ${endpoint}    DEBUG
    ${response}=    Safe Delete Request
    ...    ${endpoint}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code}    DEBUG
    RETURN    ${response}
