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


*** Variables ***
${SEMVER_PATTERN}       \\d+\\.\\d+\\.\\d+


*** Keywords ***
# =============================================================================
# Given keywords (UI preconditions)
# =============================================================================

User is on workloads page
    [Documentation]    Navigates to the Dashboard which contains the workloads table.
    ...                Expects ${UI_BASE_URL} to be set (e.g., by User is logged in).

    Navigate to dashboard    ${UI_BASE_URL}

User is on AIM details page
    [Documentation]    Navigates to the AIM service details page.
    ...                Expects ${UI_BASE_URL} and ${TEST_AIM_ID} to be set.

    Navigate to AIM details page    ${UI_BASE_URL}    ${TEST_AIM_ID}

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
            Log    Attempt ${attempt}: Workload not in table yet, reloading dashboard...    level=WARN
            IF    ${attempt} < 5
                Sleep    10s
                Reload
            ELSE
                Fail    Workload not found in dashboard table after 5 reload attempts
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

    Workload row should show status

Workload details should show logs button
    [Documentation]    Verifies the AIM details page has a Logs button for log access.

    AIM details should show logs button

Workload details should show performance metric
    [Documentation]    Verifies the AIM details page shows the optimization metric.

    AIM details should show performance metric

Deployed workloads list should have entries
    [Documentation]    Verifies the deployed workloads list shows at least one entry.

    ${count}=    Get deployed workload row count
    Should Be True    ${count} > 0    msg=Workloads list should have at least one entry
