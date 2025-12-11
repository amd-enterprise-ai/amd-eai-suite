# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level chart testing keywords.
...                 Provides business-logic level keywords for testing chart operations.
...                 Uses the low-level API keywords from api/charts.resource to implement
...                 higher-level testing scenarios.
Resource            api/charts.resource
Resource            airm_projects.resource
Resource            test_data.resource
Resource            common/resource_tracking.resource
Library             String
Library             uuid


*** Variables ***
${TEMPLATE_FILE}        ${CURDIR}/../../workloads/templates/deployment.yaml
${VALUES_FILE}          ${CURDIR}/../../workloads/values.yaml
${SCHEMA_FILE}          ${CURDIR}/../../workloads/schema.yaml
${SIGNATURE_FILE}       ${CURDIR}/../test_data/charts/signature.yaml
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
        Log                     Found existing chart with name ${test_chart_name}, deleting it first                         DEBUG
        ${response}=            Delete chart            ${chart_id}             expected_status=204
    END

    &{chart_data}=          Create Dictionary       name=${test_chart_name}                         type=${chart_type}      project_id=${TEST_PROJECT_ID}
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
    Log                     Chart ${chart_id} does not exist in database (404 Not Found) as expected              DEBUG

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
        Log                     Using chart ID: ${chart_id}                     DEBUG
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
        Log                     Using chart ID from charts array: ${chart_id}                   DEBUG
    END

    # Verify chart was actually created by making a separate verification call
    ${verify_response}=     Get chart               ${TEST_CHART_ID}        expected_status=200

A chart exists without files
    [Documentation]    Creates a new chart via API without template files and stores its ID
    ...    This is the preferred method for workload API tests that don't need actual chart templates
    Valid chart data is prepared

    # Create chart using the file-less API keyword
    ${response}=            Create chart without files    ${TEST_CHART_NAME}    INFERENCE

    # Accept 201 as success for chart creation
    Should Be Equal As Integers    ${response.status_code}    201    msg=Chart creation failed: ${response.text}

    # Extract chart ID
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key    ${json}    id    msg=Chart response missing 'id' field
    ${chart_id}=            Get from dictionary     ${json}                 id
    Set test variable       ${TEST_CHART_ID}        ${chart_id}
    Log                     Created chart without files, ID: ${chart_id}    DEBUG

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

    Set Test Variable       ${TEST_CHART_ID}        ${TEST_JOB_CHART_ID}

    Log                     Job chart exists with ID: ${TEST_CHART_ID}      DEBUG

A service chart exists
    [Documentation]    Ensures a service chart exists in the system and stores its ID
    # Check if TEST_SERVICE_CHART_ID exists AND has a valid value
    ${is_empty}=            Run Keyword And Return Status                   Evaluate                "${TEST_SERVICE_CHART_ID}" == "${None}" or "${TEST_SERVICE_CHART_ID}" == ""

    IF    ${is_empty}
        # We need to set up the service test chart
        Setup service test chart
    END

    Set Test Variable       ${TEST_CHART_ID}        ${TEST_SERVICE_CHART_ID}

    Log                     Service chart exists with ID: ${TEST_CHART_ID}                  DEBUG

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
    Create api session
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

# Initialize Chart Tracking is now imported from common/resource_tracking.resource
# Clean Up All Created Charts is now imported from common/resource_tracking.resource

Register Chart For Cleanup
    [Documentation]    Manually registers a chart ID to be cleaned up later
    ...    Useful when charts are created through methods that don't
    ...    automatically track them in the CREATED_CHART_IDS list
    [Arguments]             ${chart_id}
    Append To List          ${CREATED_CHART_IDS}    ${chart_id}
    Log                     Manually added chart ${chart_id} to cleanup list: ${CREATED_CHART_IDS}                          level=DEBUG
