# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for workload quota preemption.
...                 Verifies that projects with guaranteed GPU quotas can preempt
...                 workloads from projects with zero guaranteed quota.
Resource            ../resources/airm_workloads.resource
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            ../resources/common/resource_resolver.resource
Resource            ../resources/api/common.resource
Resource            ../resources/authorization.resource
Library             Collections
Library             Process
Test Setup          Run keywords
...                 Initialize project tracking    AND
...                 Initialize workload ID tracking
Test Teardown       Clean up preemption test resources


*** Keywords ***
Clean up preemption test resources
    [Documentation]    Clean up all resources created during preemption tests
    Clean up all created workloads
    Clean up all created projects

Submit GPU job via kubectl
    [Documentation]    Submits a GPU Job directly via kubectl
    ...    Returns the job name for later verification
    [Arguments]    ${namespace}    ${gpu_count}    ${sleep_seconds}=300

    ${unique_suffix}=    Generate Random String    6    [LOWER][NUMBERS]
    ${job_name}=    Set Variable    gpu-job-${unique_suffix}

    ${job_yaml}=    Catenate    SEPARATOR=\n
    ...    apiVersion: batch/v1
    ...    kind: Job
    ...    metadata:
    ...    ${SPACE}${SPACE}name: ${job_name}
    ...    ${SPACE}${SPACE}namespace: ${namespace}
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

    ${result}=    Run Process    kubectl    apply    -f    -    stdin=${job_yaml}
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to create Job: ${result.stderr}

    Log    Created Job ${job_name} in namespace ${namespace}    INFO
    RETURN    ${job_name}

Kubectl job should be running
    [Documentation]    Verifies that a kubectl-submitted Job has Running pods
    [Arguments]    ${namespace}    ${job_name}    ${timeout}=2 min

    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify kubectl job running    ${namespace}    ${job_name}

Verify kubectl job running
    [Documentation]    Helper to verify Job has Running pods
    [Arguments]    ${namespace}    ${job_name}

    ${result}=    Run Process    sh    -c
    ...    kubectl get pods -n ${namespace} -l job-name\=${job_name} -o 'jsonpath\={.items[0].status.phase}'

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get pod status: ${result.stderr}

    ${phase}=    Set Variable    ${result.stdout.strip()}
    Should Be Equal    ${phase}    Running
    ...    msg=Expected pod phase Running, got ${phase}

    Log    Job ${job_name} pod is Running    DEBUG

Kubectl job should be suspended
    [Documentation]    Verifies that a kubectl-submitted Job is suspended (preempted)
    [Arguments]    ${namespace}    ${job_name}    ${timeout}=2 min

    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify kubectl job suspended    ${namespace}    ${job_name}

Verify kubectl job suspended
    [Documentation]    Helper to verify Job is suspended
    [Arguments]    ${namespace}    ${job_name}

    ${result}=    Run Process    sh    -c
    ...    kubectl get job -n ${namespace} ${job_name} -o 'jsonpath\={.status.conditions[?(@.type\=\="Suspended")].status}'

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get job status: ${result.stderr}

    ${suspended_status}=    Set Variable    ${result.stdout.strip()}
    Should Be Equal    ${suspended_status}    True
    ...    msg=Expected Job to be Suspended (status=True), got ${suspended_status}

    Log    Job ${job_name} is Suspended    DEBUG

Workload should be preempted via AIRM API
    [Documentation]    Verifies workload was preempted by checking AIRM API status
    ...    Note: This may be different from kubectl status due to sync delays
    ...    AIRM may still report "Running" briefly after K8s suspends the Job
    [Arguments]    ${workload_id}=${None}    ${timeout}=3 min

    ${id}=    The workload    id=${workload_id}

    # Wait longer for AIRM to detect and update workload status after K8s suspension
    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify workload is preempted via AIRM    ${id}

Verify workload is preempted via AIRM
    [Documentation]    Helper to verify workload is preempted in AIRM API
    [Arguments]    ${workload_id}

    ${response}=    Get workload    ${workload_id}    expected_status=200
    ${status}=    Set variable    ${response.json()['status']}
    Log    Checking workload ${workload_id} preemption status in AIRM: ${status}    DEBUG

    # AIRM may report various statuses for preempted workloads
    Should be true    '${status}' in ['Preempted', 'Suspended', 'Pending', 'Evicted']
    ...    msg=Expected workload to be preempted in AIRM but status is ${status}

Wait for namespace RBAC to be ready
    [Documentation]    Waits for kubectl permissions to be ready in the current project namespace
    ...    This ensures that user can create jobs before we try to submit workloads
    ...    Checks both Keycloak group membership and RBAC permissions
    [Arguments]    ${namespace}=${TEST_PROJECT_SLUG}    ${timeout}=5 min

    # Give Keycloak and AIRM time to propagate user addition
    Sleep    10 sec    reason=Allow Keycloak user-to-group propagation

    # Force another token refresh to pick up new group membership
    Refresh kubectl and API tokens

    # Wait for Keycloak group membership
    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify user has Keycloak group    ${namespace}

    # Then verify RBAC permissions
    Wait Until Keyword Succeeds    30 sec    2 sec
    ...    Verify can create jobs in namespace    ${namespace}

Verify user has Keycloak group
    [Documentation]    Verifies that user has the Keycloak group for the namespace
    [Arguments]    ${namespace}
    ${expected_group}=    Set Variable    oidc${namespace}
    ${result}=    Run Process    kubectl    auth    whoami    -o    json
    ${groups}=    Evaluate    json.loads('''${result.stdout}''')['status']['userInfo']['groups']    json
    Should Contain    ${groups}    ${expected_group}
    ...    msg=User does not have Keycloak group ${expected_group} yet. Groups: ${groups}
    Log    User has Keycloak group ${expected_group}    INFO

Verify can create jobs in namespace
    [Documentation]    Verifies that current user can create jobs in namespace
    [Arguments]    ${namespace}
    ${result}=    Run Process    kubectl    auth    can-i    create    jobs    --namespace    ${namespace}
    Should Be Equal As Strings    ${result.stdout.strip()}    yes
    ...    msg=User cannot create jobs in namespace ${namespace} yet


*** Test Cases ***
Low quota project gets preempted when high quota project needs resources via kubectl
    [Documentation]    Verify preemption when high quota project submits workload via kubectl
    ...    Tests the kubectl path: Jobs submitted via kubectl, verified via kubectl
    [Tags]    workload    preemption    quota    gpu    kubectl    skip

    ${max_gpus}=    Get cluster GPU capacity

    # Calculate GPU counts for preemption test
    # Low workload uses 2 GPUs, high workload needs enough to force preemption
    # To ensure preemption: high_gpus > (max_gpus - low_gpus)
    # So if low uses 2 GPUs out of 8, high needs > 6 GPUs to force preemption
    ${low_gpu_count}=    Set Variable    ${2}
    ${high_gpu_count}=    Evaluate    ${max_gpus} - ${low_gpu_count} + 1

    # Step 1: Create low quota project with user access (uses minimal quota initially)
    A ready project with user access exists    project_name=e2e-preempt-low-kubectl
    Set Test Variable    ${LOW_PROJECT_NAMESPACE}    ${TEST_PROJECT_SLUG}
    # Step 2: Keep quota at 0 GPUs (already set by default, no action needed)
    Wait for namespace RBAC to be ready

    # Submit workload to low quota project (will borrow GPUs) via kubectl
    ${low_job_name}=    Submit GPU job via kubectl    ${LOW_PROJECT_NAMESPACE}    ${low_gpu_count}    sleep_seconds=1800
    Kubectl job should be running    ${LOW_PROJECT_NAMESPACE}    ${low_job_name}

    # Step 1: Create high quota project with user access
    A ready project with user access exists    project_name=e2e-preempt-high-kubectl
    Set Test Variable    ${HIGH_PROJECT_NAMESPACE}    ${TEST_PROJECT_SLUG}
    # Step 2: Set high quota to guarantee all GPUs
    Project quota is set to    gpu_count=${max_gpus}
    Wait for namespace RBAC to be ready

    # Submit to high quota project - requests more GPUs than available after low workload
    # This creates resource pressure and should trigger preemption
    ${high_job_name}=    Submit GPU job via kubectl    ${HIGH_PROJECT_NAMESPACE}    ${high_gpu_count}    sleep_seconds=300

    # Verify low workload was preempted (should happen before high workload starts)
    Kubectl job should be suspended    ${LOW_PROJECT_NAMESPACE}    ${low_job_name}

    # High workload should now be able to run using the reclaimed GPUs
    Kubectl job should be running    ${HIGH_PROJECT_NAMESPACE}    ${high_job_name}

Low quota project gets preempted when high quota project needs resources via AIRM API
    [Documentation]    Verify preemption when high quota project submits workload via AIRM API
    ...    Tests the AIRM API path: Workloads submitted via AIRM API (helm), verified via AIRM API
    [Tags]    workload    preemption    quota    gpu    api    skip

    ${max_gpus}=    Get cluster GPU capacity

    # Calculate GPU counts for preemption test
    ${low_gpu_count}=    Set Variable    ${2}
    ${high_gpu_count}=    Evaluate    ${max_gpus} - ${low_gpu_count} + 1

    # Step 1: Create low quota project with user access (uses minimal quota initially)
    A ready project with user access exists    project_name=e2e-preempt-low-api
    # Step 2: Keep quota at 0 GPUs (already set by default, no action needed)
    Wait for namespace RBAC to be ready

    # Submit workload to low quota project (will borrow GPUs) via AIRM API
    A GPU workload is prepared    gpu_count=${low_gpu_count}
    ${low_workload}=    Test workload is submitted via helm
    Workload should exist in AIRM    workload_id=${low_workload}
    Workload status should transition to "Running"    workload_id=${low_workload}

    # Step 1: Create high quota project with user access
    A ready project with user access exists    project_name=e2e-preempt-high-api
    # Step 2: Set high quota to guarantee all GPUs
    Project quota is set to    gpu_count=${max_gpus}
    Wait for namespace RBAC to be ready

    # Submit to high quota project - requests more GPUs than available after low workload
    # This creates resource pressure and should trigger preemption
    A GPU workload is prepared    gpu_count=${high_gpu_count}
    ${high_workload}=    Test workload is submitted via helm
    Workload should exist in AIRM    workload_id=${high_workload}

    # Verify low workload was preempted via AIRM API
    # AIRM may take time to detect and update the workload status after K8s suspends it
    Workload should be preempted via AIRM API    workload_id=${low_workload}

    # High workload should now be able to run using the reclaimed GPUs
    Workload status should transition to "Running"    workload_id=${high_workload}

Low quota project can borrow free resources
    [Documentation]    Verify that projects with zero quota can use free resources
    [Tags]    workload    preemption    quota    gpu    borrowing    skip

    # Step 1: Create project with user access (minimal quota by default)
    A ready project with user access exists    project_name=e2e-borrow-test
    # Step 2: Keep quota at 0 GPUs (already set by default, no action needed)
    Wait for namespace RBAC to be ready

    # Submit workload - should be able to use free GPUs
    A GPU workload is prepared    gpu_count=2
    ${workload}=    Test workload is submitted via helm
    Workload should exist in AIRM    workload_id=${workload}

    # Verify workload can run (borrowing works)
    Workload status should transition to "Running"    workload_id=${workload}

Low quota project gets preempted when high quota project needs resources via AIRM API with kubectl verification
    [Documentation]    Hybrid test: AIRM API for deployment, kubectl for verification
    ...    This isolates whether the issue is in AIRM API workload deployment or status sync
    [Tags]    workload    preemption    quota    gpu    api    kubectl    hybrid    skip

    ${max_gpus}=    Get cluster GPU capacity

    # Calculate GPU counts for preemption test
    ${low_gpu_count}=    Set Variable    ${2}
    ${high_gpu_count}=    Evaluate    ${max_gpus} - ${low_gpu_count} + 1

    # Step 1: Create low quota project with user access (uses minimal quota initially)
    A ready project with user access exists    project_name=e2e-preempt-hybrid-low
    Set Test Variable    ${LOW_PROJECT_NAMESPACE}    ${TEST_PROJECT_SLUG}
    # Step 2: Keep quota at 0 GPUs (already set by default, no action needed)
    Wait for namespace RBAC to be ready

    # Submit workload to low quota project via AIRM API
    A GPU workload is prepared    gpu_count=${low_gpu_count}
    ${low_workload}=    Test workload is submitted via helm
    Workload should exist in AIRM    workload_id=${low_workload}
    Workload status should transition to "Running"    workload_id=${low_workload}

    # Get the job name to verify via kubectl - MUST capture BEFORE submitting next workload
    ${low_job_name}=    Set Variable    ${TEST_WORKLOAD_RELEASE_NAME}
    Set Test Variable    ${LOW_JOB_NAME}    ${low_job_name}

    # Verify low job is actually running via kubectl (not just AIRM API status)
    Kubectl job should be running    ${LOW_PROJECT_NAMESPACE}    ${low_job_name}

    # Step 3: Create high quota project with user access
    A ready project with user access exists    project_name=e2e-preempt-hybrid-high
    Set Test Variable    ${HIGH_PROJECT_NAMESPACE}    ${TEST_PROJECT_SLUG}
    # Step 4: Set high quota to guarantee all GPUs
    Project quota is set to    gpu_count=${max_gpus}
    Wait for namespace RBAC to be ready

    # Submit to high quota project via AIRM API
    A GPU workload is prepared    gpu_count=${high_gpu_count}
    ${high_workload}=    Test workload is submitted via helm
    Workload should exist in AIRM    workload_id=${high_workload}

    # Get the job name to verify via kubectl
    ${high_job_name}=    Set Variable    ${TEST_WORKLOAD_RELEASE_NAME}
    Set Test Variable    ${HIGH_JOB_NAME}    ${high_job_name}

    # Verify preemption happened via KUBECTL (not AIRM API)
    Kubectl job should be suspended    ${LOW_PROJECT_NAMESPACE}    ${low_job_name}

    # High workload should be running via kubectl
    Kubectl job should be running    ${HIGH_PROJECT_NAMESPACE}    ${high_job_name}
