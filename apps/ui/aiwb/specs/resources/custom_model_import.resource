# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for the custom model import wizard.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)

Library             Collections
Library             libraries/custom_model_import_network.py
Resource            common/session.resource
Resource            pages/models_page.resource
Resource            resources/aiwb_secrets.resource
Resource            resources/aiwb_custom_models.resource


*** Variables ***
# Same tiny public fixture repo as AIWB API custom-model E2Es (`aiwb_custom_models.resource`).
${CUSTOM_MODEL_IMPORT_PREVIEW_SOURCE}    hf-internal-testing/tiny-random-LlamaForCausalLM
# Gated repo — requires a valid HuggingFace token; used to exercise credential failure paths.
${CUSTOM_MODEL_IMPORT_GATED_SOURCE}      hf-internal-testing/dummy_gated_model


*** Keywords ***
# =============================================================================
# Given keywords (UI preconditions)
# =============================================================================

User is on custom models tab
    [Documentation]    Navigates to the Custom Models tab of the models page.
    ...                Expects ${UI_BASE_URL} and ${TEST_PROJECT} to be set.

    Navigate to custom models page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]

A custom model named "${display_name}" exists in the project
    [Documentation]    Seeds a minimal custom-model CR in the project namespace so the
    ...                import wizard's duplicate-name check has an existing name to match.

    Seed Custom Model With Display Name    duplicate-probe-model    ${display_name}    ${TEST_PROJECT}[name]
    Track Custom Model For Cleanup    ${TEST_PROJECT}[name]    duplicate-probe-model

User is on fine-tune models tab
    [Documentation]    Navigates to the Fine-tune Models tab of the models page.
    ...                Expects ${UI_BASE_URL} and ${TEST_PROJECT} to be set.

    Navigate to fine-tune models page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]

# =============================================================================
# When keywords (actions)
# =============================================================================

User opens the custom model import wizard
    [Documentation]    Clicks the "Import model" toolbar button to open the wizard.

    Click import model button
    Wait for import wizard page

User attempts to advance from the source step
    [Documentation]    Clicks the source step primary action (Preview model). Also used
    ...                after filling valid data to advance the wizard.

    Click import wizard next on source step

User advances from the information step
    [Documentation]    Clicks the information step's "Next" button to move to the runtime
    ...                profile step. Expects the wizard to already be on step 2.

    Click import wizard next on information step

User submits the import wizard
    [Documentation]    Clicks the final "Import model" submit button on the runtime profile
    ...                step. The wizard redirects to the custom models tab on success.

    Click import wizard submit

User enters source "${value}" in the import wizard
    [Documentation]    Types a Hugging Face source value into the source input.

    Fill import wizard source    ${value}

User enters display name "${value}" in the import wizard
    [Documentation]    Types a display name into the information step's display-name input.

    Fill import wizard display name    ${value}

User selects saved Hugging Face token by display name
    [Arguments]    ${display_name}
    [Documentation]    Picks an existing project Hugging Face token in the import wizard
    ...                using the label shown in the dropdown (the secret display name).

    Open project Hugging Face token dropdown
    Click Hugging Face token option labeled    ${display_name}

User cancels the import wizard
    [Documentation]    Cancels the wizard via the source step's Cancel button.

    Click import wizard cancel

User returns to the custom models list via the header back link
    [Documentation]    Navigates back to the Custom Models tab using the header
    ...                back link rendered above the wizard title.

    Click import wizard header back

User advances to the runtime profile step
    [Documentation]    From the information step, advances the wizard to the runtime profile
    ...                step and waits for it to render.

    Click import wizard next on information step
    Wait for runtime profile step

User sets runtime profile engine settings to "${engine_args_yaml}" and "${env_vars_yaml}"
    [Documentation]    Fills the runtime step's engine-arguments and environment-variables
    ...                YAML editors, the per-deployment runtime knobs the wizard collects.

    Fill runtime profile engine arguments    ${engine_args_yaml}
    Fill runtime profile environment variables    ${env_vars_yaml}

User saves the runtime profile and starts onboarding
    [Documentation]    Submits the wizard's runtime step to onboard the model with the
    ...                supplied runtime profile.

    Submit import wizard runtime step

# =============================================================================
# Then keywords (verification)
# =============================================================================

The import wizard should be open
    [Documentation]    Verifies the import wizard page is visible.

    Wait for import wizard page

The import wizard should show all three steps
    [Documentation]    Verifies the wizard renders the three-step stepper with the
    ...                expected step labels.

    Import wizard should show stepper labels

The import wizard should remain on the source step
    [Documentation]    Verifies the source step input is still visible — proving
    ...                the wizard did not advance after a failed validation.

    Import wizard source input should be visible

The duplicate display name warning should be shown
    [Documentation]    Verifies the wizard warns that the entered display name
    ...                matches an existing custom model, warning that saving may
    ...                overwrite that model's settings or be rejected.

    Import wizard duplicate name warning should be visible

The duplicate display name warning should not be shown
    [Documentation]    Verifies the wizard shows no duplicate-name warning when the
    ...                entered display name does not match an existing custom model.

    Import wizard duplicate name warning should be hidden

The custom models tab should be shown
    [Documentation]    Verifies the user is back on the Custom Models tab.

    Custom models tab should be visible

A custom model card should appear as importing or ready
    [Documentation]    Polls until at least one custom model card shows "Importing" or
    ...                "Ready" status, confirming the onboard API accepted the submission
    ...                and the list page reflects it.

    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Custom model card with importing or ready status should be visible

The import wizard should show a preview error
    [Documentation]    Verifies that a preview failure surfaces an error toast to the user.
    ...                The toast message starts with "Failed to preview model source" regardless
    ...                of the specific backend error appended after the prefix.

    Wait For Elements State    text=Failed to preview model source    visible    timeout=30s

The import model entry point should not be available
    [Documentation]    Verifies the "Import model" toolbar button is absent —
    ...                used to confirm the entry point lives on the Custom
    ...                Models tab only and not on adjacent tabs.

    Import model button should be absent

The custom model preview request should name the Hugging Face secret
    [Arguments]    ${preview_response}    ${expected_k8s_secret_name}
    [Documentation]    Verifies the browser's preview POST carried the Kubernetes secret
    ...                resource name as ``hfTokenSecretName`` (not the human display label).

    Should Be Equal As Integers    ${preview_response.status}    200
    ${request}=    Get From Dictionary    ${preview_response}    request
    Should Not Be Equal    ${request}    ${None}
    ${post}=    Get From Dictionary    ${request}    postData
    ${post_dict}=    Normalize Json Post Payload    ${post}
    Dictionary Should Contain Key    ${post_dict}    hfTokenSecretName
    ${actual}=    Get From Dictionary    ${post_dict}    hfTokenSecretName
    Should Be Equal    ${actual}    ${expected_k8s_secret_name}

The onboarded model should carry engine argument "${arg_key}" set to "${arg_value}"
    [Documentation]    Reads the onboarded AIMModel's persisted runtime overrides via the API to
    ...                prove the wizard's runtime profile values reached the backend, not just the
    ...                form. Polled because onboarding writes the CR asynchronously after submit.

    Wait Until Keyword Succeeds    90 sec    5 sec
    ...    Onboarded model overrides should carry engine argument    ${arg_key}    ${arg_value}

Onboarded model overrides should carry engine argument
    [Documentation]    Single-poll helper: the onboarded model's ``engineArgs`` override carries
    ...                the supplied key and value.
    [Arguments]    ${arg_key}    ${arg_value}
    ${overrides}=    Get onboarded model overrides
    ${args}=    Get From Dictionary    ${overrides}    engineArgs    default=&{EMPTY}
    Should Be Equal As Strings    ${args}[${arg_key}]    ${arg_value}
    ...    msg=Wizard runtime profile engine argument '${arg_key}' was not persisted on the model

The onboarded model should carry environment variable "${var_name}" set to "${var_value}"
    [Documentation]    Reads the onboarded AIMModel's persisted runtime overrides via the API to
    ...                prove the wizard's environment variable value reached the backend.
    ...                Polled because onboarding writes the CR asynchronously after submit.

    Wait Until Keyword Succeeds    90 sec    5 sec
    ...    Onboarded model overrides should carry environment variable    ${var_name}    ${var_value}

Onboarded model overrides should carry environment variable
    [Documentation]    Single-poll helper: searches the onboarded model's ``engineEnv`` list for
    ...                an entry with the given name and asserts its value matches.
    [Arguments]    ${var_name}    ${var_value}
    ${overrides}=    Get onboarded model overrides
    ${env_list}=    Get From Dictionary    ${overrides}    engineEnv    default=@{EMPTY}
    FOR    ${entry}    IN    @{env_list}
        IF    '${entry}[name]' == '${var_name}'
            Should Be Equal As Strings    ${entry}[value]    ${var_value}
            ...    msg=Wizard runtime profile env var '${var_name}' is '${entry}[value]', expected '${var_value}'
            RETURN
        END
    END
    Fail    Environment variable '${var_name}' not found in onboarded model overrides engineEnv
