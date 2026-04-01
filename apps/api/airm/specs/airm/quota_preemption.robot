# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Kueue quota-based workload preemption.
...
...                 **What this tests:** Projects with guaranteed GPU quotas can reclaim
...                 (preempt) GPUs that were borrowed by projects with zero guaranteed quota.
...
...                 **Test design:** Each preemption test creates a zero-quota "filler" project
...                 that borrows all cluster GPUs, then a guaranteed-quota project submits a
...                 workload. Kueue's reclaimWithinCohort mechanism preempts the filler's
...                 borrowed workloads to satisfy the guaranteed quota.
...
...                 **Kueue mechanism:** ClusterQueue cohort borrowing with reclaimWithinCohort: Any.
...                 Zero-quota projects can borrow free GPUs, but guaranteed-quota projects can
...                 reclaim those borrowed resources when they need them.
...
...                 **Note:** This is DIFFERENT from priority class preemption (see
...                 priority_class_preemption.robot). Quota preemption is about resource
...                 guarantees, not workload priority.
Resource            ../resources/airm_workloads.resource
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            ../resources/kubectl_priority_class.resource
Resource            resources/common/resource_resolver.resource
Resource            resources/api/common.resource
Resource            resources/authorization.resource
Library             Collections
Library             Process
Test Setup          Run keywords
...                 Initialize project tracking    AND
...                 Initialize Workload Tracking
Test Teardown       Clean up quota preemption test resources


*** Keywords ***
Clean up quota preemption test resources
    [Documentation]    Clean up all resources created during preemption tests.
    ...    Cleans kubectl jobs from all tracked namespaces before project deletion.
    Clean up kubectl jobs in tracked namespaces
    Clean up all created workloads
    Clean up all created projects

Clean up kubectl jobs in tracked namespaces
    [Documentation]    Deletes all kubectl jobs from namespaces used during the test
    @{namespaces}=    Get Variable Value    ${QUOTA_TEST_NAMESPACES}    @{EMPTY}
    FOR    ${namespace}    IN    @{namespaces}
        Run Keyword And Ignore Error
        ...    Run Process    kubectl    delete    jobs    --all    -n    ${namespace}    --ignore-not-found\=true
    END

Fill cluster from zero-quota filler project
    [Documentation]    Creates a zero-quota filler project and fills the cluster with 1-GPU jobs.
    ...    All jobs borrow GPUs since the project has zero guaranteed quota.
    ...    Uses the same cluster-filling pattern as priority class preemption tests.
    ...    Stores filler namespace and job names for preemption verification.
    [Arguments]    ${project_suffix}

    ${filler_project}=    Test Name    ${project_suffix}
    A ready project with user access exists    project_name=${filler_project}
    ${namespace}=    Set Variable    ${TEST_PROJECT}[name]

    # Track namespace for cleanup
    @{namespaces}=    Get Variable Value    ${QUOTA_TEST_NAMESPACES}    @{EMPTY}
    Append To List    ${namespaces}    ${namespace}
    Set Test Variable    @{QUOTA_TEST_NAMESPACES}    @{namespaces}

    # Zero quota — all GPU usage is borrowed from the cohort
    Project quota is set to    gpu_count=${0}

    # Fill cluster using the shared exhaustion keyword (submits 1-GPU jobs)
    Cluster GPU resources are exhausted with workloads    priority_class=low

    # Save filler state for preemption assertions
    Set Test Variable    ${FILLER_NAMESPACE}    ${namespace}
    Set Test Variable    @{FILLER_JOB_NAMES}    @{TEST_LOW_PRIORITY_JOB_NAMES}

    RETURN    ${namespace}

At least N filler jobs should be suspended
    [Documentation]    Verifies at least N of the filler jobs were suspended (preempted).
    [Arguments]    ${expected_count}

    Wait Until Keyword Succeeds    3 min    5 sec
    ...    Verify filler job suspension count    ${expected_count}

Verify filler job suspension count
    [Documentation]    Counts suspended filler jobs and verifies >= expected_count
    [Arguments]    ${expected_count}

    ${suspended_count}=    Set Variable    ${0}
    FOR    ${job_name}    IN    @{FILLER_JOB_NAMES}
        ${is_suspended}=    Run Keyword And Return Status
        ...    Verify kubectl job suspended    ${FILLER_NAMESPACE}    ${job_name}
        IF    ${is_suspended}
            ${suspended_count}=    Evaluate    ${suspended_count} + 1
        END
    END

    Should Be True    ${suspended_count} >= ${expected_count}
    ...    msg=Expected at least ${expected_count} filler jobs suspended, but found ${suspended_count}


*** Test Cases ***
Zero-quota project can borrow GPUs when cluster has free capacity
    [Documentation]    Verify that projects with zero GPU quota can still borrow
    ...    free GPU resources via Kueue cohort borrowing.
    ...    This is a precondition for the preemption tests below.
    [Tags]    workload    preemption    quota    gpu    borrowing

    ${project}=    Test Name    borrow-test
    Given a ready project with user access exists    project_name=${project}
    ${namespace}=    Set Variable    ${TEST_PROJECT}[name]

    @{namespaces}=    Create List    ${namespace}
    Set Test Variable    @{QUOTA_TEST_NAMESPACES}    @{namespaces}

    And project quota is set to    gpu_count=${0}

    ${job_name}=    When submit GPU job with priority class via kubectl
    ...    ${namespace}    ${1}    low    sleep_seconds=300
    Then kubectl job should be running    ${namespace}    ${job_name}

Guaranteed-quota project preempts zero-quota project via kubectl
    [Documentation]    Verify quota-based preemption via kubectl.
    ...    Step 1: Fill cluster with 1-GPU jobs from a zero-quota filler project (borrows all GPUs).
    ...    Step 2: Create a guaranteed-quota project and submit a 1-GPU workload.
    ...    Step 3: Kueue reclaims 1 borrowed GPU from the filler, suspending a job.
    [Tags]    workload    preemption    quota    gpu    kubectl

    # Fill cluster with zero-quota filler project
    Given fill cluster from zero-quota filler project    quota-filler-kctl

    # Create guaranteed-quota project and submit workload
    ${guaranteed_project}=    Test Name    quota-guaranteed-kctl
    And a ready project with user access exists    project_name=${guaranteed_project}
    ${guaranteed_namespace}=    Set Variable    ${TEST_PROJECT}[name]

    @{namespaces}=    Get Variable Value    ${QUOTA_TEST_NAMESPACES}    @{EMPTY}
    Append To List    ${namespaces}    ${guaranteed_namespace}
    Set Test Variable    @{QUOTA_TEST_NAMESPACES}    @{namespaces}

    And project quota is set to    gpu_count=${1}

    ${guaranteed_job}=    When submit GPU job with priority class via kubectl
    ...    ${guaranteed_namespace}    ${1}    low    sleep_seconds=300

    # Verify: guaranteed job runs, filler jobs preempted
    Then kubectl job should be running    ${guaranteed_namespace}    ${guaranteed_job}
    And at least N filler jobs should be suspended    ${1}
