# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Page object for the AIWB Workspaces catalog page.
...                 Contains selectors and atomic browser interactions only.
...                 Business logic and assertions belong in feature resources.


*** Variables ***
${WORKSPACES_PATH}                      /workspaces


*** Keywords ***
Navigate To Workspaces Page
    [Documentation]    Navigates to the Workspaces page via sidebar link to preserve project context.
    [Arguments]    ${base_url}

    # Use sidebar navigation to avoid full page reload which resets project context
    VAR    ${sidebar_link}    css=a[href="/workspaces"]
    ${link_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    ${sidebar_link}    visible    timeout=5s
    IF    ${link_visible}
        Click    ${sidebar_link}
    ELSE
        Go To    ${base_url}${WORKSPACES_PATH}
    END
    VAR    ${search}    css=input[placeholder="Search workspaces"]
    Wait For Elements State    ${search}    visible    timeout=30s

Click First Workspace Deploy Button
    [Documentation]    Clicks the "View and deploy" button on the first workspace card.

    VAR    ${button}    css=button:has-text("View and deploy") >> nth=0
    Click    ${button}

Wait For Deploy Drawer
    [Documentation]    Waits for the workspace deploy drawer (dialog) to become visible
    ...                and for the form fields to fully load.

    VAR    ${drawer}    css=[role="dialog"]
    Wait For Elements State    ${drawer}    visible    timeout=15s
    # Wait for the imagePullSecrets trigger which loads after catalog item data fetches
    VAR    ${secrets_btn}    css=[role="dialog"] button[aria-label="Image pull secrets"]
    Wait For Elements State    ${secrets_btn}    visible    timeout=30s

Open Image Pull Secrets Dropdown
    [Documentation]    Clicks the imagePullSecrets dropdown trigger to expand options.

    VAR    ${trigger}    css=[role="dialog"] button[aria-label="Image pull secrets"]
    Click    ${trigger}
    # Wait for the listbox popover to appear (ul element, not the wrapper div)
    VAR    ${listbox}    css=ul[role="listbox"][data-slot="listbox"]
    Wait For Elements State    ${listbox}    visible    timeout=10s

Get Image Pull Secrets Options Text
    [Documentation]    Returns the text content of all visible options in the imagePullSecrets dropdown.

    VAR    ${listbox}    css=ul[role="listbox"][data-slot="listbox"]
    ${text}=    Get Text    ${listbox}
    RETURN    ${text}

Close Deploy Drawer
    [Documentation]    Closes the deploy drawer by clicking Cancel.

    VAR    ${cancel}    css=[role="dialog"] button:has-text("Cancel")
    Click    ${cancel}
    VAR    ${drawer}    css=[role="dialog"]
    Wait For Elements State    ${drawer}    detached    timeout=10s
