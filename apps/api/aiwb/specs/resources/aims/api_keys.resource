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
...                 - Dual-AIM deployment keywords for multi-model regression tests
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
Library             ModelCatalog


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
    # Extract cluster auth group ID for API key assignment
    ${cluster_auth_group_id}=    Get from dictionary    ${json}    clusterAuthGroupId
    Set test variable    ${TEST_AIM_AUTH_GROUP_ID}    ${cluster_auth_group_id}

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
    ...    Uses PATCH /api-keys/{api_key_id} endpoint with aimIds parameter (AIM service IDs)
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
    ${update_data}=    Create dictionary    aimIds=${aim_ids}

    ${project}=    Get Project Namespace
    ${response}=    Update api key
    ...    ${api_key}[id]
    ...    ${update_data}
    ...    project=${project}
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
    # 403/404 from the gateway may not have a structured JSON body
    IF    ${status} in [403, 404]
        Log    Gateway returned ${status} (expected for authentication failure)    INFO
        RETURN
    END
    # For other error codes, verify JSON error message
    ${error_response}=    Set variable    ${TEST_RESPONSE.json()}
    Should contain    ${error_response}    error
    ${error_message}=    Get from dictionary    ${error_response}    error
    ${error_lower}=    Convert to lowercase    ${error_message}
    Should contain any    ${error_lower}    unauthorized    authentication    invalid

AIMS model should reject the revoked api key
    [Documentation]    Verify that a revoked key is rejected when accessing AIMS model,
    ...    waiting up to 120 seconds for revocation to propagate through the auth cache.
    ...    The gateway returns 404 for any unknown credential (revoked or fake alike)
    ...    to avoid leaking whether a key ever existed. 401/403 may still be observed
    ...    depending on which auth layer enforces the rejection.
    Wait Until Keyword Succeeds    120s    10s    Revoked api key request should be denied

Revoked api key request should be denied
    [Documentation]    Make a request with the revoked key and assert it is rejected.
    ...    Used as the polling condition inside Wait Until Keyword Succeeds.
    # TEST_API_KEY_VALUE still holds the revoked key's value string
    Request is made to AIMS model with valid api key
    ${status}=    Set variable    ${TEST_RESPONSE.status_code}
    Should be true    ${status} in [401, 403, 404]
    ...    Expected 401/403/404 for revoked key, got ${status}

# AIM Redeployment Keywords
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
    ${new_auth_group}=    Get from dictionary    ${json}    clusterAuthGroupId

    # Get the key's current group bindings
    ${project}=    Get Project Namespace
    ${key_response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]
    ...    project=${project}    expected_status=200
    ${key_data}=    Set variable    ${key_response.json()}
    ${groups}=    Get from dictionary    ${key_data}    groups

    # The key should NOT be bound to the new auth group
    Should not contain    ${groups}    ${new_auth_group}
    ...    API key should not be bound to the new deployment's auth group after redeployment

Api key should still exist in system
    [Documentation]    Verify the API key still exists and is retrievable
    ${project}=    Get Project Namespace
    ${response}=    api_keys_api.Get api key    ${TEST_API_KEY}[id]
    ...    project=${project}    expected_status=200
    ${key_data}=    Set variable    ${response.json()}
    Should be equal    ${key_data}[id]    ${TEST_API_KEY}[id]

# Group Membership Keywords for AIMS
The api-key's group memberships are listed
    [Documentation]    List the cluster-auth groups the current API key belongs to
    ${project}=    Get Project Namespace
    ${response}=    api_keys_api.List api key groups
    ...    ${TEST_API_KEY}[id]
    ...    project=${project}
    ...    expected_status=200
    Set test variable    ${TEST_RESPONSE}    ${response}

The api-key has no group memberships
    [Documentation]    Verify the API key has no group memberships in the listing response
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${data}    ${TEST_RESPONSE.json()}[data]
    Should be empty    ${data}
    ...    Expected no group memberships, got ${data}

The api-key is added to the AIM's auth group
    [Documentation]    Add the current API key to the running AIM's cluster-auth group
    Should not be empty    ${TEST_AIM_AUTH_GROUP_ID}
    ...    msg=AIM auth group ID required - ensure "an AIM model is running" ran first
    ${project}=    Get Project Namespace
    ${response}=    api_keys_api.Add api key to group
    ...    ${TEST_API_KEY}[id]
    ...    ${TEST_AIM_AUTH_GROUP_ID}
    ...    project=${project}
    ...    expected_status=201
    Set test variable    ${TEST_RESPONSE}    ${response}

The api-key has that group in its memberships
    [Documentation]    Verify the API key's membership list contains the AIM's auth group
    VAR    ${data}    ${TEST_RESPONSE.json()}[data]
    Should contain    ${data}    ${TEST_AIM_AUTH_GROUP_ID}
    ...    Expected membership list to contain ${TEST_AIM_AUTH_GROUP_ID}, got ${data}

The api-key is removed from the AIM's auth group
    [Documentation]    Remove the current API key from the running AIM's cluster-auth group
    Should not be empty    ${TEST_AIM_AUTH_GROUP_ID}
    ...    msg=AIM auth group ID required - ensure "an AIM model is running" ran first
    ${project}=    Get Project Namespace
    ${response}=    api_keys_api.Remove api key from group
    ...    ${TEST_API_KEY}[id]
    ...    ${TEST_AIM_AUTH_GROUP_ID}
    ...    project=${project}
    ...    expected_status=204
    Set test variable    ${TEST_RESPONSE}    ${response}
    # Refresh memberships into TEST_RESPONSE so subsequent assertions can re-check the state.
    The api-key's group memberships are listed

# ========================================================================
# Dual-AIM keywords for multi-model regression tests (Bug A)
# ========================================================================

Second smallest deployable AIM resource name
    [Documentation]    Returns the metadata.name of the second-smallest open
    ...    auto-deployable AIM on this cluster. Used by dual-AIM regression tests
    ...    (Bug A — per-model auth when two AIMs share the workloads.* hostname)
    ...    so that AIM-B is a genuinely distinct model from AIM-A.
    ${response}=    List AIMs    expected_status=200    status_filter=Ready    page_size=100
    VAR    ${aims_list}    ${response.json()}[data]
    ${count}=    Get Length    ${aims_list}
    Should Be True    ${count} > 1
    ...    msg=Need at least two Ready AIMs on cluster for dual-AIM regression test
    ${profiles}=    All inference profiles
    ${resource_name}=    Get Second Smallest Deployable Aim    ${aims_list}    ${profiles}
    Log    Selected second-smallest deployable AIM: ${resource_name}    INFO
    RETURN    ${resource_name}

A second AIM model is running
    [Documentation]    Deploys a second AIM (distinct from TEST_AIM_NAME / TEST_AIM_ID)
    ...    and records its external host and cluster-auth group in TEST_AIM_B_* variables.
    ...    AIM-A state (TEST_AIM_NAME, TEST_AIM_ID, TEST_AIM_EXTERNAL_HOST,
    ...    TEST_AIM_AUTH_GROUP_ID) is preserved — only the B-suffixed variables are set.
    ...    Used by the Bug-A regression: "Inference is authorized per model when two AIMs
    ...    share the workloads host".

    # Remember A-side state so we can restore after touching TEST_AIM_* in AIM-B setup.
    VAR    ${saved_aim_name}    ${TEST_AIM_NAME}
    VAR    ${saved_aim_id}    ${TEST_AIM_ID}
    VAR    ${saved_ext_host}    ${TEST_AIM_EXTERNAL_HOST}
    VAR    ${saved_auth_group}    ${TEST_AIM_AUTH_GROUP_ID}

    # Select and deploy AIM-B (second-smallest, different from AIM-A).
    ${aim_b_name}=    Second smallest deployable AIM resource name
    Should Not Be Equal    ${aim_b_name}    ${TEST_AIM_NAME}
    ...    msg=Second smallest AIM resolves to the same model as AIM-A (${TEST_AIM_NAME}); need a second distinct model on cluster
    VAR    ${TEST_AIM_NAME}    ${aim_b_name}    scope=TEST

    AIM is deployed and running

    # Capture AIM-B service details.
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${endpoints}=    Get From Dictionary    ${json}    endpoints
    ${ext_b}=    Get From Dictionary    ${endpoints}    external
    ${auth_b}=    Get From Dictionary    ${json}    clusterAuthGroupId
    VAR    ${TEST_AIM_B_NAME}    ${aim_b_name}    scope=TEST
    VAR    ${TEST_AIM_B_ID}    ${TEST_AIM_ID}    scope=TEST
    VAR    ${TEST_AIM_B_EXTERNAL_HOST}    ${ext_b}    scope=TEST
    VAR    ${TEST_AIM_B_AUTH_GROUP_ID}    ${auth_b}    scope=TEST

    # Restore AIM-A state so subsequent steps see A's coordinates again.
    VAR    ${TEST_AIM_NAME}    ${saved_aim_name}    scope=TEST
    VAR    ${TEST_AIM_ID}    ${saved_aim_id}    scope=TEST
    VAR    ${TEST_AIM_EXTERNAL_HOST}    ${saved_ext_host}    scope=TEST
    VAR    ${TEST_AIM_AUTH_GROUP_ID}    ${saved_auth_group}    scope=TEST

An api key authorized only for model A is created
    [Documentation]    Creates a fresh API key bound to AIM-A's cluster-auth group only.
    ...    AIM-B's group is intentionally excluded so cross-model enforcement is
    ...    testable. Stores the key in TEST_API_KEY / TEST_API_KEY_VALUE.
    ...    Requires: TEST_AIM_AUTH_GROUP_ID (set by "An AIM model is running")
    Variable Should Exist    ${TEST_AIM_AUTH_GROUP_ID}
    ...    msg=TEST_AIM_AUTH_GROUP_ID not set — run "An AIM model is running" first
    Api key exists for user
    # Bind the key to AIM-A's auth group.
    ${project}=    Get Project Namespace
    api_keys_api.Add api key to group
    ...    ${TEST_API_KEY}[id]
    ...    ${TEST_AIM_AUTH_GROUP_ID}
    ...    project=${project}
    ...    expected_status=201
    # Discover model ID for AIM-A so requests can target the correct model name.
    ${models}=    List models from external endpoint
    ...    ${TEST_AIM_EXTERNAL_HOST}    ${TEST_AIM_ID}    ${TEST_API_KEY_VALUE}
    ${first}=    Get From List    ${models}    0
    VAR    ${TEST_AIM_MODEL_ID}    ${first}[id]    scope=TEST

A request is made to model A with key A
    [Documentation]    Sends a chat completion to AIM-A's external endpoint with the
    ...    key that is authorized only for AIM-A.
    ...    Sets: TEST_RESPONSE
    ...    Requires: TEST_AIM_EXTERNAL_HOST, TEST_AIM_MODEL_ID, TEST_API_KEY_VALUE
    Variable Should Exist    ${TEST_AIM_EXTERNAL_HOST}
    ...    msg=TEST_AIM_EXTERNAL_HOST not set — run "An AIM model is running" first
    Variable Should Exist    ${TEST_AIM_MODEL_ID}
    ...    msg=TEST_AIM_MODEL_ID not set — run "An api key authorized only for model A is created" first
    ${response}=    Send chat completion request to external endpoint
    ...    ${TEST_AIM_EXTERNAL_HOST}    ${TEST_AIM_MODEL_ID}
    ...    api_key=${TEST_API_KEY_VALUE}
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

Model A should accept the request
    [Documentation]    Verifies that AIM-A's external endpoint returned HTTP 200,
    ...    confirming the authorized key was accepted (Bug-A false-denial regression:
    ...    cluster-auth hostname-only lookup would have wrongly denied this key).
    ...    Requires: TEST_RESPONSE (from "A request is made to model A with key A")
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    ...    msg=Key authorized for model A should be ACCEPTED on model A's endpoint; got ${TEST_RESPONSE.status_code}: ${TEST_RESPONSE.text}

A request is made to model B with key A
    [Documentation]    Sends a chat completion to AIM-B's external endpoint with the
    ...    key authorized only for AIM-A. Lists AIM-B's models with the key first:
    ...    200 yields the real model id; an expected auth denial (401/403/404) falls
    ...    back to AIM-B's resource name (the chat request is denied either way); any
    ...    other status fails the test rather than masking a regression.
    ...    Sets: TEST_RESPONSE
    ...    Requires: TEST_AIM_B_EXTERNAL_HOST, TEST_AIM_B_ID, TEST_AIM_B_NAME,
    ...              TEST_API_KEY_VALUE
    Variable Should Exist    ${TEST_AIM_B_EXTERNAL_HOST}
    ...    msg=TEST_AIM_B_EXTERNAL_HOST not set — run "A second AIM model is running" first
    ${models_resp}=    Get models response from external endpoint
    ...    ${TEST_AIM_B_EXTERNAL_HOST}    ${TEST_AIM_B_ID}    ${TEST_API_KEY_VALUE}
    ${status}=    Set Variable    ${models_resp.status_code}
    IF    ${status} == 200
        ${body}=    Set Variable    ${models_resp.json()}
        VAR    ${model_b_id}    ${body}[data][0][id]
    ELSE IF    ${status} in [401, 403, 404]
        # Expected: the key is authorized for A, not B, so listing B's models is denied.
        # Fall back to AIM-B's resource name; the chat request below is denied anyway.
        VAR    ${model_b_id}    ${TEST_AIM_B_NAME}
        Log    Model listing on AIM-B denied (${status}) as expected; using resource name    INFO
    ELSE
        Fail    Unexpected status ${status} listing models on AIM-B: ${models_resp.text}
    END
    ${response}=    Send chat completion request to external endpoint
    ...    ${TEST_AIM_B_EXTERNAL_HOST}    ${model_b_id}
    ...    api_key=${TEST_API_KEY_VALUE}
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

Model B should reject the request
    [Documentation]    Verifies that AIM-B's external endpoint returned HTTP 401/403/404,
    ...    confirming that a key authorized only for AIM-A is denied on AIM-B
    ...    (cross-model enforcement half of the Bug-A regression).
    ...    Requires: TEST_RESPONSE (from "A request is made to model B with key A")
    ${status}=    Set Variable    ${TEST_RESPONSE.status_code}
    Should Be True    ${status} in [401, 403, 404]
    ...    msg=Key authorized only for model A should be REJECTED on model B's endpoint; got ${status}: ${TEST_RESPONSE.text}

# Setup and Teardown for AIMS
Initialize AIMS API key test environment
    [Documentation]    Initialize test environment for AIMS API key testing.
    ...    Uses Set Suite Variable so variables are available in all tests when called
    ...    from Suite Setup.
    Initialize api key test environment
