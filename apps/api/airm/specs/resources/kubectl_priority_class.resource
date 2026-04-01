# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Priority class-specific kubectl operations for workload preemption tests
Resource            resources/common/resource_resolver.resource
Resource            resources/api/common.resource
Library             Process


*** Keywords ***
Submit GPU job with priority class via kubectl
    [Documentation]    Submits a GPU Job with priority class directly via kubectl
    ...    Extends the kubectl job pattern to support priority classes
    [Arguments]    ${namespace}    ${gpu_count}    ${priority_class}    ${sleep_seconds}=600

    ${unique_suffix}=    Generate random string    6    [LOWER][NUMBERS]
    ${job_name}=    Set variable    gpu-job-${priority_class}-${unique_suffix}

    ${job_yaml}=    Catenate    SEPARATOR=\n
    ...    apiVersion: batch/v1
    ...    kind: Job
    ...    metadata:
    ...    ${SPACE}${SPACE}name: ${job_name}
    ...    ${SPACE}${SPACE}namespace: ${namespace}
    ...    ${SPACE}${SPACE}labels:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}kueue.x-k8s.io/queue-name: ${namespace}
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}kueue.x-k8s.io/priority-class: ${priority_class}
    ...    spec:
    ...    ${SPACE}${SPACE}ttlSecondsAfterFinished: 300
    ...    ${SPACE}${SPACE}template:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}spec:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}restartPolicy: Never
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}containers:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}- name: gpu-test
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}image: busybox:latest
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}command: ["sh", "-c", "echo 'GPU job starting' && sleep ${sleep_seconds} && echo 'Completed'"]
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}resources:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}requests:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}cpu: 100m
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}memory: 128Mi
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}amd.com/gpu: "${gpu_count}"
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}limits:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}cpu: 100m
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}memory: 128Mi
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}amd.com/gpu: "${gpu_count}"

    ${result}=    Run process    kubectl    apply    -f    -    stdin=${job_yaml}
    Should be equal as integers    ${result.rc}    0
    ...    msg=Failed to create Job: ${result.stderr}

    Log    Created Job ${job_name} with priority class ${priority_class} in namespace ${namespace}    INFO
    RETURN    ${job_name}

Kubectl job should be pending
    [Documentation]    Verifies that a kubectl-submitted Job has Pending pods
    [Arguments]    ${namespace}    ${job_name}    ${timeout}=2 min

    Wait until keyword succeeds    ${timeout}    5 sec
    ...    Verify kubectl job pending    ${namespace}    ${job_name}

Verify kubectl job pending
    [Documentation]    Helper to verify Job has Pending pods
    [Arguments]    ${namespace}    ${job_name}

    ${result}=    Run process    kubectl    get    pods    -n    ${namespace}    -l    job-name\=${job_name}    -o    jsonpath\={.items[0].status.phase}

    Should be equal as integers    ${result.rc}    0
    ...    msg=Failed to get pod status: ${result.stderr}

    ${phase}=    Set variable    ${result.stdout.strip()}
    Should be equal    ${phase}    Pending
    ...    msg=Expected pod phase Pending, got ${phase}

    Log    Job ${job_name} pod is Pending    DEBUG

Kubectl job should be running
    [Documentation]    Verifies that a kubectl-submitted Job has Running pods
    [Arguments]    ${namespace}    ${job_name}    ${timeout}=2 min

    Wait until keyword succeeds    ${timeout}    5 sec
    ...    Verify kubectl job running    ${namespace}    ${job_name}

Verify kubectl job running
    [Documentation]    Helper to verify Job has Running pods
    ...    Checks Job status (active/ready) and Suspended condition
    [Arguments]    ${namespace}    ${job_name}

    # Check if job is suspended
    ${suspended_check}=    Run process    kubectl    get    job    ${job_name}    -n    ${namespace}    -o    jsonpath\={.status.conditions[?(@.type\=\=\"Suspended\")].status}
    IF    "${suspended_check.stdout.strip()}" == "True"
        ${suspend_reason}=    Run process    kubectl    get    job    ${job_name}    -n    ${namespace}    -o    jsonpath\={.status.conditions[?(@.type\=\=\"Suspended\")].message}
        Fail    Job ${job_name} is SUSPENDED. Reason: ${suspend_reason.stdout}
    END

    # Check Job has active or ready pods
    ${active}=    Run process    kubectl    get    job    ${job_name}    -n    ${namespace}    -o    jsonpath\={.status.active}
    ${ready}=    Run process    kubectl    get    job    ${job_name}    -n    ${namespace}    -o    jsonpath\={.status.ready}

    ${active_count}=    Set variable if    "${active.stdout.strip()}" != ""    ${active.stdout.strip()}    0
    ${ready_count}=    Set variable if    "${ready.stdout.strip()}" != ""    ${ready.stdout.strip()}    0

    Should be true    ${active_count} > 0 or ${ready_count} > 0
    ...    msg=Job ${job_name} has no active or ready pods (active=${active_count}, ready=${ready_count})

    Log    Job ${job_name} pod is Running    DEBUG

Kubectl job should be suspended
    [Documentation]    Verifies that a kubectl-submitted Job is suspended (preempted)
    [Arguments]    ${namespace}    ${job_name}    ${timeout}=2 min

    Wait until keyword succeeds    ${timeout}    5 sec
    ...    Verify kubectl job suspended    ${namespace}    ${job_name}

Verify kubectl job suspended
    [Documentation]    Helper to verify Job is suspended
    [Arguments]    ${namespace}    ${job_name}

    ${result}=    Run process    kubectl    get    job    -n    ${namespace}    ${job_name}    -o    jsonpath\={.status.conditions[?(@.type\=\=\"Suspended\")].status}

    Should be equal as integers    ${result.rc}    0
    ...    msg=Failed to get job status: ${result.stderr}

    ${suspended_status}=    Set variable    ${result.stdout.strip()}
    Should be equal    ${suspended_status}    True
    ...    msg=Expected Job to be Suspended (status=True), got ${suspended_status}

    Log    Job ${job_name} is Suspended    DEBUG

Verify job has priority class
    [Documentation]    Verifies that a kubectl-submitted Job has the expected Kueue WorkloadPriorityClass label
    [Arguments]    ${namespace}    ${job_name}    ${expected_priority_class}

    ${result}=    Run process    kubectl    get    job    -n    ${namespace}    ${job_name}    -o    jsonpath\={.metadata.labels.kueue\\.x-k8s\\.io/priority-class}

    Should be equal as integers    ${result.rc}    0
    ...    msg=Failed to get job priority class label: ${result.stderr}

    ${actual_priority_class}=    Set variable    ${result.stdout.strip()}
    Should be equal    ${actual_priority_class}    ${expected_priority_class}
    ...    msg=Expected priority class ${expected_priority_class}, got ${actual_priority_class}

    Log    Job ${job_name} has Kueue WorkloadPriorityClass label ${actual_priority_class}    DEBUG
