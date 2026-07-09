# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for custom model delete scenarios.
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

An onboarded custom model exists in the project
    [Documentation]    Previews and onboards the public test fixture so UI delete
    ...                scenarios have a model to work with.

    A custom model is onboarded in the project

# =============================================================================
# When keywords (actions)
# =============================================================================

User opens the delete action from the custom model card
    [Documentation]    Opens the card actions menu on the first visible model card
    ...                and selects "Delete" to open the confirmation modal.

    Click actions menu on first custom model card
    Click delete action in custom model card menu

User confirms the model deletion
    [Documentation]    Waits for the delete confirmation modal and clicks the confirm
    ...                button to proceed with the deletion.

    Wait for custom model delete confirmation modal
    Confirm model deletion in modal

User closes the delete confirmation modal
    [Documentation]    Waits for the delete confirmation modal and clicks the Close
    ...                button to dismiss it without deleting the model.

    Wait for custom model delete confirmation modal
    Close delete confirmation modal

# =============================================================================
# Then keywords (verification)
# =============================================================================

The model deletion success toast should be shown
    [Documentation]    Confirms the success feedback appears after a model is deleted.

    Wait for delete success toast

The custom model card should no longer be visible
    [Documentation]    Polls until all custom model cards have been removed from the
    ...                list, confirming the deleted model is no longer shown.

    Wait Until Keyword Succeeds    30s    3s
    ...    Custom model card should be absent

The custom model card should still be visible
    [Documentation]    Confirms the model card is still present after the delete
    ...                confirmation was dismissed without confirming.

    Wait For Elements State    ${CUSTOM_MODEL_CARD_SELECTOR}    visible    timeout=15s

The deleted model should no longer exist in the project
    [Documentation]    Polls the cluster via kubectl until the AIMModel CR is fully removed,
    ...                proving the delete reached the backend and was not just a UI rendering
    ...                artefact. Delegates to the API-layer keyword which polls for 60 seconds.

    The onboarded AIMModel should no longer exist in the namespace
