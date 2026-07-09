# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for custom model copy workflow.
...                 Verifies the card action creates a copied model on success
...                 and shows an error toast when the source no longer exists.

Resource            resources/common/browser_setup.resource
Resource            resources/custom_model_copy.resource
Resource            resources/airm_projects.resource

Suite Teardown      Run Keywords    Clean Up All Created Custom Models    AND    Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
Custom model copy creates a new card
    [Documentation]    Verify that making a copy from a custom model card succeeds
    ...                and the models grid shows one additional card.
    [Tags]    ui    models    custom-models    copy    skip

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And a copyable custom model exists in the selected project
    And user is on custom models tab
    When user triggers make copy from the first custom model card
    Then the copy success toast should be shown
    And custom model card count should increase after copy

Copy reports an error when the source model is removed
    [Documentation]    Verify that the copy action surfaces a failure toast when
    ...                the source model disappears before copy is submitted.
    [Tags]    ui    models    custom-models    copy    skip    negative

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And a copyable custom model exists in the selected project
    And user is on custom models tab
    And source custom model is deleted before copy is attempted
    When user triggers make copy from the first custom model card
    Then the copy failure toast should be shown
