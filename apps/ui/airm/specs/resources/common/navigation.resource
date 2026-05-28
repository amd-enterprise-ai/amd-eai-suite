# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Site-wide navigation keywords for AIRM UI.
...                 Covers sidebar navigation and page navigation.


*** Keywords ***
Navigate to page
    [Documentation]    Navigates to a page by its path relative to the base URL.
    [Arguments]    ${base_url}    ${path}

    Go To    ${base_url}${path}
    Wait For Elements State    css=main    visible    timeout=15s
