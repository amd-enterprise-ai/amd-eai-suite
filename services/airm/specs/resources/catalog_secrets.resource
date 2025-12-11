# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level secret testing keywords.
...                 Provides business-logic level keywords for testing secret operations.
...                 Uses the low-level API keywords from api/secrets.resource to implement
...                 higher-level testing scenarios for secrets management and project assignments.
Resource            airm_secrets.resource
Resource            airm_projects.resource
Library             Collections
Library             String
Library             OperatingSystem
Library             Process


*** Variables ***
${response}                 ${None}
${VALID_MANIFEST}           ${EMPTY}
${INVALID_MANIFEST}         ${EMPTY}
${TEST_POD_NAME}            ${None}


*** Keywords ***

A valid ExternalSecret manifest exists
    [Documentation]    Creates a valid ExternalSecret manifest for testing
    ...    Loads template file and replaces placeholder name with unique timestamp-based name

    ${timestamp}=    Evaluate    int(__import__('time').time())
    ${unique_name}=    Set Variable    e2e-test-secret-${timestamp}

    # Store the target secret name for later use
    Set Test Variable    ${TEST_SECRET_NAME}    ${unique_name}

    # Load template and replace placeholder names
    ${template}=    Get File    ${CURDIR}/../test_data/secrets/valid-externalsecret.yaml
    ${manifest}=    Replace String    ${template}    name: e2e-test-secret    name: ${unique_name}

    Set Test Variable    ${VALID_MANIFEST}    ${manifest}
    Log    Valid ExternalSecret manifest created with unique name: ${unique_name}    DEBUG

An invalid ExternalSecret manifest exists
    [Documentation]    Creates an invalid ExternalSecret manifest (missing spec)

    ${manifest}=    Get File    ${CURDIR}/../test_data/secrets/invalid-externalsecret.yaml

    Set Test Variable    ${INVALID_MANIFEST}    ${manifest}
    Log    Invalid ExternalSecret manifest loaded from file    DEBUG

A valid ExternalSecret manifest with invalid path exists
    [Documentation]    Creates a valid ExternalSecret manifest but with invalid external paths
    ...    This manifest has correct structure but references non-existent secrets in the external store

    ${manifest}=    Get File    ${CURDIR}/../test_data/secrets/valid-manifest-invalid-path.yaml

    Set Test Variable    ${VALID_MANIFEST}    ${manifest}
    Log    Valid ExternalSecret manifest with invalid path loaded from file    DEBUG

Secret is created without project assignment
    [Documentation]    Creates a secret without assigning it to any project
    ...    Uses default configuration: type=ExternalSecret, scope=Organization
    [Arguments]    ${secret_name}=${EMPTY}

    ${name}=    Run Keyword If    "${secret_name}" == "${EMPTY}"
    ...    Evaluate    "e2e-secret-" + str(int(__import__('time').time()))
    ...    ELSE    Set Variable    ${secret_name}

    Should Not Be Equal    ${VALID_MANIFEST}    ${EMPTY}
    ...    msg=Valid manifest not set. Call 'a valid ExternalSecret manifest exists' first.

    @{empty_project_ids}=    Create List

    ${secret_data}=    Create Dictionary
    ...    name=${name}
    ...    type=ExternalSecret
    ...    scope=Organization
    ...    manifest=${VALID_MANIFEST}
    ...    project_ids=${empty_project_ids}

    ${response}=    Create secret
    ...    secret_data=${secret_data}
    ...    expected_status=200

    ${secret_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_SECRET_ID}    ${secret_id}

    TRY
        Append To List    ${CREATED_SECRET_IDS}    ${secret_id}
        Log    Tracking secret ${secret_id} for cleanup    DEBUG
    EXCEPT
        Log    CREATED_SECRET_IDS not available, secret won't be auto-cleaned    WARN
    END

    Set Test Variable    ${response}    ${response}

    Log    Created secret: id=${secret_id}, name=${name}, status=Unassigned    INFO

Secret is created and assigned to project
    [Documentation]    Creates a secret and assigns it to the current project
    [Arguments]    ${secret_name}=${EMPTY}

    ${name}=    Run Keyword If    "${secret_name}" == "${EMPTY}"
    ...    Evaluate    "e2e-secret-" + str(int(__import__('time').time()))
    ...    ELSE    Set Variable    ${secret_name}

    Should Not Be Equal    ${VALID_MANIFEST}    ${EMPTY}
    ...    msg=Valid manifest not set. Call 'a valid ExternalSecret manifest exists' first.
    Should Not Be Equal    ${TEST_PROJECT_ID}    ${None}
    ...    msg=Current project not set. Create a project first.

    @{project_ids}=    Create List    ${TEST_PROJECT_ID}

    ${secret_data}=    Create Dictionary
    ...    name=${name}
    ...    type=ExternalSecret
    ...    scope=Organization
    ...    manifest=${VALID_MANIFEST}
    ...    project_ids=${project_ids}

    ${response}=    Create secret
    ...    secret_data=${secret_data}
    ...    expected_status=200

    ${secret_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_SECRET_ID}    ${secret_id}

    TRY
        Append To List    ${CREATED_SECRET_IDS}    ${secret_id}
        Log    Tracking secret ${secret_id} for cleanup    DEBUG
    EXCEPT
        Log    CREATED_SECRET_IDS not available, secret won't be auto-cleaned    WARN
    END

    Set Test Variable    ${response}    ${response}

    Log    Created secret: id=${secret_id}, name=${name}, assigned to project=${TEST_PROJECT_ID}    INFO

# Removed duplicate keyword - now using shared definition from catalog_common.resource

Secret "${secret_name}" is assigned to project
    [Documentation]    Finds a secret by name and assigns it to the current project
    ...    If the secret is already assigned to the project, logs and continues
    ...    This is useful for infrastructure secrets like minio-credentials
    Should Not Be Equal    ${TEST_PROJECT_ID}    ${None}
    ...    msg=TEST_PROJECT_ID not set. Create a project first.

    # Find the secret by name
    ${response}=    Get secrets    expected_status=200
    ${secrets}=    Set Variable    ${response.json()['secrets']}

    ${secret_id}=    Set Variable    ${None}
    FOR    ${secret}    IN    @{secrets}
        IF    '${secret['name']}' == '${secret_name}'
            ${secret_id}=    Set Variable    ${secret['id']}
            Log    Found secret ${secret_name} with ID ${secret_id}    DEBUG
            BREAK
        END
    END

    Should Not Be Equal    ${secret_id}    ${None}
    ...    msg=Secret ${secret_name} not found in system

    # Check if already assigned to avoid unnecessary API call
    ${secret_details}=    Get secret    ${secret_id}    expected_status=200
    ${secret_data}=    Set Variable    ${secret_details.json()}

    # Get project_secrets from secret - it's a list of objects with project_id field
    ${project_secrets}=    Get From Dictionary    ${secret_data}    project_secrets    default=@{EMPTY}

    # Extract project IDs from project_secrets objects
    @{current_project_ids}=    Create List
    FOR    ${proj_secret}    IN    @{project_secrets}
        ${proj_id}=    Get From Dictionary    ${proj_secret}    project_id
        Append To List    ${current_project_ids}    ${proj_id}

        # Check if already assigned
        IF    '${proj_id}' == '${TEST_PROJECT_ID}'
            Log    Secret ${secret_name} already assigned to project ${TEST_PROJECT_ID}    INFO
            RETURN
        END
    END

    # Collect all current project IDs and add the current one
    @{project_ids}=    Create List    @{current_project_ids}
    Append To List    ${project_ids}    ${TEST_PROJECT_ID}

    # Assign to project - accept both 200 (success) and 409 (already assigned)
    ${assign_response}=    Assign secret to projects
    ...    ${secret_id}
    ...    ${project_ids}
    ...    expected_status=anything

    # Verify status is either 200 or 409
    ${status_code}=    Set Variable    ${assign_response.status_code}
    Should Be True    ${status_code} == 200 or ${status_code} == 409
    ...    msg=Expected status code 200 or 409, but got ${status_code}

    Log    Assigned secret ${secret_name} to project ${TEST_PROJECT_ID} (status: ${status_code})    INFO

Secret is assigned to second project
    [Documentation]    Assigns the current secret to the second project
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set. Create secret first.
    Should Not Be Equal    ${SECOND_PROJECT_ID}    ${None}
    ...    msg=SECOND_PROJECT_ID not set. Create second project first.

    @{project_ids}=    Create List    ${TEST_PROJECT_ID}    ${SECOND_PROJECT_ID}

    ${response}=    Assign secret to projects
    ...    ${TEST_SECRET_ID}
    ...    ${project_ids}
    ...    expected_status=200

    Set Test Variable    ${response}    ${response}
    Log    Assigned secret ${TEST_SECRET_ID} to second project ${SECOND_PROJECT_ID}    INFO

Project assignment is removed
    [Documentation]    Removes all project assignments from the secret
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set. Create secret first.

    @{empty_list}=    Create List

    ${response}=    Assign secret to projects
    ...    ${TEST_SECRET_ID}
    ...    ${empty_list}
    ...    expected_status=200

    Set Test Variable    ${response}    ${response}
    Log    Removed all project assignments from secret ${TEST_SECRET_ID}    INFO

Attempting to create secret with same name
    [Documentation]    Attempts to create a secret with a duplicate name (should fail with 409)
    Should Not Be Equal    ${VALID_MANIFEST}    ${EMPTY}
    ...    msg=Valid manifest not set.

    ${secret_response}=    Get secret    ${TEST_SECRET_ID}
    ${secret_name}=    Get From Dictionary    ${secret_response.json()}    name

    @{empty_project_ids}=    Create List

    ${secret_data}=    Create Dictionary
    ...    name=${secret_name}
    ...    type=ExternalSecret
    ...    scope=Organization
    ...    manifest=${VALID_MANIFEST}
    ...    project_ids=${empty_project_ids}

    ${response}=    Create secret
    ...    secret_data=${secret_data}
    ...    expected_status=409

    Set Test Variable    ${response}    ${response}

Attempting to create secret with invalid manifest
    [Documentation]    Attempts to create a secret with an invalid manifest (should fail)
    Should Not Be Equal    ${INVALID_MANIFEST}    ${EMPTY}
    ...    msg=Invalid manifest not set.

    ${secret_data}=    Create Dictionary
    ...    name=invalid-secret
    ...    type=ExternalSecret
    ...    scope=Organization
    ...    manifest=${INVALID_MANIFEST}

    ${response}=    Create secret
    ...    secret_data=${secret_data}
    ...    expected_status=422

    Set Test Variable    ${response}    ${response}

Secret should be visible via API
    [Documentation]    Verifies that the secret is visible via GET /secrets/{id}
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set. Create secret first.

    ${response}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    Set Test Variable    ${response}    ${response}

    Log    Secret ${TEST_SECRET_ID} is visible via API    INFO

Secret should not be visible via API
    [Documentation]    Verifies that the secret returns 404 via GET /secrets/{id}
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set.

    ${response}=    Get secret    ${TEST_SECRET_ID}    expected_status=404

    Log    Secret ${TEST_SECRET_ID} correctly not found (404)    INFO

Secret should have valid ID and status
    [Documentation]    Verifies secret response contains valid id and status fields
    Should Not Be Equal    ${response}    ${None}
    ...    msg=Response not set. Call 'secret should be visible via API' first.

    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    id
    Dictionary Should Contain Key    ${json}    status

    ${secret_id}=    Get From Dictionary    ${json}    id
    ${status}=    Get From Dictionary    ${json}    status

    Log    Secret has valid ID: ${secret_id}, Status: ${status}    INFO

Secret status should be "${expected_status}"
    [Documentation]    Verifies the secret has the expected status by fetching fresh state
    ...    Always fetches current secret state using TEST_SECRET_ID
    ...    For checking immediate API response, use 'Secret status should be "${status}" in response'
    ${secret_response}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    ${json}=    Set Variable    ${secret_response.json()}
    ${status}=    Get From Dictionary    ${json}    status
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Expected secret status to be ${expected_status}, but got ${status}
    Log    Secret status: ${status}    INFO

Secret status should be "${expected_status}" in response
    [Documentation]    Verifies the secret status in the cached ${response} variable
    ...    Use this immediately after an API call to check the response without extra fetch
    ${json}=    Set Variable    ${response.json()}
    ${status}=    Get From Dictionary    ${json}    status
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Expected secret status to be ${expected_status} in response, but got ${status}
    Log    Secret status in response: ${status}    INFO

Secret status should be any of "${status_list}"
    [Documentation]    Verifies secret has one of the specified statuses
    ...    Takes a comma-separated list of acceptable statuses like "Pending, Synced"

    # Fetch the latest secret state instead of relying on cached response
    ${secret_response}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    ${json}=    Set Variable    ${secret_response.json()}
    ${actual_status}=    Get From Dictionary    ${json}    status

    # Convert comma-separated string to list
    @{acceptable_statuses}=    Split String    ${status_list}    ,${SPACE}

    # Check if actual status is in the list
    ${status_found}=    Set Variable    ${FALSE}
    FOR    ${status}    IN    @{acceptable_statuses}
        IF    "${actual_status}" == "${status}"
            ${status_found}=    Set Variable    ${TRUE}
            BREAK
        END
    END

    Should Be True    ${status_found}
    ...    msg=Secret status '${actual_status}' not in acceptable statuses [${status_list}]
    Log    Secret status ${actual_status} is acceptable (one of: ${status_list})    INFO

Secret status should be any of "${status_list}" in response
    [Documentation]    Verifies secret status in cached ${response} is one of the specified statuses
    ...    Use this immediately after an API call to check the response without extra fetch
    ${json}=    Set Variable    ${response.json()}
    ${actual_status}=    Get From Dictionary    ${json}    status

    # Convert comma-separated string to list
    @{acceptable_statuses}=    Split String    ${status_list}    ,${SPACE}

    # Check if actual status is in the list
    ${status_found}=    Set Variable    ${FALSE}
    FOR    ${status}    IN    @{acceptable_statuses}
        IF    "${actual_status}" == "${status}"
            ${status_found}=    Set Variable    ${TRUE}
            BREAK
        END
    END

    Should Be True    ${status_found}
    ...    msg=Secret status '${actual_status}' in response not in acceptable statuses [${status_list}]
    Log    Secret status ${actual_status} in response is acceptable (one of: ${status_list})    INFO

# Backward compatibility keywords (can be removed later)
Secret status should be unassigned
    [Documentation]    DEPRECATED: Use 'Secret status should be "Unassigned"' instead
    Secret status should be "Unassigned"

Secret status should be pending
    [Documentation]    DEPRECATED: Use 'Secret status should be "Pending"' instead
    Secret status should be "Pending"

Secret status should be synced
    [Documentation]    DEPRECATED: Use 'Secret status should be "Synced"' instead
    Secret status should be "Synced"

Secret status should be deleting
    [Documentation]    DEPRECATED: Use 'Secret status should be "Deleting"' instead
    Secret status should be "Deleting"

Secret should have "${count}" project assignment
    [Documentation]    Verifies the secret has the specified number of project assignments by fetching fresh state
    ...    Always fetches current secret state using TEST_SECRET_ID
    ...    For checking immediate API response, use 'Secret should have "${count}" project assignment in response'
    ${count_int}=    Convert To Integer    ${count}

    # Fetch the latest secret state
    ${secret_response}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    ${json}=    Set Variable    ${secret_response.json()}
    ${project_secrets}=    Get From Dictionary    ${json}    project_secrets
    ${actual_count}=    Get Length    ${project_secrets}

    Should Be Equal As Integers    ${actual_count}    ${count_int}
    ...    msg=Expected ${count_int} project assignments, found ${actual_count}

    Log    Secret has ${actual_count} project assignment(s)    INFO

Secret should have "${count}" project assignment in response
    [Documentation]    Verifies project assignment count in cached ${response} variable
    ...    Use this immediately after an API call to check the response without extra fetch
    ${count_int}=    Convert To Integer    ${count}

    ${json}=    Set Variable    ${response.json()}
    ${project_secrets}=    Get From Dictionary    ${json}    project_secrets
    ${actual_count}=    Get Length    ${project_secrets}

    Should Be Equal As Integers    ${actual_count}    ${count_int}
    ...    msg=Expected ${count_int} project assignments in response, found ${actual_count}

    Log    Secret has ${actual_count} project assignment(s) in response    INFO

Secret should have "${count}" project assignments
    [Documentation]    Plural variant - calls singular keyword
    Secret should have "${count}" project assignment

Secret should have "${count}" project assignments in response
    [Documentation]    Plural variant - calls singular keyword
    Secret should have "${count}" project assignment in response

Secret transitions to "${expected_status}"
    [Documentation]    Waits for secret to transition to expected status
    ...    Polls the secret endpoint until status becomes expected value
    ...    Timeout reduced to 2 min - sufficient for dispatcher processing and ExternalSecret sync
    Log    Waiting for secret ${TEST_SECRET_ID} to transition to ${expected_status}    INFO
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify secret has status "${expected_status}"
    Log    Secret ${TEST_SECRET_ID} successfully transitioned to ${expected_status}    INFO

Verify secret has status "${expected_status}"
    [Documentation]    Helper keyword to verify secret status (used with polling)
    ${secret_response}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    ${status}=    Get From Dictionary    ${secret_response.json()}    status
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Secret status is ${status}, expected ${expected_status}
    Set Test Variable    ${response}    ${secret_response}
    Log    Polling: secret ${TEST_SECRET_ID} has status ${status}    TRACE

# Backward compatibility keywords (can be removed later)
Secret transitions to synced
    [Documentation]    DEPRECATED: Use 'Secret transitions to "Synced"' instead
    Secret transitions to "Synced"

Verify secret is synced
    [Documentation]    DEPRECATED: Use 'Verify secret has status "Synced"' instead
    Verify secret has status "Synced"

All project assignments should be synced
    [Documentation]    Verifies that all project assignments have Synced status
    ${json}=    Set Variable    ${response.json()}
    ${project_secrets}=    Get From Dictionary    ${json}    project_secrets

    FOR    ${project_secret}    IN    @{project_secrets}
        ${status}=    Get From Dictionary    ${project_secret}    status
        Should Be Equal    ${status}    Synced
        ...    msg=Project secret status is ${status}, expected Synced
    END

    Log    All project assignments are synced    INFO

Secret is deleted
    [Documentation]    Deletes the secret via DELETE /secrets/{id}
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set. Create secret first.

    ${response}=    Delete secret    ${TEST_SECRET_ID}    expected_status=204

    Log    Deleted secret ${TEST_SECRET_ID} via API    INFO

Secret creation should fail with conflict
    [Documentation]    Verifies that secret creation failed with 409 Conflict
    ${status_code}=    Set Variable    ${response.status_code}
    Should Be Equal As Integers    ${status_code}    409
    ...    msg=Expected 409 Conflict, but got ${status_code}

    Log    Secret creation correctly failed with 409 Conflict    INFO

Secret creation should fail with validation error
    [Documentation]    Verifies that secret creation failed with 422 Validation Error
    ${status_code}=    Set Variable    ${response.status_code}
    Should Be Equal As Integers    ${status_code}    422
    ...    msg=Expected 422 Validation Error, but got ${status_code}

    Log    Secret creation correctly failed with 422 Validation Error    INFO

Secret should be deleted or deleting
    [Documentation]    Verifies that secret is either already deleted (404) or in Deleting status
    ...    This handles the case where deletion happens very quickly
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set. Create secret first.

    # Try to get the secret - expect either 404 (deleted) or 200 (deleting)
    ${secret_response}=    Get secret    ${TEST_SECRET_ID}    expected_status=any

    IF    ${secret_response.status_code} == 404
        Log    Secret already deleted (not found) - deletion was immediate    INFO
    ELSE IF    ${secret_response.status_code} == 200
        ${json}=    Set Variable    ${secret_response.json()}
        ${status}=    Get From Dictionary    ${json}    status
        Should Be Equal    ${status}    Deleting
        ...    msg=Expected secret status to be Deleting, but got ${status}
        Log    Secret status: ${status} (will be fully deleted soon)    INFO
    ELSE
        Fail    Unexpected response status: ${secret_response.status_code}
    END

Listing all secrets
    [Documentation]    Lists all secrets for the organization
    ${response}=    Get secrets    expected_status=200
    Set Test Variable    ${response}    ${response}
    Log    Listed all secrets for organization    INFO

At least "${count}" secret should be visible
    [Documentation]    Verifies at least the specified number of secrets are visible
    ${count_int}=    Convert To Integer    ${count}

    ${json}=    Set Variable    ${response.json()}
    ${secrets_list}=    Get From Dictionary    ${json}    secrets
    ${actual_count}=    Get Length    ${secrets_list}

    Should Be True    ${actual_count} >= ${count_int}
    ...    msg=Expected at least ${count_int} secrets, found ${actual_count}

    Log    Found ${actual_count} secrets (expected at least ${count_int})    INFO

Secret ExternalSecret should exist in cluster
    [Documentation]    Verifies that secret has created ExternalSecret in Kubernetes
    ...    Uses TEST_SECRET_ID to find the ExternalSecret
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set.

    ${secret}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    ${secret_name}=    Get From Dictionary    ${secret.json()}    name

    Log    Checking for ExternalSecret: name=${secret_name}, namespace=${TEST_PROJECT_SLUG}    DEBUG
    ${result}=    Run Process    kubectl    get    externalsecret
    ...    -n    ${TEST_PROJECT_SLUG}
    ...    ${secret_name}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get ExternalSecret for secret ${TEST_SECRET_ID}. Error: ${result.stderr}

    ${externalsecret_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    Dictionary Should Contain Key    ${externalsecret_json}    metadata
    Log    ExternalSecret manifest details: ${externalsecret_json}    DEBUG

    Log    ExternalSecret verified: secret_id=${TEST_SECRET_ID}, name=${secret_name}, namespace=${TEST_PROJECT_SLUG}    INFO

Secret ExternalSecret should not exist in cluster
    [Documentation]    Verifies that secret ExternalSecret has been deleted from Kubernetes
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set.

    Log    Waiting for ExternalSecret deletion for secret ${TEST_SECRET_ID}    INFO
    Wait Until Keyword Succeeds    2 min    2 sec
    ...    Verify secret ExternalSecret is deleted
    Log    ExternalSecret deletion confirmed for secret ${TEST_SECRET_ID}    INFO

Verify secret ExternalSecret is deleted
    [Documentation]    Helper keyword to verify ExternalSecret doesn't exist (used with polling)
    ${secret}=    Get secret    ${TEST_SECRET_ID}    expected_status=any
    ${secret_name}=    Get From Dictionary    ${secret.json()}    name

    ${result}=    Run Process    kubectl    get    externalsecret
    ...    -n    ${TEST_PROJECT_SLUG}
    ...    ${secret_name}
    ...    -o    json
    ...    stderr=PIPE

    Should Not Be Equal As Integers    ${result.rc}    0
    ...    msg=ExternalSecret still exists for secret ${TEST_SECRET_ID}

    Log    Polling: ExternalSecret deleted for secret ${TEST_SECRET_ID}    TRACE

A pod that uses the secret is deployed
    [Documentation]    Deploys a test pod that references the secret
    ...    The pod attempts to read the secret value via environment variable
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set.
    Should Not Be Equal    ${TEST_PROJECT_SLUG}    ${None}
    ...    msg=TEST_PROJECT_SLUG not set.
    Should Not Be Equal    ${TEST_SECRET_NAME}    ${None}
    ...    msg=TEST_SECRET_NAME not set. Call 'a valid ExternalSecret manifest exists' first.

    # Load static pod manifest and replace secret name
    ${pod_manifest}=    Get File    ${CURDIR}/../test_data/manifests/pod-with-secret.yaml
    ${updated_manifest}=    Replace String    ${pod_manifest}    name: e2e-test-secret    name: ${TEST_SECRET_NAME}
    ${updated_manifest}=    Replace String    ${updated_manifest}    key: username    key: ACCESS_KEY_ID

    Log    Updated pod manifest to reference secret: ${TEST_SECRET_NAME}    DEBUG

    ${temp_file}=    Set Variable    /tmp/e2e-pod-with-secret.yaml
    Create File    ${temp_file}    ${updated_manifest}

    Log    Deploying test pod to namespace ${TEST_PROJECT_SLUG}    DEBUG
    ${result}=    Run Process    kubectl    apply
    ...    -n    ${TEST_PROJECT_SLUG}
    ...    -f    ${temp_file}
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to deploy pod: ${result.stderr}

    Set Test Variable    ${TEST_POD_NAME}    e2e-pod-with-secret
    Log    Deployed test pod: name=${TEST_POD_NAME}, namespace=${TEST_PROJECT_SLUG}    INFO

Pod can access secret values
    [Documentation]    Verifies that the pod successfully accessed secret values
    ...    Checks pod logs or status to confirm secret was mounted/readable
    Should Not Be Equal    ${TEST_POD_NAME}    ${None}
    ...    msg=TEST_POD_NAME not set.
    Should Not Be Equal    ${TEST_PROJECT_SLUG}    ${None}
    ...    msg=TEST_PROJECT_SLUG not set.

    Log    Waiting for pod ${TEST_POD_NAME} to access secret    INFO
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify pod accessed secret
    Log    Pod ${TEST_POD_NAME} successfully accessed secret values    INFO

Verify pod accessed secret
    [Documentation]    Helper to verify pod successfully read secret
    ${cmd}=    Set Variable    kubectl get pod ${TEST_POD_NAME} -n ${TEST_PROJECT_SLUG} -o jsonpath={.status.phase}
    ${result}=    Run Process    bash    -c    ${cmd}    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get pod status: ${result.stderr}

    ${phase}=    Set Variable    ${result.stdout}
    Log    Polling: pod phase=${phase}    TRACE

    Should Match Regexp    ${phase}    ^(Running|Succeeded)$
    ...    msg=Pod is in phase ${phase}, expected Running or Succeeded

    ${log_result}=    Run Process    kubectl    logs
    ...    -n    ${TEST_PROJECT_SLUG}
    ...    ${TEST_POD_NAME}
    ...    stderr=PIPE

    Should Be Equal As Integers    ${log_result.rc}    0
    ...    msg=Failed to get pod logs: ${log_result.stderr}

    Should Contain    ${log_result.stdout}    SECRET_USERNAME
    ...    msg=Pod logs don't contain SECRET_USERNAME - secret was not mounted

    Log    Polling: pod accessed secret successfully    TRACE

Clean up test pod
    [Documentation]    Removes the test pod from the namespace
    IF    '${TEST_POD_NAME}' != '${None}'
        Log    Deleting test pod ${TEST_POD_NAME}    DEBUG
        ${result}=    Run Process    kubectl    delete    pod
        ...    -n    ${TEST_PROJECT_SLUG}
        ...    ${TEST_POD_NAME}
        ...    --ignore-not-found
        ...    stderr=PIPE
        IF    ${result.rc} == 0
            Log    Test pod ${TEST_POD_NAME} deleted successfully    INFO
        ELSE
            Log    Failed to delete test pod ${TEST_POD_NAME}: ${result.stderr}    WARN
        END
    END

Secret with invalid path is created and assigned to project
    [Documentation]    Creates a secret with invalid external path and assigns it to the current project
    ...    This secret will have a valid manifest structure but will fail to sync due to invalid paths
    [Arguments]    ${secret_name}=${EMPTY}

    ${name}=    Run Keyword If    "${secret_name}" == "${EMPTY}"
    ...    Evaluate    "e2e-secret-invalid-" + str(int(__import__('time').time()))
    ...    ELSE    Set Variable    ${secret_name}

    Should Not Be Equal    ${VALID_MANIFEST}    ${EMPTY}
    ...    msg=Valid manifest not set. Call 'a valid ExternalSecret manifest with invalid path exists' first.
    Should Not Be Equal    ${TEST_PROJECT_ID}    ${None}
    ...    msg=Current project not set. Create a project first.

    @{project_ids}=    Create List    ${TEST_PROJECT_ID}

    ${secret_data}=    Create Dictionary
    ...    name=${name}
    ...    type=ExternalSecret
    ...    scope=Organization
    ...    manifest=${VALID_MANIFEST}
    ...    project_ids=${project_ids}

    ${response}=    Create secret
    ...    secret_data=${secret_data}
    ...    expected_status=200

    ${secret_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${TEST_SECRET_ID}    ${secret_id}

    TRY
        Append To List    ${CREATED_SECRET_IDS}    ${secret_id}
        Log    Tracking secret ${secret_id} for cleanup    DEBUG
    EXCEPT
        Log    CREATED_SECRET_IDS not available, secret won't be auto-cleaned    WARN
    END

    Set Test Variable    ${response}    ${response}

    Log    Created secret with invalid path: id=${secret_id}, name=${name}, assigned to project=${TEST_PROJECT_ID}    INFO

Secret initial status should be pending
    [Documentation]    Verifies the secret initially has Pending or SyncedError status after creation
    ...    For invalid secrets, it may immediately go to SyncedError without Pending state
    ${json}=    Set Variable    ${response.json()}
    ${status}=    Get From Dictionary    ${json}    status
    # Allow both Pending and SyncedError for initial status (can fail immediately)
    ${valid_status}=    Evaluate    "${status}" in ["Pending", "SyncedError"]
    Should Be True    ${valid_status}
    ...    msg=Expected initial secret status to be Pending or SyncedError, but got ${status}
    Log    Initial secret status: ${status}    INFO

Secret with invalid path transitions to error state
    [Documentation]    Waits for secret with invalid path to transition to SyncedError status
    ...    Polls the secret endpoint until status becomes SyncedError
    ...    Timeout reduced to 2 min - sufficient for dispatcher processing and sync attempts
    Log    Waiting for secret ${TEST_SECRET_ID} to transition to SyncedError    INFO
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify secret is in error state
    Log    Secret ${TEST_SECRET_ID} successfully transitioned to SyncedError    INFO

Verify secret is in error state
    [Documentation]    Helper keyword to verify secret has SyncedError status (used with polling)
    ${secret_response}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    ${status}=    Get From Dictionary    ${secret_response.json()}    status
    Should Be Equal    ${status}    SyncedError
    ...    msg=Secret status is ${status}, expected SyncedError
    Set Test Variable    ${response}    ${secret_response}
    Log    Polling: secret ${TEST_SECRET_ID} has status ${status}    TRACE

Secret status should be synced error
    [Documentation]    Verifies the secret has SyncedError status
    ${json}=    Set Variable    ${response.json()}
    ${status}=    Get From Dictionary    ${json}    status
    Should Be Equal    ${status}    SyncedError
    ...    msg=Expected secret status to be SyncedError, but got ${status}

    # Optionally check for error message if available
    ${error_message}=    Get From Dictionary    ${json}    error_message    ${None}
    Run Keyword If    '${error_message}' != '${None}'
    ...    Log    Secret error message: ${error_message}    WARN

    Log    Secret status confirmed: ${status}    INFO

Get secret name
    [Documentation]    Retrieves the name of the current test secret
    Should Not Be Equal    ${TEST_SECRET_ID}    ${None}
    ...    msg=TEST_SECRET_ID not set. Create secret first.

    ${response}=    Get secret    ${TEST_SECRET_ID}    expected_status=200
    ${secret_json}=    Set Variable    ${response.json()}
    ${secret_name}=    Get From Dictionary    ${secret_json}    name
    RETURN    ${secret_name}

Wait for secret deletion to complete
    [Documentation]    Polls until secret is fully deleted from the system
    ...    For unassigned secrets, deletion is immediate
    ...    For assigned secrets, waits for DELETED status then removal
    Log    Waiting for secret ${TEST_SECRET_ID} deletion to complete    INFO
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify secret is fully deleted
    Log    Secret ${TEST_SECRET_ID} deletion completed successfully    INFO

Verify secret is fully deleted
    [Documentation]    Helper to verify secret no longer exists (404)
    ${response}=    Get secret    ${TEST_SECRET_ID}    expected_status=404
    Log    Polling: secret ${TEST_SECRET_ID} not found (deleted)    TRACE

Secret with same name "${name}" can be created
    [Documentation]    Creates a new secret with the specified name after deletion
    ...    Validates that name constraint allows recreation
    Should Not Be Equal    ${VALID_MANIFEST}    ${EMPTY}
    ...    msg=Valid manifest not set. Call 'a valid ExternalSecret manifest exists' first.

    @{empty_project_ids}=    Create List

    ${secret_data}=    Create Dictionary
    ...    name=${name}
    ...    type=ExternalSecret
    ...    scope=Organization
    ...    manifest=${VALID_MANIFEST}
    ...    project_ids=${empty_project_ids}

    ${response}=    Create secret
    ...    secret_data=${secret_data}
    ...    expected_status=200

    ${new_secret_id}=    Get From Dictionary    ${response.json()}    id
    Set Test Variable    ${NEW_SECRET_ID}    ${new_secret_id}

    TRY
        Append To List    ${CREATED_SECRET_IDS}    ${new_secret_id}
        Log    Tracking recreated secret ${new_secret_id} for cleanup    DEBUG
    EXCEPT
        Log    CREATED_SECRET_IDS not available, secret won't be auto-cleaned    WARN
    END

    Log    Created secret with reused name: id=${new_secret_id}, name=${name}    INFO

New secret should have different ID than "${old_id}"
    [Documentation]    Verifies the recreated secret has a different ID
    Should Not Be Equal    ${NEW_SECRET_ID}    ${old_id}
    ...    msg=Recreated secret has same ID as deleted secret
    Log    New secret ID ${NEW_SECRET_ID} differs from old ID ${old_id}    INFO
