# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for the Connect to model button on the AIM details page.
...
...                 Suite Teardown cleans up all created projects after the suite finishes. The test
...                 deploys an AIM as a precondition and verifies the Output card button opens the
...                 connection dialog.

# UI resources (feature layer + browser setup)
Resource            resources/common/browser_setup.resource
Resource            resources/workloads.resource

# API resources (infrastructure preconditions, resolved via pythonpath)
Resource            resources/aiwb_aims.resource
Resource            resources/airm_projects.resource

Suite Teardown      Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
Connection snippet is accessible from AIM details output card
    [Documentation]    Verifies that the model connection dialog is accessible directly from the
    ...                Output card on the AIM details page, without navigating to the models page.
    [Tags]    ui    aims    workloads    connect    gpu

    Given a ready project with user access exists
    And AIM is deployed and running
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on AIM details page
    When user clicks connect to model button
    Then connect to model dialog should be visible
    And connection snippet should target the served model id
