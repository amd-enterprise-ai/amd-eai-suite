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

# Fine-tuning drawer selectors
${FINETUNE_BTN_SELECTOR}              css=[data-testid="custom-models"] button:has-text("Fine-tune model")
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

Open finetune drawer
    [Documentation]    Clicks the Fine-tune button on the Custom Models tab to open the drawer.
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
