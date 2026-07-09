# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for custom model list and card view scenarios.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)

Resource            common/session.resource
Resource            pages/models_page.resource
Resource            resources/aiwb_custom_models.resource


*** Keywords ***
# =============================================================================
# Given keywords (preconditions)
# =============================================================================

User is on the custom models tab
    [Documentation]    Navigates to the Custom Models tab of the models page.
    ...                Expects ${UI_BASE_URL} and ${TEST_PROJECT} to be set.

    Navigate to custom models page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]

A custom model with display name "${name}" is imported into the project
    [Documentation]    Onboards the public test fixture via the API with a user-supplied
    ...                display name so UI assertions can use a known, predictable label.

    A custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Custom model preview response status should be "200"
    The previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}" overriding display name to "${name}"
    Custom model onboard response status should be "204"

# =============================================================================
# Then keywords (verification)
# =============================================================================

The custom models empty state should be shown
    [Documentation]    Confirms the empty-state placeholder is visible when the project
    ...                has no imported custom models. This is the starting state for a
    ...                fresh project before any import has been initiated.

    Custom models empty state should be visible

A custom model card with display name "${name}" should be shown
    [Documentation]    Confirms a card carrying the given display name is visible in the
    ...                list, verifying that the UI reflects the label set at import time.

    Custom model card with text "${name}" should be visible
