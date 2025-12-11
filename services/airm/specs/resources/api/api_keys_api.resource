# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keywords for interacting with the API Keys API endpoints (AIRM API).
...                 Provides low-level keywords for managing API keys through the AIRM API.
...                 Includes operations for creating, reading, updating, and deleting API keys.
Library             RequestsLibrary
Library             Collections
Resource            common.resource


*** Keywords ***
Api keys endpoint
    [Documentation]    Returns the full API keys endpoint URL
    [Arguments]    ${key_id}=${None}
    ${base_endpoint}=    Catalog endpoint    api-keys
    IF    $key_id is not None
        RETURN    ${base_endpoint}/${key_id}
    END
    RETURN    ${base_endpoint}

Create api key
    [Documentation]    Create a new API key via AIRM API
    [Arguments]    ${key_data}    ${params}=${None}    ${expected_status}=any
    Create api session
    ${endpoint}=    Api keys endpoint
    Log    API Request: POST ${endpoint} - Body: ${key_data}    DEBUG
    ${response}=    POST On Session
    ...    ${API_SESSION}
    ...    ${endpoint}
    ...    json=${key_data}
    ...    params=${params}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Get api key
    [Documentation]    Get API key details by ID via AIRM API
    [Arguments]    ${key_id}    ${params}=${None}    ${expected_status}=any
    Create api session
    ${endpoint}=    Api keys endpoint    ${key_id}
    Log    API Request: GET ${endpoint}    DEBUG
    ${response}=    GET On Session
    ...    ${API_SESSION}
    ...    ${endpoint}
    ...    params=${params}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Update api key
    [Documentation]    Update an API key via AIRM API (PATCH)
    [Arguments]    ${key_id}    ${update_data}    ${params}=${None}    ${expected_status}=any
    Create api session
    ${endpoint}=    Api keys endpoint    ${key_id}
    Log    API Request: PATCH ${endpoint} - Body: ${update_data}    DEBUG
    ${response}=    PATCH On Session
    ...    ${API_SESSION}
    ...    ${endpoint}
    ...    json=${update_data}
    ...    params=${params}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN    ${response}

Delete api key
    [Documentation]    Delete an API key via AIRM API
    [Arguments]    ${key_id}    ${params}=${None}    ${expected_status}=any
    Create api session
    ${endpoint}=    Api keys endpoint    ${key_id}
    Log    API Request: DELETE ${endpoint}    DEBUG
    ${response}=    DELETE On Session
    ...    ${API_SESSION}
    ...    ${endpoint}
    ...    params=${params}
    ...    expected_status=${expected_status}
    Log    API Response: ${response.status_code}    DEBUG
    RETURN    ${response}
