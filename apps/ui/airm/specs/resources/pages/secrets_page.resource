# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Page object for the AIRM UI Secrets page.
...                 Contains selectors and atomic browser interactions only.
...                 Business logic and assertions belong in feature resources.
...
...                 The admin secrets page (/secrets) shows all secrets across the
...                 organization in a table. Each row displays: Name, Type, Use Case,
...                 Status, Scope, Assigned To, Updated At. The Type column uses
...                 data-testid attributes to identify secret types (ExternalSecret
...                 vs KubernetesSecret).


*** Variables ***
${SECRETS_PATH}                     /secrets
${SECRETS_TABLE_SELECTOR}           main table
${SECRETS_ROW_SELECTOR}             main table tbody tr


*** Keywords ***
Navigate to secrets page
    [Documentation]    Navigates to the admin secrets page and waits for the table to load.
    [Arguments]    ${base_url}

    Go To    ${base_url}${SECRETS_PATH}
    VAR    ${table}    css=${SECRETS_TABLE_SELECTOR}
    Wait For Elements State    ${table}    visible    timeout=30s

Secret row should exist with name
    [Documentation]    Verifies a table row containing the given secret name is visible.
    ...                Uses a short timeout to allow the outer retry loop to control polling.
    [Arguments]    ${secret_name}

    VAR    ${row}    css=${SECRETS_ROW_SELECTOR}:has-text("${secret_name}")
    Wait For Elements State    ${row}    visible    timeout=3s

Secret row should not exist with name
    [Documentation]    Verifies no table row containing the given secret name is visible.
    ...                Uses a short timeout to allow the outer retry loop to control polling.
    [Arguments]    ${secret_name}

    VAR    ${row}    css=${SECRETS_ROW_SELECTOR}:has-text("${secret_name}")
    Wait For Elements State    ${row}    detached    timeout=3s

Secret type indicator should exist
    [Documentation]    Verifies that at least one secret type indicator element exists in the
    ...                table. The type column renders data-testid="secret-type-{type}" which
    ...                distinguishes ExternalSecret from KubernetesSecret. Uses nth=0 to
    ...                avoid strict-mode violations when multiple rows share the same type.
    [Arguments]    ${secret_type}

    VAR    ${indicator}    css=[data-testid="secret-type-${secret_type}"] >> nth=0
    Wait For Elements State    ${indicator}    visible    timeout=15s

Secret type indicator should exist in row
    [Documentation]    Verifies that a specific secret row contains the expected type indicator.
    [Arguments]    ${secret_name}    ${secret_type}

    VAR    ${indicator}    css=${SECRETS_ROW_SELECTOR}:has-text("${secret_name}") [data-testid="secret-type-${secret_type}"]
    Wait For Elements State    ${indicator}    visible    timeout=15s
