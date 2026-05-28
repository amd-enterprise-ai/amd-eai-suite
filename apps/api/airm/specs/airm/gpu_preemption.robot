# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for GPU idle workload pre-emption configuration.
...
...                 **What this tests:** Platform admins can configure GPU idle workload
...                 pre-emption on projects. When enabled, the Kaiwo agent monitors GPU
...                 utilization and pre-empts idle workloads based on configured thresholds,
...                 grace periods, and policies.
...
...                 **Configuration:** enabled (bool), threshold (0-100%), gracePeriod
...                 (minimum 900s, multiple of 60), policy (OnPressure | Always).
...
...                 **Kubernetes integration:** Config is propagated as namespace annotations
...                 (kaiwo.silogen.ai/gpu-preemption.*) read by the Kaiwo agent.
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            ../resources/airm_workloads.resource
Resource            ../resources/kubectl_verification.resource
Resource            resources/api/common.resource
Test Setup          Initialize Workload Tracking
Test Teardown       Clean Up GPU Pre-emption Test Resources


*** Test Cases ***
# --- Tier 1: Configuration via API ---

Project created without GPU pre-emption has it disabled by default
    [Documentation]    Creating a project without specifying GPU pre-emption config results in disabled state.
    [Tags]    projects    gpu-preemption    create

    Given a cluster exists in system
    And valid project data is prepared

    When create project request is sent

    Then project GPU pre-emption should be disabled

Project created with GPU pre-emption enabled persists all settings
    [Documentation]    Creating a project with GPU pre-emption enabled persists threshold, grace period, and policy.
    [Tags]    projects    gpu-preemption    create

    Given a cluster exists in system
    And project data with gpu preemption is prepared    threshold=10    gracePeriod=1800    policy=OnPressure

    When create project request is sent

    Then project GPU pre-emption config should match
    ...    enabled=${TRUE}    threshold=10    gracePeriod=1800    policy=OnPressure

Project created with Always pre-emption policy
    [Documentation]    The "Always" pre-emption policy is accepted and persisted at project creation.
    [Tags]    projects    gpu-preemption    create

    Given a cluster exists in system
    And project data with gpu preemption is prepared    threshold=50    gracePeriod=3600    policy=Always

    When create project request is sent

    Then project GPU pre-emption config should match
    ...    enabled=${TRUE}    threshold=50    gracePeriod=3600    policy=Always

Enable GPU pre-emption on existing project
    [Documentation]    GPU pre-emption can be enabled on a project that was created without it.
    [Tags]    projects    gpu-preemption    update

    Given a project exists
    And updated project data with gpu preemption enabled is prepared

    When update project request is sent

    Then project GPU pre-emption config should match
    ...    enabled=${TRUE}    threshold=10    gracePeriod=1800    policy=OnPressure

Change GPU pre-emption settings on existing project
    [Documentation]    GPU pre-emption threshold, grace period, and policy can be updated on an existing project.
    [Tags]    projects    gpu-preemption    update

    Given a project with GPU pre-emption enabled exists
    And updated project data with gpu preemption enabled is prepared
    ...    threshold=75    gracePeriod=900    policy=Always

    When update project request is sent

    Then project GPU pre-emption config should match
    ...    enabled=${TRUE}    threshold=75    gracePeriod=900    policy=Always

Disable GPU pre-emption on existing project
    [Documentation]    GPU pre-emption can be disabled on a project that previously had it enabled.
    [Tags]    projects    gpu-preemption    update

    Given a project with GPU pre-emption enabled exists
    And updated project data with gpu preemption disabled is prepared

    When update project request is sent

    Then project GPU pre-emption should be disabled

GPU pre-emption config preserved when updating description only
    [Documentation]    Updating only the project description does not reset GPU pre-emption settings.
    [Tags]    projects    gpu-preemption    update

    Given a project with GPU pre-emption enabled exists
    And updated project data with new description preserving gpu preemption is prepared

    When update project request is sent

    Then project GPU pre-emption config should match
    ...    enabled=${TRUE}    threshold=10    gracePeriod=1800    policy=OnPressure

# --- Tier 2: Kubernetes Annotations ---

Namespace has GPU pre-emption annotations when enabled
    [Documentation]    Enabling GPU pre-emption propagates kaiwo annotations to the project namespace.
    [Tags]    projects    gpu-preemption    kubectl

    Given a cluster exists in system
    And project data with gpu preemption is prepared    threshold=10    gracePeriod=1800    policy=OnPressure

    When create project request is sent

    Then project should transition to "ready"
    And project namespace should have GPU pre-emption annotations
    ...    threshold=10    gracePeriod=1800s    policy=OnPressure

Namespace has no GPU pre-emption annotations when disabled
    [Documentation]    Projects without GPU pre-emption enabled have no kaiwo annotations on their namespace.
    [Tags]    projects    gpu-preemption    kubectl

    Given a cluster exists in system
    And valid project data is prepared

    When create project request is sent

    Then project should transition to "ready"
    And project namespace should not have GPU pre-emption annotations

Namespace annotations update when GPU pre-emption config changes
    [Documentation]    Changing GPU pre-emption settings updates the kaiwo annotations on the namespace.
    [Tags]    projects    gpu-preemption    kubectl    update

    Given a cluster exists in system
    And project data with gpu preemption is prepared    threshold=10    gracePeriod=1800    policy=OnPressure
    And create project request is sent
    And project should transition to "ready"

    When updated project data with gpu preemption enabled is prepared
    ...    threshold=75    gracePeriod=900    policy=Always
    And update project request is sent

    Then project should transition to "ready"
    And project namespace should have GPU pre-emption annotations
    ...    threshold=75    gracePeriod=900s    policy=Always

# --- Tier 3: Workload Pre-emption Behavior ---

Idle GPU workload pre-empted with Always policy
    [Documentation]    With the "Always" pre-emption policy, Kaiwo pre-empts idle GPU workloads
    ...    after the configured grace period elapses, regardless of resource pressure.
    [Tags]    projects    gpu-preemption    gpu    kubectl    long-running

    Given a fresh project with 1 GPU quota and user access exists
    And GPU pre-emption is enabled on the project    threshold=5    gracePeriod=900    policy=Always
    And an idle GPU workload is running in the project

    Then the workload should be pre-empted    timeout=20 min
