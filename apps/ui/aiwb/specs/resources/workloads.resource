# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for workload UI features.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Resource            common/session.resource
Resource            pages/workloads_page.resource
Resource            resources/aiwb_aims.resource


*** Variables ***
${SEMVER_PATTERN}       \\d+\\.\\d+\\.\\d+


*** Keywords ***
# =============================================================================
# Given keywords (UI preconditions)
# =============================================================================

User is on workloads page
    [Documentation]    Navigates to the Dashboard which contains the workloads table.
    ...                Expects ${UI_BASE_URL} and ${TEST_PROJECT} to be set.

    Navigate to dashboard    ${UI_BASE_URL}    ${TEST_PROJECT}[name]

AIM has been deleted
    [Documentation]    Ensures the deployed AIM service is deleted so subsequent UI
    ...                scenarios can exercise the deleted-AIM detail page.
    ...                Requires: TEST_AIM_ID to be set by a preceding "AIM is deployed".

    AIM is undeployed
    Wait for AIM workload to reach state    Deleted    timeout=120

User is on AIM details page
    [Documentation]    Navigates to the AIM service details page.
    ...                Expects ${UI_BASE_URL}, ${TEST_PROJECT}, and ${TEST_AIM_ID} to be set.

    Navigate to AIM details page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]    ${TEST_AIM_ID}

User navigates directly to the deleted AIM detail page by ID
    [Documentation]    Navigates to the details page of an AIM that has been deleted,
    ...                simulating a user opening a stale URL (e.g., from a bookmark).

    User is on AIM details page

User is on workload details page for project "${project_name}"
    [Documentation]    Navigates directly to the workload details URL for the given project.
    ...                Uses a synthetic workload ID — the project switcher is accessible from
    ...                any valid route under [project]/workloads/[id], even a 404 state.
    ...                Expects ${UI_BASE_URL} to be set.

    Navigate to workload details page by id    ${UI_BASE_URL}    ${project_name}    placeholder-workload-id

# =============================================================================
# When keywords (actions)
# =============================================================================

User opens inference workload details
    [Documentation]    Opens the details page for the inference workload.
    ...                If TEST_AIM_ID is set, finds that specific workload in the table and opens it.
    ...                Otherwise, finds and clicks the first inference workload via the actions menu.
    ...                Retries with page reload if workload not found (may need time to sync).

    ${workload_id}=    Get Variable Value    ${TEST_AIM_ID}    ${None}

    # Retry with reload if workload not found in table (may need time to sync from backend)
    FOR    ${attempt}    IN RANGE    1    6
        TRY
            Click actions menu on inference workload    ${workload_id}
            Click open details in actions menu
            BREAK
        EXCEPT
            IF    ${attempt} < 5
                Log    Attempt ${attempt}: Workload not in table yet, reloading dashboard...    level=WARN
                Reload
                VAR    ${grid}    css=${WORKLOADS_GRID_SELECTOR}
                Wait For Elements State    ${grid}    visible    timeout=15s
            ELSE
                Fail    Workload not found in dashboard table after 4 reload attempts
            END
        END
    END

# =============================================================================
# Then keywords (verification)
# =============================================================================

Inference workload should show AIM version in list
    [Documentation]    Verifies an inference workload row contains a semver version string.

    ${text}=    Get inference workload row text
    Should Match Regexp    ${text}    ${SEMVER_PATTERN}

Workload details should show AIM version
    [Documentation]    Verifies the workload details page shows the AIM image version
    ...                under the Container version field.

    ${version}=    Get container version text
    Should Match Regexp    ${version}    ${SEMVER_PATTERN}

Inference workload should show status in list
    [Documentation]    Verifies an inference workload row displays a status indicator.

    ${text}=    Get inference workload status text
    ${has_status}=    Evaluate
    ...    any(s in '''${text}''' for s in ['Running', 'Pending', 'Failed', 'Deleting', 'Starting'])
    Should Be True    ${has_status}    msg=Workload row should show a status indicator

Workload details should show logs button
    [Documentation]    Verifies the workload details page has a Logs button for log access.

    ${visible}=    Is logs button visible
    Should Be True    ${visible}    msg=Workload details page should have a Logs button

Workload details should show performance metric
    [Documentation]    Verifies the workload details page shows the optimization metric.

    ${visible}=    Is performance metric visible
    Should Be True    ${visible}    msg=Workload details page should show the Performance metric field

Deployed workloads list should have entries
    [Documentation]    Verifies the deployed workloads list shows at least one entry.

    ${count}=    Get deployed workload row count
    Should Be True    ${count} > 0    msg=Workloads list should have at least one entry

Inference workload should be listed by its model display name
    [Documentation]    Verifies the dashboard workloads table presents the deployed model by
    ...                its user-facing display name rather than an internal identifier.
    ...                Requires: TEST_AIM_DISPLAY_NAME and TEST_AIM_NAME set by "AIM is deployed".

    ${grid_text}=    Get workloads grid text
    Should Contain    ${grid_text}    ${TEST_AIM_DISPLAY_NAME}
    ...    msg=Dashboard workloads table should show the model display name '${TEST_AIM_DISPLAY_NAME}'
    # Only assert the internal identifier is hidden when it actually differs from the
    # display name; some AIMs legitimately use their resource name as the display name.
    IF    '${TEST_AIM_NAME}' != '${TEST_AIM_DISPLAY_NAME}'
        Should Not Contain    ${grid_text}    ${TEST_AIM_NAME}
        ...    msg=Dashboard workloads table should not expose the internal identifier '${TEST_AIM_NAME}'
    END

User clicks connect to model button
    [Documentation]    Clicks the Connect to model button in the Output card header.

    Click connect to model button

Connect to model dialog should be visible
    [Documentation]    Verifies the Connect to model modal is open and visible.

    ${visible}=    Is connect modal visible
    Should Be True    ${visible}    msg=Connect to model modal should be visible

Connection snippet should target the served model id
    [Documentation]    Verifies the generated snippet's OpenAI `model` field is the
    ...                AIM served id (status.aimId) that vLLM registers the model
    ...                under — not the human-facing canonical display name — so the
    ...                request would not 404.
    ...                Requires: TEST_AIM_NAME to be set by a preceding "AIM is deployed".

    ${served_model_id}=    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Resolve Cluster Model aimId    ${TEST_AIM_NAME}
    ${snippet}=            Get connection snippet text
    Should Contain    ${snippet}    "model": "${served_model_id}"
    ...    msg=Snippet model field should be the served id ${served_model_id}, not the canonical name

Historical AIM details should be rendered
    [Documentation]    Verifies that the AIM details page renders content for a deleted
    ...                AIM (Basic information section is visible). The page reaches this
    ...                state by falling back to the deleted-history list when the live
    ...                lookup 404s.

    ${visible}=    Is basic information section visible
    Should Be True    ${visible}    msg=Basic information section should render for a deleted AIM

The delete button should be disabled
    [Documentation]    Verifies the Delete action button on the AIM details page is
    ...                disabled for an already-deleted AIM.

    ${disabled}=    Is delete button disabled
    Should Be True    ${disabled}    msg=Delete button should be disabled for a deleted AIM
