# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for the AIWB project dashboard page.
...
...                 These tests verify the dashboard layout, stats display, GPU usage charts,
...                 workloads table, and project switching behavior. The dashboard is the
...                 project landing page shown at /${project}/.
...
...                 Suite Efficiency Design:
...                 Uses Suite Teardown for project cleanup. Each test handles its own
...                 preconditions via Given steps and creates isolated browser sessions.

# UI resources (feature layer + browser setup)
Resource            resources/common/browser_setup.resource
Resource            resources/dashboard.resource

# API resources (infrastructure preconditions, resolved via pythonpath)
Resource            resources/airm_projects.resource

Suite Teardown      Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
# =============================================================================
# Dashboard Layout (EAI-2374)
# =============================================================================

Dashboard displays overview and workloads sections
    [Documentation]    Verify that the project dashboard loads and displays the two main
    ...                content sections: the Overview area with stats and charts, and the
    ...                Workloads area with the workloads table.
    [Tags]    ui    dashboard    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on the dashboard page
    Then dashboard should display the overview section
    And dashboard should display the workloads section

# =============================================================================
# Dashboard Stats (EAI-2374)
# =============================================================================

Dashboard shows workload stats and counts
    [Documentation]    Verify that the dashboard displays the workloads stats card with
    ...                total count, GPU usage charts, time range selector, and the
    ...                workloads table.
    [Tags]    ui    dashboard    stats

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on the dashboard page
    Then dashboard should show workload stats card
    And dashboard should show total workloads count
    And dashboard should show GPU usage charts
    And dashboard should show time range selector
    And dashboard should show workloads table

# =============================================================================
# Project Navigation (EAI-2374)
# =============================================================================

Switching projects updates dashboard content
    [Documentation]    Verify that switching between projects via the project selector
    ...                updates the dashboard to reflect the selected project's data.
    [Tags]    ui    dashboard    projects    navigation

    ${first_project}=    Test Name    testing
    ${second_project}=    Test Name    testing-2
    Given a ready project "${first_project}" with user access exists
    And a ready project "${second_project}" with user access exists
    And user is logged in
    And project "${second_project}" is selected
    And user is on the dashboard page
    When user switches to project "${first_project}"
    Then dashboard should reflect project "${first_project}"
    And dashboard should display the overview section
    And dashboard should display the workloads section
