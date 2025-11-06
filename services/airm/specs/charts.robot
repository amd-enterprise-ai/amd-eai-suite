# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API charts endpoints.
...                 Verifies chart creation, listing and deletion operations.
Resource            resources/catalog_charts.resource
Library             OperatingSystem
Test Setup          Initialize Chart Tracking
Test Teardown       Clean Up All Created Charts


*** Variables ***
# Test file paths - using CURDIR for absolute paths
${TEMPLATE_FILE}    ${CURDIR}/test_data/charts/template.yaml
${VALUES_FILE}      ${CURDIR}/test_data/charts/values.yaml
${SCHEMA_FILE}      ${CURDIR}/test_data/charts/schema.json


*** Test Cases ***
Create new chart
    [Documentation]    Verify that a new chart can be created with required files
    [Tags]                  charts                  create                  smoke

    Given required chart files exist
    And valid chart data is prepared
    When create chart request is sent
    Then response status should be 201  # API returns 201 Created for charts, which is correct
    And chart should exist in database

List charts with pagination
    [Documentation]    Verify that charts can be listed with pagination
    ...    Prerequisites:
    ...    - Multiple test charts exist in database
    ...
    ...    Steps:
    ...    1. Request paginated list of charts
    ...    2. Verify pagination metadata
    ...    3. Verify response content structure
    ...    4. Verify total count meets minimum
    [Tags]                  charts                  list                    smoke

    Given catalog_keywords.Multiple charts exist
    When list charts request is sent
    ...                     page_number=1
    ...                     page_size=2
    Then response status should be 200
    And total count should be greater than 2

Delete existing chart
    [Documentation]    Verify that an existing chart can be deleted
    ...    Steps:
    ...    1. Create a test chart
    ...    2. Delete the chart
    ...    3. Verify deletion response
    ...    4. Verify chart no longer exists in database
    [Tags]                  charts                  delete

    Given a chart exists
    When delete chart request is sent
    Then response status should be 204  # HTTP 204 No Content is correct for successful deletion
    And the chart should not exist in database

Delete non-existent chart
    [Documentation]    Verify proper error when deleting non-existent chart
    ...    Steps:
    ...    1. Attempt to delete chart with invalid ID
    ...    2. Verify error response
    [Tags]                  charts                  delete                  negative

    Given a chart does not exist
    When delete chart request is sent
    Then response status should be 404
