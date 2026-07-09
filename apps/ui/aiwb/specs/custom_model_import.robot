# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for the custom model import wizard.
...
...                 Verifies the toolbar entry point on the Custom Models tab, the
...                 wizard layout (three steps), source-step validation, preview wiring
...                 for Hugging Face tokens, navigation back to the custom models list,
...                 full wizard submission, and credential error handling.

Resource            resources/common/browser_setup.resource
Resource            resources/custom_model_import.resource
Resource            resources/airm_projects.resource

Suite Teardown      Run Keywords    Clean Up All Created Custom Models    AND    Clean Up All Created AIWB Secrets    AND    Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
Custom models tab exposes the import model entry point
    [Documentation]    Verify that the Custom Models tab shows an "Import model"
    ...                toolbar button that opens the full-page import wizard.
    [Tags]    ui    models    custom-models    import    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    When user opens the custom model import wizard
    Then the import wizard should be open
    And the import wizard should show all three steps

Fine-tune models tab does not expose the import model entry point
    [Documentation]    Verify that EAI-6124's split keeps the "Import model"
    ...                toolbar button on the Custom Models tab only — the
    ...                Fine-tune Models tab must not surface it.
    [Tags]    ui    models    custom-models    import    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    When user is on fine-tune models tab
    Then the import model entry point should not be available

Import wizard refuses to advance when the source is empty
    [Documentation]    Verify that the source step's primary action does not advance
    ...                the wizard until a source is provided.
    [Tags]    ui    models    custom-models    import    validation

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    When user attempts to advance from the source step
    Then the import wizard should remain on the source step

Cancel returns the user to the custom models list
    [Documentation]    Verify that the wizard's Cancel action returns the user to
    ...                the Custom Models tab without onboarding anything.
    [Tags]    ui    models    custom-models    import    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    When user cancels the import wizard
    Then the custom models tab should be shown

Header back link returns the user to the custom models list
    [Documentation]    Verify that the back link rendered above the wizard title
    ...                returns the user to the Custom Models tab without
    ...                onboarding anything.
    [Tags]    ui    models    custom-models    import    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    When user returns to the custom models list via the header back link
    Then the custom models tab should be shown

Import wizard warns when the display name matches an existing custom model
    [Documentation]    Custom-model dedupe is keyed on the display name, so reusing an
    ...                existing name may overwrite that model or be rejected. Verify the
    ...                information step warns about the duplicate and clears the warning
    ...                for a unique name.
    [Tags]    ui    models    custom-models    import    smoke

    Given a ready project with user access exists
    And a custom model named "Duplicate Probe Model" exists in the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    And user enters source "${CUSTOM_MODEL_IMPORT_PREVIEW_SOURCE}" in the import wizard
    And user attempts to advance from the source step
    When user enters display name "Duplicate Probe Model" in the import wizard
    Then the duplicate display name warning should be shown
    When user enters display name "A Clearly Unique Model Name" in the import wizard
    Then the duplicate display name warning should not be shown

Importing a custom model with runtime profile settings persists them
    [Documentation]    Step 3 of the import wizard collects the runtime profile. Filling the
    ...                engine-arguments and environment-variables YAML and onboarding must persist
    ...                those values on the model, so a later deploy runs with them. Verified through
    ...                the API to prove the wizard wrote them to the backend, not just the form.
    [Tags]    ui    models    custom-models    import    profile

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    And user enters source "${CUSTOM_MODEL_IMPORT_PREVIEW_SOURCE}" in the import wizard
    And user attempts to advance from the source step
    And user advances to the runtime profile step
    When user sets runtime profile engine settings to "max-model-len: 8192" and "VLLM_LOGGING_LEVEL: DEBUG"
    And user saves the runtime profile and starts onboarding
    Then the onboarded model should carry engine argument "max-model-len" set to "8192"
    And the onboarded model should carry environment variable "VLLM_LOGGING_LEVEL" set to "DEBUG"

Custom model import preview names the Kubernetes secret for the selected token
    [Documentation]    When a saved Hugging Face token's display label differs from its
    ...                Kubernetes secret name, previewing the source must send the secret
    ...                resource name as ``hfTokenSecretName`` so the API resolves the credential.
    [Tags]    ui    models    custom-models    import    hf-token    smoke

    Given a ready project with user access exists
    And a secret "hf-ui-wire" with use case "HuggingFace" is created via AIWB
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    And user enters source "${CUSTOM_MODEL_IMPORT_PREVIEW_SOURCE}" in the import wizard
    And user selects saved Hugging Face token by display name    ${TEST_AIWB_SECRET_NAME}
    ${preview_wait}=    Promise To    Wait For Response    matcher=**/models/preview    timeout=60s
    When user attempts to advance from the source step
    ${preview}=    Wait For    ${preview_wait}
    Then the custom model preview request should name the Hugging Face secret    ${preview}    ${TEST_AIWB_SECRET_K8S_NAME}

Completing the import wizard onboards the model and shows it as importing
    [Documentation]    A user who steps through all three wizard steps and submits should
    ...                see the model card appear on the Custom Models tab in Importing or
    ...                Ready state — confirming the onboard API accepted the request and
    ...                the list page reflects the new model.
    [Tags]    ui    models    custom-models    import    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    And user enters source "${CUSTOM_MODEL_IMPORT_PREVIEW_SOURCE}" in the import wizard
    When user attempts to advance from the source step
    And user advances from the information step
    And user submits the import wizard
    Then the custom models tab should be shown
    And a custom model card should appear as importing or ready

Import wizard shows an error when preview fails with an invalid token
    [Documentation]    When a user selects an invalid Hugging Face token and attempts to
    ...                preview a gated model, the wizard must stay on the source step and
    ...                surface an error toast — the user is not silently advanced past a
    ...                credential failure.
    [Tags]    ui    models    custom-models    import    hf-token    smoke

    Given a ready project with user access exists
    And a secret "hf-token-invalid" with use case "HuggingFace" is created via AIWB
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on custom models tab
    And user opens the custom model import wizard
    And user enters source "${CUSTOM_MODEL_IMPORT_GATED_SOURCE}" in the import wizard
    And user selects saved Hugging Face token by display name    ${TEST_AIWB_SECRET_NAME}
    When user attempts to advance from the source step
    Then the import wizard should remain on the source step
    And the import wizard should show a preview error
