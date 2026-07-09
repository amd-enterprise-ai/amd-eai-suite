# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for custom model copy workflow scenarios.
...                 Composes API-backed setup with UI interactions to verify
...                 copy behavior end-to-end from card action to user toast.
Resource            common/session.resource
Resource            pages/models_page.resource
Resource            resources/aiwb_custom_models.resource
Resource            resources/aiwb_common.resource
Library             Process


*** Keywords ***
User is on custom models tab
    [Documentation]    Navigates to the Custom Models tab for the selected project.

    Navigate to custom models page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]

A copyable custom model exists in the selected project
    [Documentation]    Seeds one custom model in the selected project by previewing
    ...                and onboarding a public repository, then records the model
    ...                resource name for later copy/delete actions.

    A custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Custom model preview response status should be "200"
    The previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Custom model onboard response status should be "204"
    Custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should exist in the namespace
    ${model_name}=    Get From Dictionary    ${CUSTOM_MODEL_AIM_CR}[metadata]    name
    VAR    ${TEST_COPY_SOURCE_MODEL_NAME}    ${model_name}    scope=TEST

User triggers make copy from the first custom model card
    [Documentation]    Captures the current card count, opens the card actions menu,
    ...                and clicks the "Make a copy" action.

    ${count}=    Get custom model card count
    VAR    ${TEST_CUSTOM_MODEL_COUNT_BEFORE_COPY}    ${count}    scope=TEST
    Click actions menu on first custom model card
    Click make copy action in custom model card menu

The copy success toast should be shown
    [Documentation]    Verifies the success toast shown after copy completes.

    Wait For Elements State    text="A copy of the model has been created."    visible    timeout=30s

Custom model card count should increase after copy
    [Documentation]    Polls until the custom-model card count grows by one.

    Wait Until Keyword Succeeds    30s    2s
    ...    Verify custom model card count incremented

Verify custom model card count incremented
    [Documentation]    Single-attempt assertion used by polling wrapper.

    ${current}=    Get custom model card count
    ${expected}=    Evaluate    int($TEST_CUSTOM_MODEL_COUNT_BEFORE_COPY) + 1
    Should Be Equal As Integers    ${current}    ${expected}

Source custom model is deleted before copy is attempted
    [Documentation]    Removes the source model CR after cards are visible to force
    ...                the subsequent copy action into a backend not-found path.

    ${namespace}=    Get Project Namespace
    ${result}=    Run Process
    ...    kubectl
    ...    -n
    ...    ${namespace}
    ...    delete
    ...    aimmodels.aim.eai.amd.com
    ...    ${TEST_COPY_SOURCE_MODEL_NAME}
    ...    --ignore-not-found
    Should Be Equal As Integers    ${result.rc}    0

The copy failure toast should be shown
    [Documentation]    Verifies copy failure feedback is surfaced to the user.

    Wait For Elements State    text=Failed to make a copy.    visible    timeout=30s
