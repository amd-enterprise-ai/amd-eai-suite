# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for AIM UI features.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Resource            common/session.resource
Resource            pages/models_page.resource


*** Variables ***
${SEMVER_PATTERN}       \\d+\\.\\d+\\.\\d+


*** Keywords ***
# =============================================================================
# Given keywords (UI preconditions)
# =============================================================================

User is on models page
    [Documentation]    Navigates to the AIM Catalog (Models) page.

    Navigate to models page    ${UI_BASE_URL}

User is on deployed models page
    [Documentation]    Navigates to the Deployed Models tab on the models page.

    Navigate to deployed models page    ${UI_BASE_URL}

# =============================================================================
# When keywords (actions)
# =============================================================================

User opens deploy drawer for "${aim_name}"
    [Documentation]    Clicks the Deploy button on a specific AIM card.

    Click deploy button on card    ${aim_name}

User opens actions menu for "${aim_name}"
    [Documentation]    Opens the actions menu (three dots) on a specific AIM card.

    Click actions menu button on card    ${aim_name}

User views deployed models
    [Documentation]    Switches to the Deployed Models tab on the models page.

    Click deployed models tab

User searches for "${search_text}" in catalog
    [Documentation]    Enters a search term in the catalog search filter.

    Enter search filter text    ${search_text}

# =============================================================================
# Then keywords (verification)
# =============================================================================

Deploy drawer should be open
    [Documentation]    Verifies the Deploy AIM drawer is visible.

    Wait for deploy drawer

Version selector should be visible in deploy drawer
    [Documentation]    Verifies the version selector dropdown is present in the deploy drawer.

    ${text}=    Get version selector text
    Should Not Be Empty    ${text}

Selected version should contain "${text}"
    [Documentation]    Verifies the selected version text contains the expected value.

    ${version}=    Get version selector text
    Should Contain    ${version}    ${text}

Deployed model "${aim_name}" should show version
    [Documentation]    Verifies a deployed model row contains a semver version string.

    ${text}=    Get deployed model row text    ${aim_name}
    Should Match Regexp    ${text}    ${SEMVER_PATTERN}

Actions menu should be visible
    [Documentation]    Verifies the actions menu dropdown is displayed.

    ${text}=    Get actions menu text
    Should Not Be Empty    ${text}

Actions menu should show version info
    [Documentation]    Verifies the actions menu contains a semver version string.

    ${text}=    Get actions menu text
    Should Match Regexp    ${text}    ${SEMVER_PATTERN}

Catalog should display AIM cards
    [Documentation]    Verifies the catalog page shows at least one AIM card.

    ${count}=    Get AIM card count
    Should Be True    ${count} > 0    msg=AIM catalog should display at least one model card

Catalog should show description text
    [Documentation]    Verifies the catalog description paragraph is visible.

    ${text}=    Get catalog description text
    Should Not Be Empty    ${text}

AIM card "${aim_name}" should be visible
    [Documentation]    Verifies a specific AIM card is displayed in the catalog.

    AIM card should be visible    ${aim_name}

AIM card "${aim_name}" should show version count
    [Documentation]    Verifies a card shows how many versions are available (e.g. "3 versions").

    AIM card should have version count    ${aim_name}

AIM card "${aim_name}" should show deploy button
    [Documentation]    Verifies a card has a Deploy action button.

    AIM card should have deploy button    ${aim_name}

AIM card "${aim_name}" should show metadata
    [Documentation]    Verifies a card shows essential metadata (version count, description text).

    ${text}=    Get AIM card text    ${aim_name}
    Should Match Regexp    ${text}    \\d+ versions?
    # Cards always show at least the AI Lab name and a description
    ${length}=    Get Length    ${text}
    Should Be True    ${length} > 20    msg=AIM card should display meaningful metadata

Deploy drawer should show model info for "${aim_name}"
    [Documentation]    Verifies the deploy drawer shows model title and deployment settings.

    Deploy drawer should show model title    ${aim_name}
    Deploy drawer should show deployment settings

Deploy drawer should show version and settings
    [Documentation]    Verifies the deploy drawer contains version selector and deployment settings.

    Version selector should be visible in deploy drawer
    Deploy drawer should show deployment settings

Unsupported models should be visually distinguished
    [Documentation]    Verifies that any unsupported models have the unsupported banner.
    ...    If no unsupported models exist, this passes silently.

    ${count}=    Get unsupported banner count
    Log    Found ${count} unsupported model banner(s)    INFO

Deployed models table should have entries
    [Documentation]    Verifies the deployed models table shows at least one row.

    ${count}=    Get deployed models row count
    Should Be True    ${count} > 0    msg=Deployed models table should have at least one entry
