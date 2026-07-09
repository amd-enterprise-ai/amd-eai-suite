# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for the custom model list view.
...
...                 Covers the empty state shown to users with no imports, and
...                 verification that the display name set at import time appears on
...                 the model card in the list.

Resource            resources/common/browser_setup.resource
Resource            resources/custom_model_list.resource
Resource            resources/airm_projects.resource

Suite Teardown      Run Keywords    Clean Up All Created Custom Models    AND    Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
Custom models tab shows an empty state for a project with no imports
    [Documentation]    A freshly created project that has never had a custom model
    ...                imported should display the empty-state placeholder rather
    ...                than an empty card grid — this distinguishes "nothing imported
    ...                yet" from a filtered result set that happens to be empty.
    [Tags]    ui    models    custom-models    list    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    When user is on the custom models tab
    Then the custom models empty state should be shown

Custom model card shows the display name set at import time
    [Documentation]    After onboarding a model with a user-supplied display name the
    ...                Custom Models tab must show a card carrying that exact label —
    ...                the UI reads the display-name annotation from the list response
    ...                and renders it as the card title.
    [Tags]    ui    models    custom-models    list    smoke

    Given a ready project with user access exists
    And a custom model with display name "List View Test Model" is imported into the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    When user is on the custom models tab
    Then a custom model card with display name "List View Test Model" should be shown
