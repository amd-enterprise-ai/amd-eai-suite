# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Site-wide navigation keywords for AIWB UI.
...                 Covers project selection and other global navigation elements
...                 that appear across all pages.


*** Keywords ***
Select project
    [Documentation]    Selects a project from the project selector dropdown in the header.
    ...                Skips selection if the project is already active.
    [Arguments]    ${project_name}

    Wait For Elements State    css=main    visible    timeout=15s

    # Check if the project is already selected
    # Use data-testid with >> nth=0 to select the first (toolbar) project selector
    VAR    ${project_btn}    css=[data-testid="project-select"] >> nth=0
    ${already_selected}=    Run Keyword And Return Status
    ...    Get Text    ${project_btn}    contains    ${project_name}

    IF    ${already_selected}
        RETURN
    END

    Click    ${project_btn}

    # Wait for the React Aria listbox dropdown
    VAR    ${listbox}    css=[role="listbox"]
    Wait For Elements State    ${listbox}    visible    timeout=10s

    # Click the project option
    VAR    ${option}    css=li[role="option"][data-key="${project_name}"]
    Click    ${option}

    # Wait for the selector button to reflect the new project
    Wait For Elements State    button[aria-label="Selected project"]:has-text("${project_name}")    visible    timeout=15s
