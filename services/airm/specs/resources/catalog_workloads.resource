# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level workload testing keywords.
...                 Provides business-logic level keywords for testing workload operations.
...                 Uses the low-level API keywords from api/workloads.resource to implement
...                 higher-level testing scenarios.
Resource            api/workloads.resource
Resource            catalog_charts.resource
Resource            common/resource_tracking.resource
Library             Collections
Library             String


*** Variables ***
${TEST_WORKLOAD_ID}         ${None}
${TEST_WORKLOAD_DATA}       ${None}
${TEST_MODEL_ID}            ${None}
@{CREATED_WORKLOAD_IDS}     # List to track created workload IDs for cleanup
${response}                 ${None}


*** Keywords ***
Valid workload data is prepared
    [Documentation]    Prepares valid workload submission data
    ${is_empty}=            Run Keyword And Return Status                   Evaluate                "${TEST_CHART_ID}" == "${None}" or "${TEST_CHART_ID}" == ""

    IF    ${is_empty}
        A chart exists
    END

    ${chart_id}=            Get Variable Value      ${TEST_CHART_ID}        ${None}
    Should Not Be Equal     ${chart_id}             ${None}                 msg=TEST_CHART_ID is not set or is None. Ensure a chart exists first.

    ${workload_data}=       Create dictionary
    ...                     chart_id=${TEST_CHART_ID}
    ...                     user_inputs={"replicaCount": 1}
    Set test variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}
    Log                     Prepared workload data for chart ${TEST_CHART_ID}    DEBUG

Valid job workload data is prepared
    [Documentation]    Prepares valid job workload submission data using the test job chart.
    Should Not Be Equal     ${TEST_JOB_CHART_ID}    ${None}                 msg=No test job chart ID is set. Ensure a test job chart exists.
    Set Test Variable       ${TEST_CHART_ID}        ${TEST_JOB_CHART_ID}
    &{img}=                 Evaluate                {"repository": "busybox", "tag": "latest"}
    &{user_inputs}=         Create Dictionary       image=${img}            sleepSeconds=${5}
    &{workload_data}=       Create Dictionary       chart_id=${TEST_CHART_ID}                       user_inputs=${user_inputs}
    Set Test Variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}
    Log                     Prepared job workload data for chart ${TEST_CHART_ID}    DEBUG

Valid service workload data is prepared
    [Documentation]    Prepares valid service workload submission data using the test service chart.
    Variable Should Exist                           ${TEST_SERVICE_CHART_ID}                        msg=No test service chart ID is set. Ensure a test service chart exists.
    Set Test Variable       ${TEST_CHART_ID}        ${TEST_SERVICE_CHART_ID}
    ${user_inputs}=         Evaluate                {"replicaCount": 1, "image": {"repository": "nginx", "tag": "alpine"}, "service": {"type": "ClusterIP", "port": 80}}
    ${workload_data}=       Create Dictionary       chart_id=${TEST_CHART_ID}                       user_inputs=${user_inputs}
    Set Test Variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}
    Log                     Prepared service workload data for chart ${TEST_CHART_ID}    DEBUG

Valid workload data with model is prepared
    [Documentation]    Prepares valid workload submission data with a model ID
    ${is_empty}=            Run Keyword And Return Status                   Evaluate                "${TEST_CHART_ID}" == "${None}" or "${TEST_CHART_ID}" == ""

    IF    ${is_empty}
        A chart exists
    END

    ${model_is_empty}=      Run Keyword And Return Status                   Evaluate                "${TEST_MODEL_ID}" == "${None}" or "${TEST_MODEL_ID}" == ""

    IF    ${model_is_empty}
        ${test_model_id}=       Evaluate                str(uuid.uuid4())       modules=uuid
        Set Test Variable       ${TEST_MODEL_ID}        ${test_model_id}
        Log                     Generated model ID for testing: ${TEST_MODEL_ID}    DEBUG
    END

    ${workload_data}=       Create dictionary
    ...                     chart_id=${TEST_CHART_ID}
    ...                     model_id=${TEST_MODEL_ID}
    ...                     user_inputs={"replicaCount": 1}
    Set test variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}
    Log                     Prepared workload data with model for chart ${TEST_CHART_ID}    DEBUG

Create workload request is sent
    [Documentation]    Sends request to create a workload using data in ${TEST_WORKLOAD_DATA}. Stores response.
    ${response}=            Create workload         ${TEST_WORKLOAD_DATA}                           expected_status=any
    Set test variable       ${response}             ${response}
    Log                     Sent create workload request for chart ${TEST_WORKLOAD_DATA['chart_id']}, status: ${response.status_code}    DEBUG
    RETURN                  ${response}

Workload ID should be extracted from response
    [Documentation]    Extracts workload ID from response and sets ${TEST_WORKLOAD_ID}. Fails if ID is missing.
    [Arguments]             ${resp}=${response}
    Variable Should Exist                           ${resp}                 msg=Response variable not set. Call a request keyword first.

    ${json}=                Set Variable            ${resp.json()}
    Dictionary Should Contain Key                   ${json}                 id
    ${workload_id}=         Get From Dictionary     ${json}                 id
    Set Test Variable       ${TEST_WORKLOAD_ID}     ${workload_id}
    Log                     Extracted workload ID: ${workload_id}    DEBUG
    RETURN                  ${TEST_WORKLOAD_ID}

A workload exists
    [Documentation]    Creates a new workload, verifies creation success (201/202), extracts and stores its ID.
    A chart exists
    Valid workload data is prepared
    ${create_resp}=         Create workload request is sent

    IF    ${create_resp.status_code} != 201 and ${create_resp.status_code} != 202
        Fail                    Failed to create workload for precondition. Status: ${create_resp.status_code}, Body: ${create_resp.text}
    END
    Set Test Variable       ${response}             ${create_resp}
    ${workload_id}=         Workload ID should be extracted from response

    Log                     Created workload with ID: ${workload_id}    INFO

List workloads request is sent
    [Documentation]    Sends a request to list workloads with optional filtering
    [Arguments]             ${type}=None            ${status}=None          ${expected_status}=200
    ${params}=              Create Dictionary
    Run Keyword If          $type is not None       Set To Dictionary       ${params}               type=${type}
    Run Keyword If          $status is not None     Set To Dictionary       ${params}               status=${status}

    Log                     Listing workloads with params: ${params}    DEBUG
    ${response}=            List workloads          params=${params}        expected_status=${expected_status}
    Set test variable       ${response}             ${response}
    Log                     List workloads response status: ${response.status_code}    DEBUG

Multiple workloads exist
    [Documentation]    Creates multiple test workloads for listing tests.
    [Arguments]             ${count}=3
    A chart exists

    @{created_ids}=         Create list
    Set test variable       ${CREATED_WORKLOAD_IDS}                         ${created_ids}

    FOR    ${index}    IN RANGE    ${count}
        Valid workload data is prepared
        ${response}=            Create workload request is sent

        Response status should be 201
        ${json}=                Set Variable            ${response.json()}
        Dictionary should contain key                   ${json}                 id
        ${workload_id}=         Get from dictionary     ${json}                 id
        Append to list          ${CREATED_WORKLOAD_IDS}                         ${workload_id}
        Log                     Created workload ${index+1}/${count} with ID: ${workload_id}    INFO
    END
    Log                     Created ${count} workloads    INFO
    Log                     Workload IDs: ${CREATED_WORKLOAD_IDS}    DEBUG

    FOR    ${workload_id}    IN    @{CREATED_WORKLOAD_IDS}
        Verify workload exists                          ${workload_id}
    END

A workload does not exist
    [Documentation]    Sets up a non-existent workload ID for testing
    ${workload_id}=         Evaluate                str(uuid.uuid4())       modules=uuid
    Set test variable       ${TEST_WORKLOAD_ID}     ${workload_id}
    Log                     Set non-existent workload ID: ${workload_id}    DEBUG

Delete workload request is sent
    [Documentation]    Sends a request to delete the workload specified by ${TEST_WORKLOAD_ID}.
    Variable Should Exist                           ${TEST_WORKLOAD_ID}     msg=TEST_WORKLOAD_ID is not set. Ensure a workload was created or selected first.
    Log                     Deleting workload ${TEST_WORKLOAD_ID}    DEBUG
    ${response}=            Delete workload         ${TEST_WORKLOAD_ID}     expected_status=204
    Set test variable       ${response}             ${response}
    Log                     Deleted workload ${TEST_WORKLOAD_ID}    INFO

Workload should exist in database
    [Documentation]    Verifies that a workload exists in the database
    [Arguments]             ${workload_id}=${TEST_WORKLOAD_ID}
    ${check_response}=      Get workload            ${workload_id}          expected_status=200
    Should not be empty     ${check_response.json()}
    ${current_id}=          Set variable            ${check_response.json()['id']}
    Should be equal         $current_id             $workload_id

Verify workload exists
    [Documentation]    Helper method to verify a workload exists
    [Arguments]             ${workload_id}
    ${db_response}=         Get workload            ${workload_id}          expected_status=200
    Log                     Verified workload ${workload_id} exists in database    DEBUG

The workload should not exist in database
    [Documentation]    Verifies the workload specified by ${TEST_WORKLOAD_ID} no longer exists.
    Variable Should Exist                           ${TEST_WORKLOAD_ID}     msg=TEST_WORKLOAD_ID is not set.
    ${workload_id}=         Set Variable            ${TEST_WORKLOAD_ID}
    ${response}=            Get workload            ${workload_id}          expected_status=404
    Log                     Verified workload ${workload_id} not found (404)    INFO

Response should contain workload type
    [Documentation]    Verifies response contains workload type
    [Arguments]             ${expected_type}
    Dictionary should contain value                 ${response.json()}      ${expected_type}

Response should contain workload status
    [Documentation]    Verifies response contains workload status
    [Arguments]             ${expected_status}
    Dictionary should contain value                 ${response.json()}      ${expected_status}

Response should contain workloads list
    [Documentation]    Verifies response contains a list of workloads
    @{workloads}=           Set variable            ${response.json()}
    ${count}=               Get length              ${workloads}
    Should be true          ${count} >= 0

Response should contain at least ${expected} workloads
    [Documentation]    Verifies response contains at least the expected number of workloads
    @{workloads}=           Set variable            ${response.json()}
    ${count}=               Get length              ${workloads}
    Should be true          ${count} >= ${expected}

Batch delete workloads request is sent
    [Documentation]    Sends a request to delete multiple workloads
    ${response}=            Batch delete workloads                          ${CREATED_WORKLOAD_IDS}
    Set test variable       ${response}             ${response}

Test job has completed
    [Documentation]    Wait until the KaiwoJob corresponding to the test job workload has completed.
    ${kubectl_cmd}=         Set Variable            kubectl wait --for=condition=complete kaiwojob/${TEST_WORKLOAD_ID} --timeout=300s
    ${result}=              Run Process             ${kubectl_cmd}          shell=True              stdout=PIPE             stderr=PIPE
    Should Be Equal As Integers                     ${result.rc}            0                       msg=KaiwoJob did not complete successfully

Workload resources should disappear form the cluster
    [Documentation]    Verifies that the workload resources for ${TEST_WORKLOAD_ID} have been removed from the cluster.
    Variable Should Exist                           ${TEST_WORKLOAD_ID}     msg=TEST_WORKLOAD_ID is not set.
    ${cmd}=                 Set Variable            kubectl get kaiwojob -l workload-id=${TEST_WORKLOAD_ID} --ignore-not-found
    ${result}=              Run Process             ${cmd}                  shell=True              stdout=PIPE             stderr=PIPE
    Log                     Checking for KaiwoJob for workload ${TEST_WORKLOAD_ID}. RC: ${result.rc}, Stdout: ${result.stdout}, Stderr: ${result.stderr}                    level=DEBUG
    Should Be Empty         ${result.stdout}        msg=Expected no KaiwoJob resource for workload ${TEST_WORKLOAD_ID}, but found: ${result.stdout}

Workload status should be "${expected_status}" for workload "${workload_id}"
    [Documentation]    Verifies workload status matches expected
    ${response}=            Get workload            ${workload_id}          expected_status=200
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 status
    Should Be Equal         $json['status']         $expected_status        msg=Expected workload $workload_id status to be '$expected_status', but was '$json['status']'.

Workload status should be "Deleted"
    [Documentation]    Verifies that the workload status in the database is reported as "Deleted".
    ${response}=            Get workload            ${TEST_WORKLOAD_ID}     expected_status=200
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 status
    Should Be Equal         ${json['status']}       Deleted

Response should contain key "id"
    [Documentation]    Verifies response contains expected key
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 id

Chat with finetuned model
    [Documentation]    Sends a chat request to the finetuned model and verifies the response.
    Should Not Be Empty     ${TEST_WORKLOAD_ID}     msg=Workflow ID is required to retrieve the workflow.
    Valid chat data is prepared
    ${response}=            Chat workload           ${TEST_CHAT_DATA}

A chat request is sent
    [Documentation]    Sends a chat request to the workload and verifies the response.
    Should Not Be Empty     ${TEST_WORKLOAD_ID}     msg=Workflow ID is required to retrieve the workflow.
    Valid chat data is prepared
    ${response}=            Chat workload           chat_data=${TEST_CHAT_DATA}                     expected_status=200
    Set test variable       ${response}             ${response}
    Log To Console          Sent chat request to workload ${TEST_WORKLOAD_ID}. Status: ${response.status_code}
    Log To Console          message= Response :: ${response.text}

# API Workload Submission Keywords (for workloads_api.robot)

Workload is submitted via AIRM API
    [Documentation]    Submits a workload via AIRM API using /charts/{id}/submit endpoint
    ...    Uses the TEST_CHART_ID that was set up by "A chart exists"
    Valid workload data is prepared
    ${response}=            Create workload request is sent

    # Verify creation succeeded (201 or 202)
    IF    ${response.status_code} != 201 and ${response.status_code} != 202
        Fail                Failed to submit workload via API. Status: ${response.status_code}, Body: ${response.text}
    END

    # Set response as test variable so subsequent keywords can access it
    Set Test Variable       ${response}    ${response}

    ${workload_id}=         Workload ID should be extracted from response    ${response}

    Append To List          ${CREATED_WORKLOAD_IDS}    ${workload_id}

    Log                     Submitted workload via AIRM API with ID: ${workload_id}    INFO

Workload is submitted with manifest via AIRM API
    [Documentation]    Submits a workload via AIRM API using POST /workloads with direct manifest
    ...    Uses the TEST_PROJECT_ID and requires a manifest file path
    ...    This is the preferred method for testing workload submission without charts
    [Arguments]             ${manifest_path}=${CURDIR}/../test_data/manifests/test-deployment.yaml    ${display_name}=test-workload    ${workload_type}=CUSTOM

    # Verify project exists
    Should Not Be Equal     ${TEST_PROJECT_ID}    ${None}    msg=TEST_PROJECT_ID not set. Create a project first.

    # Submit workload with manifest
    ${response}=            Submit workload with manifest
    ...                     manifest_path=${manifest_path}
    ...                     project_id=${TEST_PROJECT_ID}
    ...                     display_name=${display_name}
    ...                     workload_type=${workload_type}
    ...                     expected_status=201

    # Verify creation succeeded
    Should Be Equal As Integers    ${response.status_code}    201
    ...    msg=Failed to submit workload with manifest. Status: ${response.status_code}, Body: ${response.text}

    ${json}=                Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    id    msg=Workload response missing 'id' field
    ${workload_id}=         Get From Dictionary    ${json}    id
    Set Test Variable       ${TEST_WORKLOAD_ID}    ${workload_id}
    Set Test Variable       ${response}    ${response}

    Append To List          ${CREATED_WORKLOAD_IDS}    ${workload_id}

    Log                     Submitted workload with manifest via AIRM API, ID: ${workload_id}    INFO

Workload should be visible via API
    [Documentation]    Verifies that the workload is visible via GET /workloads/{id}
    ...    Polls for workload to appear in database to handle async operations
    Should Not Be Equal     ${TEST_WORKLOAD_ID}    ${None}    msg=TEST_WORKLOAD_ID not set. Submit workload first.

    Wait Until Keyword Succeeds    10 sec    1 sec
    ...    Workload is in database

    Log                     Workload ${TEST_WORKLOAD_ID} is visible via API    INFO

Workload is in database
    [Documentation]    Verifies workload exists in database via API
    ...    Used with polling to wait for async workload creation
    Log                     Polling for workload ${TEST_WORKLOAD_ID} in database    TRACE
    ${response}=            Get workload    ${TEST_WORKLOAD_ID}    expected_status=200
    Set Test Variable       ${response}    ${response}

Workload should have valid ID and status via API
    [Documentation]    Verifies workload response contains valid id and status fields
    Should Not Be Equal     ${response}    ${None}    msg=Response not set. Call 'workload should be visible via API' first.

    ${json}=                Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    id
    Dictionary Should Contain Key    ${json}    status

    ${workload_id}=         Get From Dictionary    ${json}    id
    ${status}=              Get From Dictionary    ${json}    status

    Log                     Workload has valid ID: ${workload_id}, Status: ${status}    INFO

"${count}" workloads should be visible via API list endpoint
    [Documentation]    Verifies that the specified number of workloads are visible via GET /workloads in the current project
    ...    Uses TEST_PROJECT_ID to filter workloads from this test only
    ${count_int}=           Convert To Integer    ${count}

    # Get all workloads and count those in current project
    ${response}=            Get workloads    expected_status=200
    ${all_workloads}=       Set Variable    ${response.json()['data']}

    # Count workloads belonging to current project
    ${project_workload_count}=    Set Variable    ${0}
    FOR    ${workload}    IN    @{all_workloads}
        IF    "${workload['project_id']}" == "${TEST_PROJECT_ID}"
            ${project_workload_count}=    Evaluate    ${project_workload_count} + 1
        END
    END

    Should Be Equal As Integers    ${project_workload_count}    ${count_int}
    ...    msg=Expected ${count_int} workloads in project ${TEST_PROJECT_ID}, found ${project_workload_count}

    Log                     Found ${project_workload_count} workloads in project ${TEST_PROJECT_ID} via API    INFO

Workload is deleted via AIRM API
    [Documentation]    Deletes the workload via DELETE /workloads/{id}
    Should Not Be Equal     ${TEST_WORKLOAD_ID}    ${None}    msg=TEST_WORKLOAD_ID not set. Submit workload first.

    ${response}=            Delete workload    ${TEST_WORKLOAD_ID}    expected_status=204

    Log                     Deleted workload ${TEST_WORKLOAD_ID} via AIRM API    INFO

Workload should not be visible via API
    [Documentation]    Verifies that after deletion, the workload has status "Deleting" or "Deleted"
    ...    AIRM API uses soft delete, so workloads remain visible with deleted status
    Should Not Be Equal     ${TEST_WORKLOAD_ID}    ${None}    msg=TEST_WORKLOAD_ID not set.

    # Get the workload - it should still be visible but with Deleting/Deleted status
    ${response}=            Get workload    ${TEST_WORKLOAD_ID}    expected_status=200
    ${json}=                Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    status
    ${status}=              Get From Dictionary    ${json}    status

    # Verify the status is either Deleting or Deleted
    ${is_deleted}=          Run Keyword And Return Status    Should Match Regexp    ${status}    ^(Deleting|Deleted)$
    Should Be True          ${is_deleted}    msg=Expected workload status to be Deleting or Deleted, but got ${status}

    Log                     Workload ${TEST_WORKLOAD_ID} has deletion status: ${status}    INFO

# Workload Status Verification Keywords

Workload status in response should be "${expected_status}"
    [Documentation]    Verifies the workload response has the expected status
    ...    Checks the response (either from creation or from a GET request)
    ${json}=                Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    status
    ${status}=              Get From Dictionary    ${json}    status
    Should Be Equal         ${status}    ${expected_status}
    ...    msg=Expected workload status to be ${expected_status}, but got ${status}
    Log                     Workload status: ${status}    INFO

Workload should transition to "${expected_status}"
    [Documentation]    Waits for workload to transition to expected status
    ...    Polls the workload endpoint until status becomes expected value
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify workload has status "${expected_status}"

Verify workload has status "${expected_status}"
    [Documentation]    Helper keyword to verify workload status (used with polling)
    ${workload_response}=   Get workload    ${TEST_WORKLOAD_ID}    expected_status=200
    ${json}=                Set Variable    ${workload_response.json()}
    ${status}=              Get From Dictionary    ${json}    status
    Log                     Polling workload ${TEST_WORKLOAD_ID} status: ${status}    TRACE
    Should Be Equal         ${status}    ${expected_status}
    ...    msg=Workload status is ${status}, expected ${expected_status}
    Set Test Variable       ${response}    ${workload_response}
    Log                     Workload ${TEST_WORKLOAD_ID} transitioned to ${expected_status}    INFO

# Backward compatibility keywords (can be removed later)
Workload status in response should be pending
    [Documentation]    DEPRECATED: Use 'Workload status in response should be "Pending"' instead
    Workload status in response should be "Pending"

Workload status in response should be running
    [Documentation]    DEPRECATED: Use 'Workload status in response should be "Running"' instead
    Workload status in response should be "Running"

Workload should transition to running
    [Documentation]    DEPRECATED: Use 'Workload should transition to "Running"' instead
    Workload should transition to "Running"

Verify workload is running
    [Documentation]    DEPRECATED: Use 'Verify workload has status "Running"' instead
    Verify workload has status "Running"
