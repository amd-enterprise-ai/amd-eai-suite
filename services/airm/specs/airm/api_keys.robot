# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for API key management functionality with AIMS models.
...                 Verifies API key creation, assignment to deployed AIMS models, access control,
...                 and key lifecycle management operations.
...                 These tests cover the integration with cluster-auth service for:
...                 - Creating and managing API keys
...                 - Assigning keys to deployed AIMS models
...                 - Authenticating AIMS model access with keys
...                 - Key revocation and rotation
...                 - AIMS model redeployment impacts on key mappings
...
...                 Architecture Note:
...                 API keys are associated with users only via AIRM DB metadata (created_by, updated_by).
...                 In OpenBao/cluster-auth, API keys are bound to entities which are bound to groups.
...                 The entity represents the API key itself, not the user, as cluster-auth does not
...                 receive user information during key creation.
...
...                 Prerequisites:
...                 - cluster-auth service deployed and accessible
...                 - Valid admin token for cluster-auth API
...                 - At least one deployable AIMS model available

Resource            ../resources/api_keys.resource
Resource            ../resources/catalog_keywords.resource
Resource            ../resources/catalog_aims.resource
Resource            ../resources/airm_projects.resource
Resource            ../resources/catalog_workloads.resource
Resource            ../resources/cluster_auth.resource
Library             Collections
Library             RequestsLibrary

Test Setup          Initialize AIMS API key test environment
Test Teardown       Clean up AIMS and api keys


*** Variables ***
${CLUSTER_AUTH_URL}     %{CLUSTER_AUTH_URL=http://localhost:8081}


*** Test Cases ***
Assign api key to deployed AIMS model
    [Documentation]    Verify that an API key can be assigned to a deployed AIMS model
    ...
    ...    Prerequisites:
    ...    - Valid API key exists
    ...    - AIMS model is deployed
    ...
    ...    Steps:
    ...    1. Deploy a test AIMS model
    ...    2. Assign API key to AIMS model
    ...    3. Verify key-model mapping
    [Tags]    api-keys    assign    aims

    Given a ready project with user access exists
    And user is authenticated
    And api key exists for user
    And an AIM model is running
    When api key is assigned to AIMS model
    Then key assignment should succeed
    And AIMS model should accept requests with api key
    And key-model mapping should be visible in management interface

Access AIMS model with valid api key
    [Documentation]    Verify that an AIMS model can be accessed with a valid API key
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Make request to AIMS model with API key
    ...    3. Verify successful access
    [Tags]    api-keys    access    aims    positive

    Given a ready project with user access exists
    And an AIM model is running with api key
    When request is made to AIMS model with valid api key
    Then request should succeed
    And response should contain model information
    # TODO: Re-enable when API key access logging is implemented for AIRM API keys
    # And access attempt should be logged

Access AIMS model with invalid api key
    [Documentation]    Verify that AIMS model access fails with invalid API key
    ...
    ...    Authentication is enforced by Envoy gateway via cluster-auth annotation.
    ...    Expected response: 403 Forbidden (authentication required)
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Make request with INVALID API key
    ...    3. Verify request fails with 401/403 (authentication failure)
    [Tags]    api-keys    access    aims    negative

    Given a ready project with user access exists
    And an AIM model is running with api key
    When request is made to AIMS model with invalid api key
    Then request should fail with 401 unauthorized
    And response error message should indicate authentication failure

Access AIMS model without api key
    [Documentation]    Verify that AIMS model access fails without API key when required
    ...
    ...    Authentication is enforced by Envoy gateway via cluster-auth annotation.
    ...    Expected response: 403 Forbidden (authentication required)
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Make request to AIMS model without any API key
    ...    3. Verify request fails with 401/403 (authentication failure)
    [Tags]    api-keys    access    aims    negative

    Given a ready project with user access exists
    And an AIM model is running with api key
    When request is made to AIMS model without api key
    Then request should fail with 401 unauthorized
    And error message should indicate missing api key

Revoke api key
    [Documentation]    Verify that an API key can be revoked
    ...
    ...    Note: Revocation is implemented as deletion in cluster-auth.
    ...    A revoked key is deleted and will not appear in listings.
    ...
    ...    Steps:
    ...    1. Create API key
    ...    2. Revoke key
    ...    3. Verify key is revoked (deleted from system)
    [Tags]    api-keys    revoke    management

    Given a ready project with user access exists
    And user is authenticated
    And api key exists for user
    When api key is revoked
    Then revocation should succeed
    And key status should show as revoked

Model redeployment breaks key mapping
    [Documentation]    Verify that AIM redeployment breaks existing key mappings
    ...
    ...    Steps:
    ...    1. Deploy AIM with API key
    ...    2. Undeploy AIM
    ...    3. Redeploy same AIM
    ...    4. Verify key mapping is broken and requires reassignment
    [Tags]    api-keys    deployment    mapping    aims

    Given a ready project with user access exists
    And an AIM model is running with api key
    And AIMS model access works with api key
    When AIM is undeployed
    And same AIM is redeployed
    Then api key should not work with redeployed AIM
    And api key should require reassignment to new deployment

Assign multiple keys to single AIMS model
    [Documentation]    Verify that multiple API keys can be assigned to one AIMS model
    [Tags]    api-keys    assign    aims    multiple

    Given a ready project with user access exists
    And an AIM model is running
    And user is authenticated

    # Create first key
    When new AIRM api key is requested
    Then AIRM api key should be created successfully
    Set test variable    ${API_KEY_1}    ${CURRENT_AIRM_API_KEY}

    # Create second key
    When new AIRM api key is requested
    Then AIRM api key should be created successfully
    Set test variable    ${API_KEY_2}    ${CURRENT_AIRM_API_KEY}

    # Create third key
    When new AIRM api key is requested
    Then AIRM api key should be created successfully
    Set test variable    ${API_KEY_3}    ${CURRENT_AIRM_API_KEY}

    # Assign all three keys to the same model
    When api key is assigned to AIMS model    api_key=${API_KEY_1}
    Then key assignment should succeed

    When api key is assigned to AIMS model    api_key=${API_KEY_2}
    Then key assignment should succeed

    When api key is assigned to AIMS model    api_key=${API_KEY_3}
    Then key assignment should succeed

    # Verify each key works with the model
    When request is made to AIMS model with valid api key    api_key_value=${API_KEY_1}[full_key]
    Then request should succeed

    When request is made to AIMS model with valid api key    api_key_value=${API_KEY_2}[full_key]
    Then request should succeed

    When request is made to AIMS model with valid api key    api_key_value=${API_KEY_3}[full_key]
    Then request should succeed

Assign single key to multiple AIMS models
    [Documentation]    Verify that one API key can be assigned to multiple AIMS models
    ...
    ...    Steps:
    ...    1. Deploy multiple AIMS models
    ...    2. Create one API key
    ...    3. Assign key to all deployed models
    ...    4. Verify all models accept the same key
    [Tags]    api-keys    assign    aims    multiple

    Given a ready project with user access exists
    And user is authenticated
    And api key exists for user
    Set test variable    ${SHARED_KEY}    ${CURRENT_AIRM_API_KEY}

    # Deploy first model
    When AIM is deployed and running
    Set test variable    ${MODEL_1_ID}    ${TEST_AIM_ID}
    Set test variable    ${MODEL_1_WORKLOAD}    ${DEPLOYED_WORKLOAD_ID}
    ${response}=    Get menaged workload    ${MODEL_1_WORKLOAD}    expected_status=200
    ${output}=    Get from dictionary    ${response.json()}    output
    Set test variable    ${MODEL_1_HOST}    ${output}[external_host]

    # Deploy second model
    When AIM is deployed and running
    Set test variable    ${MODEL_2_ID}    ${TEST_AIM_ID}
    Set test variable    ${MODEL_2_WORKLOAD}    ${DEPLOYED_WORKLOAD_ID}
    ${response}=    Get menaged workload    ${MODEL_2_WORKLOAD}    expected_status=200
    ${output}=    Get from dictionary    ${response.json()}    output
    Set test variable    ${MODEL_2_HOST}    ${output}[external_host]

    # Assign the same key to both models
    When api key is assigned to AIMS model    api_key=${SHARED_KEY}    aim_id=${MODEL_1_ID}
    Then key assignment should succeed

    When api key is assigned to AIMS model    api_key=${SHARED_KEY}    aim_id=${MODEL_2_ID}
    Then key assignment should succeed

    # Verify key works with first model
    When request is made to AIMS model with valid api key    api_key_value=${SHARED_KEY}[full_key]    host=${MODEL_1_HOST}
    Then request should succeed

    # Verify key works with second model
    When request is made to AIMS model with valid api key    api_key_value=${SHARED_KEY}[full_key]    host=${MODEL_2_HOST}
    Then request should succeed

Api key with expiration
    [Documentation]    Verify API key expiration behavior
    ...
    ...    Note: TTL is specified in seconds (3600 = 1 hour). The keyword automatically
    ...    appends 's' suffix, so duration format like "1d" cannot be used here.
    ...    Model access verification skipped due to GPU unavailability.
    [Tags]    api-keys    expiration    ttl

    Given a ready project with user access exists
    And user is authenticated
    When api key is created with ttl
    ...    ttl=3600
    Then api key should be created with expiration time

Remove AIMS model with active key mapping
    [Documentation]    Verify behavior when AIMS model is removed with active key mapping
    ...
    ...    This tests the cleanup behavior when an AIM workload is undeployed.
    ...    The API key should remain valid but with no active model mappings.
    ...
    ...    Note: Known limitation - API key may retain orphaned group bindings in cluster-auth
    ...    after AIM deletion. This is tracked for future cleanup improvements.
    [Tags]    api-keys    deployment    aims    cleanup

    Given a ready project with user access exists
    And an AIM model is running with api key
    When AIMS model is permanently deleted
    Then api key should show no active mappings
    And key status should indicate resource removed
    And api key should remain valid for other uses

# Api key rate limiting test removed - rate limiting is not exposed through AIRM API
# Rate limiting is a cluster-auth feature that would require direct cluster-auth access to test
