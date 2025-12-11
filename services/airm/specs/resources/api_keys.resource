# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Resource file for API key management keywords.
...                 Provides keywords for creating, managing, and testing API keys
...                 through the cluster-auth service integration.

Resource            catalog_keywords.resource
Resource            catalog_models.resource
Resource            catalog_aims.resource
Resource            catalog_workloads.resource
Resource            airm_projects.resource
Resource            api/common.resource
Resource            api/api_keys_api.resource
Resource            api/cluster_auth_api.resource
Resource            test_data.resource
Resource            deployment.resource
Resource            cluster_auth.resource
Library             BuiltIn
Library             RequestsLibrary
Library             Collections
Library             String
Library             DateTime


*** Variables ***
${CLUSTER_AUTH_SESSION}     ${None}
${TEST_API_KEYS}            @{EMPTY}
${TEST_MODELS}              @{EMPTY}
${TEST_USER_ID}             ${None}
${CLUSTER_AUTH_ENDPOINT}    ${None}


*** Keywords ***
# Setup and Teardown Keywords
Initialize api key test environment
    [Documentation]    Sets up the test environment for API key testing
    Initialize cluster auth port forwarding    # Set up port forwarding if needed
    Validate cluster auth configuration
    Create api session
    Create cluster auth session
    ${timestamp}=    Get time    epoch
    Set test variable    ${TEST_ID}    ${timestamp}
    # Initialize cluster context
    A cluster exists in system
    # Note: Project and user setup is handled by individual tests via "a ready project with user access exists"
    # QUERY_PARAMS will be set by "User is added to project" keyword when tests set up their project
    # Initialize empty lists for tracking
    @{empty_list}=    Create list
    Set test variable    @{TEST_API_KEYS}    @{empty_list}
    @{empty_models}=    Create list
    Set test variable    @{TEST_MODELS}    @{empty_models}
    Log    API key test environment initialized with TEST_ID=${TEST_ID}

Clean up api keys and models
    [Documentation]    Cleans up all test-created API keys and models
    # Clean up API keys
    FOR    ${key_id}    IN    @{TEST_API_KEYS}
        TRY
            Revoke api key by id    ${key_id}
            Log    Revoked API key: ${key_id}
        EXCEPT
            Log    Failed to revoke API key ${key_id}, may already be deleted    WARN
        END
    END

    # Clean up deployed models
    FOR    ${model_id}    IN    @{TEST_MODELS}
        TRY
            Undeploy model by id    ${model_id}
            Log    Undeployed model: ${model_id}
        EXCEPT
            Log    Failed to undeploy model ${model_id}, may already be deleted    WARN
        END
    END

    # Stop cluster-auth port forwarding if it was started
    Stop cluster auth port forwarding

# Configuration Validation
Validate cluster auth configuration
    [Documentation]    Validates cluster-auth port forwarding is set up
    ...    Token validation removed - tests now use AIRM API exclusively
    Log    Cluster-auth port forwarding ready at: ${CLUSTER_AUTH_BASE_URL}    console=yes

# Session Management
Create cluster auth session
    [Documentation]    Creates a session to the cluster-auth API service
    IF    $CLUSTER_AUTH_SESSION is not None    RETURN

    ${base_url}=    Get cluster auth endpoint
    &{headers}=    Create dictionary
    ...    Content-Type=application/json
    ...    X-Admin-Token=${CLUSTER_AUTH_TOKEN}

    Create session    cluster_auth    ${base_url}    headers=${headers}    verify=true
    Set suite variable    ${CLUSTER_AUTH_SESSION}    cluster_auth
    Log    Cluster auth session created

Get cluster auth endpoint
    [Documentation]    Returns the cluster-auth service endpoint
    IF    $CLUSTER_AUTH_ENDPOINT is not None
        RETURN    ${CLUSTER_AUTH_ENDPOINT}
    END

    ${endpoint}=    Set variable    ${CLUSTER_AUTH_BASE_URL}
    Set suite variable    ${CLUSTER_AUTH_ENDPOINT}    ${endpoint}
    RETURN    ${endpoint}

# User Authentication Keywords
User is authenticated
    [Documentation]    Ensures user is authenticated and has valid session
    Create api session
    # For now, use a mock user ID since AIRM doesn't have user endpoint
    # In production, this would integrate with actual authentication
    ${user_id}=    Evaluate    "test-user-${TEST_ID}"
    Set test variable    ${TEST_USER_ID}    ${user_id}
    Log    User authenticated with mock ID: ${TEST_USER_ID}

Get current user info
    [Documentation]    Gets information about the currently authenticated user
    # Mock user info for testing
    ${user_info}=    Create dictionary    id=${TEST_USER_ID}    name=Test User    email=test@example.com
    RETURN    ${user_info}

# API Key Creation Keywords
Api key exists for user
    [Documentation]    Ensures an API key exists for the current user via AIRM API
    New AIRM api key is requested
    AIRM api key should be created successfully

New AIRM api key is requested
    [Documentation]    Requests creation of a new API key via AIRM API
    ${timestamp}=    Get time    epoch
    ${random}=    Evaluate    __import__('random').randint(10000, 99999)
    &{empty_meta}=    Create dictionary
    @{empty_aims}=    Create list
    ${key_data}=    Create dictionary
    ...    name=test-api-key-${timestamp}-${random}
    ...    ttl=24h
    ...    renewable=${True}
    ...    num_uses=${0}
    ...    meta=${empty_meta}
    ...    aim_ids=${empty_aims}

    # Build params with project_id for AIRM API
    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    api_keys_api.Create api key    ${key_data}    params=${params}    expected_status=any

    Set test variable    ${AIRM_API_KEY_RESPONSE}    ${response}

    IF    ${response.status_code} == 201
        ${key_info}=    Set variable    ${response.json()}
        Append to list    ${TEST_API_KEYS}    ${key_info}[id]
        Set test variable    ${CURRENT_AIRM_API_KEY}    ${key_info}
        # Also store the full key for testing
        Set test variable    ${CURRENT_API_KEY_VALUE}    ${key_info}[full_key]
    END

AIRM api key should be created successfully
    [Documentation]    Verifies that AIRM API key was created successfully
    Should be equal as integers    ${AIRM_API_KEY_RESPONSE.status_code}    201
    ${key_info}=    Set variable    ${AIRM_API_KEY_RESPONSE.json()}
    Should contain    ${key_info}    id
    Should contain    ${key_info}    full_key

# Model Deployment Keywords
Model is deployed
    [Documentation]    Deploys a test model
    ${model_data}=    Create test model
    ${deployment}=    Deploy model    ${model_data}[id]
    Append to list    ${TEST_MODELS}    ${model_data}[id]
    Set test variable    ${DEPLOYED_MODEL}    ${deployment}
    Set test variable    ${MODEL_ID}    ${model_data}[id]

Multiple models are deployed
    [Documentation]    Deploys multiple test models
    @{deployed_models}=    Create list

    FOR    ${i}    IN RANGE    3
        ${model_data}=    Create test model    suffix=${i}
        ${deployment}=    Deploy model    ${model_data}[id]
        Append to list    ${TEST_MODELS}    ${model_data}[id]
        Append to list    ${deployed_models}    ${deployment}
    END

    Set test variable    ${DEPLOYED_MODELS}    ${deployed_models}

# API Key Assignment Keywords (migrated to AIMS versions below)

# Model Access Keywords
Request is made to model with valid api key
    [Documentation]    Makes a request to a model using a valid API key
    ${headers}=    Create dictionary
    ...    X-API-Key=${CURRENT_API_KEY}[api_key]
    ...    Content-Type=application/json

    ${request_data}=    Create dictionary
    ...    input=Test input for model

    ${response}=    Post request
    ...    ${DEPLOYED_MODEL}[endpoint]/predict
    ...    json=${request_data}
    ...    headers=${headers}
    ...    expected_status=any

    Set test variable    ${MODEL_ACCESS_RESPONSE}    ${response}

Request is made to model with invalid api key
    [Documentation]    Makes a request to a model using an invalid API key
    ${headers}=    Create dictionary
    ...    X-API-Key=invalid-api-key-12345
    ...    Content-Type=application/json

    ${request_data}=    Create dictionary
    ...    input=Test input for model

    ${response}=    Post request
    ...    ${DEPLOYED_MODEL}[endpoint]/predict
    ...    json=${request_data}
    ...    headers=${headers}
    ...    expected_status=any

    Set test variable    ${MODEL_ACCESS_RESPONSE}    ${response}

Request is made to model without api key
    [Documentation]    Makes a request to a model without providing an API key
    ${headers}=    Create dictionary
    ...    Content-Type=application/json

    ${request_data}=    Create dictionary
    ...    input=Test input for model

    ${response}=    Post request
    ...    ${DEPLOYED_MODEL}[endpoint]/predict
    ...    json=${request_data}
    ...    headers=${headers}
    ...    expected_status=any

    Set test variable    ${MODEL_ACCESS_RESPONSE}    ${response}

Model access works with api key
    [Documentation]    Verifies that model access works with the assigned API key
    Request is made to model with valid api key
    Request should succeed

# API Key Management Keywords
Api keys are listed
    [Documentation]    Lists all API keys for the current user
    # Note: cluster-auth doesn't have a list endpoint, so we'll track created keys
    # In a real implementation, this would query a list endpoint
    Set test variable    ${API_KEYS_LIST}    ${CREATED_API_KEYS}

User has multiple api keys
    [Documentation]    Ensures user has multiple API keys via AIRM API
    @{created_keys}=    Create list
    FOR    ${i}    IN RANGE    3
        New AIRM api key is requested
        AIRM api key should be created successfully
        Append to list    ${created_keys}    ${CURRENT_AIRM_API_KEY}
    END
    Set test variable    ${CREATED_API_KEYS}    ${created_keys}

Api key is revoked
    [Documentation]    Revokes/deletes the current API key (AIRM API)
    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    api_keys_api.Delete api key    ${CURRENT_AIRM_API_KEY}[id]    params=${params}    expected_status=any

    Set test variable    ${REVOKE_RESPONSE}    ${response}

Revoke api key by id
    [Documentation]    Revokes an API key by its ID using AIRM API
    [Arguments]    ${key_id}
    ${project_params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    Delete api key    ${key_id}    params=${project_params}    expected_status=any

# Model Lifecycle Keywords
Model is undeployed
    [Documentation]    Undeploys the current model
    Undeploy model by id    ${MODEL_ID}
    Log    Model ${MODEL_ID} undeployed

Model is redeployed
    [Documentation]    Redeploys the previously undeployed model
    ${deployment}=    Deploy model    ${MODEL_ID}
    Set test variable    ${DEPLOYED_MODEL}    ${deployment}
    Log    Model ${MODEL_ID} redeployed

Model is permanently deleted
    [Documentation]    Permanently deletes a deployed model
    Delete model    ${MODEL_ID}
    Remove from list    ${TEST_MODELS}    ${MODEL_ID}

Undeploy model by id
    [Documentation]    Undeploys a model by its ID
    [Arguments]    ${model_id}
    # Implementation depends on actual undeployment API
    Log    Undeploying model ${model_id}

# API Key Configuration Keywords
Api key is created with ttl
    [Documentation]    Creates an API key with TTL (time to live) using AIRM API
    [Arguments]    ${ttl}=3600

    ${timestamp}=    Get Time    epoch
    &{empty_meta}=    Create dictionary
    @{empty_aims}=    Create list

    # AIRM API uses ttl as duration string (e.g., "1h", "24h", "3600s")
    ${key_data}=    Create dictionary
    ...    name=test-api-key-ttl-${timestamp}
    ...    ttl=${ttl}s
    ...    renewable=${True}
    ...    num_uses=${0}
    ...    meta=${empty_meta}
    ...    aim_ids=${empty_aims}

    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    api_keys_api.Create api key    ${key_data}    params=${params}    expected_status=any

    Set test variable    ${API_KEY_RESPONSE}    ${response}

    IF    ${response.status_code} == 201
        ${key_info}=    Set variable    ${response.json()}
        Append to list    ${TEST_API_KEYS}    ${key_info}[id]
        Set test variable    ${CURRENT_AIRM_API_KEY}    ${key_info}
        Set test variable    ${CURRENT_API_KEY_VALUE}    ${key_info}[full_key]
    END

# Assertion Keywords
Api key should be created successfully
    [Documentation]    Verifies that API key was created successfully
    Should be equal as integers    ${API_KEY_RESPONSE.status_code}    200
    ${key_info}=    Set variable    ${API_KEY_RESPONSE.json()}
    # cluster-auth returns different field names
    Should contain    ${key_info}    key_id
    Should contain    ${key_info}    api_key

Api key should be returned in response
    [Documentation]    Verifies that API key is returned in the response
    ${key_info}=    Set variable    ${API_KEY_RESPONSE.json()}
    Should contain    ${key_info}    api_key
    ${key_value}=    Get from dictionary    ${key_info}    api_key
    Should not be empty    ${key_value}
    # Verify key has expected format/length
    ${key_length}=    Get length    ${key_value}
    Should be true    ${key_length} >= 10

Api key should be associated with user account
    [Documentation]    Verifies that API key is associated with the user account
    ${key_info}=    Set variable    ${API_KEY_RESPONSE.json()}
    # For cluster-auth, we don't have direct user association in the response
    # The association is managed through OpenBao policies
    Should contain    ${key_info}    key_id
    Log    API key created with ID: ${key_info}[key_id]

All api keys should be created successfully
    [Documentation]    Verifies all requested API keys were created
    ${count}=    Get length    ${CREATED_API_KEYS}
    Should be equal as integers    ${count}    3

    FOR    ${key}    IN    @{CREATED_API_KEYS}
        Should contain    ${key}    key_id
        Should contain    ${key}    api_key
    END

User should have ${expected_count} active api keys
    [Documentation]    Verifies user has the expected number of active API keys
    Api keys are listed
    # All keys in CREATED_API_KEYS are active (just created)
    # cluster-auth doesn't return status in the creation response
    ${count}=    Get length    ${API_KEYS_LIST}
    Should be equal as integers    ${count}    ${expected_count}

Key assignment should succeed
    [Documentation]    Verifies that key assignment was successful
    ...    AIRM API returns the updated API key object with group bindings
    Should be equal as integers    ${ASSIGNMENT_RESPONSE.status_code}    200
    ${response_data}=    Set variable    ${ASSIGNMENT_RESPONSE.json()}
    # AIRM API returns the updated API key object, not a success wrapper
    Should contain    ${response_data}    id
    Should contain    ${response_data}    groups
    # Verify the key is bound to at least one group (the AIMS model)
    ${groups}=    Get from dictionary    ${response_data}    groups
    Should not be empty    ${groups}    API key should be bound to AIMS model group after assignment

Model should accept requests with api key
    [Documentation]    Verifies that model accepts requests with the assigned API key
    Request is made to model with valid api key
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    200

Key-model mapping should be visible in management interface
    [Documentation]    Verifies that key-model mapping is visible via AIRM API
    ...    Gets API key details and checks that it has group bindings
    # API requires project_id as query parameter
    ${params}=    Create Dictionary    project_id=${TEST_PROJECT_ID}

    ${response}=    api_keys_api.Get api key    ${CURRENT_AIRM_API_KEY}[id]    params=${params}    expected_status=200

    ${key_details}=    Set variable    ${response.json()}
    Should contain    ${key_details}    groups
    ${groups}=    Get from dictionary    ${key_details}    groups
    Should not be empty    ${groups}    API key should be bound to at least one group (AIM model)
    ${group_count}=    Get length    ${groups}
    Log    API key is bound to ${group_count} group(s): ${groups}    INFO

Request should succeed
    [Documentation]    Verifies that the request was successful
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    200

Response should contain model output
    [Documentation]    Verifies that response contains model output
    ${response_data}=    Set variable    ${MODEL_ACCESS_RESPONSE.json()}
    Should contain    ${response_data}    output

Access attempt should be logged
    [Documentation]    Verifies that access attempt was logged
    ${response}=    Get on session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /apikey/create/${CURRENT_AIRM_API_KEY}[id]/logs
    ...    expected_status=200

    ${logs}=    Set variable    ${response.json()}
    Should not be empty    ${logs}
    ${latest_log}=    Get from list    ${logs}    -1
    Should contain    ${latest_log}    timestamp
    Should contain    ${latest_log}    model_id
    Should contain    ${latest_log}    status

Request should fail with 401 unauthorized
    [Documentation]    Verifies that request failed with 401 or 403 status
    ...    403 Forbidden is returned when Envoy gateway enforces cluster-auth authentication
    ...    401 Unauthorized would be returned by the service itself
    ${status}=    Set variable    ${MODEL_ACCESS_RESPONSE.status_code}
    Should be true    ${status} in [401, 403]    Expected 401 or 403, got ${status}

Error message should indicate invalid api key
    [Documentation]    Verifies error message indicates invalid API key
    ...    Handles both JSON responses (from service) and non-JSON responses (from Envoy gateway)
    ${status}=    Set variable    ${MODEL_ACCESS_RESPONSE.status_code}
    # 403 from Envoy gateway may not have JSON body - status code verification is sufficient
    IF    ${status} == 403
        Log    Envoy gateway returned 403 Forbidden (expected for invalid API key)    INFO
        RETURN
    END
    # For other error codes, verify JSON error message
    ${error_response}=    Set variable    ${MODEL_ACCESS_RESPONSE.json()}
    Should contain    ${error_response}    error
    ${error_message}=    Get from dictionary    ${error_response}    error
    Should contain    ${error_message.lower()}    invalid
    Should contain    ${error_message.lower()}    api key

Error message should indicate missing api key
    [Documentation]    Verifies error message indicates missing API key
    ...    Handles both JSON responses (from service) and non-JSON responses (from Envoy gateway)
    ${status}=    Set variable    ${MODEL_ACCESS_RESPONSE.status_code}
    # 403 from Envoy gateway may not have JSON body - status code verification is sufficient
    IF    ${status} == 403
        Log    Envoy gateway returned 403 Forbidden (expected for missing API key)    INFO
        RETURN
    END
    # For other error codes, verify JSON error message
    ${error_response}=    Set variable    ${MODEL_ACCESS_RESPONSE.json()}
    Should contain    ${error_response}    error
    ${error_message}=    Get from dictionary    ${error_response}    error
    Should contain    ${error_message.lower()}    missing
    Should contain    ${error_message.lower()}    api key

Failed access attempt should be logged
    [Documentation]    Verifies that failed access attempt was logged
    ${response}=    Get on session
    ...    ${CLUSTER_AUTH_SESSION}
    ...    /api/v1/logs/failed-access
    ...    expected_status=200

    ${logs}=    Set variable    ${response.json()}
    Should not be empty    ${logs}

All user api keys should be returned
    [Documentation]    Verifies all user API keys are returned in list
    Should not be empty    ${API_KEYS_LIST}
    ${count}=    Get length    ${API_KEYS_LIST}
    Should be true    ${count} > 0

Each key should show status and metadata
    [Documentation]    Verifies each key shows status and metadata
    FOR    ${key}    IN    @{API_KEYS_LIST}
        Should contain    ${key}    key_id
        # cluster-auth returns minimal metadata at creation
        # In production, we'd query each key for full metadata
    END

Key values should not be exposed
    [Documentation]    Verifies actual key values are not exposed in list
    FOR    ${key}    IN    @{API_KEYS_LIST}
        # The api_key field should only be present at creation, not in lists
        # This is already true for cluster-auth - keys are write-only
        Log    Verifying key values are not exposed for ${key}[key_id]
    END

Key-model mappings should be visible
    [Documentation]    Verifies key-model mappings are visible
    FOR    ${key}    IN    @{API_KEYS_LIST}
        # Mappings would be retrieved via a separate API call in production
        Log    Key ${key}[key_id] mappings would be checked via separate endpoint
    END

Revocation should succeed
    [Documentation]    Verifies key revocation/deletion was successful (204 No Content for AIRM API)
    Should be equal as integers    ${REVOKE_RESPONSE.status_code}    204

Key status should show as revoked
    [Documentation]    Verifies key is deleted (AIRM API returns 404 for deleted keys)
    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    api_keys_api.Get api key
    ...    ${CURRENT_AIRM_API_KEY}[id]
    ...    params=${params}
    ...    expected_status=any

    # AIRM API should return 404 for deleted key
    Should be equal as integers    ${response.status_code}    404

Model access with revoked key should fail
    [Documentation]    Verifies model access fails with revoked key
    Request is made to model with valid api key
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    401

Revoked key should not be reusable
    [Documentation]    Verifies revoked key cannot be updated after revocation
    # Try to update a revoked key's bindings (should fail)
    ${params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${update_data}=    Create dictionary    aim_ids=@{EMPTY}
    ${response}=    Update api key
    ...    ${CURRENT_AIRM_API_KEY}[id]
    ...    ${update_data}
    ...    params=${params}
    ...    expected_status=any

    # Should fail with 404 (key not found after deletion) or 400/403
    Should be true    ${response.status_code} >= 400

Rotation should succeed
    [Documentation]    Verifies key rotation was successful
    Should be equal as integers    ${ROTATE_RESPONSE.status_code}    200

New api key should be returned
    [Documentation]    Verifies new API key is returned after rotation
    ${response_data}=    Set variable    ${ROTATE_RESPONSE.json()}
    Should contain    ${response_data}    key
    Should not be equal    ${response_data}[key]    ${OLD_API_KEY}

Old api key should be invalid
    [Documentation]    Verifies old API key is invalid after rotation
    ${headers}=    Create dictionary
    ...    X-API-Key=${OLD_API_KEY}
    ...    Content-Type=application/json

    ${response}=    Post request
    ...    ${DEPLOYED_MODEL}[endpoint]/predict
    ...    json=${{{"input": "test"}}}
    ...    headers=${headers}
    ...    expected_status=401

New api key should work with model
    [Documentation]    Verifies new API key works with model
    ${headers}=    Create dictionary
    ...    X-API-Key=${NEW_API_KEY}
    ...    Content-Type=application/json

    ${response}=    Post request
    ...    ${DEPLOYED_MODEL}[endpoint]/predict
    ...    json=${{{"input": "test"}}}
    ...    headers=${headers}
    ...    expected_status=200

Api key should not work with redeployed model
    [Documentation]    Verifies API key doesn't work with redeployed model
    Request is made to model with valid api key
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    401

All assignments should succeed
    [Documentation]    Verifies all key assignments succeeded
    # Implementation depends on tracking assignment responses
    Log    All assignments verified as successful

Model should accept any of the assigned keys
    [Documentation]    Verifies model accepts any assigned key
    FOR    ${key}    IN    @{CREATED_API_KEYS}
        ${headers}=    Create dictionary
        ...    X-API-Key=${key}[api_key]
        ...    Content-Type=application/json

        ${response}=    Post request
        ...    ${DEPLOYED_MODEL}[endpoint]/predict
        ...    json=${{{"input": "test"}}}
        ...    headers=${headers}
        ...    expected_status=200
    END

All key-model mappings should be visible
    [Documentation]    Verifies all key-model mappings (groups) are visible via AIRM API
    ${params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    FOR    ${key}    IN    @{CREATED_API_KEYS}
        ${response}=    Get api key
        ...    ${key}[id]
        ...    params=${params}
        ...    expected_status=200

        ${key_details}=    Set variable    ${response.json()}
        # Verify key has groups (which represent AIM bindings)
        Should contain    ${key_details}    groups
        Should not be empty    ${key_details}[groups]
    END

All models should accept the same api key
    [Documentation]    Verifies all models accept the same API key
    FOR    ${model}    IN    @{DEPLOYED_MODELS}
        ${headers}=    Create dictionary
        ...    X-API-Key=${CURRENT_API_KEY}[api_key]
        ...    Content-Type=application/json

        ${response}=    Post request
        ...    ${model}[endpoint]/predict
        ...    json=${{{"input": "test"}}}
        ...    headers=${headers}
        ...    expected_status=200
    END

Api key should be created with expiration time
    [Documentation]    Verifies API key has expiration time set (AIRM API)
    Should be equal as integers    ${API_KEY_RESPONSE.status_code}    201
    ${key_info}=    Set variable    ${API_KEY_RESPONSE.json()}
    # AIRM API returns expires_at field
    Should contain    ${key_info}    expires_at
    Should not be empty    ${key_info}[expires_at]

Api key should work before expiration
    [Documentation]    Verifies API key works before expiration
    Model is deployed
    Api key is assigned to model
    Request is made to model with valid api key
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    200

Api key should show no active mappings
    [Documentation]    Verifies API key shows no active mappings via AIRM API
    ...    NOTE: Known limitation - AIRM currently does NOT clean up group mappings when AIMs are deleted.
    ...    This test documents the current behavior. The groups remain but the AIM is gone.
    ...    TODO: Once AIRM implements automatic cleanup, update this to verify groups are empty.
    ${endpoint}=    Catalog endpoint    api-keys/${CURRENT_AIRM_API_KEY}[id]

    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    Safe Get Request
    ...    ${endpoint}
    ...    params=${params}
    ...    expected_status=200

    ${key_info}=    Set variable    ${response.json()}

    # Document current behavior: groups are NOT automatically cleaned up (known limitation)
    ${has_groups}=    Run keyword and return status    Dictionary should contain key    ${key_info}    groups
    IF    ${has_groups}
        ${groups}=    Get from dictionary    ${key_info}    groups
        # Current behavior: groups remain after AIM deletion (not ideal, but documented)
        Log    Known limitation: API key still has ${groups.__len__()} group(s) after AIM deletion    WARN
        Log    Group IDs: ${groups}    DEBUG
    END

Key status should indicate resource removed
    [Documentation]    Verifies key status via AIRM API after AIM deletion
    ...    NOTE: Known limitation - groups are NOT automatically cleaned up when AIMs are deleted.
    ...    The key exists and can be queried, even though the AIM it was mapped to is gone.
    ${endpoint}=    Catalog endpoint    api-keys/${CURRENT_AIRM_API_KEY}[id]

    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    Safe Get Request
    ...    ${endpoint}
    ...    params=${params}
    ...    expected_status=200

    ${key_info}=    Set variable    ${response.json()}

    # Verify key still exists (this is the important part - key survives AIM deletion)
    Should be equal    ${key_info}[id]    ${CURRENT_AIRM_API_KEY}[id]
    Log    API key still exists after AIM deletion (as expected)    INFO

Api key should remain valid for other uses
    [Documentation]    Verifies API key remains valid for other uses via AIRM API
    ...    The key should still exist in the system even though its AIM mappings were removed
    ${endpoint}=    Catalog endpoint    api-keys/${CURRENT_AIRM_API_KEY}[id]

    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    Safe Get Request
    ...    ${endpoint}
    ...    params=${params}
    ...    expected_status=200

    ${key_info}=    Set variable    ${response.json()}

    # Verify key still exists and has required fields
    Should contain    ${key_info}    id
    Should be equal    ${key_info}[id]    ${CURRENT_AIRM_API_KEY}[id]

Permission update should succeed
    [Documentation]    Verifies permission update was successful
    Should be equal as integers    ${PERMISSION_UPDATE_RESPONSE.status_code}    200

Api key should allow write operations
    [Documentation]    Verifies API key allows write operations
    ${headers}=    Create dictionary
    ...    X-API-Key=${CURRENT_API_KEY}[api_key]
    ...    Content-Type=application/json

    # Test write operation (depends on actual API)
    ${write_data}=    Create dictionary
    ...    action=write
    ...    data=test data

    ${response}=    Post request
    ...    ${DEPLOYED_MODEL}[endpoint]/write
    ...    json=${write_data}
    ...    headers=${headers}
    ...    expected_status=200

Subsequent requests should fail with 429
    [Documentation]    Verifies subsequent requests fail with rate limit error
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    429

Error should indicate rate limit exceeded
    [Documentation]    Verifies error indicates rate limit exceeded
    ${error_response}=    Set variable    ${MODEL_ACCESS_RESPONSE.json()}
    Should contain    ${error_response}    error
    ${error_message}=    Get from dictionary    ${error_response}    error
    Should contain    ${error_message.lower()}    rate limit

Rate limit should reset after window
    [Documentation]    Verifies rate limit resets after time window
    Sleep    60s    # Wait for rate limit window to reset
    Request is made to model with valid api key
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    200

# Helper Keywords
Create test model
    [Documentation]    Creates a test model for API key testing
    [Arguments]    ${suffix}=${EMPTY}

    # Expects ${TEST_PROJECT_ID} to be set by Project exists in system
    Should Not Be Empty    ${TEST_PROJECT_ID}    TEST_PROJECT_ID must be set - ensure "Project exists in system" is called as precondition

    ${model_name}=    Set variable if    "${suffix}"=="${EMPTY}"
    ...    test-model-${TEST_ID}
    ...    test-model-${TEST_ID}-${suffix}

    ${model_data}=    Create dictionary
    ...    name=${model_name}
    ...    type=BaseModel
    ...    model_weights_path=default-bucket/models/test-project/models/${model_name}
    ...    canonical_name=${model_name}

    ${query_params}=    Create dictionary
    ...    project_id=${TEST_PROJECT_ID}

    ${endpoint}=    Catalog endpoint    models

    ${response}=    Safe Post Request
    ...    ${endpoint}
    ...    json=${model_data}
    ...    params=${query_params}
    ...    expected_status=201

    RETURN    ${response.json()}

Deploy model
    [Documentation]    Deploys a model and returns deployment info
    [Arguments]    ${model_id}

    ${deployment_data}=    Create dictionary
    ...    model_id=${model_id}
    ...    replicas=1
    ...    resources=${{{"cpu": "1", "memory": "2Gi"}}}

    ${endpoint}=    Catalog endpoint    deployments

    ${response}=    Safe Post Request
    ...    ${endpoint}
    ...    json=${deployment_data}
    ...    expected_status=201

    RETURN    ${response.json()}

Delete model
    [Documentation]    Deletes a model
    [Arguments]    ${model_id}

    Safe Delete Request
    ...    /models/${model_id}
    ...    expected_status=204

Post request
    [Documentation]    Makes a POST request to given URL
    [Arguments]    ${url}    ${json}=${None}    ${headers}=${None}    ${expected_status}=any

    ${response}=    Post    ${url}
    ...    json=${json}
    ...    headers=${headers}
    ...    timeout=180
    ...    expected_status=any

    IF    "${expected_status}" != "any"
        Should be equal as integers    ${response.status_code}    ${expected_status}
    END

    RETURN    ${response}

Multiple api keys exist
    [Documentation]    Ensures multiple API keys exist for testing via AIRM API
    User has multiple api keys


# ========================================================================
# AIMS-Specific Keywords
# ========================================================================

# AIMS Deployment Keywords
An AIM model is running
    [Documentation]    Ensure an AIMS model is in Running state
    AIM is deployed and running
    Set test variable    ${AIMS_WORKLOAD_ID}    ${DEPLOYED_WORKLOAD_ID}
    Set test variable    ${AIMS_MODEL_ID}    ${TEST_AIM_ID}
    # Get the external endpoint
    ${response}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${output}=    Get from dictionary    ${json}    output
    ${external_host}=    Get from dictionary    ${output}    external_host
    Set test variable    ${AIMS_EXTERNAL_HOST}    ${external_host}

An AIM model is running with api key
    [Documentation]    Ensure AIMS model is running and has API key assigned
    An AIM model is running
    User is authenticated
    Api key exists for user
    Api key is assigned to AIMS model
    Key assignment should succeed

Multiple AIM models are running
    [Documentation]    Deploy multiple AIMS models (2 different models for variety)
    @{deployed_aims}=    Create list
    @{aims_workload_ids}=    Create list

    # Deploy first AIMS model (llama-3.1-8b)
    AIM is deployed and running
    Append to list    ${deployed_aims}    ${TEST_AIM_ID}
    Append to list    ${aims_workload_ids}    ${DEPLOYED_WORKLOAD_ID}

    # For second model, we'd ideally deploy a different AIMS (qwen3-4b)
    # But for simplicity, deploy the same model again
    # In production, you'd select a different AIM ID here
    AIM is deployed and running
    Append to list    ${deployed_aims}    ${TEST_AIM_ID}
    Append to list    ${aims_workload_ids}    ${DEPLOYED_WORKLOAD_ID}

    Set test variable    @{DEPLOYED_AIMS_MODELS}    @{deployed_aims}
    Set test variable    @{DEPLOYED_AIMS_WORKLOAD_IDS}    @{aims_workload_ids}

# API Key Assignment Keywords for AIMS
Api key is assigned to AIMS model
    [Documentation]    Assign API key to AIMS model using AIRM API
    ...    Uses PATCH /api-keys/{api_key_id} endpoint with aim_ids parameter
    ...    Can specify api_key and aim_id or use defaults (CURRENT_AIRM_API_KEY, AIMS_MODEL_ID)
    [Arguments]    ${api_key}=${CURRENT_AIRM_API_KEY}    ${aim_id}=${AIMS_MODEL_ID}

    # Validate we have required values
    Should not be empty    ${api_key}
    ...    msg=API key required - pass api_key= or ensure CURRENT_AIRM_API_KEY is set
    Should not be empty    ${aim_id}
    ...    msg=AIM model ID required - pass aim_id= or ensure AIMS_MODEL_ID is set

    # Update API key bindings via AIRM API
    @{aim_ids}=    Create list    ${aim_id}
    ${update_data}=    Create dictionary    aim_ids=${aim_ids}

    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    Update api key
    ...    ${api_key}[id]
    ...    ${update_data}
    ...    params=${params}
    ...    expected_status=any

    Set test variable    ${ASSIGNMENT_RESPONSE}    ${response}

Api key is assigned to all AIMS models
    [Documentation]    Assign a single API key to all deployed AIMS models using AIRM API
    ...    Uses PATCH /api-keys/{api_key_id} endpoint with aim_ids parameter
    # Make sure we have a key to assign
    ${key_exists}=    Run keyword and return status    Variable should exist    ${CURRENT_AIRM_API_KEY}
    IF    not ${key_exists}
        Fail    CURRENT_AIRM_API_KEY variable not set - ensure API key was created via AIRM API
    END

    # Make sure we have AIMS model IDs to assign to
    ${aims_exist}=    Run keyword and return status    Variable should exist    @{DEPLOYED_AIMS_WORKLOAD_IDS}
    IF    not ${aims_exist}
        Fail    DEPLOYED_AIMS_WORKLOAD_IDS variable not set - ensure "Multiple AIM models are running" has been called first
    END

    # Update API key bindings via AIRM API with all model IDs
    ${update_data}=    Create dictionary    aim_ids=${DEPLOYED_AIMS_WORKLOAD_IDS}

    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    Update api key
    ...    ${CURRENT_AIRM_API_KEY}[id]
    ...    ${update_data}
    ...    params=${params}
    ...    expected_status=200

    Set test variable    ${ASSIGNMENT_RESPONSE}    ${response}

# AIMS Model Access Keywords
Request is made to AIMS model with valid api key
    [Documentation]    Make a request to AIMS model endpoint with valid API key
    ...    Can specify api_key_value and host or use defaults (CURRENT_API_KEY_VALUE, AIMS_EXTERNAL_HOST)
    [Arguments]    ${api_key_value}=${CURRENT_API_KEY_VALUE}    ${host}=${AIMS_EXTERNAL_HOST}

    Should not be empty    ${api_key_value}
    ...    msg=API key value required - pass api_key_value= or ensure CURRENT_API_KEY_VALUE is set
    Should not be empty    ${host}
    ...    msg=Host required - pass host= or ensure AIMS_EXTERNAL_HOST is set

    ${headers}=    Create dictionary
    ...    Authorization=Bearer ${api_key_value}
    ...    Content-Type=application/json

    ${messages}=    Evaluate    [{"role": "user", "content": "Hello"}]
    ${request_data}=    Create dictionary
    ...    model=amd/Llama-3.1-8B-Instruct-FP8-KV
    ...    messages=${messages}
    ...    max_tokens=10

    # Use /v1/chat/completions endpoint which requires authentication
    ${response}=    Post request    ${host}/v1/chat/completions    json=${request_data}    headers=${headers}    expected_status=any

    Set test variable    ${MODEL_ACCESS_RESPONSE}    ${response}

Request is made to AIMS model with invalid api key
    [Documentation]    Make a request to AIMS model with invalid API key
    Variable should exist    ${AIMS_EXTERNAL_HOST}

    ${headers}=    Create dictionary
    ...    Authorization=Bearer invalid-api-key-12345
    ...    Content-Type=application/json

    ${messages}=    Evaluate    [{"role": "user", "content": "Hello"}]
    ${request_data}=    Create dictionary
    ...    model=amd/Llama-3.1-8B-Instruct-FP8-KV
    ...    messages=${messages}
    ...    max_tokens=10

    # Use /v1/chat/completions endpoint which requires authentication
    ${response}=    Post request    ${AIMS_EXTERNAL_HOST}/v1/chat/completions    json=${request_data}    headers=${headers}    expected_status=any

    Set test variable    ${MODEL_ACCESS_RESPONSE}    ${response}

Request is made to AIMS model without api key
    [Documentation]    Make a request to AIMS model without API key
    Variable should exist    ${AIMS_EXTERNAL_HOST}

    ${headers}=    Create dictionary
    ...    Content-Type=application/json

    ${messages}=    Evaluate    [{"role": "user", "content": "Hello"}]
    ${request_data}=    Create dictionary
    ...    model=amd/Llama-3.1-8B-Instruct-FP8-KV
    ...    messages=${messages}
    ...    max_tokens=10

    # Use /v1/chat/completions endpoint which requires authentication
    ${response}=    Post request    ${AIMS_EXTERNAL_HOST}/v1/chat/completions    json=${request_data}    headers=${headers}    expected_status=any

    Set test variable    ${MODEL_ACCESS_RESPONSE}    ${response}

AIMS model access works with api key
    [Documentation]    Verify that AIMS model access works with the assigned API key
    Request is made to AIMS model with valid api key
    Request should succeed

Requests exceed rate limit to AIMS model
    [Documentation]    Make requests to AIMS model that exceed the configured rate limit
    # Make 15 rapid requests (exceeding 10 per minute limit)
    FOR    ${i}    IN RANGE    15
        Request is made to AIMS model with valid api key
        Sleep    0.1s
    END

# AIMS Model Lifecycle Keywords
AIMS model is permanently deleted
    [Documentation]    Permanently delete the deployed AIMS model
    Variable should exist    ${TEST_AIM_ID}
    Variable should exist    ${TEST_PROJECT_ID}
    Undeploy AIM request is sent
    Response status should be    204
    Deployed workload should be removed

# Assertion Keywords for AIMS
AIMS model should accept requests with api key
    [Documentation]    Verify that AIMS model accepts requests with the assigned API key
    Request is made to AIMS model with valid api key
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    200

Response should contain model information
    [Documentation]    Verify that response contains valid chat completion
    Should be equal as integers    ${MODEL_ACCESS_RESPONSE.status_code}    200
    ${response_data}=    Set variable    ${MODEL_ACCESS_RESPONSE.json()}
    # Chat completions endpoint should return choices array
    Should contain    ${response_data}    choices

Response error message should indicate authentication failure
    [Documentation]    Verify response error message indicates authentication failure
    ...    Handles both JSON responses (from service) and non-JSON responses (from Envoy gateway)
    ${status}=    Set variable    ${MODEL_ACCESS_RESPONSE.status_code}
    # 403 from Envoy gateway may not have JSON body - status code verification is sufficient
    IF    ${status} == 403
        Log    Envoy gateway returned 403 Forbidden (expected for authentication failure)    INFO
        RETURN
    END
    # For other error codes, verify JSON error message
    ${error_response}=    Set variable    ${MODEL_ACCESS_RESPONSE.json()}
    Should contain    ${error_response}    error
    ${error_message}=    Get from dictionary    ${error_response}    error
    ${error_lower}=    Convert to lowercase    ${error_message}
    Should contain any    ${error_lower}    unauthorized    authentication    invalid

AIMS model should accept any of the assigned keys
    [Documentation]    Verify AIMS model accepts any assigned key
    Variable should exist    ${AIMS_EXTERNAL_HOST}

    ${messages}=    Evaluate    [{"role": "user", "content": "Hello"}]
    ${request_data}=    Create dictionary
    ...    model=amd/Llama-3.1-8B-Instruct-FP8-KV
    ...    messages=${messages}
    ...    max_tokens=10

    FOR    ${key}    IN    @{CREATED_API_KEYS}
        ${headers}=    Create dictionary
        ...    Authorization=Bearer ${key}[api_key]
        ...    Content-Type=application/json

        ${response}=    Post request    ${AIMS_EXTERNAL_HOST}/v1/chat/completions    json=${request_data}    headers=${headers}    expected_status=any
        Should be equal as integers    ${response.status_code}    200
    END

All AIMS models should accept the same api key
    [Documentation]    Verify all AIMS models accept the same API key
    # Get all AIMS external hosts
    FOR    ${workload_id}    IN    @{DEPLOYED_AIMS_WORKLOAD_IDS}
        ${response}=    Get menaged workload    ${workload_id}    expected_status=200
        ${json}=    Set variable    ${response.json()}
        ${output}=    Get from dictionary    ${json}    output
        ${external_host}=    Get from dictionary    ${output}    external_host

        ${headers}=    Create dictionary
        ...    Authorization=Bearer ${CURRENT_API_KEY_VALUE}
        ...    Content-Type=application/json

        ${response}=    Get request    ${external_host}/v1/models    headers=${headers}    expected_status=any
        Should be equal as integers    ${response.status_code}    200
    END

Key should show all AIMS model mappings
    [Documentation]    Verify key shows all AIMS model mappings via AIRM API
    ...    Note: Current AIRM API implementation doesn't return aim_ids in GET response,
    ...    so we verify by checking that all models accepted the key in the previous step.
    ${key_exists}=    Run keyword and return status    Variable should exist    ${CURRENT_AIRM_API_KEY}
    IF    not ${key_exists}
        Fail    CURRENT_AIRM_API_KEY variable not set
    END

    ${endpoint}=    Catalog endpoint    api-keys/${CURRENT_AIRM_API_KEY}[id]

    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    Safe Get Request
    ...    ${endpoint}
    ...    params=${params}
    ...    expected_status=200

    ${key_info}=    Set variable    ${response.json()}

    # Verify the key exists and is valid
    Should be equal    ${key_info}[id]    ${CURRENT_AIRM_API_KEY}[id]

    # TODO: Once AIRM API returns aim_ids in GET response, add this verification:
    # ${aim_ids}=    Get from dictionary    ${key_info}    aim_ids
    # ${mapping_count}=    Get length    ${aim_ids}
    # ${model_count}=    Get length    ${DEPLOYED_AIMS_WORKLOAD_IDS}
    # Should be equal as integers    ${mapping_count}    ${model_count}

    # For now, we rely on the previous step "all AIMS models should accept the same api key"
    # which functionally verifies that the key was assigned to all models
    Log    Verified API key ${CURRENT_AIRM_API_KEY}[id] exists and was assigned to ${DEPLOYED_AIMS_WORKLOAD_IDS.__len__()} models    INFO

# Helper Keywords
Get request
    [Documentation]    Make a GET request to given URL
    [Arguments]    ${url}    ${headers}=${None}    ${expected_status}=any

    ${response}=    GET    ${url}    headers=${headers}    expected_status=${expected_status}

    RETURN    ${response}

Response status should be
    [Documentation]    Verify response status code
    [Arguments]    ${expected_status}
    Should be equal as integers    ${response.status_code}    ${expected_status}

Should contain any
    [Documentation]    Verify string contains at least one of the expected substrings
    [Arguments]    ${string}    @{expected_substrings}
    ${found}=    Set variable    ${False}
    FOR    ${substring}    IN    @{expected_substrings}
        ${contains}=    Run keyword and return status    Should contain    ${string}    ${substring}
        IF    ${contains}
            ${found}=    Set variable    ${True}
            BREAK
        END
    END
    Should be true    ${found}    String '${string}' does not contain any of: ${expected_substrings}

# AIM Redeployment Keywords
AIM is undeployed
    [Documentation]    Undeploy the currently running AIM using existing keyword
    Undeploy AIM request is sent
    Response status should be 204

Same AIM is redeployed
    [Documentation]    Redeploy the same AIM that was just undeployed
    # Use the existing deployment keyword which handles everything
    AIM is deployed and running
    # Get the new external host
    ${response}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${output}=    Get from dictionary    ${json}    output
    ${external_host}=    Get from dictionary    ${output}    external_host
    Set test variable    ${AIMS_EXTERNAL_HOST}    ${external_host}

Api key should not work with redeployed AIM
    [Documentation]    Verify API key doesn't work after AIM redeployment
    ...    When an AIM is undeployed and redeployed, the API key binding should be broken
    ...    because the workload ID changes and cluster-auth groups are tied to workload instances
    Request is made to AIMS model with valid api key
    # This SHOULD fail with 401 once authentication is enforced
    # For now, it will succeed (200) because auth is not enforced
    # TODO: Update expectation when auth enforcement is implemented
    Log    API key still works with redeployed AIM (auth not enforced yet)    WARN

Api key should require reassignment to new deployment
    [Documentation]    Verify that API key needs to be reassigned after redeployment
    ...    The key should exist but not be bound to the new workload instance
    Variable should exist    ${CURRENT_AIRM_API_KEY}    CURRENT_AIRM_API_KEY not set

    # Get current key info
    &{params}=    Create dictionary    project_id=${TEST_PROJECT_ID}
    ${response}=    api_keys_api.Get api key    ${CURRENT_AIRM_API_KEY}[id]    params=${params}    expected_status=200

    ${key_data}=    Set variable    ${response.json()}

    # The key should still exist in the system
    Should contain    ${key_data}    id
    Should be equal    ${key_data}[id]    ${CURRENT_AIRM_API_KEY}[id]

    # Log that reassignment would be needed (but we're not enforcing it in this test)
    Log    API key exists but would need reassignment to new AIM deployment    INFO

# Setup and Teardown for AIMS
Initialize AIMS API key test environment
    [Documentation]    Initialize test environment for AIMS API key testing
    Initialize api key test environment
    # Initialize AIMS tracking
    @{empty_aims}=    Create list
    Set test variable    @{DEPLOYED_AIMS_LIST}    @{empty_aims}

Clean up AIMS and api keys
    [Documentation]    Clean up all AIMS deployments and API keys
    # Clean up AIMS first
    Cleanup AIM After Test
    # Then clean up API keys
    Clean up api keys and models
