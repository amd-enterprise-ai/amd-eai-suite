# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keywords for interacting with the Cluster Auth API endpoints.
...                 Provides low-level keywords for managing API keys through cluster-auth service.
...                 These are legacy endpoints - prefer using AIRM API (api_keys_api.resource) where possible.
Library             RequestsLibrary
Library             Collections


*** Variables ***
${CLUSTER_AUTH_SESSION}     ${None}


*** Keywords ***
Create api key via cluster auth
    [Documentation]    Create a new API key via cluster-auth service
    [Arguments]    ${key_data}    ${expected_status}=any
    ${response}=    POST On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create
    ...    json=${key_data}
    ...    expected_status=${expected_status}
    RETURN    ${response}

Revoke api key via cluster auth
    [Documentation]    Revoke an API key via cluster-auth service
    [Arguments]    ${key_id}    ${expected_status}=any
    ${revoke_data}=    Create dictionary    key_id=${key_id}
    ${response}=    POST On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/revoke
    ...    json=${revoke_data}
    ...    expected_status=${expected_status}
    RETURN    ${response}

Lookup api key via cluster auth
    [Documentation]    Lookup API key status via cluster-auth service
    [Arguments]    ${key_id}    ${expected_status}=any
    ${lookup_data}=    Create dictionary    key_id=${key_id}
    ${response}=    POST On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/lookup
    ...    json=${lookup_data}
    ...    expected_status=${expected_status}
    RETURN    ${response}

Update api key permissions via cluster auth
    [Documentation]    Update API key permissions via cluster-auth service
    [Arguments]    ${key_id}    ${permissions}    ${expected_status}=any
    ${update_data}=    Create dictionary    permissions=${permissions}
    ${response}=    PATCH On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create/${key_id}
    ...    json=${update_data}
    ...    expected_status=${expected_status}
    RETURN    ${response}

Configure api key rate limit via cluster auth
    [Documentation]    Configure rate limiting for an API key via cluster-auth service
    [Arguments]    ${key_id}    ${rate_limit_data}    ${expected_status}=any
    ${response}=    PATCH On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create/${key_id}/rate-limit
    ...    json=${rate_limit_data}
    ...    expected_status=${expected_status}
    RETURN    ${response}

Assign api key to model via cluster auth
    [Documentation]    Assign API key to a model via cluster-auth service
    [Arguments]    ${key_id}    ${model_id}    ${expected_status}=any
    ${assignment_data}=    Create dictionary    key_id=${key_id}    model_id=${model_id}
    ${response}=    POST On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create/${key_id}/assign
    ...    json=${assignment_data}
    ...    expected_status=${expected_status}
    RETURN    ${response}

Get api key logs via cluster auth
    [Documentation]    Get access logs for an API key via cluster-auth service
    [Arguments]    ${key_id}    ${expected_status}=any
    ${response}=    GET On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create/${key_id}/logs
    ...    expected_status=${expected_status}
    RETURN    ${response}

Get api key mappings via cluster auth
    [Documentation]    Get key-model mappings for an API key via cluster-auth service
    [Arguments]    ${key_id}    ${expected_status}=any
    ${response}=    GET On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create/${key_id}/mappings
    ...    expected_status=${expected_status}
    RETURN    ${response}

Get api key audit log via cluster auth
    [Documentation]    Get audit log for an API key via cluster-auth service
    [Arguments]    ${key_id}    ${expected_status}=any
    ${response}=    GET On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create/${key_id}/audit-log
    ...    expected_status=${expected_status}
    RETURN    ${response}

Get failed access logs via cluster auth
    [Documentation]    Get failed access logs from cluster-auth service
    [Arguments]    ${expected_status}=any
    ${response}=    GET On Session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /api/v1/logs/failed-access
    ...    expected_status=${expected_status}
    RETURN    ${response}
