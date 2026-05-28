# Copyright (c) Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level overlay testing keywords.
...                 Provides business-logic level keywords for testing overlay operations.
...                 Uses the low-level API keywords from api/overlays.resource to implement
...                 higher-level testing scenarios.
Resource            api/overlays.resource
Resource            aiwb_charts.resource
Resource            resources/resource_tracking.resource
Library             Collections
Library             uuid
Library             OperatingSystem


*** Variables ***
${OVERLAY_FILE}             ${CURDIR}/../test_data/overlays/overlay.yaml
${OVERLAY_UPDATE_FILE}      ${CURDIR}/../test_data/overlays/overlay_update.yaml
${TEST_OVERLAY_ID}          ${None}
@{CREATED_OVERLAY_IDS}


*** Keywords ***
# --- Setup and Teardown ---

Initialize Overlay Test Environment
    [Documentation]    Creates a chart needed for overlay tests.
    ...    Sets TEST_CHART_ID for use as the parent chart in overlay operations.
    # Overlays require a chart to exist - create one for the suite
    Valid chart data is prepared
    Create chart request is sent

# --- Given keywords ---

Required overlay files exist
    [Documentation]    Verifies required overlay files exist on disk
    File Should Exist       ${OVERLAY_FILE}         Overlay file does not exist
    File Should Exist       ${OVERLAY_UPDATE_FILE}  Overlay update file does not exist

An overlay exists
    [Documentation]    Creates a new overlay and stores its ID as a test variable.
    ...    Requires TEST_CHART_ID to be set (from chart creation in setup).
    Create overlay request is sent
    Response status should be 201

An overlay does not exist
    [Documentation]    Sets up a non-existent overlay ID for negative testing
    ${overlay_id}=          Evaluate                str(uuid.uuid4())       modules=uuid
    Set Test Variable       ${TEST_OVERLAY_ID}      ${overlay_id}

Multiple overlays exist
    [Documentation]    Creates multiple overlays for listing tests
    FOR    ${i}    IN RANGE    3
        Create overlay request is sent
    END

# --- When keywords ---

Create overlay request is sent
    [Documentation]    Sends a request to create a new overlay and stores the ID.
    ...    Uses the current TEST_CHART_ID as the parent chart.
    [Arguments]             ${overlay_file}=${OVERLAY_FILE}     ${canonical_name}=${None}
    ${response}=            Create overlay request    ${TEST_CHART_ID}    ${overlay_file}    canonical_name=${canonical_name}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

    IF    ${response.status_code} in [200, 201]
        ${json}=                Set Variable            ${response.json()}
        ${overlay_id}=          Get From Dictionary     ${json}                 id
        Set Test Variable       ${TEST_OVERLAY_ID}      ${overlay_id}
        Append To List          ${CREATED_OVERLAY_IDS}  ${overlay_id}
        Log                     Added overlay ${overlay_id} to cleanup list     DEBUG
    END

List overlays request is sent
    [Documentation]    Sends a list overlays request and stores the response
    [Arguments]             ${chart_id}=${None}     ${canonical_name}=${None}
    ${response}=            List overlays request   chart_id=${chart_id}    canonical_name=${canonical_name}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

List overlays filtered by chart request is sent
    [Documentation]    Sends a list overlays request filtered by the current test chart.
    ...    Resolves the chart ID from test state automatically.
    ${response}=            List overlays request   chart_id=${TEST_CHART_ID}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

Get overlay request is sent
    [Documentation]    Sends a get overlay request for the current test overlay
    ${response}=            Get overlay             ${TEST_OVERLAY_ID}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

Update overlay request is sent
    [Documentation]    Sends an update overlay request with an updated file.
    ...    Note: chart_id must be re-sent on update because the API currently
    ...    treats omitted fields as null rather than preserving existing values.
    [Arguments]             ${overlay_file}=${OVERLAY_UPDATE_FILE}
    ${response}=            Update overlay request  ${TEST_OVERLAY_ID}      overlay_file=${overlay_file}    chart_id=${TEST_CHART_ID}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

Delete overlay request is sent
    [Documentation]    Sends a delete overlay request for the current test overlay
    ${response}=            Delete overlay          ${TEST_OVERLAY_ID}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

Batch delete overlays request is sent
    [Documentation]    Sends a batch delete request for all created overlay IDs.
    ...    Resolves overlay IDs from the tracking list automatically.
    ${response}=            Batch delete overlays request    ${CREATED_OVERLAY_IDS}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

# --- Then keywords ---

Overlay should exist in system
    [Documentation]    Verifies the created overlay exists by fetching it
    ${overlay_id}=          Set Variable            ${TEST_OVERLAY_ID}
    Get overlay             ${overlay_id}           expected_status=200

The overlay should not exist in system
    [Documentation]    Verifies the overlay no longer exists (expects 404)
    ${overlay_id}=          Set Variable            ${TEST_OVERLAY_ID}
    ${response}=            Get overlay             ${overlay_id}           expected_status=404
    Log                     Overlay ${overlay_id} does not exist (404) as expected    DEBUG

Response should contain overlay with chart ID
    [Documentation]    Verifies the response overlay has the expected chart ID
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    ${response_chart_id}=   Get From Dictionary     ${json}                 chartId
    Should Be Equal As Strings    ${response_chart_id}    ${TEST_CHART_ID}

Response data should not be empty
    [Documentation]    Verifies the response data list is not empty
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    ${data}=                Get From Dictionary     ${json}                 data
    ${count}=               Get Length              ${data}
    Should Be True          ${count} > 0            Expected non-empty data list but got ${count} items

# --- Cleanup ---

Clean Up All Created Overlays
    [Documentation]    Clean up all created overlay resources using generic pattern
    Generic Clean Up All Created Overlay

Clean Up Overlay Test Environment
    [Documentation]    Cleans up all overlays and charts created during tests.
    ...    Overlays must be deleted before charts due to foreign key constraints.
    Clean Up All Created Overlays
    Clean Up All Created Charts
