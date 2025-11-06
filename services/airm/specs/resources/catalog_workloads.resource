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
Library             Collections
Library             String


*** Variables ***
${TEST_WORKLOAD_ID}         ${None}
${TEST_WORKLOAD_DATA}       ${None}
${TEST_MODEL_ID}            ${None}
${CREATED_WORKLOAD_IDS}     @{EMPTY}
${response}                 ${None}


*** Keywords ***
Valid workload data is prepared
    [Documentation]    Prepares valid workload submission data
    # Check if TEST_CHART_ID exists AND has a valid value
    ${is_empty}=            Run Keyword And Return Status                   Evaluate                "${TEST_CHART_ID}" == "${None}" or "${TEST_CHART_ID}" == ""

    IF    ${is_empty}
        A chart exists  # Ensure we have a chart created properly
    END

    # Verify chart exists before preparing workload data
    ${chart_id}=            Get Variable Value      ${TEST_CHART_ID}        ${None}
    Should Not Be Equal     ${chart_id}             ${None}                 msg=TEST_CHART_ID is not set or is None. Ensure a chart exists first.

    ${workload_data}=       Create dictionary
    ...                     chart_id=${TEST_CHART_ID}
    ...                     user_inputs={"replicaCount": 1}
    Set test variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}

Valid job workload data is prepared
    [Documentation]    Prepares valid job workload submission data using the test job chart.
    # Fail if test job chart ID is not set. Ensure a test job chart exists prior to this keyword.
    Should Not Be Equal     ${TEST_JOB_CHART_ID}    ${None}                 msg=No test job chart ID is set. Ensure a test job chart exists.
    # Ensure TEST_CHART_ID is set to the job chart ID for consistency
    Set Test Variable       ${TEST_CHART_ID}        ${TEST_JOB_CHART_ID}
    &{img}=                 Evaluate                {"repository": "busybox", "tag": "latest"}
    &{user_inputs}=         Create Dictionary       image=${img}            sleepSeconds=${5}
    &{workload_data}=       Create Dictionary       chart_id=${TEST_CHART_ID}                       user_inputs=${user_inputs}
    Set Test Variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}
    Log                     Prepared job workload data with chart ID: ${TEST_CHART_ID}

Valid service workload data is prepared
    [Documentation]    Prepares valid service workload submission data using the test service chart.
    Variable Should Exist                           ${TEST_SERVICE_CHART_ID}                        msg=No test service chart ID is set. Ensure a test service chart exists.
    Set Test Variable       ${TEST_CHART_ID}        ${TEST_SERVICE_CHART_ID}
    ${user_inputs}=         Evaluate                {"replicaCount": 1, "image": {"repository": "nginx", "tag": "alpine"}, "service": {"type": "ClusterIP", "port": 80}}
    ${workload_data}=       Create Dictionary       chart_id=${TEST_CHART_ID}                       user_inputs=${user_inputs}
    Set Test Variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}
    Log                     Prepared service workload data with chart ID: ${TEST_CHART_ID}

Valid workload data with model is prepared
    [Documentation]    Prepares valid workload submission data with a model ID
    # Check if TEST_CHART_ID exists AND has a valid value
    ${is_empty}=            Run Keyword And Return Status                   Evaluate                "${TEST_CHART_ID}" == "${None}" or "${TEST_CHART_ID}" == ""

    IF    ${is_empty}
        # Instead of generating a random ID, ensure we have a chart created properly
        A chart exists
    END

    # Check if TEST_MODEL_ID exists AND has a valid value
    ${model_is_empty}=      Run Keyword And Return Status                   Evaluate                "${TEST_MODEL_ID}" == "${None}" or "${TEST_MODEL_ID}" == ""

    IF    ${model_is_empty}
        ${test_model_id}=       Evaluate                str(uuid.uuid4())       modules=uuid
        Set Test Variable       ${TEST_MODEL_ID}        ${test_model_id}
        Log                     Using generated model ID for testing: ${TEST_MODEL_ID}
    END

    ${workload_data}=       Create dictionary
    ...                     chart_id=${TEST_CHART_ID}
    ...                     model_id=${TEST_MODEL_ID}
    ...                     user_inputs={"replicaCount": 1}
    Set test variable       ${TEST_WORKLOAD_DATA}                           ${workload_data}

Create workload request is sent
    [Documentation]    Sends request to create a workload using data in ${TEST_WORKLOAD_DATA}. Stores response.
    ${response}=            Create workload         ${TEST_WORKLOAD_DATA}                           expected_status=any  # Let caller verify status
    Set test variable       ${response}             ${response}
    # Log basic info without console spam
    Log                     Sent create workload request for chart ${TEST_WORKLOAD_DATA['chart_id']}. Status: ${response.status_code}               level=DEBUG
    # Return the response object for the test case to handle
    RETURN                  ${response}

Workload ID should be extracted from response
    [Documentation]    Extracts workload ID from response and sets ${TEST_WORKLOAD_ID}. Fails if ID is missing.
    [Arguments]             ${resp}=${response}
    Variable Should Exist                           ${resp}                 msg=Response variable not set. Call a request keyword first.

    ${json}=                Set Variable            ${resp.json()}
    Dictionary Should Contain Key                   ${json}                 id
    ${workload_id}=         Get From Dictionary     ${json}                 id
    Set Test Variable       ${TEST_WORKLOAD_ID}     ${workload_id}
    Log                     Successfully extracted workload ID: ${workload_id}
    RETURN                  ${TEST_WORKLOAD_ID}

A workload exists
    [Documentation]    Creates a new workload, verifies creation success (201/202), extracts and stores its ID.
    A chart exists  # Ensure we have a chart first
    Valid workload data is prepared
    ${create_resp}=         Create workload request is sent  # Store response for later use

    # Verify creation succeeded and extract ID
    IF    ${create_resp.status_code} != 201 and ${create_resp.status_code} != 202
        Fail                    Failed to create workload for precondition. Status: ${create_resp.status_code}, Body: ${create_resp.text}
    END
    Set Test Variable       ${response}             ${create_resp}  # Set response for extraction keyword
    ${workload_id}=         Workload ID should be extracted from response

    Log                     Precondition satisfied: Workload exists with ID: ${workload_id}

List workloads request is sent
    [Documentation]    Sends a request to list workloads with optional filtering
    [Arguments]             ${type}=None            ${status}=None          ${expected_status}=200
    ${params}=              Create Dictionary
    Run Keyword If          $type is not None       Set To Dictionary       ${params}               type=${type}
    Run Keyword If          $status is not None     Set To Dictionary       ${params}               status=${status}

    ${response}=            List workloads          params=${params}        expected_status=${expected_status}
    Set test variable       ${response}             ${response}

Multiple workloads exist
    [Documentation]    Creates multiple test workloads for listing tests.
    [Arguments]             ${count}=3
    A chart exists  # Ensure we have a chart first

    @{created_ids}=         Create list
    Set test variable       ${CREATED_WORKLOAD_IDS}                         ${created_ids}

    FOR    ${index}    IN RANGE    ${count}
        Log                     Creating workload ${index+1} of ${count}
        Valid workload data is prepared
        ${response}=            Create workload request is sent

        # Verify creation succeeded and extract ID
        Response status should be 201
        ${json}=                Set Variable            ${response.json()}
        Dictionary should contain key                   ${json}                 id
        ${workload_id}=         Get from dictionary     ${json}                 id
        Append to list          ${CREATED_WORKLOAD_IDS}                         ${workload_id}
        Log                     Created workload ${index+1} with ID: ${workload_id}
    END
    Log                     Precondition satisfied: Created ${count} workloads with IDs: ${CREATED_WORKLOAD_IDS}

    # Verify that the created workloads exist in the database
    FOR    ${workload_id}    IN    @{CREATED_WORKLOAD_IDS}
        Verify workload exists                          ${workload_id}
    END

A workload does not exist
    [Documentation]    Sets up a non-existent workload ID for testing
    ${workload_id}=         Evaluate                str(uuid.uuid4())       modules=uuid
    Set test variable       ${TEST_WORKLOAD_ID}     ${workload_id}

Delete workload request is sent
    [Documentation]    Sends a request to delete the workload specified by ${TEST_WORKLOAD_ID}.
    Variable Should Exist                           ${TEST_WORKLOAD_ID}     msg=TEST_WORKLOAD_ID is not set. Ensure a workload was created or selected first.
    ${response}=            Delete workload         ${TEST_WORKLOAD_ID}     expected_status=204
    Set test variable       ${response}             ${response}

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
    Log                     Workload ${workload_id} found in database

The workload should not exist in database
    [Documentation]    Verifies the workload specified by ${TEST_WORKLOAD_ID} no longer exists.
    Variable Should Exist                           ${TEST_WORKLOAD_ID}     msg=TEST_WORKLOAD_ID is not set.
    ${workload_id}=         Set Variable            ${TEST_WORKLOAD_ID}
    ${response}=            Get workload            ${workload_id}          expected_status=404
    Log                     Workload ${workload_id} correctly not found (404 Not Found).

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
