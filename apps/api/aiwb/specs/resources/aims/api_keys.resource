# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       LAYER 2: Business Logic - AIMS-specific API key management keywords.
...
...                 This resource provides high-level keywords for API key operations specific to AIMS models.
...                 It builds on top of the generic API key testing framework in resources/api_keys.resource.
...
...                 This file contains:
...                 - AIMS model deployment keywords for API key testing
...                 - API key assignment to AIMS models
...                 - AIMS model access verification with API keys
...                 - AIMS-specific lifecycle management
...
...                 Usage:
...                 - Import this file for AIMS-specific API key tests
...                 - This file automatically imports the generic api_keys.resource
...                 - All generic keywords are available through this import

Resource            resources/api_keys.resource
Resource            resources/airm_keywords.resource
Resource            resources/aiwb_aims.resource
Resource            resources/airm_workloads.resource
Resource            resources/airm_projects.resource
Resource            resources/api/common.resource
Resource            resources/api/api_keys_api.resource
Library             BuiltIn
Library             Collections


*** Keywords ***
# ========================================================================
# AIMS-Specific Keywords
# ========================================================================

# AIMS Deployment Keywords
An AIM model is running
    [Documentation]    Ensure an AIMS model is in Running state
    AIM is deployed and running
    # Get the external endpoint and cluster auth group ID from AIM Service (AIWB API)
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${endpoints}=    Get from dictionary    ${json}    endpoints
    ${external_url}=    Get from dictionary    ${endpoints}    external
    Set test variable    ${TEST_AIM_EXTERNAL_HOST}    ${external_url}

An AIM model is running with api key
    [Documentation]    Ensure AIMS model is running and has API key assigned
    An AIM model is running
    User is authenticated
    Api key exists for user
    Api key is assigned to AIMS model
    Key assignment should succeed
    # Discover model ID using the API key for auth (external endpoint requires it)
    ${models}=    List models from external endpoint    ${TEST_AIM_EXTERNAL_HOST}    ${TEST_AIM_ID}    ${TEST_API_KEY_VALUE}
    ${first_model}=    Get from list    ${models}    0
    ${model_id}=    Get from dictionary    ${first_model}    id
    Set test variable    ${TEST_AIM_MODEL_ID}    ${model_id}

# API Key Assignment Keywords for AIMS
Api key is assigned to AIMS model
    [Documentation]    Assign API key to AIMS model using AIWB API
    ...    Uses PATCH /api-keys/{api_key_id} endpoint with aim_ids parameter (AIM service IDs)
    ...    The API internally maps AIM service IDs to cluster auth group IDs
    ...    Can specify api_key and aim_id or use defaults (TEST_API_KEY, TEST_AIM_ID)
    [Arguments]    ${api_key}=${TEST_API_KEY}    ${aim_id}=${TEST_AIM_ID}

    # Validate we have required values
    Should not be empty    ${api_key}
    ...    msg=API key required - pass api_key= or ensure TEST_API_KEY is set
    Should not be empty    ${aim_id}
    ...    msg=AIM service ID required - pass aim_id= or ensure TEST_AIM_ID is set

    # Update API key bindings via AIWB API with AIM service ID
    @{aim_ids}=    Create list    ${aim_id}
    ${update_data}=    Create dictionary    aim_ids=${aim_ids}

    ${namespace}=    Get Project Namespace
    ${response}=    Update api key
    ...    ${api_key}[id]
    ...    ${update_data}
    ...    namespace=${namespace}
    ...    expected_status=any

    Set test variable    ${TEST_RESPONSE}    ${response}

# AIMS Model Access Keywords
Request is made to AIMS model with valid api key
    [Documentation]    Make a request to AIMS model endpoint with valid API key
    ...    Can specify api_key_value and host or use defaults (TEST_API_KEY_VALUE, TEST_AIM_EXTERNAL_HOST)
    ...    Lazily discovers the model ID on first call using /v1/models with the API key.
    [Arguments]    ${api_key_value}=${TEST_API_KEY_VALUE}    ${host}=${TEST_AIM_EXTERNAL_HOST}

    Should not be empty    ${api_key_value}
    ...    msg=API key value required - pass api_key_value= or ensure TEST_API_KEY_VALUE is set
    Should not be empty    ${host}
    ...    msg=Host required - pass host= or ensure TEST_AIM_EXTERNAL_HOST is set

    # Discover model ID if not already set (external endpoint requires API key auth)
    ${model_id_set}=    Get variable value    ${TEST_AIM_MODEL_ID}    ${None}
    IF    $model_id_set is None
        ${models}=    List models from external endpoint    ${host}    ${TEST_AIM_ID}    ${api_key_value}
        ${first_model}=    Get from list    ${models}    0
        ${discovered_id}=    Get from dictionary    ${first_model}    id
        Set test variable    ${TEST_AIM_MODEL_ID}    ${discovered_id}
    END

    ${response}=    Send chat completion request to external endpoint
    ...    ${host}    ${TEST_AIM_MODEL_ID}    api_key=${api_key_value}

    Set test variable    ${TEST_RESPONSE}    ${response}

Request is made to AIMS model with invalid api key
    [Documentation]    Make a request to AIMS model with invalid API key
    Variable should exist    ${TEST_AIM_EXTERNAL_HOST}
    Variable should exist    ${TEST_AIM_MODEL_ID}

    ${response}=    Send chat completion request to external endpoint
    ...    ${TEST_AIM_EXTERNAL_HOST}    ${TEST_AIM_MODEL_ID}    api_key=invalid-api-key-12345

    Set test variable    ${TEST_RESPONSE}    ${response}

Request is made to AIMS model without api key
    [Documentation]    Make a request to AIMS model without API key
    Variable should exist    ${TEST_AIM_EXTERNAL_HOST}
    Variable should exist    ${TEST_AIM_MODEL_ID}

    ${response}=    Send chat completion request to external endpoint
    ...    ${TEST_AIM_EXTERNAL_HOST}    ${TEST_AIM_MODEL_ID}

    Set test variable    ${TEST_RESPONSE}    ${response}

AIMS model access works with api key
    [Documentation]    Verify that AIMS model access works with the assigned API key
    Request is made to AIMS model with valid api key
    Request should succeed

# AIMS Model Lifecycle Keywords
AIMS model is permanently deleted
    [Documentation]    Permanently delete the deployed AIMS model
    Variable should exist    ${TEST_AIM_ID}
    Variable should exist    ${TEST_PROJECT_ID}
    Undeploy AIM request is sent
    Response status should be 204
    Deployed workload should be removed

Response should contain model information
    [Documentation]    Verify that response contains valid chat completion
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200
    ${response_data}=    Set variable    ${TEST_RESPONSE.json()}
    # Chat completions endpoint should return choices array
    Should contain    ${response_data}    choices

Response error message should indicate authentication failure
    [Documentation]    Verify response error message indicates authentication failure
    ...    Handles both JSON responses (from service) and non-JSON responses (from Envoy gateway)
    ${status}=    Set variable    ${TEST_RESPONSE.status_code}
    # 403 from Envoy gateway may not have JSON body - status code verification is sufficient
    IF    ${status} == 403
        Log    Envoy gateway returned 403 Forbidden (expected for authentication failure)    INFO
        RETURN
    END
    # For other error codes, verify JSON error message
    ${error_response}=    Set variable    ${TEST_RESPONSE.json()}
    Should contain    ${error_response}    error
    ${error_message}=    Get from dictionary    ${error_response}    error
    ${error_lower}=    Convert to lowercase    ${error_message}
    Should contain any    ${error_lower}    unauthorized    authentication    invalid

${duration} pass for revocation to propagate
    [Documentation]    Wait for API key revocation to propagate through the auth layer cache.
    Sleep    ${duration}    Waiting for API key revocation to propagate

AIMS model should reject the revoked api key
    [Documentation]    Verify that a revoked key is rejected when accessing AIMS model.
    # TEST_API_KEY_VALUE still holds the revoked key's value string
    Request is made to AIMS model with valid api key
    ${status}=    Set variable    ${TEST_RESPONSE.status_code}
    Should be true    ${status} in [401, 403]
    ...    Expected 401/403 for revoked key, got ${status}

# AIM Redeployment Keywords
AIM is undeployed
    [Documentation]    Undeploy the currently running AIM using existing keyword
    Undeploy AIM request is sent
    Response status should be 204

Same AIM is redeployed
    [Documentation]    Redeploy the same AIM that was just undeployed
    # Use the existing deployment keyword which handles everything
    AIM is deployed and running
    # Get the new external host from AIM Service (AIWB API)
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${endpoints}=    Get from dictionary    ${json}    endpoints
    ${external_url}=    Get from dictionary    ${endpoints}    external
    Set test variable    ${TEST_AIM_EXTERNAL_HOST}    ${external_url}
    # Model ID stays the same after redeployment (same AIM, same vLLM model).
    # No need to rediscover — the old key can't auth against the new deployment anyway.

Api key should not be bound to redeployed AIM
    [Documentation]    Verify the key's group bindings don't include the new AIM's auth group.
    ...    After redeployment, the AIM gets a new cluster_auth_group_id.
    ...    The key should still be bound to the OLD group, not the new one.

    # Get the NEW deployment's auth group ID
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${new_auth_group}=    Get from dictionary    ${json}    cluster_auth_group_id

    # Get the key's current group bindings
    ${namespace}=    Get Project Namespace
    ${key_response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]
    ...    namespace=${namespace}    expected_status=200
    ${key_data}=    Set variable    ${key_response.json()}
    ${groups}=    Get from dictionary    ${key_data}    groups

    # The key should NOT be bound to the new auth group
    Should not contain    ${groups}    ${new_auth_group}
    ...    API key should not be bound to the new deployment's auth group after redeployment

Api key should still exist in system
    [Documentation]    Verify the API key still exists and is retrievable
    ${namespace}=    Get Project Namespace
    ${response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]
    ...    namespace=${namespace}    expected_status=200
    ${key_data}=    Set variable    ${response.json()}
    Should be equal    ${key_data}[id]    ${TEST_API_KEY}[id]

# Setup and Teardown for AIMS
Initialize AIMS API key test environment
    [Documentation]    Initialize test environment for AIMS API key testing.
    ...    Uses Set Suite Variable so variables are available in all tests when called
    ...    from Suite Setup.
    Initialize api key test environment
