# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for secret auto-discovery via kubectl.
...                 Verifies that secrets applied directly to AIRM-managed namespaces
...                 are auto-discovered by the webhook and registered in the AIRM API.
Resource            ../resources/airm_secrets.resource
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            resources/api/common.resource
Library             Collections
Test Setup          Run Keywords
...                 Initialize Project Tracking    AND
...                 Initialize Secret ID Tracking
Test Teardown       Run Keywords
...                 Clean Up Kubectl ExternalSecret    AND
...                 Clean Up Kubectl Secret    AND
...                 Clean Up All Created Secrets    AND
...                 Clean Up All Created Projects


*** Test Cases ***
Apply Kubernetes secret and verify auto-discovery
    [Documentation]    Verify that a K8s Secret applied via kubectl in a managed namespace
    ...    is auto-discovered by the webhook and registered in the AIRM API.
    ...    Tests the full pipeline: webhook injection → controller reconciliation → API registration.
    [Tags]    secret    kubectl    autodiscovery

    Given a ready project with user access exists
    When a Kubernetes secret is applied via kubectl
    Then kubectl secret should have tracking labels
    And secret SHOULD be discovered by AIRM
    And auto-discovered secret metadata should be correct    expected_kind=KubernetesSecret

Delete Kubernetes secret via kubectl and verify AIRM removes it
    [Documentation]    Verify that when a user deletes an auto-discovered K8s Secret via kubectl,
    ...    AIRM detects the deletion and removes the secret from its inventory.
    ...    Tests the full pipeline: kubectl delete → controller finalizer → DELETED status → API cleanup.
    [Tags]    secret    kubectl    autodiscovery    delete

    Given a ready project with user access exists
    When a Kubernetes secret is applied via kubectl
    And kubectl secret should have tracking labels
    And secret SHOULD be discovered by AIRM
    When kubectl secret is deleted
    Then secret SHOULD be removed from AIRM

Auto-discovered secret survives pod restart without duplicates
    [Documentation]    Verify that after the AIRM controller pod restarts, an auto-discovered secret
    ...    remains in K8s, stays in AIRM inventory, and does not produce duplicates.
    ...    The controller re-reconciles on startup; register_auto_discovered_secret is idempotent.
    [Tags]    secret    kubectl    autodiscovery    restart

    Given a ready project with user access exists
    When a Kubernetes secret is applied via kubectl
    And kubectl secret should have tracking labels
    And secret SHOULD be discovered by AIRM

    VAR    ${original_secret_id}    ${TEST_SECRET_ID}

    When AIRM controller pod is restarted
    And AIRM controller pod should be ready

    Then kubectl secret should still exist
    And secret SHOULD be discovered by AIRM
    And auto-discovered secret should not be duplicated    ${original_secret_id}

ExternalSecret applied via kubectl is auto-discovered by AIRM
    [Documentation]    Verify that an ExternalSecret resource applied via kubectl in a managed namespace
    ...    is auto-discovered by AIRM and registered with correct metadata.
    ...    AIRM must NOT register the child KubernetesSecret created by the ExternalSecret controller
    ...    as a separate entry — only the ExternalSecret itself should appear.
    [Tags]    secret    kubectl    autodiscovery    externalsecret

    Given a ready project with user access exists
    When an ExternalSecret is applied via kubectl
    Then secret SHOULD be discovered by AIRM    expected_kind=ExternalSecret
    And auto-discovered secret metadata should be correct    expected_kind=ExternalSecret
    And child KubernetesSecret should not be separately discovered by AIRM

Delete ExternalSecret via kubectl and verify AIRM removes it
    [Documentation]    Verify that when a user deletes an auto-discovered ExternalSecret via kubectl,
    ...    AIRM detects the deletion and removes it from inventory.
    ...    Also verifies use-case label normalization on ExternalSecrets.
    [Tags]    secret    kubectl    autodiscovery    externalsecret    delete

    Given a ready project with user access exists
    When an ExternalSecret with use-case "huggingface" is applied via kubectl
    Then secret SHOULD be discovered by AIRM    expected_kind=ExternalSecret
    And discovered secret should have use case "HuggingFace"
    When kubectl ExternalSecret is deleted
    Then secret SHOULD be removed from AIRM

Apply Kubernetes secret with use-case label and verify normalization
    [Documentation]    Verify that a K8s Secret with a use-case label in non-canonical casing
    ...    is auto-discovered with the normalized canonical value.
    ...    Tests the agent's case-insensitive normalization: "huggingface" → "HuggingFace".
    [Tags]    secret    kubectl    autodiscovery    use-case

    Given a ready project with user access exists
    When a Kubernetes secret with use-case "huggingface" is applied via kubectl
    Then kubectl secret should have tracking labels
    And secret SHOULD be discovered by AIRM    expected_kind=KubernetesSecret
    And discovered secret should have use case "HuggingFace"
