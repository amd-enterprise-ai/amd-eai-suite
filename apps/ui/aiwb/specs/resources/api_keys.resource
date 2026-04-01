# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for API key UI features.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Library             DateTime
Resource            common/session.resource
Resource            pages/api_keys_page.resource


*** Keywords ***
# =============================================================================
# Suite setup
# =============================================================================

Initialize API Key Suite
    [Documentation]    Generates a unique API key name prefix for this suite run
    ...                and initializes project tracking.

    Initialize Project Tracking
    ${epoch}=    Get Current Date    result_format=epoch
    ${suffix}=    Evaluate    int(${epoch})
    Set Suite Variable    ${TEST_API_KEY_NAME}    e2e-key-${suffix}

# =============================================================================
# Given keywords (UI preconditions)
# =============================================================================

User is on API keys page
    [Documentation]    Navigates to the API Keys page via the sidebar link.

    Navigate to API keys page

# =============================================================================
# When keywords (actions)
# =============================================================================

User creates API key "${key_name}"
    [Documentation]    Creates a new API key with the given name through the UI.
    ...                Retries the entire open-fill-submit sequence because the
    ...                DrawerForm can close unexpectedly when React re-renders due
    ...                to async query resolution or project context changes.

    Wait Until Keyword Succeeds    60s    3s    Open fill and submit API key form    ${key_name}

Open fill and submit API key form
    [Documentation]    Opens the drawer, fills the name, submits, and waits for
    ...                the success drawer. Designed to be retried as a unit —
    ...                includes drawer opening so that if the drawer closes during
    ...                a previous attempt, it gets reopened.
    [Arguments]    ${key_name}

    # Dismiss any drawer left open from a previous failed attempt
    ${drawer_open}=    Run Keyword And Return Status
    ...    Wait For Elements State    ${CREATE_DRAWER_TITLE}    visible    timeout=1s
    IF    ${drawer_open}
        Keyboard Key    press    Escape
        Wait For Elements State    ${CREATE_DRAWER_TITLE}    hidden    timeout=5s
    END

    Click create API key button
    Fill API key name    ${key_name}
    Submit create API key form
    Wait For Elements State    ${KEY_CREATED_TITLE}    visible    timeout=15s

User closes key created drawer
    [Documentation]    Clicks Done on the key created drawer to return to the table.

    Click done on key created drawer

User deletes API key "${key_name}"
    [Documentation]    Deletes an API key via the actions menu and confirms the deletion.

    Click actions menu on API key row    ${key_name}
    Click delete action in actions menu
    Wait for delete confirmation modal
    Confirm delete API key

User clicks copy API key button
    [Documentation]    Clicks the copy button on the key created drawer.

    Click copy API key button

# =============================================================================
# Then keywords (verification)
# =============================================================================

API keys page should be visible
    [Documentation]    Verifies the API Keys page heading is visible.

    Wait For Elements State    ${API_KEYS_PAGE_HEADING}    visible    timeout=15s

Create API key button should be visible
    [Documentation]    Verifies the "Create API Key" button is present on the page.

    Wait For Elements State    css=${CREATE_API_KEY_BUTTON}    visible    timeout=10s

API key "${key_name}" should be visible in table
    [Documentation]    Verifies that an API key with the given name appears in the table.

    Table row containing text should exist    ${key_name}

API key "${key_name}" should not be visible in table
    [Documentation]    Verifies that an API key with the given name is not in the table.

    Table row containing text should not exist    ${key_name}

Key created drawer should be visible
    [Documentation]    Verifies the key created drawer is shown after creation.

    Wait For Elements State    ${KEY_CREATED_TITLE}    visible    timeout=10s

Copy API key button should be visible
    [Documentation]    Verifies the copy button is present in the key created drawer.

    VAR    ${btn}    css=${COPY_API_KEY_BUTTON}
    Wait For Elements State    ${btn}    visible    timeout=10s

API key deleted successfully toast should appear
    [Documentation]    Verifies the success toast notification appears after deletion.

    Wait For Elements State    text="API key deleted successfully"    visible    timeout=10s
