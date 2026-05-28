# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for the global user menu.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Resource            common/session.resource
Resource            pages/user_menu_page.resource


*** Keywords ***
# =============================================================================
# When keywords (actions)
# =============================================================================

User opens the user menu
    [Documentation]    Opens the global user menu dropdown from the header.

    Open user menu

# =============================================================================
# Then keywords (verification)
# =============================================================================

Report issue menu entry should link to support mailto
    [Documentation]    Verifies the "Report issue" entry in the user menu exposes a
    ...                support mailto link with the expected subject. Clicking a mailto
    ...                cannot be verified end-to-end in the browser, so we assert the
    ...                anchor target instead.

    ${href}=    Get report issue menu item href
    Should Start With    ${href}    mailto:amd-eai-support@amd.com
    Should Contain    ${href}    subject=Issue%20report
