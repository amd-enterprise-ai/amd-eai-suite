# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


*** Settings ***
Documentation       Test scenarios for API key management functionality with AIMS models.
...                 Verifies API key creation, assignment to deployed AIMS models, access control,
...                 and key lifecycle management operations via AIWB API.
...                 These tests cover:
...                 - Creating and managing API keys through AIWB API
...                 - Assigning keys to deployed AIMS models
...                 - Authenticating AIMS model access with keys
...                 - Key revocation and access enforcement
...                 - AIMS model redeployment impacts on key bindings
...
...                 Architecture Note:
...                 API keys are managed through AIWB's namespace-based API endpoints.
...                 Authentication is enforced at the API gateway level.
...                 Tests interact only with the AIWB API.
...
...                 Suite Efficiency Design:
...                 Uses Suite Setup/Teardown so the project is created once and deleted once
...                 at the end. Each test declares its preconditions via Given steps for
...                 readability and standalone execution. The AIM deployment keywords are
...                 idempotent - they reuse a running AIM when present, only deploying when
...                 needed. This avoids redundant AIM deployments across tests.
...
...                 Test Ordering:
...                 Tests are ordered for efficiency: non-GPU tests first, then tests
...                 sharing a single AIM deployment, then destructive operations last.

Resource            resources/aims/api_keys.resource
Resource            resources/airm_keywords.resource
Resource            resources/aiwb_aims.resource
Resource            resources/airm_projects.resource
Resource            resources/airm_workloads.resource
Resource            resources/deployment.resource
Library             Collections
Library             RequestsLibrary

Suite Setup         Run Keywords
...                 Initialize Project Tracking    AND
...                 Initialize AIMS API key test environment
Suite Teardown      Clean Up All Created Projects


*** Test Cases ***
# Phase 1 — No GPU needed

Api key with expiration
    [Documentation]    Verify API key expiration behavior
    ...
    ...    Note: TTL is specified in seconds (3600 = 1 hour). The keyword automatically
    ...    appends 's' suffix, so duration format like "1d" cannot be used here.
    ...
    ...    Verifies that expires_at is set and in the future. Actual expiration enforcement
    ...    (rejecting expired keys) can't be reliably tested in E2E due to timing constraints.
    [Tags]    api-keys    expiration    ttl

    Given a ready project with user access exists
    And user is authenticated
    When api key is created with ttl of 3600s
    Then api key should be created with expiration time

Revoke api key
    [Documentation]    Verify that an API key can be revoked
    ...
    ...    Note: Revocation permanently deletes the API key.
    ...    A revoked key will not appear in listings.
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

# Phase 2 — Single AIM (deployed once, reused by all)

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
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And user is authenticated
    And api key exists for user
    And an AIM model is running
    When api key is assigned to AIMS model
    Then key assignment should succeed
    And AIMS model access works with api key
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
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    When request is made to AIMS model with valid api key
    Then request should succeed
    And response should contain model information
    # TODO: Re-enable when API key access logging is implemented for AIWB API keys
    # And access attempt should be logged

Access AIMS model with invalid api key
    [Documentation]    Verify that AIMS model access fails with invalid API key
    ...
    ...    Authentication is enforced at the API gateway level.
    ...    Expected response: 403 Forbidden (authentication required)
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Make request with INVALID API key
    ...    3. Verify request fails with 401/403 (authentication failure)
    [Tags]    api-keys    access    aims    negative

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    When request is made to AIMS model with invalid api key
    Then request should fail with 401 unauthorized
    And response error message should indicate authentication failure

Access AIMS model without api key
    [Documentation]    Verify that AIMS model access fails without API key when required
    ...
    ...    Authentication is enforced at the API gateway level.
    ...    Expected response: 403 Forbidden (authentication required)
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Make request to AIMS model without any API key
    ...    3. Verify request fails with 401/403 (authentication failure)
    [Tags]    api-keys    access    aims    negative

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    When request is made to AIMS model without api key
    Then request should fail with 401 unauthorized
    And error message should indicate missing api key

Assign multiple keys to single AIMS model
    [Documentation]    Verify that multiple API keys can be assigned to one AIMS model
    [Tags]    api-keys    assign    aims    multiple

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running
    And user is authenticated

    When new api key is created
    Then api key should be created successfully
    And api key 1 is remembered

    When new api key is created
    Then api key should be created successfully
    And api key 2 is remembered

    When new api key is created
    Then api key should be created successfully
    And api key 3 is remembered

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

Access AIMS model with revoked api key
    [Documentation]    Verify that a revoked API key is rejected when accessing AIMS model
    ...
    ...    This tests the access enforcement side of revocation.
    ...    The key is created, assigned, verified working, then revoked.
    ...    After revocation, the same key value should be rejected.
    ...    Waits 60 seconds for revocation to propagate through the auth cache.
    ...    Skipped: Gateway auth cache does not propagate key revocation (SDA-3395).
    [Tags]    api-keys    access    aims    negative    revoke    skip

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    And AIMS model access works with api key
    When api key is revoked
    Then revocation should succeed
    And 60 seconds pass for revocation to propagate
    And AIMS model should reject the revoked api key

# Phase 3 — Destructive (undeploy/redeploy/delete)

Model redeployment preserves key but breaks binding
    [Documentation]    Verify that AIM redeployment breaks the key-to-model binding.
    ...    After redeployment, the AIM gets a new cluster auth group ID.
    ...    The key remains bound to the OLD group, so the binding is stale.
    [Tags]    api-keys    deployment    mapping    aims

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    And AIMS model access works with api key
    When AIM is undeployed
    And same AIM is redeployed
    Then api key should not be bound to redeployed AIM
    And api key should still exist in system

# TODO: "Assign single key to multiple AIMS models" test removed — needs multi-model
# infrastructure support (multiple AIM models available, enough GPU quota for two
# simultaneous deployments, and cleanup for second deployment).

# Phase 4 — Renewal

Renew renewable API key
    [Documentation]    Verify that a renewable API key's lease can be extended
    ...
    ...    Steps:
    ...    1. Ensure project and authentication
    ...    2. Create a renewable API key
    ...    3. Renew the key's lease
    ...    4. Verify renewal succeeded with lease_duration in response
    [Tags]    api-keys    renewal    management

    Given a ready project with user access exists
    And user is authenticated
    And api key exists for user
    When api key is renewed
    Then api key renewal should succeed

Access AIMS model after key renewal
    [Documentation]    Verify that an AIMS model remains accessible after key renewal
    ...
    ...    The key value does not change on renewal — only the lease is extended.
    ...    Model access should continue working with the same key.
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key
    ...    2. Renew the API key
    ...    3. Verify renewal succeeded
    ...    4. Verify AIMS model still accepts the same key
    [Tags]    api-keys    renewal    aims    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    When api key is renewed
    Then api key renewal should succeed
    And AIMS model access works with api key

Renew non-renewable API key fails
    [Documentation]    Verify that a non-renewable API key cannot be renewed
    ...
    ...    Keys created with renewable=False should be rejected by the renewal endpoint.
    ...
    ...    Steps:
    ...    1. Create a non-renewable API key
    ...    2. Attempt to renew it
    ...    3. Verify renewal is rejected
    [Tags]    api-keys    renewal    negative

    Given a ready project with user access exists
    And user is authenticated
    When non-renewable api key is created
    Then api key should be created successfully
    When non-renewable api key renewal is attempted
    Then api key renewal should fail with expected error

# Phase 5 — Cleanup (permanent AIM deletion)

Remove AIMS model with active key mapping
    [Documentation]    Verify behavior when AIMS model is removed with active key mapping
    ...
    ...    This tests the cleanup behavior when an AIM workload is undeployed.
    ...    The API key should remain valid but with no active model mappings.
    ...
    ...    Note: Known limitation - API key cleanup after AIM deletion may have edge cases.
    ...    This is tracked for future improvements.
    [Tags]    api-keys    deployment    aims    cleanup

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    When AIMS model is permanently deleted
    Then api key should show no active mappings
    And key status should indicate resource removed
    And api key should remain valid for other uses

# Rate limiting is not currently exposed through the API
