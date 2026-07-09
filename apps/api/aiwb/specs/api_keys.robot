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
...                 API keys are managed through AIWB's project-based API endpoints.
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

Suite Setup         Initialize AIMS API key test environment
Suite Teardown      Clean Up All Tracked Resources


*** Test Cases ***
# Phase 1 — No GPU needed

Api key with expiration
    [Documentation]    Verify API key expiration behavior
    ...
    ...    Note: TTL is specified in seconds (3600 = 1 hour). The keyword automatically
    ...    appends 's' suffix, so duration format like "1d" cannot be used here.
    ...
    ...    Verifies that expiresAt is set and in the future. Actual expiration enforcement
    ...    (rejecting expired keys) can't be reliably tested in E2E due to timing constraints.
    [Tags]    api-keys    expiration    ttl

    Given a ready project with user access exists
    And user is authenticated
    When api key is created with ttl of 3600s
    Then api key should be created with expiration time

User can browse api keys page by page
    [Documentation]    API keys are served in pages rather than as one flat list,
    ...                so a consumer can navigate without loading every key.
    [Tags]    api-keys    list    pagination

    Given a ready project with user access exists
    And user is authenticated
    When api keys are listed for the project
    Then the result is returned page by page

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
    [Tags]    api-keys    assign    aims    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And user is authenticated
    And api key exists for user
    And an AIM model is running
    When api key is assigned to AIMS model
    Then key assignment should succeed
    And AIMS model access works with api key
    And key-model mapping should be visible in management interface

Manage api key group memberships
    [Documentation]    Verify the api-key /groups sub-resource: list, add, remove.
    [Tags]    api-keys    groups    management    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running
    And user is authenticated
    And api key exists for user
    When the api-key's group memberships are listed
    Then the api-key has no group memberships
    When the api-key is added to the AIM's auth group
    Then the api-key has that group in its memberships
    When the api-key is removed from the AIM's auth group
    Then the api-key has no group memberships

Access AIMS model with valid api key
    [Documentation]    Verify that an AIMS model can be accessed with a valid API key
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Make request to AIMS model with API key
    ...    3. Verify successful access
    [Tags]    api-keys    access    aims    positive    gpu

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
    ...    The gateway returns 404 for any unknown credential (invalid or never-existent)
    ...    to avoid leaking key existence; 401/403 may also be observed from other
    ...    enforcement layers.
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Prove model is reachable with a valid key (guards against spurious 404)
    ...    3. Make request with INVALID API key
    ...    4. Verify request fails with 401/403/404 (access denied)
    [Tags]    api-keys    access    aims    negative    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    And AIMS model access works with api key
    When request is made to AIMS model with invalid api key
    Then request should be rejected as unauthorized
    And response error message should indicate authentication failure

Access AIMS model without api key
    [Documentation]    Verify that AIMS model access fails without API key when required
    ...
    ...    Authentication is enforced at the API gateway level.
    ...    The request is rejected because no credential is supplied.
    ...
    ...    Steps:
    ...    1. Deploy AIMS model with API key assigned
    ...    2. Make request to AIMS model without any API key
    ...    3. Verify the request is rejected as unauthorized
    [Tags]    api-keys    access    aims    negative    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    When request is made to AIMS model without api key
    Then request should be rejected as unauthorized
    And error message should indicate missing api key

Assign multiple keys to single AIMS model
    [Documentation]    Verify that multiple API keys can be assigned to one AIMS model
    [Tags]    api-keys    assign    aims    multiple    gpu

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
    When request is made to AIMS model with valid api key    api_key_value=${API_KEY_1}[fullKey]
    Then request should succeed

    When request is made to AIMS model with valid api key    api_key_value=${API_KEY_2}[fullKey]
    Then request should succeed

    When request is made to AIMS model with valid api key    api_key_value=${API_KEY_3}[fullKey]
    Then request should succeed

Access AIMS model with revoked api key
    [Documentation]    Verify that a revoked API key is rejected when accessing AIMS model
    ...
    ...    This tests the access enforcement side of revocation.
    ...    The key is created, assigned, verified working, then revoked.
    ...    After revocation, the same key value should be rejected.
    ...    Polls up to 120 seconds for revocation to propagate through the auth cache.
    ...    The gateway returns 404 for unknown credentials (revoked or never-existed keys)
    ...    to avoid leaking whether a key ever existed. 401/403 may still be observed
    ...    depending on which enforcement layer rejects the request.
    [Tags]    api-keys    access    aims    negative    revoke    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    And AIMS model access works with api key
    When api key is revoked
    Then revocation should succeed
    And AIMS model should reject the revoked api key

# Phase 3 — Destructive (undeploy/redeploy/delete)

Model redeployment preserves key but breaks binding
    [Documentation]    Verify that AIM redeployment breaks the key-to-model binding.
    ...    After redeployment, the AIM gets a new cluster auth group ID.
    ...    The key remains bound to the OLD group, so the binding is stale.
    [Tags]    api-keys    deployment    mapping    aims    gpu

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
    ...    4. Verify renewal succeeded with leaseDuration in response
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
    [Tags]    api-keys    deployment    aims    cleanup    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM model is running with api key
    When AIMS model is permanently deleted
    Then api key should show no active mappings
    And key status should indicate resource removed
    And api key should remain valid for other uses

# Phase 6 — Multi-AIM regression (two AIMs deployed simultaneously)

Inference is authorized per model when two AIMs share the workloads host
    [Documentation]    Regression test for the cluster-auth hostname-only route-selection
    ...    bug (Bug A): when two or more AIMs share the workloads.<domain> hostname,
    ...    cluster-auth previously resolved the HTTPRoute by hostname alone and applied
    ...    the wrong model's allowed-group. The result was that a key valid for model A
    ...    could be falsely denied on A (because auth looked up model B's group), while
    ...    cross-model enforcement was also broken.
    ...
    ...    This test exercises BOTH halves with two distinct AIMs in the same project:
    ...      1. Key-A → AIM-A external endpoint → 200 (catches the false-denial).
    ...      2. Key-A → AIM-B external endpoint → 401/403/404 (cross-model enforcement).
    ...
    ...    The test deliberately deploys a second AIM so that both AIMs are live on
    ...    the workloads.* hostname simultaneously — the bug only manifests when
    ...    cluster-auth has two HTTPRoute candidates for the same hostname.
    [Tags]    api-keys    inference    negative    positive    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And user is authenticated
    And an AIM model is running
    And a second AIM model is running
    And an api key authorized only for model A is created
    When a request is made to model A with key A
    Then model A should accept the request
    When a request is made to model B with key A
    Then model B should reject the request

# Rate limiting is not currently exposed through the API
