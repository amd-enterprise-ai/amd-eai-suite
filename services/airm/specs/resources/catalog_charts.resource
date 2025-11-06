# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level chart testing keywords.
...                 Provides business-logic level keywords for testing chart operations.
...                 Uses the low-level API keywords from api/charts.resource to implement
...                 higher-level testing scenarios.
Resource            api/charts.resource
Resource            catalog_projects.resource
Resource            test_data.resource
Library             String
Library             uuid


*** Variables ***
${TEMPLATE_FILE}        ${CURDIR}/../../workloads/templates/deployment.yaml
${VALUES_FILE}          ${CURDIR}/../../workloads/values.yaml
${SCHEMA_FILE}          ${CURDIR}/../../workloads/schema.yaml
${TEST_CHART_ID}        ${None}
${TEST_CHART_NAME}      ${None}
${TEST_CHART_DATA}      ${None}
@{CREATED_CHART_IDS}    # List to track created chart IDs for cleanup


*** Keywords ***
Valid chart data is prepared
    [Documentation]    Creates chart data with valid test values and cleans up any existing chart with same name
    [Arguments]             ${chart_name}=test-chart-id                     ${chart_type}=INFERENCE
    # Ensure we have a project to work with
    Project exists in system

    ${test_chart_name}=     Set Variable            ${chart_name}
    Set Test Variable       ${TEST_CHART_NAME}      ${test_chart_name}

    # Try to find and delete existing chart with same name
    ${chart_id}=            Find chart ID by name                           ${test_chart_name}      TEST_CHART_ID
    IF    $chart_id is not None
        Log                     Found existing chart with name ${test_chart_name}, deleting it first
        ${response}=            Delete chart            ${chart_id}             expected_status=204
    END

    &{chart_data}=          Create Dictionary       name=${test_chart_name}                         type=${chart_type}      project_id=${CURRENT_PROJECT_ID}
    Set Test Variable       ${TEST_CHART_DATA}      ${chart_data}

Finetuning chart exists
    Required chart files exist
    Valid chart data is prepared                    chart_name=llm-finetune-silogen-engine          chart_type=FINE_TUNING
    Create chart request is sent
    Response status should be 201  # API returns 201 Created for charts, which is correct
    Chart should exist in database

Chart name should match expected
    [Documentation]    Verifies chart name matches expected value
    [Arguments]             ${expected_name}        ${response}
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 name
    ${actual_name}=         Get From Dictionary     ${json}                 name
    Should Be Equal         $actual_name            $expected_name          msg=Chart response does not contain expected name '$expected_name'

Chart should exist in database
    [Documentation]    Verifies the created chart exists in database and is ready for use
    ${chart_id}=            Set Variable            ${TEST_CHART_ID}
    Get chart               ${chart_id}             expected_status=200

The chart should not exist in database
    [Documentation]    Verifies the chart no longer exists in database
    ${chart_id}=            Set Variable            ${TEST_CHART_ID}

    ${chart}=               Get chart               ${chart_id}             expected_status=404
    Log                     Chart ${chart_id} does not exist in database (404 Not Found) as expected

A chart exists
    [Documentation]    Creates a new chart and stores its ID as a test variable
    Valid chart data is prepared
    Create chart request is sent

    # Accept 201 as success for chart creation (201 is the expected status for resource creation)
    Response status should be 201

    # Extract chart ID as a test variable to ensure test independence
    ${json}=                Set Variable            ${response.json()}

    # Try to get direct ID first
    ${has_direct_id}=       Run Keyword And Return Status                   Dictionary Should Contain Key                   ${json}                 id

    IF    ${has_direct_id}
        ${chart_id}=            Get from dictionary     ${json}                 id
        Set test variable       ${TEST_CHART_ID}        ${chart_id}
        Log                     Using chart ID: ${chart_id}
    ELSE
        # Try to get it from charts array
        Dictionary Should Contain Key                   ${json}                 charts                  Chart response does not contain either direct ID or charts array
        ${charts}=              Get from dictionary     ${json}                 charts
        @{charts_list}=         Convert to list         ${charts}
        Should not be empty     ${charts_list}          Charts array is empty, cannot extract chart ID
        ${chart}=               Get from list           ${charts_list}          0
        Dictionary Should Contain Key                   ${chart}                id                      First chart in array does not contain ID
        ${chart_id}=            Get from dictionary     ${chart}                id
        Set test variable       ${TEST_CHART_ID}        ${chart_id}
        Log                     Using chart ID from charts array: ${chart_id}
    END

    # Verify chart was actually created by making a separate verification call
    ${verify_response}=     Get chart               ${TEST_CHART_ID}        expected_status=200

A job chart exists
    [Documentation]    Ensures a job chart exists in the system and stores its ID
    # Check if TEST_JOB_CHART_ID exists AND has a valid value
    ${is_empty}=            Run Keyword And Return Status                   Evaluate                "${TEST_JOB_CHART_ID}" == "${None}" or "${TEST_JOB_CHART_ID}" == ""

    IF    ${is_empty}
        # We need to set up the job test chart
        Setup job test chart
    END

    # Set TEST_CHART_ID to the job chart ID for consistency
    Set Test Variable       ${TEST_CHART_ID}        ${TEST_JOB_CHART_ID}

    # Log the chart ID for debugging
    Log                     Job chart exists with ID: ${TEST_CHART_ID}

A service chart exists
    [Documentation]    Ensures a service chart exists in the system and stores its ID
    # Check if TEST_SERVICE_CHART_ID exists AND has a valid value
    ${is_empty}=            Run Keyword And Return Status                   Evaluate                "${TEST_SERVICE_CHART_ID}" == "${None}" or "${TEST_SERVICE_CHART_ID}" == ""

    IF    ${is_empty}
        # We need to set up the service test chart
        Setup service test chart
    END

    # Set TEST_CHART_ID to the service chart ID for consistency
    Set Test Variable       ${TEST_CHART_ID}        ${TEST_SERVICE_CHART_ID}

    # Log the chart ID for debugging
    Log                     Service chart exists with ID: ${TEST_CHART_ID}

Required chart files exist
    [Documentation]    Verifies required chart files exist
    File should exist       ${TEMPLATE_FILE}        Template file does not exist
    File should exist       ${VALUES_FILE}          Values file does not exist
    File should exist       ${SCHEMA_FILE}          Schema file does not exist

A chart does not exist
    [Documentation]    Sets up a non-existent chart ID for testing
    ${chart_id}=            Evaluate                str(uuid.uuid4())       modules=uuid
    Set test variable       ${TEST_CHART_ID}        ${chart_id}

Find chart ID by name
    [Documentation]    Find chart ID by chart name through API and set as variable
    [Arguments]             ${chart_name}           ${variable_name}=TEST_CHART_ID
    Create API Session
    ${endpoint}=            Charts endpoint
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             expected_status=200

    ${json}=                Set Variable            ${response.json()}

    # Handle different response formats (direct list or object with charts property)
    @{charts}=              Run Keyword If
    ...                     $json.__class__.__name__ == 'list'              Set Variable            ${json}
    ...                     ELSE                    Get From Dictionary     ${json}                 charts                  default=@{EMPTY}

    FOR    ${chart}    IN    @{charts}
        ${name}=                Get From Dictionary     ${chart}                name                    default=${None}
        IF    "${name}" == "${chart_name}"
            ${chart_id}=            Get From Dictionary     ${chart}                id
            Set Test Variable       ${${variable_name}}     ${chart_id}
            RETURN                  ${chart_id}
        END
    END

    RETURN                  ${None}

Initialize Chart Tracking
    [Documentation]    Resets the list of created charts
    ...    This keyword should be used in a test suite setup to ensure
    ...    the tracking list starts empty for each test suite
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_CHART_IDS}    ${empty_list}
    Log                     Chart tracking initialized. CREATED_CHART_IDS: ${CREATED_CHART_IDS}     level=DEBUG

Register Chart For Cleanup
    [Documentation]    Manually registers a chart ID to be cleaned up later
    ...    Useful when charts are created through methods that don't
    ...    automatically track them in the CREATED_CHART_IDS list
    [Arguments]             ${chart_id}
    Append To List          ${CREATED_CHART_IDS}    ${chart_id}
    Log                     Manually added chart ${chart_id} to cleanup list: ${CREATED_CHART_IDS}                          level=DEBUG

Clean Up All Created Charts
    [Documentation]    Deletes all charts created during test execution
    ...    This keyword should be used in a test suite teardown to ensure
    ...    all charts created during testing are cleaned up properly.
    ${count}=               Get Length              ${CREATED_CHART_IDS}

    # Skip if no charts were created or list is empty
    Return From Keyword If                          ${count} == 0           No charts to clean up
    Log                     Cleaning up ${count} charts: ${CREATED_CHART_IDS}                       level=INFO

    # Delete each chart individually
    FOR    ${chart_id}    IN    @{CREATED_CHART_IDS}
        TRY
            Log                     Deleting chart ${chart_id}                      level=INFO
            Delete chart            ${chart_id}             expected_status=any
            Log                     Successfully deleted chart ${chart_id}          level=INFO
        EXCEPT    AS    ${error}
            Log                     Failed to delete chart ${chart_id}: ${error}    level=WARN
        END
    END

    # Reset the list of created charts
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_CHART_IDS}    ${empty_list}
    Log                     Chart cleanup complete. CREATED_CHART_IDS reset to: ${CREATED_CHART_IDS}                        level=INFO
