# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for deleting a custom model.
...
...                 Covers the delete confirmation modal happy path (confirm → card removed)
...                 and the cancel path (close modal → card unchanged).

Resource            resources/common/browser_setup.resource
Resource            resources/custom_model_import.resource
Resource            resources/custom_model_delete.resource
Resource            resources/airm_projects.resource

Suite Teardown      Run Keywords    Clean Up All Created Custom Models    AND    Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
Deleting a custom model from the card confirms before removing it from the list
    [Documentation]    A user who triggers delete from the card actions menu and confirms
    ...                the modal should see a success toast, the card should disappear from
    ...                the Custom Models tab, and the model should be gone from the cluster.
    [Tags]    ui    models    custom-models    delete    smoke    kubectl

    Given a ready project with user access exists
    And an onboarded custom model exists in the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    When user opens the delete action from the custom model card
    And user confirms the model deletion
    Then the model deletion success toast should be shown
    And the custom model card should no longer be visible
    And the deleted model should no longer exist in the project

Closing the delete confirmation modal leaves the model card in place
    [Documentation]    A user who opens the delete menu and then closes the confirmation
    ...                modal without confirming should see the model card unchanged —
    ...                the cancel action must not trigger deletion.
    [Tags]    ui    models    custom-models    delete    smoke

    Given a ready project with user access exists
    And an onboarded custom model exists in the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    When user opens the delete action from the custom model card
    And user closes the delete confirmation modal
    Then the custom model card should still be visible
