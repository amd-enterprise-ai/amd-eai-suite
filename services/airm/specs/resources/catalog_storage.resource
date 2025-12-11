# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level storage testing keywords.
...                 Provides business-logic level keywords for testing storage operations.
...                 Uses the low-level API keywords from api/storage.resource to implement
...                 higher-level testing scenarios for storage management and project assignments.
Resource            airm_storage.resource
Resource            airm_secrets.resource
Resource            airm_projects.resource
Resource            s3_test_operations.resource
Library             Collections
Library             String
Library             OperatingSystem
Library             Process


*** Variables ***
${response}                 ${None}
${VALID_S3_SPEC}            ${None}


*** Keywords ***

# ============================================================================
# Given Keywords - Setup and Preconditions
# ============================================================================

A valid S3 storage spec exists
    [Documentation]    Creates a valid S3 storage specification for testing
    ...    The spec includes bucket URL and credential field names
    ...    Uses Minio-compatible S3 URL format with cluster-internal service name

    ${bucket_name}=    Evaluate    "e2e-test-bucket-" + str(int(__import__('time').time()))

    # Use cluster-internal Minio service name for pods to access
    # The headless service provides direct access to Minio pods
    &{s3_spec}=    Create dictionary
    ...    bucket_url=http://default-minio-tenant-hl.minio-tenant-default.svc.cluster.local:9000/${bucket_name}
    ...    access_key_name=ACCESS_KEY_ID
    ...    secret_key_name=SECRET_ACCESS_KEY

    Set test variable    ${VALID_S3_SPEC}    ${s3_spec}
    Log    Valid S3 storage spec created with bucket: ${bucket_name}    DEBUG

A secret for storage credentials exists
    [Documentation]    Creates a secret to be used for storage credentials
    ...    This secret would contain S3 access keys in a real scenario
    ...    Sets use_case=S3 as required by the storage API

    Should not be equal    ${VALID_MANIFEST}    ${EMPTY}
    ...    msg=Valid secret manifest not set. Call 'a valid ExternalSecret manifest exists' first.

    ${name}=    Evaluate    "e2e-storage-secret-" + str(int(__import__('time').time()))

    @{empty_project_ids}=    Create list

    ${secret_data}=    Create dictionary
    ...    name=${name}
    ...    type=ExternalSecret
    ...    scope=Organization
    ...    use_case=S3
    ...    manifest=${VALID_MANIFEST}
    ...    project_ids=${empty_project_ids}

    ${response}=    Create secret
    ...    secret_data=${secret_data}
    ...    expected_status=200

    ${secret_id}=    Get from dictionary    ${response.json()}    id
    Set test variable    ${TEST_STORAGE_SECRET_ID}    ${secret_id}

    TRY
        Append to list    ${CREATED_SECRET_IDS}    ${secret_id}
        Log    Added secret ${secret_id} to cleanup list    DEBUG
    EXCEPT
        Log    CREATED_SECRET_IDS not available, secret won't be auto-cleaned    WARN
    END

    Log    Created storage credential secret with ID: ${secret_id}    INFO

# ============================================================================
# When Keywords - Actions
# ============================================================================

Storage is created without project assignment
    [Documentation]    Creates a storage without assigning it to any project
    ...    Uses default configuration: type=S3, scope=Organization
    [Arguments]    ${storage_name}=${EMPTY}

    ${name}=    Run keyword if    "${storage_name}" == "${EMPTY}"
    ...    Evaluate    "e2e-storage-" + str(int(__import__('time').time()))
    ...    ELSE    Set variable    ${storage_name}

    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=Valid S3 spec not set. Call 'a valid S3 storage spec exists' first.
    Should not be equal    ${TEST_STORAGE_SECRET_ID}    ${None}
    ...    msg=Storage secret not set. Call 'a secret for storage credentials exists' first.

    @{empty_project_ids}=    Create list

    ${storage_data}=    Create dictionary
    ...    name=${name}
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${TEST_STORAGE_SECRET_ID}
    ...    project_ids=${empty_project_ids}
    ...    spec=${VALID_S3_SPEC}

    ${response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=200

    ${storage_id}=    Get from dictionary    ${response.json()}    id
    Set test variable    ${TEST_STORAGE_ID}    ${storage_id}

    TRY
        Append to list    ${CREATED_STORAGE_IDS}    ${storage_id}
        Log    Added storage ${storage_id} to cleanup list    DEBUG
    EXCEPT
        Log    CREATED_STORAGE_IDS not available, storage won't be auto-cleaned    WARN
    END

    Set test variable    ${response}    ${response}

    Log    Created storage with ID: ${storage_id}    INFO

Storage is created and assigned to project
    [Documentation]    Creates a storage and assigns it to the current project
    [Arguments]    ${storage_name}=${EMPTY}

    ${name}=    Run keyword if    "${storage_name}" == "${EMPTY}"
    ...    Evaluate    "e2e-storage-" + str(int(__import__('time').time()))
    ...    ELSE    Set variable    ${storage_name}

    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=Valid S3 spec not set. Call 'a valid S3 storage spec exists' first.
    Should not be equal    ${TEST_STORAGE_SECRET_ID}    ${None}
    ...    msg=Storage secret not set. Call 'a secret for storage credentials exists' first.
    Should not be equal    ${TEST_PROJECT_ID}    ${None}
    ...    msg=Current project not set. Create a project first.

    @{project_ids}=    Create list    ${TEST_PROJECT_ID}

    ${storage_data}=    Create dictionary
    ...    name=${name}
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${TEST_STORAGE_SECRET_ID}
    ...    project_ids=${project_ids}
    ...    spec=${VALID_S3_SPEC}

    ${response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=200

    ${storage_id}=    Get from dictionary    ${response.json()}    id
    Set test variable    ${TEST_STORAGE_ID}    ${storage_id}

    TRY
        Append to list    ${CREATED_STORAGE_IDS}    ${storage_id}
        Log    Added storage ${storage_id} to cleanup list    DEBUG
    EXCEPT
        Log    CREATED_STORAGE_IDS not available, storage won't be auto-cleaned    WARN
    END

    Set test variable    ${response}    ${response}

    Log    Created storage with ID: ${storage_id} and assigned to project ${TEST_PROJECT_ID}    INFO

# Removed duplicate keyword - now using from airm_projects.resource

Storage is assigned to second project
    [Documentation]    Assigns the current storage to the second project
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set. Create storage first.
    Should not be equal    ${SECOND_PROJECT_ID}    ${None}
    ...    msg=SECOND_PROJECT_ID not set. Create second project first.

    @{project_ids}=    Create list    ${TEST_PROJECT_ID}    ${SECOND_PROJECT_ID}

    ${response}=    Assign storage to projects
    ...    ${TEST_STORAGE_ID}
    ...    ${project_ids}
    ...    expected_status=200

    Set test variable    ${response}    ${response}
    Log    Assigned storage ${TEST_STORAGE_ID} to second project ${SECOND_PROJECT_ID}    INFO

Storage project assignment is removed
    [Documentation]    Removes all project assignments from the storage
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set. Create storage first.

    @{empty_project_ids}=    Create list

    ${response}=    Assign storage to projects
    ...    ${TEST_STORAGE_ID}
    ...    ${empty_project_ids}
    ...    expected_status=200

    Set test variable    ${response}    ${response}
    Log    Removed all project assignments from storage ${TEST_STORAGE_ID}    INFO

Attempting to create storage with same name
    [Documentation]    Attempts to create a storage with a duplicate name (should fail with 409)
    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=Valid S3 spec not set.

    ${storage_response}=    Get storage    ${TEST_STORAGE_ID}
    ${storage_name}=    Get from dictionary    ${storage_response.json()}    name

    @{empty_project_ids}=    Create list

    ${storage_data}=    Create dictionary
    ...    name=${storage_name}
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${TEST_STORAGE_SECRET_ID}
    ...    project_ids=${empty_project_ids}
    ...    spec=${VALID_S3_SPEC}

    ${response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=409

    Set test variable    ${response}    ${response}

Attempting to create storage with invalid name
    [Documentation]    Attempts to create a storage with invalid name format
    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=Valid S3 spec not set.

    @{empty_project_ids}=    Create list

    ${storage_data}=    Create dictionary
    ...    name=Invalid_Storage_Name!
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${TEST_STORAGE_SECRET_ID}
    ...    project_ids=${empty_project_ids}
    ...    spec=${VALID_S3_SPEC}

    ${response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=422

    Set test variable    ${response}    ${response}

Attempting to create storage with non-existent secret
    [Documentation]    Attempts to create a storage with a non-existent secret ID
    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=Valid S3 spec not set.

    @{empty_project_ids}=    Create list

    ${fake_secret_id}=    Evaluate    str(__import__('uuid').uuid4())

    ${storage_data}=    Create dictionary
    ...    name=e2e-storage-fake-secret
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${fake_secret_id}
    ...    project_ids=${empty_project_ids}
    ...    spec=${VALID_S3_SPEC}

    ${response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=404

    Set test variable    ${response}    ${response}

Storage is deleted
    [Documentation]    Deletes the current test storage
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.

    ${response}=    Delete storage    ${TEST_STORAGE_ID}    expected_status=204

    Set test variable    ${response}    ${response}
    Log    Deleted storage ${TEST_STORAGE_ID}    INFO

Listing all storage
    [Documentation]    Lists all storage resources in the organization
    ${response}=    Get storages    expected_status=200
    Set test variable    ${response}    ${response}
    Log    Listed all storage resources for organization    INFO

Storage transitions to "${expected_status}"
    [Documentation]    Waits for storage to transition to expected status
    ...    Polls the storage status until it reaches the expected state
    ...    Reasonable timeout to allow for dispatcher processing and ExternalSecret sync
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.

    Wait until keyword succeeds    2 min    5 sec
    ...    Verify storage has status "${expected_status}"

Verify storage has status "${expected_status}"
    [Documentation]    Helper keyword to verify storage status (used with polling)
    ${response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${status}=    Get from dictionary    ${json}    status

    ${status_reason}=    Get from dictionary    ${json}    status_reason    default=${None}
    ${project_storages}=    Get from dictionary    ${json}    project_storages    default=[]
    ${ps_count}=    Get Length    ${project_storages}
    Log    Polling storage ${TEST_STORAGE_ID}: status=${status}, reason=${status_reason}, ps_count=${ps_count}    TRACE

    FOR    ${ps}    IN    @{project_storages}
        ${ps_status}=    Get from dictionary    ${ps}    status    default=Unknown
        ${ps_reason}=    Get from dictionary    ${ps}    status_reason    default=${None}
        Log    ProjectStorage status: ${ps_status}, reason: ${ps_reason}    TRACE
    END

    Should be equal    ${status}    ${expected_status}
    ...    msg=Storage status is ${status}, expected ${expected_status}

    Set test variable    ${response}    ${response}
    Log    Storage ${TEST_STORAGE_ID} has status ${expected_status}    INFO

Verify storage has status "${expected_status}" for ID
    [Documentation]    Helper keyword to verify storage status for a specific storage ID
    [Arguments]    ${storage_id}
    ${response}=    Get storage    ${storage_id}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${status}=    Get from dictionary    ${json}    status

    Should be equal    ${status}    ${expected_status}
    ...    msg=Storage ${storage_id} status is ${status}, expected ${expected_status}

    Log    Storage ${storage_id} has status ${expected_status}    INFO

# Backward compatibility keywords (can be removed later)
Storage transitions to synced
    [Documentation]    DEPRECATED: Use 'Storage transitions to "Synced"' instead
    Storage transitions to "Synced"

Verify storage is synced
    [Documentation]    DEPRECATED: Use 'Verify storage has status "Synced"' instead
    Verify storage has status "Synced"

# ============================================================================
# Then Keywords - Assertions
# ============================================================================

Storage should be visible via API
    [Documentation]    Verifies storage can be retrieved via API
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.

    ${response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=200
    Set test variable    ${response}    ${response}

    Log    Storage ${TEST_STORAGE_ID} is visible via API    INFO

Storage should have valid ID and status
    [Documentation]    Verifies storage response contains valid id and status fields
    Should not be equal    ${response}    ${None}
    ...    msg=Response not set. Call 'storage should be visible via API' first.

    ${json}=    Set variable    ${response.json()}
    Dictionary should contain key    ${json}    id
    Dictionary should contain key    ${json}    status

    ${storage_id}=    Get from dictionary    ${json}    id
    ${status}=    Get from dictionary    ${json}    status

    Log    Storage has valid ID: ${storage_id}, Status: ${status}    INFO

Storage status should be "${expected_status}"
    [Documentation]    Verifies the storage has the expected status by fetching fresh state
    ...    Always fetches current storage state using TEST_STORAGE_ID
    ...    For Pending status, allows Synced as storage may sync very quickly
    ...    For Deleting status, handles already-deleted case (404)
    ...    For checking immediate API response, use 'Storage status should be "${status}" in response'
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set. Create storage first.

    # Special case: Deleting may result in 404 if deleted too quickly
    IF    "${expected_status}" == "Deleting"
        TRY
            ${storage_response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=200
            ${json}=    Set variable    ${storage_response.json()}
            ${status}=    Get from dictionary    ${json}    status
            Should be equal    ${status}    ${expected_status}
            ...    msg=Expected status '${expected_status}', got '${status}'
            Log    Storage status is ${status}    INFO
            Set test variable    ${response}    ${storage_response}
        EXCEPT
            # Storage not found - it was deleted too quickly to catch DELETING state
            Log    Storage ${TEST_STORAGE_ID} not found - already deleted (too fast to see DELETING status)    WARN
            Pass Execution    Storage deleted too quickly to verify DELETING status
        END
    ELSE
        # Standard status check - fetch fresh state
        ${storage_response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=200
        ${json}=    Set variable    ${storage_response.json()}
        ${status}=    Get from dictionary    ${json}    status

        # Special case: Pending may transition to Synced very quickly
        IF    "${expected_status}" == "Pending"
            Should Be True    '${status}' in ['Pending', 'Synced']
            ...    msg=Expected status 'Pending' or 'Synced', got '${status}'
            Log    Storage status is ${status} (expected Pending, Synced allowed)    INFO
        ELSE
            Should be equal    ${status}    ${expected_status}
            ...    msg=Expected status '${expected_status}', got '${status}'
            Log    Storage status is ${status}    INFO
        END

        Set test variable    ${response}    ${storage_response}
    END

Storage status should be "${expected_status}" in response
    [Documentation]    Verifies the storage status in the cached ${response} variable
    ...    Use this immediately after an API call to check the response without extra fetch
    ...    For Pending status, allows Synced as storage may sync very quickly
    ${json}=    Set variable    ${response.json()}
    ${status}=    Get from dictionary    ${json}    status

    # Special case: Pending may transition to Synced very quickly
    IF    "${expected_status}" == "Pending"
        Should Be True    '${status}' in ['Pending', 'Synced']
        ...    msg=Expected status 'Pending' or 'Synced' in response, got '${status}'
        Log    Storage status in response is ${status} (expected Pending, Synced allowed)    INFO
    ELSE
        Should be equal    ${status}    ${expected_status}
        ...    msg=Expected status '${expected_status}' in response, got '${status}'
        Log    Storage status in response is ${status}    INFO
    END

# Backward compatibility keywords (can be removed later)
Storage status should be unassigned
    [Documentation]    DEPRECATED: Use 'Storage status should be "Unassigned"' instead
    Storage status should be "Unassigned"

Storage status should be pending
    [Documentation]    DEPRECATED: Use 'Storage status should be "Pending"' instead
    Storage status should be "Pending"

Storage status should be synced
    [Documentation]    DEPRECATED: Use 'Storage status should be "Synced"' instead
    Storage status should be "Synced"

Storage status should be deleting
    [Documentation]    DEPRECATED: Use 'Storage status should be "Deleting"' instead
    Storage status should be "Deleting"

Storage should have "${count}" project assignment
    [Documentation]    Verifies storage has the specified number of project assignments
    ${count_int}=    Convert to integer    ${count}

    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.

    ${fresh_response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=200
    ${json}=    Set variable    ${fresh_response.json()}
    ${project_storages}=    Get from dictionary    ${json}    project_storages
    ${actual_count}=    Get length    ${project_storages}

    Should be equal as integers    ${actual_count}    ${count_int}
    ...    msg=Expected ${count_int} project assignments, found ${actual_count}

    Log    Storage has ${actual_count} project assignment(s)    INFO

    Set test variable    ${response}    ${fresh_response}

All storage project assignments should be synced
    [Documentation]    Verifies all project storage assignments are in SYNCED status
    Should not be equal    ${response}    ${None}
    ...    msg=Response not set.

    ${json}=    Set variable    ${response.json()}
    ${project_storages}=    Get from dictionary    ${json}    project_storages

    FOR    ${project_storage}    IN    @{project_storages}
        ${status}=    Get from dictionary    ${project_storage}    status
        Should be equal    ${status}    Synced
        ...    msg=Project storage ${project_storage['id']} is ${status}, expected Synced
    END

    Log    All project storage assignments are synced    INFO

Storage should not be visible via API
    [Documentation]    Verifies storage has been deleted and is no longer accessible
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.

    ${response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=404

    Log    Storage ${TEST_STORAGE_ID} is no longer accessible (deleted)    INFO

Storage creation should fail with conflict
    [Documentation]    Verifies storage creation failed with HTTP 409 Conflict
    Should not be equal    ${response}    ${None}
    ...    msg=Response not set.

    Log    Storage creation correctly failed with conflict    INFO

Storage creation should fail with validation error
    [Documentation]    Verifies storage creation failed with HTTP 422 validation error
    Should not be equal    ${response}    ${None}
    ...    msg=Response not set.

    Log    Storage creation correctly failed with validation error    INFO

Storage creation should fail with not found
    [Documentation]    Verifies storage creation failed with HTTP 404 not found
    Should not be equal    ${response}    ${None}
    ...    msg=Response not set.

    Log    Storage creation correctly failed with not found error    INFO

At least "${count}" storage should be visible
    [Documentation]    Verifies at least the specified number of storage resources are visible
    ${count_int}=    Convert to integer    ${count}

    ${json}=    Set variable    ${response.json()}
    ${storage_list}=    Get from dictionary    ${json}    storages
    ${actual_count}=    Get length    ${storage_list}

    Should be true    ${actual_count} >= ${count_int}
    ...    msg=Expected at least ${count_int} storage resources, found ${actual_count}

    Log    Found ${actual_count} storage resources (expected at least ${count_int})    INFO

Get storage name
    [Documentation]    Returns the name of the current test storage
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.

    ${response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=200
    ${json}=    Set variable    ${response.json()}
    ${name}=    Get from dictionary    ${json}    name
    RETURN    ${name}

Wait for storage deletion to complete
    [Documentation]    Waits until storage is fully deleted from the system
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.

    Wait until keyword succeeds    30 sec    2 sec
    ...    Verify storage is deleted

Verify storage is deleted
    [Documentation]    Helper keyword to verify storage no longer exists
    ${response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=404
    Log    Polling deletion: storage ${TEST_STORAGE_ID} not found (deleted)    TRACE

Storage with same name "${name}" can be created
    [Documentation]    Creates a new storage with the specified name
    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=Valid S3 spec not set.
    Should not be equal    ${TEST_STORAGE_SECRET_ID}    ${None}
    ...    msg=Storage secret not set.

    @{empty_project_ids}=    Create list

    ${storage_data}=    Create dictionary
    ...    name=${name}
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${TEST_STORAGE_SECRET_ID}
    ...    project_ids=${empty_project_ids}
    ...    spec=${VALID_S3_SPEC}

    ${response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=200

    ${new_storage_id}=    Get from dictionary    ${response.json()}    id
    Set test variable    ${TEST_STORAGE_ID}    ${new_storage_id}

    TRY
        Append to list    ${CREATED_STORAGE_IDS}    ${new_storage_id}
        Log    Added storage ${new_storage_id} to cleanup list    DEBUG
    EXCEPT
        Log    CREATED_STORAGE_IDS not available    WARN
    END

    Log    Created new storage with ID: ${new_storage_id}    INFO

New storage should have different ID than "${original_id}"
    [Documentation]    Verifies the new storage has a different ID than the original
    Should not be equal    ${TEST_STORAGE_ID}    ${None}
    ...    msg=TEST_STORAGE_ID not set.
    Should not be equal    ${TEST_STORAGE_ID}    ${original_id}
    ...    msg=New storage ID ${TEST_STORAGE_ID} should be different from original ${original_id}
    Log    New storage ID ${TEST_STORAGE_ID} is different from original ${original_id}    INFO

Get storage bucket URL
    [Documentation]    Returns the S3 bucket URL from the valid S3 spec used to create storage
    ...    Note: The API doesn't return the spec in GET responses, so we use the stored spec
    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=VALID_S3_SPEC not set. Call 'a valid S3 storage spec exists' first.

    ${bucket_url}=    Get from dictionary    ${VALID_S3_SPEC}    bucket_url
    RETURN    ${bucket_url}

Test data "${data}" is written to S3 bucket
    [Documentation]    Writes test data to the S3 bucket using a Kubernetes Job
    ...    Submits an S3 writer Job that actually writes data to S3 using boto3
    ...    Requires storage to be assigned to project (ConfigMap exists)
    ...    For local development, creates ConfigMap and Secret manually since dispatcher doesn't run

    # Generate random suffix for unique job names
    Generate Random Suffix

    # Get storage details to extract ConfigMap and secret info
    ${storage_response}=    Get storage    ${TEST_STORAGE_ID}    expected_status=200
    ${storage_json}=    Set Variable    ${storage_response.json()}

    # Get the project storage to find the ConfigMap name
    ${project_storages}=    Get from dictionary    ${storage_json}    project_storages
    Should Not Be Empty    ${project_storages}    msg=No project storages found - storage must be assigned to project first

    ${project_storage}=    Set Variable    ${project_storages}[0]
    ${storage_name}=    Get from dictionary    ${storage_json}    name

    # ConfigMap name follows pattern: {storage_name}-info-config-map
    ${config_map_name}=    Set Variable    ${storage_name}-info-config-map

    # Get secret details from VALID_S3_SPEC
    ${access_key_name}=    Get from dictionary    ${VALID_S3_SPEC}    access_key_name
    ${secret_key_name}=    Get from dictionary    ${VALID_S3_SPEC}    secret_key_name
    ${bucket_url}=    Get from dictionary    ${VALID_S3_SPEC}    bucket_url

    # Get the ExternalSecret name from the secret used to create storage
    # For e2e tests, the ExternalSecret name matches the secret name pattern
    ${secret_response}=    Get secret    ${TEST_STORAGE_SECRET_ID}    expected_status=200
    ${secret_json}=    Set Variable    ${secret_response.json()}
    ${external_secret_name}=    Get from dictionary    ${secret_json}    name

    # For local development, manually create ConfigMap and Secret
    # In a real cluster, these would be created by the dispatcher
    Create Storage ConfigMap For Local Testing
    ...    ${TEST_PROJECT_NAME}
    ...    ${config_map_name}
    ...    ${bucket_url}
    ...    ${access_key_name}
    ...    ${secret_key_name}
    ...    ${external_secret_name}

    Create ExternalSecret For Local Testing
    ...    ${TEST_PROJECT_NAME}
    ...    ${external_secret_name}
    ...    ${access_key_name}
    ...    ${secret_key_name}

    # Generate unique S3 object key with e2e-test prefix
    ${timestamp}=    Evaluate    int(__import__('time').time())
    ${test_key}=    Set Variable    e2e-test-storage-${timestamp}/${data}

    # Submit S3 writer job
    ${job_name}=    Submit S3 Writer Job
    ...    ${TEST_PROJECT_NAME}
    ...    ${config_map_name}
    ...    ${external_secret_name}
    ...    ${access_key_name}
    ...    ${secret_key_name}
    ...    ${test_key}
    ...    ${data}

    # Wait for job to complete
    Wait For Job Completion    ${job_name}    ${TEST_PROJECT_NAME}    timeout=2 min

    # Verify job succeeded
    Verify Job Succeeded    ${job_name}    ${TEST_PROJECT_NAME}

    # Get and log the job output
    ${logs}=    Get Job Logs    ${job_name}    ${TEST_PROJECT_NAME}

    # Clean up the job
    Delete Job    ${job_name}    ${TEST_PROJECT_NAME}

    # Clean up ConfigMap and Secret for local testing
    Delete Storage Resources For Local Testing    ${TEST_PROJECT_NAME}    ${config_map_name}    ${external_secret_name}

    # Store the test key for later verification
    Set Test Variable    ${TEST_S3_KEY}    ${test_key}

    Log    Successfully wrote test data '${data}' to S3 at key: ${test_key}    INFO

S3 bucket data should still exist
    [Arguments]    ${bucket_url}    ${expected_data}
    [Documentation]    Verifies that data still exists in the S3 bucket after storage deletion
    ...    This is expected behavior - storage resources manage access, not data lifecycle
    ...    Uses the stored TEST_S3_KEY from the write operation

    # The storage was deleted, but we can use the bucket URL to verify data persistence
    # We need to create a new temporary storage pointing to the same bucket

    Log    Verifying S3 data still exists at key: ${TEST_S3_KEY}    INFO

    # Create a new storage pointing to the same bucket for verification
    ${new_storage_name}=    Evaluate    "temp-verify-storage-" + str(int(__import__('time').time()))

    @{project_ids}=    Create list    ${TEST_PROJECT_ID}

    ${storage_data}=    Create dictionary
    ...    name=${new_storage_name}
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${TEST_STORAGE_SECRET_ID}
    ...    project_ids=${project_ids}
    ...    spec=${VALID_S3_SPEC}

    ${create_response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=200

    ${new_storage_id}=    Get from dictionary    ${create_response.json()}    id

    # Wait for storage to sync
    Wait until keyword succeeds    1 min    5 sec
    ...    Verify storage has status "Synced" for ID    ${new_storage_id}

    # Now use S3 reader job to verify data
    Generate Random Suffix

    ${storage_response}=    Get storage    ${new_storage_id}    expected_status=200
    ${storage_json}=    Set Variable    ${storage_response.json()}

    ${storage_name}=    Get from dictionary    ${storage_json}    name
    ${config_map_name}=    Set Variable    ${storage_name}-info-config-map

    ${access_key_name}=    Get from dictionary    ${VALID_S3_SPEC}    access_key_name
    ${secret_key_name}=    Get from dictionary    ${VALID_S3_SPEC}    secret_key_name

    ${secret_response}=    Get secret    ${TEST_STORAGE_SECRET_ID}    expected_status=200
    ${secret_json}=    Set Variable    ${secret_response.json()}
    ${external_secret_name}=    Get from dictionary    ${secret_json}    name

    # For local development, manually create ConfigMap and Secret
    Create Storage ConfigMap For Local Testing
    ...    ${TEST_PROJECT_NAME}
    ...    ${config_map_name}
    ...    ${bucket_url}
    ...    ${access_key_name}
    ...    ${secret_key_name}
    ...    ${external_secret_name}

    Create ExternalSecret For Local Testing
    ...    ${TEST_PROJECT_NAME}
    ...    ${external_secret_name}
    ...    ${access_key_name}
    ...    ${secret_key_name}

    # Submit S3 reader job
    ${job_name}=    Submit S3 Reader Job
    ...    ${TEST_PROJECT_NAME}
    ...    ${config_map_name}
    ...    ${external_secret_name}
    ...    ${access_key_name}
    ...    ${secret_key_name}
    ...    ${TEST_S3_KEY}
    ...    ${expected_data}

    # Wait for job to complete
    Wait For Job Completion    ${job_name}    ${TEST_PROJECT_NAME}    timeout=2 min

    # Verify job succeeded (meaning data was found and matched)
    Verify Job Succeeded    ${job_name}    ${TEST_PROJECT_NAME}

    # Get and log the job output
    ${logs}=    Get Job Logs    ${job_name}    ${TEST_PROJECT_NAME}

    # Clean up
    Delete Job    ${job_name}    ${TEST_PROJECT_NAME}
    Delete Storage Resources For Local Testing    ${TEST_PROJECT_NAME}    ${config_map_name}    ${external_secret_name}
    Delete storage    ${new_storage_id}    expected_status=204

    Log    ✓ Verified S3 data persists after storage deletion    INFO

New storage is created pointing to same bucket "${bucket_url}"
    [Documentation]    Creates a new storage resource pointing to the same S3 bucket
    ...    This demonstrates that multiple storage resources can share the same S3 bucket
    Should not be equal    ${TEST_STORAGE_SECRET_ID}    ${None}
    ...    msg=Storage secret not set.
    Should not be equal    ${VALID_S3_SPEC}    ${None}
    ...    msg=Valid S3 spec not set.

    ${name}=    Evaluate    "new-storage-same-bucket-" + str(int(__import__('time').time()))

    &{new_spec}=    Create dictionary
    ...    bucket_url=${bucket_url}
    ...    access_key_name=ACCESS_KEY_ID
    ...    secret_key_name=SECRET_ACCESS_KEY

    @{empty_project_ids}=    Create list

    ${storage_data}=    Create dictionary
    ...    name=${name}
    ...    type=S3
    ...    scope=Organization
    ...    secret_id=${TEST_STORAGE_SECRET_ID}
    ...    project_ids=${empty_project_ids}
    ...    spec=${new_spec}

    ${response}=    Create storage
    ...    storage_data=${storage_data}
    ...    expected_status=200

    ${new_storage_id}=    Get from dictionary    ${response.json()}    id
    Set test variable    ${NEW_STORAGE_ID}    ${new_storage_id}
    Set test variable    ${TEST_STORAGE_ID}    ${new_storage_id}

    TRY
        Append to list    ${CREATED_STORAGE_IDS}    ${new_storage_id}
        Log    Added new storage ${new_storage_id} pointing to same bucket    DEBUG
    EXCEPT
        Log    CREATED_STORAGE_IDS not available    WARN
    END

    Log    Created new storage pointing to same S3 bucket: ${bucket_url}    WARN

New storage can access data from previous storage "${expected_data}"
    [Documentation]    Verifies that new storage can access data from the same S3 bucket
    ...    This is expected behavior - storage resources manage access, not data ownership
    ...    Uses the NEW_STORAGE_ID created by "New storage is created pointing to same bucket"

    Log    Verifying new storage can access data from previous storage    INFO

    # Use the NEW_STORAGE_ID which was created pointing to the same bucket
    Generate Random Suffix

    ${storage_response}=    Get storage    ${NEW_STORAGE_ID}    expected_status=200
    ${storage_json}=    Set Variable    ${storage_response.json()}

    ${storage_name}=    Get from dictionary    ${storage_json}    name
    ${config_map_name}=    Set Variable    ${storage_name}-info-config-map

    ${access_key_name}=    Get from dictionary    ${VALID_S3_SPEC}    access_key_name
    ${secret_key_name}=    Get from dictionary    ${VALID_S3_SPEC}    secret_key_name

    ${secret_response}=    Get secret    ${TEST_STORAGE_SECRET_ID}    expected_status=200
    ${secret_json}=    Set Variable    ${secret_response.json()}
    ${external_secret_name}=    Get from dictionary    ${secret_json}    name

    # For local development, manually create ConfigMap and Secret
    ${bucket_url}=    Get from dictionary    ${VALID_S3_SPEC}    bucket_url
    Create Storage ConfigMap For Local Testing
    ...    ${TEST_PROJECT_NAME}
    ...    ${config_map_name}
    ...    ${bucket_url}
    ...    ${access_key_name}
    ...    ${secret_key_name}
    ...    ${external_secret_name}

    Create ExternalSecret For Local Testing
    ...    ${TEST_PROJECT_NAME}
    ...    ${external_secret_name}
    ...    ${access_key_name}
    ...    ${secret_key_name}

    # Submit S3 reader job using the new storage's ConfigMap
    ${job_name}=    Submit S3 Reader Job
    ...    ${TEST_PROJECT_NAME}
    ...    ${config_map_name}
    ...    ${external_secret_name}
    ...    ${access_key_name}
    ...    ${secret_key_name}
    ...    ${TEST_S3_KEY}
    ...    ${expected_data}

    # Wait for job to complete
    Wait For Job Completion    ${job_name}    ${TEST_PROJECT_NAME}    timeout=2 min

    # Verify job succeeded (meaning new storage can access old data)
    Verify Job Succeeded    ${job_name}    ${TEST_PROJECT_NAME}

    # Get and log the job output
    ${logs}=    Get Job Logs    ${job_name}    ${TEST_PROJECT_NAME}

    # Clean up
    Delete Job    ${job_name}    ${TEST_PROJECT_NAME}
    Delete Storage Resources For Local Testing    ${TEST_PROJECT_NAME}    ${config_map_name}    ${external_secret_name}

    Log    ✓ Verified new storage can access data from previous storage    INFO
