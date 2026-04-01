# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Page object for the AIWB Dashboard workloads section.
...                 Contains selectors and atomic browser interactions only.
...                 The workloads table is on the Dashboard page (/).
...                 Business logic and assertions belong in feature resources.


*** Variables ***
${DASHBOARD_PATH}                  /
${AIM_DETAILS_PATH}                /aims
${WORKLOADS_GRID_SELECTOR}         [role="grid"]
${WORKLOAD_ROW_SELECTOR}           [role="row"]
${ACTIONS_BUTTON_SELECTOR}         button[aria-label="list.actions.label"]
${DETAILS_BUTTON_SELECTOR}         [data-testid="details"]
${CONTAINER_VERSION_SELECTOR}      h5:has-text("Container version") + p
${AIM_LABEL_SELECTOR}             text="AIM"
${CONTAINER_VERSION_LABEL}        text="Container version"
${LOGS_BUTTON_SELECTOR}           button:has-text("Logs")
${STATUS_DISPLAY_SELECTOR}        [class*="status"], [class*="Status"]
${METRICS_SECTION_SELECTOR}       text="Inference metrics"
${BASIC_INFO_SECTION_SELECTOR}    text="Basic information"
${CHAT_BUTTON_SELECTOR}           button:has-text("Chat")
${DELETE_BUTTON_SELECTOR}         button:has-text("Delete")


*** Keywords ***
Navigate to dashboard
    [Documentation]    Navigates to the Dashboard which contains the workloads table.
    [Arguments]    ${base_url}

    Go To    ${base_url}${DASHBOARD_PATH}
    VAR    ${grid}    css=${WORKLOADS_GRID_SELECTOR}
    Wait For Elements State    ${grid}    visible    timeout=15s

Navigate to AIM details page
    [Documentation]    Navigates directly to an AIM service details page.
    [Arguments]    ${base_url}    ${service_id}

    Go To    ${base_url}${AIM_DETAILS_PATH}/${service_id}
    Wait For Elements State    ${BASIC_INFO_SECTION_SELECTOR}    visible    timeout=30s

Get inference workload row text
    [Documentation]    Returns the text content of the first inference workload row.

    VAR    ${row_selector}    css=${WORKLOAD_ROW_SELECTOR}:has-text("Inference")
    ${rows}=    Get Elements    ${row_selector}
    ${row}=    Set Variable    ${rows}[0]
    ${text}=    Get Text    ${row}
    RETURN    ${text}

Click actions menu on inference workload
    [Documentation]    Clicks the actions menu on the inference workload row.
    ...                If workload_id is provided, selects that specific workload.
    ...                Otherwise, selects the first inference workload found.
    [Arguments]    ${workload_id}=${None}

    IF    $workload_id is not None
        # Use data-key attribute to find specific workload by ID
        VAR    ${row_selector}    css=[role="row"]\[data-key="${workload_id}"]
        # Wait for the specific workload to appear in the table (may take time after deployment)
        # Longer timeout for workloads to sync from K8s to UI
        TRY
            Wait For Elements State    ${row_selector}    visible    timeout=30s
        EXCEPT
            Take Screenshot    workload-not-found-debug
            # Get all visible workload rows for debugging
            ${all_rows}=    Get Elements    css=[role="row"]
            ${count}=    Get Length    ${all_rows}
            Log    Found ${count} total rows in table    level=WARN
            FOR    ${row}    IN    @{all_rows}
                ${row_html}=    Get Property    ${row}    outerHTML
                Log    Row HTML: ${row_html}    level=DEBUG
            END
            Fail    Workload ${workload_id} not found in UI table after 30s. Check screenshot for details.
        END
    ELSE
        # Fall back to first inference workload
        VAR    ${row_selector}    css=${WORKLOAD_ROW_SELECTOR}:has-text("Inference") >> nth=0
    END

    ${row}=    Get Element    ${row_selector}
    VAR    ${actions_btn}    ${row} >> css=${ACTIONS_BUTTON_SELECTOR}
    Click    ${actions_btn}
    VAR    ${details}    css=${DETAILS_BUTTON_SELECTOR}
    Wait For Elements State    ${details}    visible    timeout=5s

Click open details in actions menu
    [Documentation]    Clicks "Open details" in the currently visible actions menu.

    VAR    ${details}    css=${DETAILS_BUTTON_SELECTOR}
    Click    ${details}
    Wait For Elements State    ${AIM_LABEL_SELECTOR}    visible    timeout=15s

Get container version text
    [Documentation]    Returns the Container version value from the workload details page.

    Wait For Elements State    ${CONTAINER_VERSION_LABEL}    visible    timeout=10s
    VAR    ${selector}    css=${CONTAINER_VERSION_SELECTOR}
    ${version}=    Get Text    ${selector}
    RETURN    ${version}

Get deployed workload row count
    [Documentation]    Returns the number of workload rows in the grid.

    ${elements}=    Get Elements    css=${WORKLOAD_ROW_SELECTOR}
    ${count}=    Get Length    ${elements}
    RETURN    ${count}

Workload row should show status
    [Documentation]    Verifies that an inference workload row displays a status indicator.

    VAR    ${row_selector}    css=${WORKLOAD_ROW_SELECTOR}:has-text("Inference")
    ${rows}=    Get Elements    ${row_selector}
    ${row}=    Set Variable    ${rows}[0]
    ${text}=    Get Text    ${row}
    # Workloads should show one of these statuses
    ${has_status}=    Evaluate
    ...    any(s in '''${text}''' for s in ['Running', 'Pending', 'Failed', 'Deleting', 'Starting'])
    Should Be True    ${has_status}    msg=Workload row should show a status indicator

AIM details should show logs button
    [Documentation]    Verifies the AIM details page has a Logs button.

    Wait For Elements State    css=${LOGS_BUTTON_SELECTOR}    visible    timeout=10s

AIM details should show performance metric
    [Documentation]    Verifies the AIM details page shows the Performance metric field.

    VAR    ${selector}    text="Performance metric"
    Wait For Elements State    ${selector}    visible    timeout=10s
