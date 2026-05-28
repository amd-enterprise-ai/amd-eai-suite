# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for dataset UI features.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Library             String
Resource            common/session.resource
Resource            pages/datasets_page.resource
Resource            resources/aiwb_datasets.resource


*** Variables ***
${UI_DATASET_FILE}    ${EXECDIR}/test_data/datasets/sample.jsonl


*** Keywords ***
# =============================================================================
# Given keywords (UI preconditions)
# =============================================================================

User is on datasets page
    [Documentation]    Navigates to the Datasets page via the sidebar link.
    ...                Expects ${TEST_PROJECT} to be set.

    Navigate to datasets page    ${TEST_PROJECT}[name]

# =============================================================================
# When keywords (actions)
# =============================================================================

User uploads a dataset through the UI
    [Documentation]    Uploads a dataset via the upload modal with a unique name.
    ...                Stores the generated name in ${UI_UPLOADED_DATASET_NAME} for verification.
    ...                Retries the full sequence because the modal can close on React re-renders.

    ${random_suffix}=    Generate Random String    8    [LETTERS][NUMBERS]
    VAR    ${name}    e2e-ui-upload-${random_suffix}
    Set Test Variable    ${UI_UPLOADED_DATASET_NAME}    ${name}
    Wait Until Keyword Succeeds    60s    3s    Open fill and submit upload form    ${name}

Open fill and submit upload form
    [Documentation]    Opens the upload modal, fills fields, selects a file, and submits.
    ...                Designed to be retried as a unit if the modal closes unexpectedly.
    [Arguments]    ${name}

    # Dismiss any modal left open from a previous failed attempt
    ${modal_open}=    Run Keyword And Return Status
    ...    Wait For Elements State    ${UPLOAD_MODAL_TITLE}    visible    timeout=1s
    IF    ${modal_open}
        Keyboard Key    press    Escape
        Wait For Elements State    ${UPLOAD_MODAL_TITLE}    hidden    timeout=5s
    END

    Click upload button
    Fill dataset name    ${name}
    Select dataset file    ${UI_DATASET_FILE}
    Submit upload form
    Upload success toast should be visible

User triggers download for dataset "${dataset_name}"
    [Documentation]    Clicks the Download action in the row actions menu for the given dataset.

    Click download action on dataset row    ${dataset_name}

User dismisses the download indicator
    [Documentation]    Clicks the dismiss button on the download indicator and waits for it
    ...                to disappear.

    Click dismiss on download indicator
    Download indicator should be hidden

# =============================================================================
# Then keywords (verification)
# =============================================================================

Download indicator should be in preparing state
    [Documentation]    Verifies the download indicator shows the preparing state.

    Download indicator preparing state should be visible

Download indicator should be in done state
    [Documentation]    Verifies the download indicator transitions to the done state.

    Download indicator done state should be visible

Download indicator should not be visible
    [Documentation]    Verifies the download indicator is fully hidden.

    Download indicator should be hidden

Download indicator should not reappear after dismissal
    [Documentation]    Verifies the "Download ready" indicator does not appear after the indicator
    ...                was dismissed. Waits long enough for any in-flight download to complete,
    ...                confirming the dismissed state is permanent.

    Download done indicator should not appear within    15s

The uploaded dataset should appear in the dataset list
    [Documentation]    Verifies the UI-uploaded dataset appears in the table.

    Dataset row should be visible in table    ${UI_UPLOADED_DATASET_NAME}

Datasets should be listed with their metadata
    [Documentation]    Verifies the datasets table shows rows with name and type metadata.

    Dataset table should have rows
    Dataset row should contain metadata    ${TEST_DATASET}[name]    Fine-tuning

Track UI uploaded dataset for cleanup
    [Documentation]    Looks up the UI-uploaded dataset by name via API and tracks its ID
    ...                for cleanup at suite teardown. Silently skips if test variables are not set.

    ${name}=    Get Variable Value    ${UI_UPLOADED_DATASET_NAME}    ${None}
    IF    $name is None    RETURN
    TRY
        ${namespace}=    Get Project Namespace
        ${response}=    List datasets    ${namespace}    name=${name}    expected_status=200
        ${datasets}=    Evaluate    ${response.json()}["data"]
        ${length}=    Get Length    ${datasets}
        IF    ${length} > 0
            VAR    ${dataset_id}    ${datasets}[0][id]
            Track Dataset For Cleanup    ${dataset_id}
        END
    EXCEPT    AS    ${error}
        Log    Could not track UI-uploaded dataset for cleanup: ${error}    WARN
    END
