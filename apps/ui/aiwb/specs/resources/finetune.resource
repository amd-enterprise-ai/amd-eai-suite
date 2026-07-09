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
Library             String
Library             Process
Resource            common/session.resource
Resource            pages/models_page.resource
Resource            resources/airm_clusters.resource
Resource            resources/airm_projects.resource
Resource            resources/aiwb_common.resource
Resource            resources/aiwb_models.resource
Resource            resources/aiwb_aims.resource


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

A completed fine-tuned model exists for the test project
    [Documentation]    Creates a minimal AIMModel CR and patches its status to Ready,
    ...    so the UI treats the row as Complete and displays the Fine-tune row action.
    ...    Delegates to the API resource keyword to avoid duplication and drift.
    A completed fine-tuned model exists in the namespace

More fine-tuned models exist in the namespace than fit a single page
    [Documentation]    Seeds enough AIMModel CRs to force at least two pages at the default
    ...                page size (10). Uses kubectl so no GPU is required — the CRs share the
    ...                same shape the UI consumes from the live cluster.
    ...                Idempotent across re-runs: kubectl apply patches existing CRs in place.
    ${namespace}=    Get Project Namespace
    Apply Multiple Dummy AIMModel CRs    ${namespace}    12

Test project is selected
    [Documentation]    Selects the current test project via the toolbar.
    ...                Extracts the project name from TEST_PROJECT and selects it via the toolbar.

    Project "${TEST_PROJECT}[name]" is selected

User is on fine-tune models page
    [Documentation]    Navigates to the Fine-tune Models tab on the models page.
    ...                Expects ${UI_BASE_URL} and ${TEST_PROJECT} to be set.
    ...                EAI-6124 moved the fine-tune table off the Custom Models
    ...                tab into its own tab; scenarios that used to navigate to
    ...                "user is on custom models page" should now use this.

    Navigate to fine-tune models page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]

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

User selects a gated base model
    [Documentation]    Opens the base model dropdown and selects the first recipe whose
    ...                hfTokenRequired flag is true in the finetunable catalog API.
    ...                Skips when no gated recipes are available on the cluster.

    ${response}=    Get finetunable models    expected_status=200
    VAR    ${models}    ${response.json()["data"]}
    VAR    ${gated_name}    ${None}
    FOR    ${m}    IN    @{models}
        IF    $m.get("hfTokenRequired") is True
            VAR    ${gated_name}    ${m["canonicalName"]}
            BREAK
        END
    END
    Skip If    $gated_name is None    No gated fine-tuning recipes available on this cluster
    Click base model select
    Wait Until Keyword Succeeds    10s    500ms    Base model options should be non-empty
    Click base model option with name    ${gated_name}

User selects a non-gated base model
    [Documentation]    Opens the base model dropdown and selects the first recipe whose
    ...                hfTokenRequired flag is explicitly false in the finetunable catalog API.
    ...                Skips when no non-gated recipes are available on the cluster.

    ${response}=    Get finetunable models    expected_status=200
    VAR    ${models}    ${response.json()["data"]}
    VAR    ${non_gated_name}    ${None}
    FOR    ${m}    IN    @{models}
        IF    $m.get("hfTokenRequired") is False
            VAR    ${non_gated_name}    ${m["canonicalName"]}
            BREAK
        END
    END
    Skip If    $non_gated_name is None    No non-gated fine-tuning recipes available on this cluster
    Click base model select
    Wait Until Keyword Succeeds    10s    500ms    Base model options should be non-empty
    Click base model option with name    ${non_gated_name}

# =============================================================================
# Then keywords (verification)
# =============================================================================

The HuggingFace token section should be visible
    [Documentation]    Verifies the Hugging Face Authentication section is shown in the drawer.
    ...                The section is mounted only when the selected base model is gated.

    HF token section should be present

The HuggingFace token section should not be visible
    [Documentation]    Verifies the Hugging Face Authentication section is absent from the drawer.
    ...                The section is unmounted when the selected base model is not gated.

    HF token section should not be present

Submitting the form without a token should be blocked
    [Documentation]    Fills in the display name, clicks the confirm button, and verifies the
    ...                drawer remains open with the HF token section still visible — proving
    ...                that the missing HF token (not an unrelated validation error) blocked
    ...                form submission.

    ${suffix}=    Generate Random String    8    [LOWER][NUMBERS]
    Fill finetune display name    test-hf-${suffix}
    Click finetune confirm button
    HF token section should be present

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
# =============================================================================
# Keywords for fine-tuning from completed model row action
# =============================================================================

User opens fine-tune action on the completed model row
    [Documentation]    Finds the completed model row in the custom models table, opens its row
    ...    actions menu, and clicks the Fine-tune option.

    Open fine-tune action from model row    ${TEST_MODEL_NAME}

The user can submit the fine-tuning form without a token
    [Documentation]    Fills in the display name and submits the drawer for a re-fine-tuned
    ...                source, then confirms the HuggingFace token section never appears —
    ...                the source keeps its weights in project storage, so no token is
    ...                requested and the submission is not gated on one.

    Wait For Elements State    ${BASE_MODEL_SELECT_SELECTOR}    visible    timeout=15s
    ${suffix}=    Generate Random String    8    [LOWER][NUMBERS]
    Fill finetune display name    refinetune-${suffix}
    Click finetune confirm button
    HF token section should not be present

Fine-tuning drawer should be open
    [Documentation]    Verifies the fine-tuning drawer is visible (base model select is shown).

    Wait For Elements State    ${BASE_MODEL_SELECT_SELECTOR}    visible    timeout=15s

The base model selector should be locked to the completed model
    [Documentation]    Verifies the base model selector is disabled and shows the completed
    ...    model's name, proving the row action pre-selected the correct model rather than
    ...    locking on an unrelated state (e.g., no-recipes lock).

    Wait For Elements State    ${BASE_MODEL_SELECT_SELECTOR}    disabled    timeout=10s
    ${selector_text}=    Get Text    ${BASE_MODEL_SELECT_SELECTOR}
    Should Contain    ${selector_text}    ${TEST_MODEL_NAME}
    ...    msg=Base model selector should show the completed model name but shows: ${selector_text}

# =============================================================================
# Keywords for paginated fine-tune models table
# =============================================================================

The fine-tune models table shows the first page of fine-tuned models
    [Documentation]    Verifies the table renders only one page worth of rows on initial load,
    ...                proving the UI consumed the paginated envelope and did not eagerly fetch
    ...                every fine-tuned model. Default page size is 10.
    Wait for fine-tune models table to load
    ${row_count}=    Get fine-tune models row count
    Should Be True    ${row_count} <= 10
    ...    msg=Expected at most 10 rows on the first page; got ${row_count}
    # Remember the first row's text so the next-page assertion can prove the page changed.
    ${first_row_text}=    Get fine-tune models first row text
    VAR    ${PAGE_1_FIRST_ROW_TEXT}    ${first_row_text}    scope=TEST

Pagination controls are visible on the fine-tune models table
    [Documentation]    Verifies the pagination component is rendered. It only appears when
    ...                the total count exceeds the page size, so this implicitly checks
    ...                that the UI received pagination metadata from the envelope.
    Wait for fine-tune models pagination controls

User navigates to the next page of fine-tune models
    [Documentation]    Clicks the next-page control on the pagination component, triggering
    ...                a new fetch for page 2.
    Click fine-tune models next page button

The fine-tune models table shows the next page of fine-tuned models
    [Documentation]    Verifies that navigating to page 2 changed the rendered set — the first
    ...                row's text must differ from what was shown on page 1.
    Wait for fine-tune models table to load
    Wait Until Keyword Succeeds    10s    500ms    Fine-tune models first row should differ from page 1

Fine-tune models first row should differ from page 1
    [Documentation]    Single-poll check used by Wait Until Keyword Succeeds. Fails when the
    ...                first row text still matches the text captured on page 1.
    ${current}=    Get fine-tune models first row text
    Should Not Be Equal    ${current}    ${PAGE_1_FIRST_ROW_TEXT}
    ...    msg=First row on page 2 should differ from page 1 (${PAGE_1_FIRST_ROW_TEXT})

# =============================================================================
# Keywords for custom-model deploy drawer
# =============================================================================

User opens the deploy drawer for the custom model
    [Documentation]    Finds the ready custom model's row in the fine-tune models table,
    ...                opens its row actions menu, and clicks the Deploy option.
    ...                Returns after the menu action; scenarios should assert drawer
    ...                visibility in Then steps (e.g. ``Wait for custom model deploy drawer``).
    ...                Requires: TEST_MODEL_NAME (set by "A completed fine-tuned model exists for the test project")

    Open deploy action from model row    ${TEST_MODEL_NAME}

The deploy drawer should show the custom model's details
    [Documentation]    Verifies the deploy drawer header shows the custom model name
    ...                and the namespace (deploy target) so the user knows which model
    ...                and where it will be deployed.
    ...                Requires: TEST_MODEL_NAME

    Wait for custom model deploy drawer
    Deploy drawer header should show model name    ${TEST_MODEL_NAME}
    Deploy drawer header should show namespace

The deploy drawer should offer a deployment name and autoscaling
    [Documentation]    Verifies the deploy drawer contains the deployment-name input
    ...                and the autoscaling toggle — the two primary user-controlled
    ...                settings in the custom deploy drawer.

    Deploy drawer should show display name input
    Deploy drawer should show autoscaling toggle

User deploys the model with default settings
    [Documentation]    Submits the deploy drawer without modifying any field,
    ...                accepting all default values (empty display name, autoscaling off).
    ...                Waits for the drawer to close, which signals the deploy mutation
    ...                completed successfully and the success toast was shown.

    Submit custom model deploy drawer
    Wait Until Keyword Succeeds    30s    2s    Custom model deploy drawer should be closed

A deployment for the custom model should exist in the project
    [Documentation]    Verifies via the AIWB API that an AIMService CR was created in
    ...                the project namespace referencing the fine-tuned model.
    ...                Polls to tolerate the short lag between UI form submit and K8s
    ...                reconciliation.
    ...                Requires: TEST_MODEL_NAME

    Wait Until Keyword Succeeds    2 min    10s
    ...    AIMService should reference model    ${TEST_MODEL_NAME}

The deployed model should be ready to chat
    [Documentation]    Verifies the AIMService created from the custom model appears in
    ...                the AIWB inference list filtered to chat-capable deployments.
    ...                Polls until the service is chat-accessible (requires GPU — the
    ...                service must be Running before it surfaces in the chat filter).
    ...                Requires: TEST_AIM_ID (set by "A deployment for the custom model should exist in the project")

    Wait Until Keyword Succeeds    30 min    30s
    ...    Deployed fine-tuned model should be accessible for inference

AIMService should reference model
    [Documentation]    Single-poll check used by Wait Until Keyword Succeeds.
    ...                Searches the AIM services list for an entry whose spec.model.name
    ...                matches the expected fine-tuned model resource name, then stores
    ...                the AIMService ID in TEST_AIM_ID for subsequent steps.
    [Arguments]    ${model_resource_name}
    ${namespace}=    Get Project Namespace
    ${existing}=    Find Existing Fine-Tuned AIM Service    ${namespace}    ${model_resource_name}
    Should Not Be Equal    ${existing}    ${None}
    ...    msg=No AIMService found referencing fine-tuned model '${model_resource_name}' in namespace ${namespace}
    ${service_id}=    Get From Dictionary    ${existing}    id
    VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST
    Log    AIMService ${service_id} found for model ${model_resource_name}    INFO
