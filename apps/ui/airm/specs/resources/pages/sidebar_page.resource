# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Page object for AIRM UI sidebar navigation.
...                 Provides selectors and atomic interactions for sidebar items.
...                 The sidebar renders menu items as links inside a list element.
...                 Role-based filtering hides items not accessible to the current user.
Library             Collections


*** Keywords ***
Wait for sidebar to load
    [Documentation]    Waits for at least one sidebar navigation link to be visible.

    Wait For Elements State    css=li a[role="link"]    visible    timeout=10s

Get visible sidebar items
    [Documentation]    Returns the text content of all visible sidebar navigation links.
    ...                The sidebar renders items as links inside list items (li > a).

    VAR    ${sidebar_links}    css=li a[role="link"]
    ${elements}=    Get Elements    ${sidebar_links}
    VAR    @{items}
    FOR    ${element}    IN    @{elements}
        ${text}=    Get Text    ${element}
        IF    "${text}" != "${EMPTY}"
            Append To List    ${items}    ${text}
        END
    END
    RETURN    ${items}
