# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for the API key metrics dashboard.
...
...                 Tests cover navigation to the metrics page, stat card visibility,
...                 chart section display, and time range selection. Each test creates
...                 its own API key via the AIWB API to obtain a key ID for direct
...                 URL navigation (the metrics page has no sidebar link).

# UI resources (feature layer + browser setup)
Resource            resources/common/browser_setup.resource
Resource            resources/api_key_metrics.resource

# API resources (infrastructure preconditions, resolved via pythonpath)
Resource            resources/airm_projects.resource

Suite Setup         Initialize API Key Metrics Suite
Suite Teardown      Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
API key metrics page loads with expected elements
    [Documentation]    Verify that navigating to the API key metrics page shows the key name
    ...                in the header, the usage stat cards, and both chart sections.
    [Tags]    ui    api-keys    metrics    smoke

    Given a ready project with user access exists
    And an API key exists for the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    When user is on API key metrics page
    Then API key metrics page should be visible
    And stat cards should be visible on metrics page
    And chart sections should be visible on metrics page

Changing time range updates the selected tab
    [Documentation]    Verify that clicking the 7-day tab on the metrics page changes the
    ...                active selection in the time range selector.
    [Tags]    ui    api-keys    metrics

    Given a ready project with user access exists
    And an API key exists for the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on API key metrics page
    When user changes time range to 7 days
    Then 7 day time range should be selected
