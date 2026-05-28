# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for AIRM secret autodiscovery visibility.
...
...                 These tests verify that autodiscovered secrets (created via kubectl)
...                 are visible in the AIRM UI secrets page alongside AIRM-managed
...                 secrets, and that the UI correctly reflects backend deletion events.
...
...                 Preconditions use API and kubectl keywords to create secrets, then
...                 verify visibility and distinguishability through the browser UI.

# UI resources (feature layer + browser setup)
Resource            resources/common/browser_setup.resource
Resource            resources/secrets.resource

# API resources (infrastructure preconditions, resolved via pythonpath)
Resource            resources/airm_projects.resource
Resource            resources/airm_secrets.resource

Suite Teardown      Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Run Keywords
...                 Close test browser    AND
...                 Clean Up Kubectl Secret


*** Test Cases ***
Autodiscovered secrets are visible alongside managed secrets
    [Documentation]    Verify that a secret created via kubectl is autodiscovered by AIRM
    ...                and displayed in the UI secrets page alongside AIRM-managed secrets.
    ...                The secret type should be distinguishable (KubernetesSecret vs ExternalSecret).
    [Tags]    ui    airm    secrets    autodiscovery

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
