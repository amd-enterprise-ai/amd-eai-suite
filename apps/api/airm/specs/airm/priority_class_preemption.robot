# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Kueue WorkloadPriorityClass-based workload preemption.
...
...                 **What this tests:** Workloads with higher priority classes (medium, high)
...                 preempting lower priority workloads (low) when GPU resources are exhausted.
...
...                 **Kueue mechanism:** WorkloadPriorityClass preemption. Priority is set via
...                 kueue.x-k8s.io/priority-class label on Jobs. Higher priority workloads can
...                 evict lower priority workloads to claim resources.
...
...                 **Note:** This is DIFFERENT from quota preemption (see quota_preemption.robot).
...                 Priority class preemption is about workload priority, not resource guarantees.
Resource            ../resources/airm_workloads.resource
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            resources/common/resource_resolver.resource
Library             Collections
Test Setup          Run keywords
...                 Initialize project tracking    AND
...                 Initialize workload ID tracking
Test Teardown       Run keywords
...                 Clean up kubectl jobs in test project    AND
...                 Clean up all created workloads    AND
...                 Clean up all created projects


*** Test Cases ***
Medium priority workload preempts low priority workload in same project
    [Documentation]    Verify that medium priority workload can preempt low priority workload
    ...    when GPU resources are exhausted. Submits low priority workloads to fill the entire
    ...    cluster GPU capacity (via cohort borrowing), then submits medium priority workload
    ...    which should preempt one of the running low priority workloads.
    [Tags]    workload    preemption    priority-class    gpu    kubectl

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And cluster GPU resources are exhausted with workloads    priority_class=low

    When a "medium" priority GPU workload is submitted    gpu_count=1

    Then workload should be running
    And at least one "low" priority workload should be suspended

High priority workload preempts medium priority workload
    [Documentation]    Verify that high priority workload can preempt medium priority workload
    ...    when GPU resources are exhausted. Medium priority workload uses 1 GPU, then high
    ...    priority requests all available GPUs, forcing Kueue to preempt the medium priority job.
    [Tags]    workload    preemption    priority-class    gpu    kubectl

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And cluster GPU resources are exhausted with workloads    priority_class=medium

    When a "high" priority GPU workload is submitted    gpu_count=1

    Then workload should be running
    And at least one "medium" priority workload should be suspended

High priority workload preempts low priority workload
    [Documentation]    Verify that high priority workload can preempt low priority workload
    ...    when GPU resources are exhausted. Submits low priority workloads to fill the entire
    ...    cluster GPU capacity (via cohort borrowing), then submits high priority workload
    ...    which should preempt one of the running low priority workloads.
    [Tags]    workload    preemption    priority-class    gpu    kubectl

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And cluster GPU resources are exhausted with workloads    priority_class=low

    When a "high" priority GPU workload is submitted    gpu_count=1

    Then workload should be running
    And at least one "low" priority workload should be suspended

Same priority workloads do not preempt each other
    [Documentation]    Verify that workloads with same priority class do not preempt each other.
    ...    Exhausts cluster GPU capacity with low priority workloads (creates 16 jobs, some running,
    ...    some suspended due to physical capacity), then submits another low priority workload.
    ...    The new workload should remain Pending/Suspended without preempting any of the existing
    ...    low priority workloads. This is a NEGATIVE test - verifying that same-priority workloads
    ...    respect FIFO ordering and do not preempt each other (unlike different priority workloads).
    [Tags]    workload    preemption    priority-class    gpu    kubectl

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And cluster GPU resources are exhausted with workloads    priority_class=low

    When a "low" priority GPU workload is submitted    gpu_count=1

    Then workload should be pending or suspended
    And none of the initial "low" priority workloads should be newly suspended


*** Keywords ***
Clean up kubectl jobs in test project
    [Documentation]    Cleans up all kubectl-created GPU jobs in the test project namespace
    ...    Required because tests reuse the e2e-testing project which doesn't get deleted between tests
    ${project}=    Get Variable Value    ${TEST_PROJECT}    ${None}

    IF    $project == $None
        Log    No test project to clean up    WARN
        RETURN
    END

    # Delete all jobs in the test namespace (kubectl-created jobs)
    # Deletion is async - subsequent tests will wait for their own clean state
    ${namespace}=    Get From Dictionary    ${project}    name
    ${result}=    Run Process    kubectl    delete    jobs    --all    -n    ${namespace}    --ignore-not-found\=true
    Log    Cleaned up kubectl jobs in namespace ${namespace}: ${result.stdout}    INFO
