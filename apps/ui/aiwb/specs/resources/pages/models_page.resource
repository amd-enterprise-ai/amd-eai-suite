# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Page object for the AIWB Models / AIM Catalog page.
...                 Contains selectors and atomic browser interactions only.
...                 Business logic and assertions belong in feature resources.


*** Variables ***
${MODELS_PATH}                     /models/aim-catalog
${CUSTOM_MODELS_PATH}              /models/custom-models
${FINE_TUNE_MODELS_PATH}           /models/fine-tune-models
${DEPLOYED_MODELS_PATH}            /models/deployed-models
${AIM_CATALOG_SELECTOR}            [data-testid="aim-catalog"]
${AIM_CATALOG_LOADING_SELECTOR}    [data-testid="aim-catalog-loading"]
${AIM_CARD_SELECTOR}               [data-testid="aim-catalog"] .grid > div
${DEPLOYED_MODELS_SELECTOR}        [data-testid="deployed-models"]
${DEPLOYED_TAB_SELECTOR}           role=tab[name="Deployed Models"]
${DEPLOY_DRAWER_SELECTOR}          text="Deploy AIM"
${ACTIONS_MENU_SELECTOR}           [role="menu"]
${VERSION_SELECTOR}                [aria-label="Version"]
${METRIC_SELECTOR}                 [aria-label="Performance metric"]
${UNSUPPORTED_BANNER_SELECTOR}     [data-testid="unsupported-banner"]
${DEPLOY_SETTINGS_SELECTOR}        text="Deployment settings"
${SEARCH_FILTER_SELECTOR}          input[placeholder*="Search"]
${CATALOG_DESCRIPTION_SELECTOR}    [data-testid="aim-catalog"] > p
${REQUEST_MODEL_CARD_SELECTOR}     [data-testid="request-model"]
${ACCELERATOR_LABEL_SELECTOR}      [data-testid="aim-card-accelerator-types"]
${ACCELERATOR_FILTER_TRIGGER}      button[aria-label="Accelerator"]
${ACCELERATOR_FILTER_MENU}         [role="menu"][aria-label="Accelerator"]
${HAS_DEPLOYMENTS_CHIP_SELECTOR}   [data-testid="aim-card-has-deployments"]

# Fine-tune Models tab selectors
${FINE_TUNE_MODELS_SELECTOR}          [data-testid="fine-tune-models"]
${FINETUNE_BTN_SELECTOR}              css=[data-testid="fine-tune-models-finetune"]
${BASE_MODEL_SELECT_SELECTOR}         css=[data-testid="baseModelSelect"]
${BASE_MODEL_OPTION_SELECTOR}         css=[role="option"][data-testid^="model-select-"]
${BASE_MODEL_EMPTY_MSG}               No fine-tuning recipes available for your cluster hardware
${ADVANCED_SETTINGS_TRIGGER}          css=button:has-text("Advanced settings")
# HeroUI's NumberInput renders TWO inputs in the same wrapper: a hidden input
# carrying name= for form submission, and a type="text" input the user types into
# (react-aria avoids type="number" so locale formatting works). The visible input
# has data-slot="input" but no name; selectors must scope through the wrapper to
# disambiguate batchSize from epochs/learningRate.
${BATCH_SIZE_WRAPPER_SELECTOR}        css=[data-slot="inner-wrapper"]:has(input[name="batchSize"])
${BATCH_SIZE_INPUT_SELECTOR}          ${BATCH_SIZE_WRAPPER_SELECTOR} >> css=input[data-slot="input"]
${BATCH_SIZE_INCREMENT_SELECTOR}      ${BATCH_SIZE_WRAPPER_SELECTOR} >> css=[data-slot="increase-button"]
${FINE_TUNE_MODELS_ROW_ACTION_BTN}    css=button[aria-label="Actions"]
${FINE_TUNE_MODELS_FINETUNE_OPTION}   css=[data-testid="finetune"]

# Custom-model deploy drawer — anchor on stable in-drawer markup (not translated title copy).
${CUSTOM_DEPLOY_DRAWER_SELECTOR}         css=[data-testid="runtime-profile-slot"]
# Row action item for the Deploy option — data-testid is the action key ("deploy")
${FINE_TUNE_MODELS_DEPLOY_OPTION}        css=[data-testid="deploy"]
# Display-name input: FormInput renders an <input> whose name attr is "displayName"
${CUSTOM_DEPLOY_DISPLAY_NAME_INPUT}      css=input[name="displayName"]
# Autoscaling toggle: FormSwitch with data-testid="autoscaling-toggle"
${CUSTOM_DEPLOY_AUTOSCALING_TOGGLE}      css=[data-testid="autoscaling-toggle"]
# Deploy (confirm) button in the drawer footer: aria-label matches the confirmText prop
${CUSTOM_DEPLOY_SUBMIT_BTN}              css=button[aria-label="Deploy"]

# Custom Model Import wizard selectors
${IMPORT_MODEL_BUTTON_SELECTOR}            css=[data-testid="custom-models-import-model"]
${CUSTOM_MODEL_CARD_SELECTOR}              css=[data-testid="custom-model-card"]
${CUSTOM_MODEL_CARD_ACTIONS_SELECTOR}      css=[data-testid="custom-model-card-actions"]
${CUSTOM_MODEL_COPY_MENU_ITEM_SELECTOR}    css=[role="menuitem"]:has-text("Make a copy")
${CUSTOM_MODEL_SETTINGS_MENU_ITEM_SELECTOR}    css=[role="menuitem"]:has-text("Model settings")
${CUSTOM_MODEL_DELETE_MENU_ITEM_SELECTOR}      css=[role="menuitem"]:has-text("Delete")
${CUSTOM_MODEL_DELETE_MODAL_SELECTOR}          [data-testid="confirmation-modal"]
${CUSTOM_MODEL_DELETE_CONFIRM_BUTTON_SELECTOR}    [data-testid="confirm-button"]
${CUSTOM_MODEL_DELETE_CLOSE_BUTTON_SELECTOR}      css=[data-testid="confirmation-modal"] button:has-text("Close")
${IMPORT_WIZARD_PAGE_SELECTOR}             css=[data-testid="custom-model-import-page"]
${IMPORT_WIZARD_SOURCE_INPUT_SELECTOR}     css=[data-testid="custom-model-import-source"] input
${IMPORT_WIZARD_NEXT_SOURCE_SELECTOR}          css=[data-testid="custom-model-import-next-source"]
${IMPORT_WIZARD_NEXT_INFORMATION_SELECTOR}    css=[data-testid="custom-model-import-next-information"]
${IMPORT_WIZARD_SUBMIT_SELECTOR}              css=[data-testid="custom-model-import-submit"]
${IMPORT_WIZARD_CANCEL_SELECTOR}              css=[data-testid="custom-model-import-cancel"]
${IMPORT_WIZARD_HEADER_BACK_SELECTOR}         css=[data-testid="custom-model-import-header-back"]
${CUSTOM_MODEL_CARD_IMPORTING_SELECTOR}       css=[data-testid="custom-model-card"]:has-text("Importing")
${CUSTOM_MODEL_CARD_READY_SELECTOR}           css=[data-testid="custom-model-card"]:has-text("Ready")
${CUSTOM_MODEL_CARD_DEPLOY_BUTTON_SELECTOR}   css=[data-testid="custom-model-card-deploy"]
${CUSTOM_MODELS_EMPTY_STATE_SELECTOR}         css=[data-testid="custom-models-empty"]
${PROJECT_HF_TOKEN_SELECTOR}               css=[data-testid="project-hf-token-selector"]
${CUSTOM_MODEL_EDIT_LOAD_ERROR_SELECTOR}   css=[data-testid="custom-model-edit-error"]

# Custom Model Import/Edit wizard — runtime profile step selectors
# Engine args and env vars are YAML textareas in the runtime step (not a key/value editor).
${RUNTIME_ENGINE_ARGS_YAML_SELECTOR}           css=[data-testid="custom-model-import-engine-args-yaml"]
${RUNTIME_ENV_VARS_YAML_SELECTOR}              css=[data-testid="custom-model-import-env-vars-yaml"]
${RUNTIME_DISABLED_NOTICE_SELECTOR}            css=[data-testid="custom-model-import-runtime-disabled-notice"]

# Catalog deploy drawer — advanced profile overrides. These fields carry no testids;
# the expander is matched on its visible label and the selects on their aria-labels.
${DEPLOY_ADVANCED_TOGGLE_SELECTOR}             css=button:has-text("advanced profile parameters")
${DEPLOY_ADVANCED_PRECISION_SELECTOR}          css=[aria-label="Precision"]
${CUSTOM_MODEL_EDIT_LOADING_SELECTOR}      css=[data-testid="custom-model-edit-loading"]
${IMPORT_WIZARD_DISPLAY_NAME_SELECTOR}     css=[data-testid="custom-model-import-page"] input[name="displayName"]
${IMPORT_WIZARD_DUP_WARNING_SELECTOR}      css=[data-testid="custom-model-import-duplicate-name-warning"]

# Pagination — HeroUI's Pagination component renders a sibling list with
# numbered buttons and prev/next controls. The next-page control carries
# aria-label="next page button" (HeroUI default). EAI-6124 moved the fine-tune
# table off the Custom Models tab into its own tab; selectors target the
# fine-tune-models testid root accordingly.
${FINE_TUNE_MODELS_TABLE_ROW}           css=${FINE_TUNE_MODELS_SELECTOR} table tbody tr
${FINE_TUNE_MODELS_PAGINATION}          css=${FINE_TUNE_MODELS_SELECTOR} [role="navigation"]
${FINE_TUNE_MODELS_NEXT_PAGE_BTN}       css=${FINE_TUNE_MODELS_SELECTOR} button[aria-label="next page button"]
# HF token section — the h4 heading is the stable anchor; the section is only
# mounted when the selected base model is gated, so its presence/absence
# proves the gating flag was respected.
${HF_TOKEN_SECTION_SELECTOR}            css=h4:has-text("Hugging Face Authentication")
# DrawerForm renders the confirm button with aria-label equal to confirmText.
${FINETUNE_CONFIRM_BTN_SELECTOR}        button[aria-label="Start training"]
${FINETUNE_DISPLAY_NAME_INPUT}          css=input[name="displayName"]


*** Keywords ***
Navigate to models page
    [Documentation]    Navigates to the AIM Catalog page and waits for it to load.
    [Arguments]    ${base_url}    ${project}

    Go To    ${base_url}/${project}${MODELS_PATH}
    Wait For Elements State    css=${AIM_CATALOG_SELECTOR}    visible    timeout=30s

Navigate to deployed models page
    [Documentation]    Navigates directly to the Deployed Models tab.
    [Arguments]    ${base_url}    ${project}

    Go To    ${base_url}/${project}${DEPLOYED_MODELS_PATH}
    Wait For Elements State    css=${DEPLOYED_MODELS_SELECTOR}    visible    timeout=30s

Click deploy button on card
    [Documentation]    Clicks the Deploy button on a specific AIM card.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") >> css=button:has-text("Deploy")
    Click    ${selector}

Click actions menu button on card
    [Documentation]    Clicks the actions menu (three dots) on a specific AIM card.
    ...                Waits for the button to become enabled since deployment data loads
    ...                asynchronously and the button is disabled until deployments are detected.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") >> css=button[aria-label="Actions menu"]
    Wait For Elements State    ${selector}    visible    timeout=15s
    Wait For Elements State    ${selector}    enabled    timeout=30s
    Click    ${selector}

Click deployed models tab
    [Documentation]    Switches to the "Deployed Models" tab.

    Click    ${DEPLOYED_TAB_SELECTOR}
    Wait For Elements State    css=${DEPLOYED_MODELS_SELECTOR}    visible    timeout=15s

Wait for deploy drawer
    [Documentation]    Waits for the Deploy AIM drawer to become visible.

    Wait For Elements State    ${DEPLOY_DRAWER_SELECTOR}    visible    timeout=15s

Get actions menu text
    [Documentation]    Returns the text content of the currently visible actions menu.

    VAR    ${menu}    css=${ACTIONS_MENU_SELECTOR}
    Wait For Elements State    ${menu}    visible    timeout=10s
    ${text}=    Get Text    ${menu}
    RETURN    ${text}

Get deployed model row text
    [Documentation]    Returns the text content of a deployed model row matching the given name.
    ...                Waits for the row to appear since the deployed models table loads
    ...                asynchronously (AIM services first, then catalog data for canonical name).
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${DEPLOYED_MODELS_SELECTOR} tr:has-text("${aim_name}")
    Wait For Elements State    ${selector}    visible    timeout=30s
    ${text}=    Get Text    ${selector}
    RETURN    ${text}

Get AIM card text
    [Documentation]    Returns the full text content of a specific AIM card.
    ...                Selects the first (outermost) card grid element matching the AIM name,
    ...                avoiding strict-mode violations when inner card divs also contain the text.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}")
    ${elements}=    Get Elements    ${selector}
    ${text}=    Get Text    ${elements}[0]
    RETURN    ${text}

Get version selector text
    [Documentation]    Returns the currently selected version text from the version selector.

    VAR    ${selector}    css=${VERSION_SELECTOR}
    Wait For Elements State    ${selector}    visible    timeout=10s
    ${text}=    Get Text    ${selector}
    RETURN    ${text}

Get AIM card count
    [Documentation]    Returns the number of AIM cards displayed in the catalog grid.

    ${elements}=    Get Elements    css=${AIM_CARD_SELECTOR}
    ${count}=    Get Length    ${elements}
    RETURN    ${count}

Get catalog description text
    [Documentation]    Returns the catalog description text shown above the grid.

    ${text}=    Get Text    css=${CATALOG_DESCRIPTION_SELECTOR}
    RETURN    ${text}

AIM card should be visible
    [Documentation]    Verifies that a specific AIM card is visible in the catalog.
    ...                Uses Get Elements to avoid strict-mode violations from nested text matches.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}")
    ${elements}=    Get Elements    ${selector}
    Should Be True    len($elements) > 0    msg=No AIM card found with name "${aim_name}"
    Wait For Elements State    ${elements}[0]    visible    timeout=15s

AIM card should have version count
    [Documentation]    Verifies a card contains a version count string (e.g. "N version(s)").
    [Arguments]    ${aim_name}

    ${text}=    Get AIM card text    ${aim_name}
    Should Match Regexp    ${text}    \\d+ versions?

AIM card should have tags
    [Documentation]    Verifies a card displays at least one tag.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") [class*="chip"], ${AIM_CARD_SELECTOR}:has-text("${aim_name}") [class*="tag"]
    ${count}=    Get Element Count    ${selector}
    Should Be True    ${count} > 0    msg=AIM card "${aim_name}" should display at least one tag

AIM card should have deploy button
    [Documentation]    Verifies a card has a Deploy button.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") >> css=button:has-text("Deploy")
    Wait For Elements State    ${selector}    visible    timeout=10s

Get unsupported banner count
    [Documentation]    Returns the number of unsupported banners visible in the catalog.

    ${elements}=    Get Elements    css=${UNSUPPORTED_BANNER_SELECTOR}
    ${count}=    Get Length    ${elements}
    RETURN    ${count}

AIM card should have unsupported banner
    [Documentation]    Verifies that a specific AIM card has the unsupported hardware banner.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") ${UNSUPPORTED_BANNER_SELECTOR}
    Wait For Elements State    ${selector}    visible    timeout=10s

AIM card has deployments chip should be visible
    [Documentation]    Verifies the "Has deployments" chip is visible on the given AIM card.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") ${HAS_DEPLOYMENTS_CHIP_SELECTOR}
    Wait For Elements State    ${selector}    visible    timeout=15s

AIM card has deployments chip should not be present
    [Documentation]    Verifies the "Has deployments" chip is absent from the given AIM card.
    [Arguments]    ${aim_name}

    VAR    ${card_selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}")
    Wait For Elements State    ${card_selector}    visible    timeout=15s
    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") ${HAS_DEPLOYMENTS_CHIP_SELECTOR}
    Wait For Elements State    ${selector}    detached    timeout=10s

Deploy drawer should show deployment settings
    [Documentation]    Verifies the deploy drawer shows the "Deployment settings" section.

    Wait For Elements State    ${DEPLOY_SETTINGS_SELECTOR}    visible    timeout=10s

Get metric selector text
    [Documentation]    Returns the currently selected metric text from the metric selector.

    VAR    ${selector}    css=${METRIC_SELECTOR}
    Wait For Elements State    ${selector}    visible    timeout=10s
    ${text}=    Get Text    ${selector}
    RETURN    ${text}

Deploy drawer should show model title
    [Documentation]    Verifies the deploy drawer shows the given model title.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=.text-2xl:has-text("${aim_name}")
    Wait For Elements State    ${selector}    visible    timeout=10s

Get deployed models row count
    [Documentation]    Returns the number of rows in the deployed models table.

    VAR    ${selector}    css=${DEPLOYED_MODELS_SELECTOR} [role="row"]
    ${elements}=    Get Elements    ${selector}
    ${count}=    Get Length    ${elements}
    RETURN    ${count}

Enter search filter text
    [Documentation]    Types text into the search filter input.
    [Arguments]    ${text}

    Fill Text    css=${SEARCH_FILTER_SELECTOR}    ${text}

Get AIM card accelerator label
    [Documentation]    Returns the accelerator label text shown in a specific AIM card's
    ...                metadata line, or an empty string when the card omits the label.
    [Arguments]    ${aim_name}

    VAR    ${selector}    css=${AIM_CARD_SELECTOR}:has-text("${aim_name}") ${ACCELERATOR_LABEL_SELECTOR}
    ${elements}=    Get Elements    ${selector}
    IF    len($elements) == 0    RETURN    ${EMPTY}
    ${text}=    Get Text    ${elements}[0]
    RETURN    ${text}

Get accelerator label match count
    [Documentation]    Returns how many catalog cards show exactly the given accelerator label.
    [Arguments]    ${label}

    ${count}=    Get Element Count    css=${ACCELERATOR_LABEL_SELECTOR}:text-is("${label}")
    RETURN    ${count}

Open accelerator filter
    [Documentation]    Opens the Accelerator multi-select filter dropdown.

    Wait For Elements State    css=${ACCELERATOR_FILTER_TRIGGER}    visible    timeout=10s
    Click    css=${ACCELERATOR_FILTER_TRIGGER}
    Wait For Elements State    css=${ACCELERATOR_FILTER_MENU}    visible    timeout=10s

Select accelerator filter option "${label}"
    [Documentation]    Selects an option (e.g. "GPU" or "CPU") inside the open Accelerator filter.

    VAR    ${selector}    css=${ACCELERATOR_FILTER_MENU} [role="menuitemcheckbox"]:has-text("${label}")
    Wait For Elements State    ${selector}    visible    timeout=10s
    Click    ${selector}

Close accelerator filter
    [Documentation]    Dismisses the Accelerator dropdown via Escape so subsequent
    ...                catalog cards are not obscured by the open menu.

    Press Keys    None    Escape

Get request model card mailto href
    [Documentation]    Returns the href of the anchor inside the "Request model" card.
    ...                Waits for the card to be visible since it renders after the catalog list.

    VAR    ${card}    css=${REQUEST_MODEL_CARD_SELECTOR}
    Wait For Elements State    ${card}    visible    timeout=15s
    ${href}=    Get Attribute    css=${REQUEST_MODEL_CARD_SELECTOR} a    href
    RETURN    ${href}

Navigate to custom models page
    [Documentation]    Navigates to the Custom Models tab on the models page.
    [Arguments]    ${base_url}    ${project}

    Go To    ${base_url}/${project}${CUSTOM_MODELS_PATH}
    Wait For Elements State    css=[data-testid="custom-models"]    visible    timeout=30s

Navigate to custom model edit page
    [Documentation]    Opens the full-page edit wizard for a custom model by CR name.
    ...                The shell renders immediately; the model payload loads asynchronously.
    [Arguments]    ${base_url}    ${project}    ${model_id}

    Go To    ${base_url}/${project}/models/custom-models/${model_id}/edit
    Wait For Elements State    ${IMPORT_WIZARD_PAGE_SELECTOR}    visible    timeout=30s

Wait for custom model edit load error
    [Documentation]    Waits until the edit wizard shows the load-failure affordance
    ...                (missing model, wrong project, or upstream error).

    Wait For Elements State    ${CUSTOM_MODEL_EDIT_LOAD_ERROR_SELECTOR}    visible    timeout=45s

Custom model edit page should show edit title
    [Documentation]    Verifies the edit-mode page chrome (distinct from import).

    Wait For Elements State    ${IMPORT_WIZARD_PAGE_SELECTOR}    visible    timeout=15s
    ${text}=    Get Text    ${IMPORT_WIZARD_PAGE_SELECTOR}
    Should Contain    ${text}    Edit model

Navigate to fine-tune models page
    [Documentation]    Navigates to the Fine-tune Models tab on the models page.
    ...                Fine-tune flows live on this tab since EAI-6124 split the
    ...                previous Custom Models tab into Custom Models (imported
    ...                models) and Fine-tune Models (the fine-tune table).
    [Arguments]    ${base_url}    ${project}

    Go To    ${base_url}/${project}${FINE_TUNE_MODELS_PATH}
    Wait For Elements State    css=${FINE_TUNE_MODELS_SELECTOR}    visible    timeout=30s

Open finetune drawer
    [Documentation]    Clicks the Fine-tune button on the Fine-tune Models tab to open the drawer.
    ...                Waits for the button to be enabled since workload data loads asynchronously
    ...                and the button is disabled until the initial load completes.

    Wait For Elements State    ${FINETUNE_BTN_SELECTOR}    visible    timeout=15s
    Wait For Elements State    ${FINETUNE_BTN_SELECTOR}    enabled    timeout=15s
    Click    ${FINETUNE_BTN_SELECTOR}
    Wait For Elements State    ${BASE_MODEL_SELECT_SELECTOR}    visible    timeout=15s

Click base model select
    [Documentation]    Opens the base model dropdown by clicking the select trigger.

    Click    ${BASE_MODEL_SELECT_SELECTOR}

Get base model option count
    [Documentation]    Returns the number of options in the open base model dropdown.

    ${elements}=    Get Elements    ${BASE_MODEL_OPTION_SELECTOR}
    ${count}=    Get Length    ${elements}
    RETURN    ${count}

Get base model option text
    [Documentation]    Returns the full text content of a base model option by index.
    [Arguments]    ${index}=0

    ${elements}=    Get Elements    ${BASE_MODEL_OPTION_SELECTOR}
    ${text}=    Get Text    ${elements}[${index}]
    RETURN    ${text}

Base model select should show empty state
    [Documentation]    Verifies the base model select shows the no-compatible-recipes placeholder.
    ...                Uses polling since the message is populated asynchronously.

    Wait For Elements State    ${BASE_MODEL_SELECT_SELECTOR}    visible    timeout=10s
    Wait Until Keyword Succeeds    10s    500ms    Base model empty state text should be shown

Base model empty state text should be shown
    ${text}=    Get Text    ${BASE_MODEL_SELECT_SELECTOR}
    Should Contain    ${text}    ${BASE_MODEL_EMPTY_MSG}

Base model options should be non-empty
    [Documentation]    Verifies at least one option is visible in the open base model dropdown.

    ${count}=    Get base model option count
    Should Be True    ${count} > 0    msg=Expected at least one fine-tuning recipe option

Click first base model option
    [Documentation]    Selects the first option in the open base model dropdown.

    ${elements}=    Get Elements    ${BASE_MODEL_OPTION_SELECTOR}
    Click    ${elements}[0]

Open advanced fine-tuning settings
    [Documentation]    Expands the Advanced settings accordion in the fine-tuning drawer.
    ...                Waits for the batch size input to attach since the accordion
    ...                mounts its children only when expanded.

    Click    ${ADVANCED_SETTINGS_TRIGGER}
    Wait For Elements State    ${BATCH_SIZE_INPUT_SELECTOR}    attached    timeout=10s

Click batch size increment button
    [Documentation]    Clicks the + stepper button on the batch size NumberInput.
    ...                The button steps the value by the recipe's GPU count (the
    ...                input's step prop), and clamps the result to >= the recipe's
    ...                GPU count (the input's minValue prop).

    Click    ${BATCH_SIZE_INCREMENT_SELECTOR}

Get batch size value
    [Documentation]    Returns the current value displayed in the batch size input as an
    ...                integer, or 0 when the input is empty. Reads the DOM `value`
    ...                property (not the `value` attribute, which only reflects the
    ...                initial value) so it sees user-typed and stepper-applied changes.

    ${raw}=    Get Property    ${BATCH_SIZE_INPUT_SELECTOR}    value
    IF    not $raw    RETURN    ${0}
    ${value}=    Convert To Integer    ${raw}
    RETURN    ${value}

Batch size input should be enabled
    [Documentation]    Waits for the batch size input to be interactive. The form
    ...                disables the input until a recipe is selected; this keyword
    ...                verifies that selection has unlocked it.

    Wait For Elements State    ${BATCH_SIZE_INPUT_SELECTOR}    enabled    timeout=5s

Batch size input should be disabled
    [Documentation]    Verifies the batch size input is disabled. The form keeps it
    ...                disabled until a recipe is selected so the GPU-count-derived
    ...                constraints (min, step) can be applied to a known recipe.

    Wait For Elements State    ${BATCH_SIZE_INPUT_SELECTOR}    disabled    timeout=5s

Click import model button
    [Documentation]    Clicks the "Import model" toolbar button on the custom models tab.
    ...                Waits for the button to be enabled (it disables while the models list
    ...                loads).

    Wait For Elements State    ${IMPORT_MODEL_BUTTON_SELECTOR}    visible    timeout=15s
    Wait For Elements State    ${IMPORT_MODEL_BUTTON_SELECTOR}    enabled    timeout=15s
    Click    ${IMPORT_MODEL_BUTTON_SELECTOR}

Click actions menu on first custom model card
    [Documentation]    Opens the actions menu on the first visible custom model card.
    ...                Waits for at least one card and an enabled actions button.

    Wait For Elements State    ${CUSTOM_MODEL_CARD_SELECTOR}    visible    timeout=30s
    ${buttons}=    Get Elements    ${CUSTOM_MODEL_CARD_SELECTOR} >> ${CUSTOM_MODEL_CARD_ACTIONS_SELECTOR}
    Should Be True    len($buttons) > 0    msg=Expected at least one custom model card actions button
    Wait For Elements State    ${buttons}[0]    enabled    timeout=10s
    Click    ${buttons}[0]

Click make copy action in custom model card menu
    [Documentation]    Clicks the "Make a copy" action in the open custom model card menu.

    Wait For Elements State    ${CUSTOM_MODEL_COPY_MENU_ITEM_SELECTOR}    visible    timeout=10s
    Click    ${CUSTOM_MODEL_COPY_MENU_ITEM_SELECTOR}

Click model settings action in custom model card menu
    [Documentation]    Clicks the "Model settings" action in the open custom model card menu,
    ...                which navigates to the full-page edit wizard for that model.

    Wait For Elements State    ${CUSTOM_MODEL_SETTINGS_MENU_ITEM_SELECTOR}    visible    timeout=10s
    Click    ${CUSTOM_MODEL_SETTINGS_MENU_ITEM_SELECTOR}

Click delete action in custom model card menu
    [Documentation]    Clicks the "Delete" action in the open custom model card menu.

    Wait For Elements State    ${CUSTOM_MODEL_DELETE_MENU_ITEM_SELECTOR}    visible    timeout=10s
    Click    ${CUSTOM_MODEL_DELETE_MENU_ITEM_SELECTOR}

Wait for custom model delete confirmation modal
    [Documentation]    Waits for the delete confirmation modal to appear after triggering delete.

    Wait For Elements State    ${CUSTOM_MODEL_DELETE_MODAL_SELECTOR}    visible    timeout=10s

Confirm model deletion in modal
    [Documentation]    Clicks the confirm button inside the delete confirmation modal.

    Click    css=${CUSTOM_MODEL_DELETE_CONFIRM_BUTTON_SELECTOR}

Close delete confirmation modal
    [Documentation]    Clicks the "Close" button to dismiss the delete confirmation modal
    ...                without triggering deletion.

    Wait For Elements State    ${CUSTOM_MODEL_DELETE_CLOSE_BUTTON_SELECTOR}    visible    timeout=10s
    Click    ${CUSTOM_MODEL_DELETE_CLOSE_BUTTON_SELECTOR}

Wait for delete success toast
    [Documentation]    Waits for the "Model successfully deleted." success toast to appear
    ...                after a successful deletion.

    Wait For Elements State    text=Model successfully deleted.    visible    timeout=30s

Custom model card should be absent
    [Documentation]    Asserts no custom model cards are visible. Used as a single-poll
    ...                check inside a Wait Until Keyword Succeeds wrapper.

    ${cards}=    Get Elements    ${CUSTOM_MODEL_CARD_SELECTOR}
    ${count}=    Get Length    ${cards}
    Should Be Equal As Integers    ${count}    0
    ...    msg=Expected no custom model cards but found ${count}

Click import wizard next on source step in edit mode
    [Documentation]    Waits for the edit wizard's source step to finish loading and
    ...                clicks Next to advance to the information step. Edit mode mounts
    ...                the wizard from a navigation event, so a visibility wait is needed
    ...                before the source-step Next button is interactable.

    Wait For Elements State    ${IMPORT_WIZARD_NEXT_SOURCE_SELECTOR}    visible    timeout=30s
    Wait For Elements State    ${IMPORT_WIZARD_NEXT_SOURCE_SELECTOR}    enabled    timeout=15s
    Click    ${IMPORT_WIZARD_NEXT_SOURCE_SELECTOR}

Get custom model card count
    [Documentation]    Returns the number of custom model cards currently shown.

    ${cards}=    Get Elements    ${CUSTOM_MODEL_CARD_SELECTOR}
    ${count}=    Get Length    ${cards}
    RETURN    ${count}

Wait for import wizard page
    [Documentation]    Waits for the custom model import wizard page to be visible.

    Wait For Elements State    ${IMPORT_WIZARD_PAGE_SELECTOR}    visible    timeout=15s

Click import wizard next on source step
    [Documentation]    Clicks the "Preview model" button on the source step of the wizard.

    Click    ${IMPORT_WIZARD_NEXT_SOURCE_SELECTOR}

Click import wizard next on information step
    [Documentation]    Clicks the "Next" button on the information step to advance to the
    ...                runtime profile step. Waits for the button to be enabled since the
    ...                information step only mounts once the wizard advances from step 1.

    Wait For Elements State    ${IMPORT_WIZARD_NEXT_INFORMATION_SELECTOR}    visible    timeout=30s
    Wait For Elements State    ${IMPORT_WIZARD_NEXT_INFORMATION_SELECTOR}    enabled    timeout=15s
    Click    ${IMPORT_WIZARD_NEXT_INFORMATION_SELECTOR}

Click import wizard submit
    [Documentation]    Clicks the "Import model" submit button on the runtime profile step.
    ...                Waits for the button to be enabled since the step loads asynchronously.

    Wait For Elements State    ${IMPORT_WIZARD_SUBMIT_SELECTOR}    visible    timeout=30s
    Wait For Elements State    ${IMPORT_WIZARD_SUBMIT_SELECTOR}    enabled    timeout=15s
    Click    ${IMPORT_WIZARD_SUBMIT_SELECTOR}

Custom model card with importing or ready status should be visible
    [Documentation]    Asserts that at least one custom model card showing "Importing" or
    ...                "Ready" status is visible. Used as a single-poll check inside a
    ...                Wait Until Keyword Succeeds wrapper.

    ${importing}=    Get Elements    ${CUSTOM_MODEL_CARD_IMPORTING_SELECTOR}
    ${ready}=        Get Elements    ${CUSTOM_MODEL_CARD_READY_SELECTOR}
    ${total}=        Evaluate    len($importing) + len($ready)
    Should Be True    ${total} > 0
    ...    msg=Expected at least one custom model card with "Importing" or "Ready" status

Click import wizard cancel
    [Documentation]    Clicks the "Cancel" button on the source step of the wizard.

    Click    ${IMPORT_WIZARD_CANCEL_SELECTOR}

Click import wizard header back
    [Documentation]    Clicks the header back link that returns to the custom models list.

    Click    ${IMPORT_WIZARD_HEADER_BACK_SELECTOR}

Fill import wizard source
    [Documentation]    Types into the wizard's model source input.
    [Arguments]    ${value}

    Fill Text    ${IMPORT_WIZARD_SOURCE_INPUT_SELECTOR}    ${value}

Open project Hugging Face token dropdown
    [Documentation]    Opens the Hugging Face token selector on the custom model import source step.

    Wait For Elements State    ${PROJECT_HF_TOKEN_SELECTOR}    visible    timeout=15s
    Click    ${PROJECT_HF_TOKEN_SELECTOR}

Click Hugging Face token option labeled
    [Documentation]    Selects an existing Hugging Face token in the open listbox by its visible label text.
    [Arguments]    ${label}

    Wait For Elements State    css=[role="listbox"]    visible    timeout=15s
    Click    css=[role="listbox"] [role="option"]:has-text("${label}")

Import wizard should show stepper labels
    [Documentation]    Verifies the wizard renders the three step labels: source,
    ...                information, and runtime.

    Wait For Elements State    ${IMPORT_WIZARD_PAGE_SELECTOR}    visible    timeout=15s
    ${page_text}=    Get Text    ${IMPORT_WIZARD_PAGE_SELECTOR}
    Should Contain    ${page_text}    Model source
    Should Contain    ${page_text}    Model information
    Should Contain    ${page_text}    Runtime profile

Import wizard source input should be visible
    [Documentation]    Verifies the wizard's source input is currently visible —
    ...                used to assert that the wizard has not advanced past the
    ...                source step (e.g. after a failed validation).

    Wait For Elements State    ${IMPORT_WIZARD_SOURCE_INPUT_SELECTOR}    visible    timeout=10s

Fill import wizard display name
    [Documentation]    Types into the information step's display-name input,
    ...                replacing any preview-seeded value. Waits for the input
    ...                first since it only mounts once the wizard reaches step 2.
    [Arguments]    ${value}

    Wait For Elements State    ${IMPORT_WIZARD_DISPLAY_NAME_SELECTOR}    visible    timeout=30s
    Fill Text    ${IMPORT_WIZARD_DISPLAY_NAME_SELECTOR}    ${value}

Import wizard duplicate name warning should be visible
    [Documentation]    Verifies the duplicate display-name warning Alert is shown
    ...                on the information step.

    Wait For Elements State    ${IMPORT_WIZARD_DUP_WARNING_SELECTOR}    visible    timeout=10s

Import wizard duplicate name warning should be hidden
    [Documentation]    Verifies the duplicate display-name warning Alert is not
    ...                present (the entered name does not collide).

    Wait For Elements State    ${IMPORT_WIZARD_DUP_WARNING_SELECTOR}    detached    timeout=10s

Custom models tab should be visible
    [Documentation]    Verifies the Custom Models tab content is currently visible.
    ...                Distinct from `Navigate to custom models page`: this only
    ...                asserts visibility without performing navigation, suitable
    ...                for post-action checks (e.g. after canceling the import
    ...                wizard).

    Wait For Elements State    css=[data-testid="custom-models"]    visible    timeout=15s

Import model button should be absent
    [Documentation]    Verifies the "Import model" toolbar button is not present
    ...                on the current tab. EAI-6124 placed the button on the
    ...                Custom Models tab only; it must not appear on the
    ...                Fine-tune Models tab.

    Wait For Elements State    ${IMPORT_MODEL_BUTTON_SELECTOR}    detached    timeout=10s

# =============================================================================
# Runtime profile wizard step page keywords
# =============================================================================

Wait for runtime profile step
    [Documentation]    Waits for the runtime profile step to render its engine-arguments
    ...                YAML field — the step's most stable, catalog-independent control.

    Wait For Elements State    ${RUNTIME_ENGINE_ARGS_YAML_SELECTOR}    visible    timeout=15s

Runtime profile step should be editable
    [Documentation]    Verifies the runtime profile fields are editable — the disabled
    ...                notice (shown when the profile is not yet ready) must be absent.

    Wait For Elements State    ${RUNTIME_ENGINE_ARGS_YAML_SELECTOR}    visible    timeout=15s
    Wait For Elements State    ${RUNTIME_DISABLED_NOTICE_SELECTOR}    detached    timeout=5s

Fill runtime profile engine arguments
    [Documentation]    Replaces the engine-arguments YAML textarea content.
    [Arguments]    ${yaml}

    Wait For Elements State    ${RUNTIME_ENGINE_ARGS_YAML_SELECTOR}    visible    timeout=15s
    Fill Text    ${RUNTIME_ENGINE_ARGS_YAML_SELECTOR}    ${yaml}

Fill runtime profile environment variables
    [Documentation]    Replaces the environment-variables YAML textarea content.
    [Arguments]    ${yaml}

    Wait For Elements State    ${RUNTIME_ENV_VARS_YAML_SELECTOR}    visible    timeout=15s
    Fill Text    ${RUNTIME_ENV_VARS_YAML_SELECTOR}    ${yaml}

Submit import wizard runtime step
    [Documentation]    Clicks the runtime step's primary action (Save and start onboarding
    ...                on import, Save on edit) to submit the wizard.

    Wait For Elements State    ${IMPORT_WIZARD_SUBMIT_SELECTOR}    visible    timeout=15s
    Wait For Elements State    ${IMPORT_WIZARD_SUBMIT_SELECTOR}    enabled    timeout=15s
    Click    ${IMPORT_WIZARD_SUBMIT_SELECTOR}

Open model settings on first custom model card
    [Documentation]    Opens the first custom model card's actions menu and clicks
    ...                "Model settings", which navigates to the edit wizard.

    Click actions menu on first custom model card
    Wait For Elements State    ${CUSTOM_MODEL_SETTINGS_MENU_ITEM_SELECTOR}    visible    timeout=10s
    Click    ${CUSTOM_MODEL_SETTINGS_MENU_ITEM_SELECTOR}

# =============================================================================
# Catalog deploy drawer — advanced profile override page keywords
# =============================================================================

Expand advanced profile parameters
    [Documentation]    Clicks the advanced-profile-parameters expander in the deploy drawer
    ...                and waits for the precision override select to render.

    Wait For Elements State    ${DEPLOY_ADVANCED_TOGGLE_SELECTOR}    visible    timeout=10s
    Click    ${DEPLOY_ADVANCED_TOGGLE_SELECTOR}
    Wait For Elements State    ${DEPLOY_ADVANCED_PRECISION_SELECTOR}    visible    timeout=10s

Advanced profile parameters should be visible
    [Documentation]    Verifies the advanced override fields (precision select) are shown.

    Wait For Elements State    ${DEPLOY_ADVANCED_PRECISION_SELECTOR}    visible    timeout=10s

Select deploy precision override
    [Documentation]    Picks a precision value in the advanced override precision select.
    [Arguments]    ${precision}

    Click    ${DEPLOY_ADVANCED_PRECISION_SELECTOR}
    Wait For Elements State    css=[role="listbox"]    visible    timeout=10s
    Click    css=[role="listbox"] [role="option"]:has-text("${precision}")

Submit catalog deploy drawer
    [Documentation]    Clicks the Deploy confirm button in the catalog deploy drawer footer.

    Wait For Elements State    ${CUSTOM_DEPLOY_SUBMIT_BTN}    visible    timeout=10s
    Wait For Elements State    ${CUSTOM_DEPLOY_SUBMIT_BTN}    enabled    timeout=10s
    Click    ${CUSTOM_DEPLOY_SUBMIT_BTN}

# =============================================================================
# Custom-model deploy drawer page keywords
# =============================================================================

Open deploy action from model row
    [Documentation]    Opens the row actions menu for the given model row and clicks
    ...                the Deploy option. Waits for the model row to appear (the
    ...                fine-tune models list loads asynchronously), clicks the row
    ...                actions button, and selects Deploy.
    ...                The Deploy action is only visible for Ready/Complete models —
    ...                test setup must seed the CR with Ready status first.
    [Arguments]    ${model_name}

    VAR    ${row}    css=${FINE_TUNE_MODELS_SELECTOR} table tbody tr:has-text("${model_name}")
    Wait For Elements State    ${row}    visible    timeout=30s
    ${actions_btn}=    Get Element    ${row} >> ${FINE_TUNE_MODELS_ROW_ACTION_BTN}
    Click    ${actions_btn}
    Wait For Elements State    ${FINE_TUNE_MODELS_DEPLOY_OPTION}    visible    timeout=5s
    Click    ${FINE_TUNE_MODELS_DEPLOY_OPTION}

Wait for custom model deploy drawer
    [Documentation]    Waits for the custom-model deploy drawer to mount, anchored on the
    ...                runtime-profile placeholder (stable ``data-testid``). The placeholder
    ...                is an intentionally-empty reserved <div>, so it is never "visible" to
    ...                Playwright (zero bounding box) — assert presence (attached) instead.

    Wait For Elements State    ${CUSTOM_DEPLOY_DRAWER_SELECTOR}    attached    timeout=15s

Deploy drawer header should show model name
    [Documentation]    Verifies the deploy drawer header shows the model name as a
    ...                prominent heading (text-2xl). The component renders model.name
    ...                in a div with class text-2xl.
    [Arguments]    ${model_name}

    VAR    ${selector}    css=.text-2xl:has-text("${model_name}")
    Wait For Elements State    ${selector}    visible    timeout=10s

Deploy drawer header should show namespace
    [Documentation]    Verifies the deploy drawer shows the "Deploying into ..." namespace
    ...                label, confirming the header section rendered correctly.

    Wait For Elements State    text=Deploying into    visible    timeout=10s

Deploy drawer should show display name input
    [Documentation]    Verifies the deployment-name (displayName) input is present
    ...                and interactive in the deploy drawer.

    Wait For Elements State    ${CUSTOM_DEPLOY_DISPLAY_NAME_INPUT}    visible    timeout=10s

Deploy drawer should show autoscaling toggle
    [Documentation]    Verifies the autoscaling enable toggle is visible in the
    ...                deploy drawer. The toggle carries data-testid="autoscaling-toggle".

    Wait For Elements State    ${CUSTOM_DEPLOY_AUTOSCALING_TOGGLE}    visible    timeout=10s

Submit custom model deploy drawer
    [Documentation]    Clicks the Deploy (confirm) button in the drawer footer to
    ...                submit the form with whatever values are currently set.
    ...                The button is identified by aria-label="Deploy".

    Wait For Elements State    ${CUSTOM_DEPLOY_SUBMIT_BTN}    visible    timeout=10s
    Wait For Elements State    ${CUSTOM_DEPLOY_SUBMIT_BTN}    enabled    timeout=10s
    Click    ${CUSTOM_DEPLOY_SUBMIT_BTN}

Custom model deploy drawer should be closed
    [Documentation]    Verifies the custom-model deploy drawer is gone. Anchored on the
    ...                runtime-profile placeholder, which is an empty reserved <div>: it is
    ...                only in the DOM while the drawer is mounted, so assert it has detached
    ...                rather than "hidden" (an empty div counts as hidden even when open).

    Wait For Elements State    ${CUSTOM_DEPLOY_DRAWER_SELECTOR}    detached    timeout=5s

Open fine-tune action from model row
    [Documentation]    Opens the row actions menu for the given model row and clicks the Fine-tune option.
    ...                Waits for the model row to appear (the fine-tune models list loads asynchronously)
    ...                and then clicks the row actions button and selects Fine-tune.
    [Arguments]    ${model_name}

    VAR    ${row}    css=${FINE_TUNE_MODELS_SELECTOR} table tbody tr:has-text("${model_name}")
    Wait For Elements State    ${row}    visible    timeout=30s
    ${actions_btn}=    Get Element    ${row} >> ${FINE_TUNE_MODELS_ROW_ACTION_BTN}
    Click    ${actions_btn}
    Wait For Elements State    ${FINE_TUNE_MODELS_FINETUNE_OPTION}    visible    timeout=5s
    Click    ${FINE_TUNE_MODELS_FINETUNE_OPTION}

Wait for fine-tune models table to load
    [Documentation]    Waits for the fine-tune models table to render at least one row.

    Wait For Elements State    ${FINE_TUNE_MODELS_TABLE_ROW}    visible    timeout=30s

Get fine-tune models row count
    [Documentation]    Returns the number of rows currently displayed in the fine-tune models table body.

    ${elements}=    Get Elements    ${FINE_TUNE_MODELS_TABLE_ROW}
    ${count}=    Get Length    ${elements}
    RETURN    ${count}

Wait for fine-tune models pagination controls
    [Documentation]    Waits for the table's pagination control to appear. Pagination only
    ...                renders when there is more than one page, so this implicitly verifies
    ...                that pageSize < total.

    Wait For Elements State    ${FINE_TUNE_MODELS_PAGINATION}    visible    timeout=30s

Click fine-tune models next page button
    [Documentation]    Clicks the next-page control on the fine-tune models table pagination.

    Wait For Elements State    ${FINE_TUNE_MODELS_NEXT_PAGE_BTN}    visible    timeout=10s
    Wait For Elements State    ${FINE_TUNE_MODELS_NEXT_PAGE_BTN}    enabled    timeout=10s
    Click    ${FINE_TUNE_MODELS_NEXT_PAGE_BTN}

Get fine-tune models first row text
    [Documentation]    Returns the text content of the first row in the fine-tune models table.
    ...                Useful for verifying that the rendered page changed between paginations
    ...                without depending on the absolute model name (which varies by seed batch).

    Wait For Elements State    ${FINE_TUNE_MODELS_TABLE_ROW}    visible    timeout=15s
    ${elements}=    Get Elements    ${FINE_TUNE_MODELS_TABLE_ROW}
    ${text}=    Get Text    ${elements}[0]
    RETURN    ${text}

Click base model option with name
    [Documentation]    Selects a specific base model option by canonical name.
    [Arguments]    ${canonical_name}

    VAR    ${selector}    css=[data-testid="model-select-${canonical_name}"]
    Wait For Elements State    ${selector}    visible    timeout=10s
    Click    ${selector}

HF token section should be present
    [Documentation]    Verifies the Hugging Face Authentication section is visible in the drawer.
    ...                The section is only mounted when the selected base model is gated.

    Wait For Elements State    ${HF_TOKEN_SECTION_SELECTOR}    visible    timeout=10s

HF token section should not be present
    [Documentation]    Verifies the Hugging Face Authentication section is not in the DOM.
    ...                The section is unmounted when the selected base model is not gated.

    Wait For Elements State    ${HF_TOKEN_SECTION_SELECTOR}    detached    timeout=10s

Click finetune confirm button
    [Documentation]    Clicks the "Start training" confirm button in the fine-tuning drawer.

    Click    ${FINETUNE_CONFIRM_BTN_SELECTOR}

Fill finetune display name
    [Documentation]    Types a display name into the fine-tuning drawer's model name input.
    [Arguments]    ${name}

    Fill Text    ${FINETUNE_DISPLAY_NAME_INPUT}    ${name}

Custom models empty state should be visible
    [Documentation]    Waits for the empty-state placeholder shown when a project has no
    ...                imported custom models. This is distinct from the filtered empty
    ...                state which appears when a search or status filter yields no results.

    Wait For Elements State    ${CUSTOM_MODELS_EMPTY_STATE_SELECTOR}    visible    timeout=15s

Custom model card with text "${text}" should be visible
    [Documentation]    Asserts that at least one custom model card contains the given text.
    ...                Used to verify a specific display name or label is shown on a card.

    Wait For Elements State    css=[data-testid="custom-model-card"]:has-text("${text}")    visible    timeout=30s

Click deploy button on custom model card
    [Documentation]    Clicks the deploy button of a Ready custom model card. The button is
    ...                enabled only for Ready models (disabled while Importing or Failed), and a
    ...                Ready card renders no status pill — so the enabled button, not a "Ready"
    ...                text match, is the deployability signal. Waits for an enabled deploy button
    ...                to appear so a stale Importing/Failed card whose button never enables cannot
    ...                make this flaky, and acts on [0] to avoid strict mode with several cards.

    Wait For Elements State    ${CUSTOM_MODEL_CARD_SELECTOR}    visible    timeout=30s
    VAR    ${enabled_deploy}    ${CUSTOM_MODEL_CARD_DEPLOY_BUTTON_SELECTOR}:not([disabled])
    Wait For Elements State    ${enabled_deploy}    visible    timeout=60s
    ${buttons}=    Get Elements    ${enabled_deploy}
    Should Be True    len($buttons) > 0    msg=Expected at least one enabled (Ready) custom model card deploy button
    Click    ${buttons}[0]

Custom model deploy success toast should be shown
    [Documentation]    Waits for the success toast emitted by DeployCustomAIMDrawer after a
    ...                successful deploy POST. The message is "Model deployment started".

    Wait For Elements State    text=Model deployment started    visible    timeout=30s

Deployed models table should contain a model with display name "${name}"
    [Documentation]    Waits for a row in the Deployed Models table whose text includes the
    ...                given display name. The row appears quickly after the AIMService CR
    ...                is created, regardless of whether the deployment has reached Running.

    Wait For Elements State    css=${DEPLOYED_MODELS_SELECTOR} tr:has-text("${name}")    visible    timeout=60s

Click undeploy action for deployed model with display name "${name}"
    [Documentation]    Opens the row-actions menu for the deployed model row identified by
    ...                display name and selects the "Undeploy" option. The option is
    ...                available for any non-Deleted status.

    VAR    ${row}    css=${DEPLOYED_MODELS_SELECTOR} tr:has-text("${name}")
    Wait For Elements State    ${row}    visible    timeout=30s
    Click    ${row} >> css=button[aria-label="Actions"]
    Wait For Elements State    css=[data-testid="undeploy"]    visible    timeout=10s
    Click    css=[data-testid="undeploy"]

Undeploy confirmation modal should be visible
    [Documentation]    Waits for the undeploy confirmation modal to appear. The modal uses
    ...                the shared ConfirmationModal component.

    Wait For Elements State    css=[data-testid="confirmation-modal"]    visible    timeout=10s

Confirm model undeploy in modal
    [Documentation]    Clicks the confirm button in the undeploy confirmation modal.

    Click    css=[data-testid="confirm-button"]

Undeploy success toast should be shown
    [Documentation]    Waits for the "Workload deletion started" toast shown after the undeploy
    ...                is confirmed. Deletion is async — the backend kicks off finalizers rather
    ...                than completing synchronously, so the toast signals initiation, not completion.

    Wait For Elements State    text=Workload deletion started    visible    timeout=30s

Deployed models table should not contain a model with display name "${name}"
    [Documentation]    Asserts that no row in the Deployed Models table matches the given
    ...                display name, confirming the undeploy removed the entry.
    ...                Uses a 2 min timeout because the row disappears only once the AIMService
    ...                CR is physically gone, after Kubernetes finalizers complete.

    Wait For Elements State    css=${DEPLOYED_MODELS_SELECTOR} tr:has-text("${name}")    hidden    timeout=2min
