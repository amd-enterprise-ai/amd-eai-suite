# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Page object for the AIWB API Keys page.
...                 Contains selectors and atomic browser interactions only.
...                 Business logic and assertions belong in feature resources.


*** Variables ***
${API_KEYS_PATH}                       /api-keys

# Page elements — scoped to main content area to avoid matching sidebar nav links
${API_KEYS_PAGE_HEADING}               css=main div.text-md.font-semibold
${CREATE_API_KEY_BUTTON}               button:has-text("Create API Key")

# Create API key drawer — use header element to avoid matching the trigger button
${CREATE_DRAWER_TITLE}                 css=header:has-text("Create API Key")
${NAME_INPUT_PLACEHOLDER}              Enter API key name
${CREATE_SUBMIT_BUTTON}                button[type="submit"]

# Key created drawer
${KEY_CREATED_TITLE}                   text="Key created"
${COPY_API_KEY_BUTTON}                 button[aria-label="Copy API key"]
${KEY_CREATED_DONE_BUTTON}             button:has-text("Done")

# Delete confirmation modal
${DELETE_MODAL_SELECTOR}               [data-testid="confirmation-modal"]
${CONFIRM_DELETE_BUTTON}               [data-testid="confirm-button"]

# Table elements
${API_KEYS_TABLE_ROW}                  css=table tbody tr
${EMPTY_TABLE_TEXT}                     text="No API keys found for this project."


*** Keywords ***
Navigate to API keys page
    [Documentation]    Navigates to the API Keys page via the sidebar link (SPA navigation).
    ...                Using the sidebar link instead of Go To avoids a full page reload,
    ...                which would cause React to reinitialize and potentially redirect
    ...                away due to project context race conditions.
    ...                Uses retry because the sidebar link click occasionally doesn't
    ...                navigate (e.g., due to animation timing or project context
    ...                redirecting back to Dashboard).

    Wait Until Keyword Succeeds    30s    2s    Navigate to API keys via sidebar

Navigate to API keys via sidebar
    [Documentation]    Clicks the sidebar API Keys link and verifies the page loaded.

    VAR    ${sidebar_link}    css=a[href="${API_KEYS_PATH}"]
    Wait For Elements State    ${sidebar_link}    visible    timeout=5s
    Click    ${sidebar_link}
    Wait For Elements State    ${API_KEYS_PAGE_HEADING}    visible    timeout=10s

Click create API key button
    [Documentation]    Clicks the "Create API Key" button to open the creation drawer.
    ...                Waits for the drawer to appear and its opening animation to settle
    ...                before returning control to the caller.

    Click    css=${CREATE_API_KEY_BUTTON}
    Wait For Elements State    ${CREATE_DRAWER_TITLE}    visible    timeout=15s
    Wait For Elements State    css=${CREATE_SUBMIT_BUTTON}    stable    timeout=10s

Fill API key name
    [Documentation]    Fills in the API key name in the create drawer.
    ...                Uses Fill Text which replaces any existing value and
    ...                triggers React Hook Form's onChange handler, then
    ...                verifies the value was set correctly.
    [Arguments]    ${name}

    VAR    ${input}    css=input[placeholder="${NAME_INPUT_PLACEHOLDER}"]
    Wait For Elements State    ${input}    visible    timeout=5s
    Wait For Elements State    ${input}    stable    timeout=5s
    Click    ${input}
    Fill Text    ${input}    ${name}
    Get Text    ${input}    ==    ${name}

Submit create API key form
    [Documentation]    Submits the create API key form by clicking the submit button.
    ...                The DrawerForm's submit button is in the DrawerFooter, OUTSIDE
    ...                the <form> element, using React Aria's onPress to call
    ...                formRef.current.requestSubmit(). Uses Click which triggers
    ...                React Aria's pointer-based press handler.

    VAR    ${btn}    css=${CREATE_SUBMIT_BUTTON}
    Wait For Elements State    ${btn}    visible    timeout=5s
    Wait For Elements State    ${btn}    enabled    timeout=5s
    Click    ${btn}

Click copy API key button
    [Documentation]    Clicks the copy button on the key created drawer.

    VAR    ${btn}    css=${COPY_API_KEY_BUTTON}
    Wait For Elements State    ${btn}    visible    timeout=10s
    Click    ${btn}

Click done on key created drawer
    [Documentation]    Clicks the "Done" button to close the key created drawer.

    Click    css=${KEY_CREATED_DONE_BUTTON}
    Wait For Elements State    ${KEY_CREATED_TITLE}    hidden    timeout=10s

Table row containing text should exist
    [Documentation]    Verifies a table row with the given text exists.
    [Arguments]    ${text}

    VAR    ${row}    css=table tbody tr:has-text("${text}")
    Wait For Elements State    ${row}    visible    timeout=15s

Click actions menu on API key row
    [Documentation]    Clicks the actions menu (three dots) on a specific API key row.
    [Arguments]    ${key_name}

    VAR    ${row}    css=table tbody tr:has-text("${key_name}")
    ${actions_btn}=    Get Element    ${row} >> css=button[aria-label="list.actions.label"]
    Click    ${actions_btn}

Click delete action in actions menu
    [Documentation]    Clicks the "Delete API Key" option in the actions dropdown.

    VAR    ${delete_option}    text="Delete API Key"
    Wait For Elements State    ${delete_option}    visible    timeout=5s
    Click    ${delete_option}

Wait for delete confirmation modal
    [Documentation]    Waits for the delete confirmation modal to appear.

    VAR    ${modal}    css=${DELETE_MODAL_SELECTOR}
    Wait For Elements State    ${modal}    visible    timeout=10s

Confirm delete API key
    [Documentation]    Clicks the confirm button on the delete confirmation modal.

    VAR    ${confirm}    css=${CONFIRM_DELETE_BUTTON}
    Click    ${confirm}
    VAR    ${modal}    css=${DELETE_MODAL_SELECTOR}
    Wait For Elements State    ${modal}    hidden    timeout=10s

Table row containing text should not exist
    [Documentation]    Verifies a table row with the given text does not exist.
    [Arguments]    ${text}

    VAR    ${row}    css=table tbody tr:has-text("${text}")
    Wait For Elements State    ${row}    hidden    timeout=15s
