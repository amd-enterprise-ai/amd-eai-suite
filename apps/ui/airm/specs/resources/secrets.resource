# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Feature-layer keywords for AIRM UI secrets autodiscovery testing.
...                 Composes page-level interactions into business-meaningful keywords
...                 that verify autodiscovered secrets are visible and distinguishable
...                 from AIRM-managed secrets in the admin secrets page.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Resource            common/session.resource
Resource            pages/secrets_page.resource


*** Keywords ***
# =============================================================================
# Precondition keywords (Given steps)
# =============================================================================

An admin user is logged in
    [Documentation]    Logs in as a platform administrator who can access the secrets page.
    Admin user is logged in

# =============================================================================
# Action keywords (When steps)
# =============================================================================

The user views the secrets page
    [Documentation]    Navigates to the admin secrets page.
    ...                Expects ${UI_BASE_URL} to be set via login.
    Navigate to secrets page    ${UI_BASE_URL}

The user refreshes the secrets page
    [Documentation]    Reloads the secrets page to pick up backend state changes.
    ...                Expects ${UI_BASE_URL} to be set via login.
    Navigate to secrets page    ${UI_BASE_URL}

# =============================================================================
# Assertion keywords (Then steps)
# =============================================================================

The kubectl secret should be visible in the secrets table
    [Documentation]    Verifies the autodiscovered kubectl secret appears in the table.
    ...                Resolves the secret name from the test state set during preconditions.
    ${name}=    The kubectl secret name
    Wait Until Keyword Succeeds    15s    2s
    ...    Secret row should exist with name    ${name}

The kubectl secret should not be visible in the secrets table
    [Documentation]    Verifies the autodiscovered kubectl secret is no longer in the table.
    ...                Resolves the secret name from the test state set during preconditions.
    ${name}=    The kubectl secret name
    Wait Until Keyword Succeeds    15s    2s
    ...    Secret row should not exist with name    ${name}

The kubectl secret should be identified as "${secret_type}"
    [Documentation]    Verifies the autodiscovered kubectl secret row shows the expected
    ...                type indicator, confirming the UI distinguishes the secret source.
    ${name}=    The kubectl secret name
    Secret type indicator should exist in row    ${name}    ${secret_type}

The secrets table should distinguish secret sources
    [Documentation]    Verifies that the secrets table contains both ExternalSecret and
    ...                KubernetesSecret type indicators, confirming the UI renders
    ...                different secret sources as distinguishable.
    Secret type indicator should exist    ExternalSecret
    Secret type indicator should exist    KubernetesSecret

# =============================================================================
# Resource resolver keywords
# =============================================================================

The kubectl secret name
    [Documentation]    Returns the name of the kubectl secret created during preconditions.
    ...                Validates that the test state variable has been set.
    Should Not Be Equal    ${TEST_KUBECTL_SECRET_NAME}    ${None}
    ...    msg=TEST_KUBECTL_SECRET_NAME not set. Apply a secret via kubectl first.
    RETURN    ${TEST_KUBECTL_SECRET_NAME}
