# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for AIRM secrets management and autodiscovery.
...
...                 Management tests verify the admin secrets page operations:
...                 viewing secrets with metadata, creating secrets, deleting
...                 secrets, assigning secrets to projects, and searching by name.
...
...                 Autodiscovery tests verify that secrets created via kubectl are
...                 visible in the AIRM UI alongside AIRM-managed secrets, and that
...                 the UI correctly reflects backend deletion events.
...
...                 Preconditions use API and kubectl keywords to create test data,
...                 then verify the operations through the browser UI.

# UI resources (feature layer + browser setup)
Resource            resources/common/browser_setup.resource
Resource            resources/secrets.resource

# API resources (infrastructure preconditions, resolved via pythonpath)
Resource            resources/airm_projects.resource
Resource            resources/airm_secrets.resource

Suite Teardown      Run Keywords
...                 Clean Up All Created Secrets    AND
...                 Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
# =============================================================================
# Secrets management tests
# =============================================================================

Secrets list displays secrets with metadata columns
    [Documentation]    Verify that admin can see secrets listed with name, type,
    ...                use case, scope, and project assignment information.
    [Tags]    ui    airm    secrets    smoke

    Given an admin user is logged in to AIRM
    When the user is on the secrets page
    Then secrets should be listed with table columns

Admin creates a new organization-level secret
    [Documentation]    Verify that admin can create a new secret through the UI
    ...                and the secret appears in the table after creation.
    [Tags]    ui    airm    secrets    create

    Given a valid ExternalSecret manifest exists
    And an admin user is logged in to AIRM
    And the user is on the secrets page
    When the user creates a secret with the test manifest
    And the user searches for "${TEST_SECRET_NAME}"
    Then secret "${TEST_SECRET_NAME}" should be visible in the secrets table
    And secret "${TEST_SECRET_NAME}" should show scope "Organization"
    And secret "${TEST_SECRET_NAME}" should show type "External Secret"

Admin deletes an unassigned secret
    [Documentation]    Verify that admin can delete a secret through the actions menu
    ...                and the secret is removed from the table.
    [Tags]    ui    airm    secrets    delete

    Given a valid ExternalSecret manifest exists
    And secret is created without project assignment    ${TEST_SECRET_NAME}
    And an admin user is logged in to AIRM
    And the user is on the secrets page
    And the user searches for "${TEST_SECRET_NAME}"
    And secret "${TEST_SECRET_NAME}" should be visible in the secrets table
    When the user deletes the secret and confirms
    Then secret "${TEST_SECRET_NAME}" should not be visible in the secrets table

Admin assigns a secret to a project
    [Documentation]    Verify that admin can assign an organization-level secret to a project
    ...                through the edit assignment dialog and the assignment is reflected
    ...                in the secrets list.
    [Tags]    ui    airm    secrets    assign

    Given an organization-level secret and a ready project exist
    And an admin user is on the secrets page
    And the user searches for "${TEST_SECRET_NAME}"
    When the user assigns the secret to the project
    Then the project count for the secret is updated

Admin searches for a secret by name
    [Documentation]    Verify that the search filter narrows the secrets list
    ...                to matching entries.
    [Tags]    ui    airm    secrets    search

    Given a valid ExternalSecret manifest exists
    And secret is created without project assignment    ${TEST_SECRET_NAME}
    And an admin user is logged in to AIRM
    And the user is on the secrets page
    When the user searches for "${TEST_SECRET_NAME}"
    Then secret "${TEST_SECRET_NAME}" should be visible in the secrets table
    And the secrets table should only show secrets matching "${TEST_SECRET_NAME}"

# =============================================================================
# Secrets autodiscovery tests
# =============================================================================

Autodiscovered secrets are visible alongside managed secrets
    [Documentation]    Verify that a secret created via kubectl is autodiscovered by AIRM
    ...                and displayed in the UI secrets page alongside AIRM-managed secrets.
    ...                The secret type should be distinguishable (KubernetesSecret vs ExternalSecret).
    [Tags]    ui    airm    secrets    autodiscovery
    [Teardown]    Run Keywords    Close test browser    AND    Clean Up Kubectl Secret

    Given a ready project with user access exists
    And a valid ExternalSecret manifest exists
    And secret is created and assigned to project
    And secret transitions to "Synced"
    And a Kubernetes secret is applied via kubectl
    And secret should be discovered by AIRM
    And an admin user is logged in
    When the user views the secrets page
    Then the kubectl secret should be visible in the secrets table
    And the kubectl secret should be identified as "KubernetesSecret"
    And the secrets table should distinguish secret sources

Deleted autodiscovered secret is removed from UI
    [Documentation]    Verify that when a kubectl-applied secret is deleted from the cluster,
    ...                AIRM detects the deletion and removes it from the UI display.
    [Tags]    ui    airm    secrets    autodiscovery    deletion
    [Teardown]    Run Keywords    Close test browser    AND    Clean Up Kubectl Secret

    Given a ready project with user access exists
    And a Kubernetes secret is applied via kubectl
    And secret should be discovered by AIRM
    And an admin user is logged in
    And the user views the secrets page
    And the kubectl secret should be visible in the secrets table
    When kubectl secret is deleted
    And secret should be removed from AIRM
    And the user refreshes the secrets page
    Then the kubectl secret should not be visible in the secrets table
