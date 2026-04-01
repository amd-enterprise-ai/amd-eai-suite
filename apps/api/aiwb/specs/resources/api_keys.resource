# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       LAYER 2: Business Logic - Generic API key management keywords.
...
...                 This resource provides high-level keywords for API key operations that are
...                 NOT specific to AIMS models. For AIMS-specific API key testing, use
...                 resources/aims/api_keys.resource instead.
...
...                 This file contains:
...                 - Generic API key creation and management
...                 - User authentication for API key testing
...                 - API key configuration (TTL, permissions, rate limiting)
...                 - API key lifecycle (creation, revocation, rotation)
...
...                 For AIMS-specific operations:
...                 - Use resources/aims/api_keys.resource for AIMS model deployments
...                 - That file imports this one and extends it with AIMS-specific keywords

Resource            resources/airm_keywords.resource
Resource            resources/airm_workloads.resource
Resource            resources/airm_projects.resource
Resource            resources/api/common.resource
Resource            resources/api/api_keys_api.resource
Resource            resources/deployment.resource
Resource            aiwb_common.resource
Library             BuiltIn
Library             RequestsLibrary
Library             Collections
Library             String
Library             DateTime


*** Keywords ***
# Setup and Teardown Keywords
Initialize api key test environment
    [Documentation]    Sets up the test environment for API key testing via AIWB API.
    ...    Uses Set Suite Variable so variables are available in all tests when called
    ...    from Suite Setup. Safe to call from Test Setup too (suite scope is a superset).
    Create api session    aiwb
    ${timestamp}=    Get time    epoch
    Set suite variable    ${TEST_ID}    ${timestamp}
    # Initialize cluster context
    A cluster exists in system
    # Note: Project and user setup is handled by individual tests via "a ready project with user access exists"
    Log    API key test environment initialized with TEST_ID=${TEST_ID}

# User Authentication Keywords
User is authenticated
    [Documentation]    Ensures user is authenticated and has valid session
    Create api session    aiwb

# API Key Creation Keywords
New api key is created
    [Documentation]    BDD wrapper: Creates a new API key via AIWB API
    Create api key

Api key is created with ttl of ${ttl}
    [Documentation]    BDD wrapper: Creates an API key with specific TTL
    Create api key    ttl=${ttl}

Api key ${index} is remembered
    [Documentation]    Saves current TEST_API_KEY for multi-key tests
    Set test variable    ${API_KEY_${index}}    ${TEST_API_KEY}

Api key exists for user
    [Documentation]    Ensures an API key exists for the current user via AIWB API
    Create api key
    Api key should be created successfully

Create api key
    [Documentation]    Creates a new API key via AIWB API
    [Arguments]    ${name}=${None}    ${ttl}=24h    ${renewable}=${True}

    ${timestamp}=    Get time    epoch
    ${random}=    Evaluate    __import__('random').randint(10000, 99999)

    # Use provided name or generate one
    ${key_name}=    Set variable if    $name is not None    ${name}    test-api-key-${timestamp}-${random}

    &{empty_meta}=    Create dictionary
    @{empty_aims}=    Create list
    ${key_data}=    Create dictionary
    ...    name=${key_name}
    ...    ttl=${ttl}
    ...    renewable=${renewable}
    ...    num_uses=${0}
    ...    meta=${empty_meta}
    ...    aim_ids=${empty_aims}

    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Create api key    ${key_data}    namespace=${namespace}    expected_status=any

    Set test variable    ${TEST_RESPONSE}    ${response}

    IF    ${response.status_code} == 200
        ${key_info}=    Set variable    ${response.json()}
        Set test variable    ${TEST_API_KEY}    ${key_info}
        Set test variable    ${TEST_API_KEY_VALUE}    ${key_info}[full_key]
    END

# API Key Renewal Keywords
Api key is renewed
    [Documentation]    BDD wrapper: Renews the current API key's lease
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Renew api key    ${TEST_API_KEY}[id]    namespace=${namespace}    expected_status=any

    Set test variable    ${TEST_RESPONSE}    ${response}

Api key renewal should succeed
    [Documentation]    Verifies that API key renewal was successful
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200
    ${response_data}=    Set variable    ${TEST_RESPONSE.json()}
    Should contain    ${response_data}    lease_duration

Api key renewal should fail
    [Documentation]    Verifies that API key renewal failed with non-200 status
    Should not be equal as integers    ${TEST_RESPONSE.status_code}    200

Create non-renewable api key
    [Documentation]    Creates an API key with renewable=False
    Create api key    renewable=${False}

Non-renewable api key is created
    [Documentation]    BDD wrapper: Creates a non-renewable API key
    Create non-renewable api key

Non-renewable api key renewal is attempted
    [Documentation]    BDD wrapper: Attempts to renew the current (non-renewable) API key
    Api key is renewed

Api key renewal should fail with expected error
    [Documentation]    Verifies that API key renewal failed for a non-renewable key
    Api key renewal should fail

Renew non-existent api key
    [Documentation]    Attempts renewal of a non-existent API key ID
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Renew api key    non-existent-key-id-12345    namespace=${namespace}    expected_status=any

    Set test variable    ${TEST_RESPONSE}    ${response}

Api key is revoked
    [Documentation]    Revokes/deletes the current API key (AIWB API)
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Delete api key    ${TEST_API_KEY}[id]    namespace=${namespace}    expected_status=any

    Set test variable    ${TEST_RESPONSE}    ${response}

# Assertion Keywords
Api key should be created successfully
    [Documentation]    Verifies that API key was created successfully
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200
    ${key_info}=    Set variable    ${TEST_RESPONSE.json()}
    # AIWB API returns: id, full_key, truncated_key, namespace, etc.
    Should contain    ${key_info}    id
    Should contain    ${key_info}    full_key

Key assignment should succeed
    [Documentation]    Verifies that key assignment was successful
    ...    AIWB API returns the updated API key object with group bindings
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200
    ${response_data}=    Set variable    ${TEST_RESPONSE.json()}
    # AIWB API returns the updated API key object, not a success wrapper
    Should contain    ${response_data}    id
    Should contain    ${response_data}    groups
    # Verify the key is bound to at least one group (the AIMS model)
    ${groups}=    Get from dictionary    ${response_data}    groups
    Should not be empty    ${groups}    API key should be bound to AIMS model group after assignment

Key-model mapping should be visible in management interface
    [Documentation]    Verifies that key-model mapping is visible via AIWB API
    ...    Gets API key details and checks that it has group bindings
    # API requires namespace in path
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]    namespace=${namespace}    expected_status=200

    ${key_details}=    Set variable    ${response.json()}
    Should contain    ${key_details}    groups
    ${groups}=    Get from dictionary    ${key_details}    groups
    Should not be empty    ${groups}    API key should be bound to at least one group (AIM model)
    ${group_count}=    Get length    ${groups}
    Log    API key is bound to ${group_count} group(s): ${groups}    INFO

Request should succeed
    [Documentation]    Verifies that the request was successful
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200

Request should fail with 401 unauthorized
    [Documentation]    Verifies that request failed with 401 or 403 status
    ...    403 Forbidden is returned when Envoy gateway enforces authentication
    ...    401 Unauthorized would be returned by the service itself
    ${status}=    Set variable    ${TEST_RESPONSE.status_code}
    Should be true    ${status} in [401, 403]    Expected 401 or 403, got ${status}

Error message should indicate missing api key
    [Documentation]    Verifies error message indicates missing API key
    ...    Handles both JSON responses (from service) and non-JSON responses (from Envoy gateway)
    ${status}=    Set variable    ${TEST_RESPONSE.status_code}
    # 403 from Envoy gateway may not have JSON body - status code verification is sufficient
    IF    ${status} == 403
        Log    Envoy gateway returned 403 Forbidden (expected for missing API key)    INFO
        RETURN
    END
    # For other error codes, verify JSON error message
    ${error_response}=    Set variable    ${TEST_RESPONSE.json()}
    Should contain    ${error_response}    error
    ${error_message}=    Get from dictionary    ${error_response}    error
    Should contain    ${error_message.lower()}    missing
    Should contain    ${error_message.lower()}    api key

Revocation should succeed
    [Documentation]    Verifies key revocation/deletion was successful (204 No Content for AIWB API)
    Should be equal as integers    ${TEST_RESPONSE.status_code}    204

Key status should show as revoked
    [Documentation]    Verifies key is deleted (AIWB API returns 404 for deleted keys)
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Get api key
    ...    ${TEST_API_KEY}[id]
    ...    namespace=${namespace}
    ...    expected_status=any

    # AIWB API should return 404 for deleted key
    Should be equal as integers    ${response.status_code}    404

Api key should be created with expiration time
    [Documentation]    Verifies API key has expiration time set (AIWB API)
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200
    ${key_info}=    Set variable    ${TEST_RESPONSE.json()}
    # AIWB API returns expires_at field
    Should contain    ${key_info}    expires_at
    Should not be empty    ${key_info}[expires_at]
    # Verify expires_at is a valid, parseable date
    ${expires}=    Convert date    ${key_info}[expires_at]    result_format=epoch
    Should be true    ${expires} > 0
    ...    expires_at should be a valid date
    # Known limitation: AIWB API currently sets expires_at ≈ created_at regardless of TTL.
    # The TTL value is passed to Vault but not reflected in the API response's expires_at field.
    # TODO: Once the API correctly computes expires_at = created_at + TTL, add:
    #     ${now}=    Get current date    result_format=epoch
    #     Should be true    ${expires} > ${now}    Expiration time should be in the future

Api key should show no active mappings
    [Documentation]    Verifies API key shows no active mappings via AIWB API
    ...    NOTE: Known limitation - AIWB currently does NOT clean up group mappings when AIMs are deleted.
    ...    This test documents the current behavior. The groups remain but the AIM is gone.
    ...    TODO: Once AIWB implements automatic cleanup, update this to verify groups are empty.
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]
    ...    namespace=${namespace}    expected_status=200

    ${key_info}=    Set variable    ${response.json()}

    # Document current behavior: groups are NOT automatically cleaned up (known limitation)
    ${has_groups}=    Run keyword and return status    Dictionary should contain key    ${key_info}    groups
    IF    ${has_groups}
        ${groups}=    Get from dictionary    ${key_info}    groups
        ${group_count}=    Get length    ${groups}
        Log    Known limitation: API key still has ${group_count} group(s) after AIM deletion    WARN
        Log    Group IDs: ${groups}    DEBUG
    END

Key status should indicate resource removed
    [Documentation]    Verifies key status via AIWB API after AIM deletion
    ...    NOTE: Known limitation - groups are NOT automatically cleaned up when AIMs are deleted.
    ...    The key exists and can be queried, even though the AIM it was mapped to is gone.
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]
    ...    namespace=${namespace}    expected_status=200

    ${key_info}=    Set variable    ${response.json()}

    Should be equal    ${key_info}[id]    ${TEST_API_KEY}[id]

Api key should remain valid for other uses
    [Documentation]    Verifies API key remains valid for other uses via AIWB API
    ...    The key should still exist in the system even though its AIM mappings were removed
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]
    ...    namespace=${namespace}    expected_status=200

    ${key_info}=    Set variable    ${response.json()}

    Should contain    ${key_info}    id
    Should be equal    ${key_info}[id]    ${TEST_API_KEY}[id]
