# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level AIWB secret testing keywords.
...                 Provides business-logic level keywords for testing AIWB secret operations.
...                 Uses the low-level API keywords from api/secrets.resource to implement
...                 higher-level testing scenarios for secret CRUD and cross-service autodiscovery.
Resource            api/secrets.resource
Resource            resources/airm_projects.resource
Resource            resources/airm_secrets.resource
Resource            aiwb_common.resource
Library             Collections
Library             Process
Library             TestPrefix


*** Variables ***
${TEST_AIWB_SECRET_NAME}        ${None}
@{CREATED_AIWB_SECRET_NAMES}    # Track created secret names for cleanup


*** Keywords ***
Initialize AIWB Secret Tracking
    [Documentation]    Resets the AIWB secret tracking list for cleanup.
    @{empty_list}=    Create List
    Set Suite Variable    @{CREATED_AIWB_SECRET_NAMES}    @{empty_list}

Clean Up All Created AIWB Secrets
    [Documentation]    Deletes all AIWB secrets created during the test.
    ...    Tolerant of missing variables or already-deleted secrets.
    ${namespace}=    Get Variable Value    ${TEST_PROJECT}    ${None}
    IF    $namespace is None
        Log    No project set, skipping AIWB secret cleanup    DEBUG
        RETURN
    END
    ${ns}=    Get From Dictionary    ${namespace}    name

    ${count}=    Get Length    ${CREATED_AIWB_SECRET_NAMES}
    IF    ${count} == 0
        Log    No AIWB secrets to clean up    DEBUG
        RETURN
    END
    Log    Cleaning up ${count} AIWB secret(s)    INFO

    FOR    ${secret_name}    IN    @{CREATED_AIWB_SECRET_NAMES}
        TRY
            Delete AIWB Secret    ${ns}    ${secret_name}    expected_status=any
            Log    Deleted AIWB secret ${secret_name}    DEBUG
        EXCEPT    AS    ${error}
            Log    Failed to delete AIWB secret ${secret_name}: ${error}    WARN
        END
    END

    @{empty_list}=    Create List
    Set Suite Variable    @{CREATED_AIWB_SECRET_NAMES}    @{empty_list}
    Log    AIWB secret cleanup complete    INFO

A secret "${name}" with use case "${use_case}" is created via AIWB
    [Documentation]    Creates a secret via the AIWB API with the given name and use case.
    ...    Uses TestPrefix to generate a unique full name for concurrency safety.
    ...    ImagePullSecret use case requires .dockerconfigjson key with valid Docker config JSON.
    ...    Requires: TEST_PROJECT (set by project setup keywords).
    ...    Sets: TEST_AIWB_SECRET_NAME
    ${full_name}=    Test Name    ${name}
    ${namespace}=    Get Project Namespace

    IF    "${use_case}" == "ImagePullSecret"
        ${docker_config}=    Set Variable    {"auths":{"registry.example.com":{"username":"user","password":"pass","auth":"dXNlcjpwYXNz"}}}
        ${encoded_value}=    Evaluate    base64.b64encode(b'${docker_config}').decode()    modules=base64
        &{secret_data}=    Create Dictionary    .dockerconfigjson=${encoded_value}
    ELSE
        ${encoded_value}=    Evaluate    base64.b64encode(b"test-value").decode()    modules=base64
        &{secret_data}=    Create Dictionary    token=${encoded_value}
    END
    &{body}=    Create Dictionary
    ...    name=${full_name}
    ...    data=${secret_data}
    ...    use_case=${use_case}

    ${response}=    Create AIWB Secret    ${namespace}    ${body}    expected_status=201

    Set Test Variable    ${TEST_AIWB_SECRET_NAME}    ${full_name}
    Append To List    ${CREATED_AIWB_SECRET_NAMES}    ${full_name}
    Log    Created AIWB secret: name=${full_name}, use_case=${use_case}    INFO

A secret "${name}" is created via AIWB
    [Documentation]    Creates a secret via AIWB API with Generic use case.
    ...    Convenience wrapper that defaults to Generic use case.
    A secret "${name}" with use case "Generic" is created via AIWB

AIWB secret "${name}" should exist
    [Documentation]    Verifies that a secret with the given name exists via AIWB GET endpoint.
    ${full_name}=    Test Name    ${name}
    ${namespace}=    Get Project Namespace

    ${response}=    Get AIWB Secret    ${namespace}    ${full_name}    expected_status=200
    Log    AIWB secret ${full_name} exists    INFO

AIWB secret "${name}" should not exist
    [Documentation]    Verifies that a secret with the given name does not exist (404).
    ${full_name}=    Test Name    ${name}
    ${namespace}=    Get Project Namespace

    ${response}=    Get AIWB Secret    ${namespace}    ${full_name}    expected_status=404
    Log    AIWB secret ${full_name} confirmed not found    INFO

AIWB secrets are listed
    [Documentation]    Lists all AIWB secrets for the current project namespace.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace

    ${response}=    List AIWB Secrets    ${namespace}    expected_status=200
    Set Test Variable    ${TEST_RESPONSE}    ${response}
    Log    Listed AIWB secrets for namespace ${namespace}    INFO

AIWB secret list should contain "${count}" secrets
    [Documentation]    Verifies the secret list response contains the expected number of secrets.
    ...    Requires: TEST_RESPONSE (set by "AIWB secrets are listed")
    ${secrets_list}=    Set Variable    ${TEST_RESPONSE.json()['data']}
    ${actual_count}=    Get Length    ${secrets_list}
    Should Be Equal As Integers    ${actual_count}    ${count}
    ...    msg=Expected ${count} secrets, found ${actual_count}
    Log    Secret list count verified: ${actual_count}    INFO

AIWB secrets filtered by use case "${use_case}" should return "${count}" results
    [Documentation]    Lists AIWB secrets filtered by use_case and verifies the count.
    ${namespace}=    Get Project Namespace

    ${response}=    List AIWB Secrets    ${namespace}    use_case=${use_case}    expected_status=200
    ${secrets_list}=    Set Variable    ${response.json()['data']}
    ${actual_count}=    Get Length    ${secrets_list}
    Should Be Equal As Integers    ${actual_count}    ${count}
    ...    msg=Expected ${count} secrets for use_case ${use_case}, found ${actual_count}
    Log    Filtered secret count for use_case=${use_case}: ${actual_count}    INFO

AIWB secret "${name}" is deleted
    [Documentation]    Deletes an AIWB secret by name.
    ${full_name}=    Test Name    ${name}
    ${namespace}=    Get Project Namespace

    ${response}=    Delete AIWB Secret    ${namespace}    ${full_name}    expected_status=204
    Log    Deleted AIWB secret ${full_name}    INFO

Creating duplicate AIWB secret "${name}" should fail
    [Documentation]    Verifies that creating a secret with the same name fails with 409.
    ${full_name}=    Test Name    ${name}
    ${namespace}=    Get Project Namespace

    ${encoded_value}=    Evaluate    base64.b64encode(b"test-value").decode()    modules=base64
    &{secret_data}=    Create Dictionary    token=${encoded_value}
    &{body}=    Create Dictionary
    ...    name=${full_name}
    ...    data=${secret_data}
    ...    use_case=Generic

    ${response}=    Create AIWB Secret    ${namespace}    ${body}    expected_status=409
    Log    Duplicate AIWB secret creation correctly rejected with 409    INFO

# Cross-service autodiscovery keywords

AIWB secret should be discovered by AIRM
    [Documentation]    Verifies the AIWB-created secret appears in the AIRM API via autodiscovery.
    ...    Polls because the autodiscovery pipeline is asynchronous.
    ...    Requires: TEST_AIWB_SECRET_NAME
    Should Not Be Equal    ${TEST_AIWB_SECRET_NAME}    ${None}
    ...    msg=TEST_AIWB_SECRET_NAME not set. Create an AIWB secret first.

    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Find AIWB secret in AIRM API    ${TEST_AIWB_SECRET_NAME}
    Log    AIWB secret discovered by AIRM autodiscovery    INFO

Find AIWB secret in AIRM API
    [Documentation]    Searches the AIRM secrets list for a secret matching the given name.
    ...    Fails if not found (used with polling).
    [Arguments]    ${secret_name}

    Log    Polling for AIWB secret ${secret_name} in AIRM API    TRACE

    ${response}=    Get secrets    expected_status=200
    ${secrets_list}=    Set Variable    ${response.json()['data']}

    FOR    ${secret}    IN    @{secrets_list}
        ${name}=    Get From Dictionary    ${secret}    name
        IF    '${name}' == '${secret_name}'
            ${secret_id}=    Get From Dictionary    ${secret}    id
            Set Test Variable    ${TEST_SECRET_ID}    ${secret_id}
            Append To List    ${CREATED_SECRET_IDS}    ${secret_id}
            Log    Found AIWB secret ${secret_name} in AIRM API with ID: ${secret_id}    INFO
            RETURN
        END
    END

    FAIL    Secret ${secret_name} not found in AIRM API yet

AIWB secret should be removed from AIRM
    [Documentation]    Verifies the AIWB-created secret is removed from the AIRM API after deletion.
    ...    Polls because the deletion pipeline is asynchronous.
    ...    Requires: TEST_AIWB_SECRET_NAME
    Should Not Be Equal    ${TEST_AIWB_SECRET_NAME}    ${None}
    ...    msg=TEST_AIWB_SECRET_NAME not set. Create an AIWB secret first.

    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify AIWB secret removed from AIRM API    ${TEST_AIWB_SECRET_NAME}
    Log    AIWB secret removed from AIRM after deletion    INFO

Verify AIWB secret removed from AIRM API
    [Documentation]    Checks that a secret with the given name no longer appears in the AIRM API.
    ...    Fails if found (used with polling).
    [Arguments]    ${secret_name}

    Log    Polling for removal of secret ${secret_name} from AIRM API    TRACE

    ${response}=    Get secrets    expected_status=200
    ${secrets_list}=    Set Variable    ${response.json()['data']}

    FOR    ${secret}    IN    @{secrets_list}
        ${name}=    Get From Dictionary    ${secret}    name
        IF    '${name}' == '${secret_name}'
            FAIL    Secret ${secret_name} still found in AIRM API (deletion not yet processed)
        END
    END

    Log    Secret ${secret_name} confirmed removed from AIRM API    INFO

AIRM agent pod is restarted
    [Documentation]    Restarts the AIRM agent pod by performing a rollout restart.
    ...    This triggers re-reconciliation of all auto-discovered secrets.
    ${result}=    Run Process    kubectl    rollout    restart
    ...    deployment/airm-agent    -n    airm
    ...    stderr=PIPE
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to restart AIRM agent pod: ${result.stderr}
    Log    AIRM agent pod restart initiated    INFO

AIRM agent pod should be ready
    [Documentation]    Waits for the AIRM agent pod to be ready after restart.
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify AIRM agent pod ready

Verify AIRM agent pod ready
    [Documentation]    Helper: checks that the AIRM agent deployment has ready replicas.
    ${result}=    Run Process    kubectl    rollout    status
    ...    deployment/airm-agent    -n    airm    --timeout\=10s
    ...    stderr=PIPE
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=AIRM agent pod not ready: ${result.stderr}
    Log    AIRM agent pod is ready    INFO

AIWB auto-discovered secret should not be duplicated
    [Documentation]    Verifies no duplicate entries exist for the AIWB-created secret in AIRM.
    ...    Requires: TEST_AIWB_SECRET_NAME
    Should Not Be Equal    ${TEST_AIWB_SECRET_NAME}    ${None}
    ...    msg=TEST_AIWB_SECRET_NAME not set. Create an AIWB secret first.

    ${response}=    Get secrets    expected_status=200
    ${secrets_list}=    Set Variable    ${response.json()['data']}

    ${match_count}=    Set Variable    ${0}
    FOR    ${secret}    IN    @{secrets_list}
        ${name}=    Get From Dictionary    ${secret}    name
        IF    '${name}' == '${TEST_AIWB_SECRET_NAME}'
            ${match_count}=    Evaluate    ${match_count} + 1
        END
    END

    Should Be Equal As Integers    ${match_count}    1
    ...    msg=Expected exactly 1 secret named ${TEST_AIWB_SECRET_NAME}, found ${match_count}

    Log    No duplicate entries: secret ${TEST_AIWB_SECRET_NAME} appears exactly once in AIRM    INFO
