# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for fine-tuning drawer UI features.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Library             Collections
Resource            common/session.resource
Resource            pages/models_page.resource
Resource            resources/airm_clusters.resource


*** Keywords ***
# =============================================================================
# Given keywords (preconditions)
# =============================================================================

A cluster with no GPU hardware exists
    [Documentation]    Skips the test if the cluster has GPU hardware. Fine-tuning recipes
    ...    are filtered by GPU compatibility, so the empty-state message only appears on
    ...    CPU-only clusters where no recipes match the available hardware.
    ${gpu_count}=    Get cluster GPU capacity
    Skip If    ${gpu_count} > 0    Cluster has ${gpu_count} GPUs — recipes will match, empty state not expected

Test project is selected
    [Documentation]    Selects the current test project via the toolbar.
    ...                Extracts the project name from TEST_PROJECT and selects it via the toolbar.

    Project "${TEST_PROJECT}[name]" is selected

User is on custom models page
    [Documentation]    Navigates to the Custom Models tab on the models page.
    ...                Expects ${UI_BASE_URL} and ${TEST_PROJECT} to be set.

    Navigate to custom models page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]

# =============================================================================
# When keywords (actions)
# =============================================================================

User opens fine-tuning drawer
    [Documentation]    Clicks the Fine-tune button to open the fine-tuning drawer.

    Open finetune drawer

User opens the base model selector
    [Documentation]    Clicks the base model select to expand the option list.

    Click base model select

User selects the first compatible recipe
    [Documentation]    Opens the base model dropdown and selects the first listed recipe.
    ...                Skips when the cluster has no GPU-compatible recipes.

    Click base model select
    TRY
        Wait Until Keyword Succeeds    30s    500ms    Base model options should be non-empty
    EXCEPT
        Skip    No GPU-compatible fine-tuning recipes available for this cluster
    END
    Click first base model option

# =============================================================================
# Then keywords (verification)
# =============================================================================

Compatible fine-tuning recipes should be listed with hardware names
    [Documentation]    Verifies the base model dropdown contains options and that each option
    ...    displays a non-empty hardware name below the model name.
    ...    Polls for async load; skips gracefully if no compatible recipes exist for this cluster.

    TRY
        Wait Until Keyword Succeeds    30s    500ms    Base model options should be non-empty
    EXCEPT
        Skip    No GPU-compatible fine-tuning recipes available for this cluster
    END

    # Each option shows the model name on the first line and compatible hardware on the second.
    ${count}=    Get base model option count
    FOR    ${i}    IN RANGE    ${count}
        ${text}=    Get base model option text    ${i}
        ${lines}=    Evaluate    [l.strip() for l in '''${text}'''.split('\\n') if l.strip()]
        Should Be True    len($lines) >= 2
        ...    msg=Base model option ${i} should display a hardware name description below the model name
        Should Not Be Empty    ${lines}[1]
        ...    msg=Hardware name description should not be empty for base model option ${i}
    END

Each base model should appear at most once in the recipe list
    [Documentation]    Verifies no model name appears more than once in the base model dropdown.
    ...    A duplicate would mean an incompatible hardware variant was not filtered out
    ...    for the cluster's GPU type. Polls for async load; skips if no recipes available.

    TRY
        Wait Until Keyword Succeeds    30s    500ms    Base model options should be non-empty
    EXCEPT
        Skip    No GPU-compatible fine-tuning recipes available for this cluster
    END

    ${count}=    Get base model option count
    VAR    @{seen_names}
    FOR    ${i}    IN RANGE    ${count}
        ${text}=    Get base model option text    ${i}
        ${name}=    Evaluate    '''${text}'''.split('\\n')[0].strip()
        Should Not Contain    ${seen_names}    ${name}
        ...    msg=Model '${name}' appears more than once — incompatible hardware variant not filtered
        Append To List    ${seen_names}    ${name}
    END

Fine-tuning drawer should show no compatible recipes message
    [Documentation]    Verifies the base model select shows a message that no fine-tuning
    ...    recipes are available for the cluster's GPU hardware.

    Base model select should show empty state

The batch size input should be locked until a recipe is chosen
    [Documentation]    Verifies the batch size input is disabled before any recipe
    ...                is selected. The form gates the field on recipe selection so
    ...                the GPU-count-derived constraints can be applied to a known
    ...                recipe (EAI-5822).

    Open advanced fine-tuning settings
    Batch size input should be disabled

The batch size input should require multiples of the recipe's GPU count
    [Documentation]    Verifies the batch size input enforces the recipe's GPU count
    ...                as both its minimum value and its step — preventing users from
    ...                submitting batch sizes that would silently crash the workload
    ...                (EAI-5822).
    ...
    ...                Verified behaviorally by clicking the + stepper twice from the
    ...                empty initial state: the first click sets the value to the
    ...                recipe's GPU count (the minimum), and the second click adds
    ...                another GPU-count's worth (the step). Reading the DOM directly
    ...                wouldn't work — react-aria's NumberField uses `type="text"` and
    ...                exposes no `min`/`step`/`aria-valuemin` attributes on the input.
    ...
    ...                Skips when the selected recipe uses a single GPU (first
    ...                increment ≤ 1), since any positive integer is a valid multiple
    ...                of 1 and the constraint is not testable.

    Open advanced fine-tuning settings
    Batch size input should be enabled

    Click batch size increment button
    ${gpu_count}=    Get batch size value
    Skip If    ${gpu_count} <= 1
    ...    Selected recipe uses ${gpu_count} GPU; multiple-of constraint does not apply

    Click batch size increment button
    ${after_step}=    Get batch size value
    ${expected}=    Evaluate    ${gpu_count} * 2
    Should Be Equal As Integers    ${after_step}    ${expected}
    ...    msg=Stepper should add the recipe's GPU count (${gpu_count}) per click; expected ${expected}, got ${after_step}
