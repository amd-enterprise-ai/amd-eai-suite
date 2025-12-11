# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Kubectl-based verification keywords for Kubernetes resources.
...                 Provides keywords to verify that K8s resources (Jobs, Pods, Namespaces, etc.)
...                 were actually created and have the expected status.
...                 This is the lowest layer - direct kubectl commands.
Library             Process
Library             Collections
Library             String
Library             BuiltIn


*** Keywords ***
Namespace should exist
    [Documentation]    Verifies that a namespace exists in the cluster
    [Arguments]    ${namespace}

    Log    Verifying namespace ${namespace} exists    DEBUG
    ${result}=    Run Process    kubectl    get    namespace    ${namespace}
    ...    stdout=DEVNULL    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Namespace ${namespace} does not exist. Error: ${result.stderr}
    Log    Namespace ${namespace} exists in cluster    DEBUG

Namespace should not exist in cluster
    [Documentation]    Verifies that a namespace does not exist in the cluster
    ...    Polls for namespace deletion to handle async API operations
    [Arguments]    ${namespace}=${None}

    IF    "${namespace}" == "${None}"
        ${namespace}=    Set Variable    ${TEST_NAMESPACE}
    END

    Log    Waiting for namespace ${namespace} to be deleted    DEBUG
    Wait Until Keyword Succeeds    2 min    2 sec
    ...    Verify namespace does not exist    ${namespace}

Verify namespace does not exist
    [Documentation]    Helper keyword to verify namespace doesn't exist (used with polling)
    [Arguments]    ${namespace}

    Log    Checking if namespace ${namespace} is deleted    TRACE
    ${result}=    Run Process    kubectl    get    namespace    ${namespace}
    ...    stdout=DEVNULL    stderr=PIPE

    Should Not Be Equal As Integers    ${result.rc}    0
    ...    msg=Namespace ${namespace} still exists in cluster
    Log    Namespace ${namespace} does not exist in cluster (verified)    INFO

Job should exist in namespace
    [Documentation]    Verifies that a Job exists in the specified namespace
    ...    Returns the Job object as a dictionary
    [Arguments]    ${job_name}    ${namespace}

    Log    Verifying Job ${job_name} exists in namespace ${namespace}    DEBUG
    ${result}=    Run Process    kubectl    get    job    ${job_name}
    ...    -n    ${namespace}    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Job ${job_name} does not exist in namespace ${namespace}. Error: ${result.stderr}

    ${job}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    Log    Job ${job_name} exists in namespace ${namespace}    DEBUG
    RETURN    ${job}

Deployment should exist in namespace
    [Documentation]    Verifies that a Deployment exists in the specified namespace
    ...    Returns the Deployment object as a dictionary
    [Arguments]    ${deployment_name}    ${namespace}

    ${result}=    Run Process    kubectl    get    deployment    ${deployment_name}
    ...    -n    ${namespace}    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Deployment ${deployment_name} does not exist in namespace ${namespace}. Error: ${result.stderr}

    ${deployment}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    RETURN    ${deployment}

Pod should exist for Job
    [Documentation]    Verifies that at least one Pod exists for the given Job
    ...    Returns the first Pod object as a dictionary
    [Arguments]    ${job_name}    ${namespace}

    ${result}=    Run Process    kubectl    get    pods
    ...    -n    ${namespace}
    ...    -l    job-name\=${job_name}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get pods for job ${job_name}. Error: ${result.stderr}

    ${pods_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    ${pods}=    Get From Dictionary    ${pods_json}    items
    ${count}=    Get Length    ${pods}

    Should Be True    ${count} > 0
    ...    msg=No pods found for job ${job_name} in namespace ${namespace}

    RETURN    ${pods[0]}

Pods should exist for Deployment
    [Documentation]    Verifies that at least one Pod exists for the given Deployment
    ...    Returns list of Pod objects
    [Arguments]    ${deployment_name}    ${namespace}

    # Get deployment to find selector labels
    ${deployment}=    Deployment should exist in namespace    ${deployment_name}    ${namespace}
    ${match_labels}=    Set Variable    ${deployment['spec']['selector']['matchLabels']}

    # Build label selector
    @{label_pairs}=    Create List
    FOR    ${key}    ${value}    IN    &{match_labels}
        Append To List    ${label_pairs}    ${key}=${value}
    END
    ${label_selector}=    Evaluate    ','.join(${label_pairs})

    ${result}=    Run Process    kubectl    get    pods
    ...    -n    ${namespace}
    ...    -l    ${label_selector}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get pods for deployment ${deployment_name}. Error: ${result.stderr}

    ${pods_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    ${pods}=    Get From Dictionary    ${pods_json}    items
    ${count}=    Get Length    ${pods}

    Should Be True    ${count} > 0
    ...    msg=No pods found for deployment ${deployment_name} in namespace ${namespace}

    RETURN    ${pods}

Pod status should be
    [Documentation]    Verifies that a Pod has the expected status phase
    [Arguments]    ${pod}    ${expected_status}

    ${phase}=    Set Variable    ${pod['status']['phase']}
    Should Be Equal    ${phase}    ${expected_status}
    ...    msg=Pod status is ${phase}, expected ${expected_status}

Wait for Pod status
    [Documentation]    Waits for a Job's Pod to reach the expected status
    [Arguments]    ${job_name}    ${namespace}    ${expected_status}    ${timeout}=2 min

    Log    Waiting for Pod ${job_name} to reach status ${expected_status}    DEBUG
    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify Pod has status    ${job_name}    ${namespace}    ${expected_status}

Verify Pod has status
    [Documentation]    Helper keyword to verify Pod status (used with polling)
    [Arguments]    ${job_name}    ${namespace}    ${expected_status}

    Log    Checking Pod status for ${job_name}    TRACE
    ${pod}=    Pod should exist for Job    ${job_name}    ${namespace}
    ${phase}=    Set Variable    ${pod['status']['phase']}

    Should Be Equal    ${phase}    ${expected_status}
    ...    msg=Pod status is ${phase}, expected ${expected_status}
    Log    Pod ${job_name} has status ${phase}    DEBUG

Wait for Deployment Pod status
    [Documentation]    Waits for at least one Deployment Pod to reach the expected status
    [Arguments]    ${deployment_name}    ${namespace}    ${expected_status}    ${timeout}=2 min

    Log    Waiting for Deployment ${deployment_name} Pod to reach status ${expected_status}    DEBUG
    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify Deployment has Pod with status    ${deployment_name}    ${namespace}    ${expected_status}

Verify Deployment has Pod with status
    [Documentation]    Helper keyword to verify at least one Deployment Pod has expected status
    [Arguments]    ${deployment_name}    ${namespace}    ${expected_status}

    Log    Checking Deployment Pod status for ${deployment_name}    TRACE
    ${pods}=    Pods should exist for Deployment    ${deployment_name}    ${namespace}

    FOR    ${pod}    IN    @{pods}
        ${phase}=    Set Variable    ${pod['status']['phase']}
        IF    '${phase}' == '${expected_status}'
            Log    Deployment ${deployment_name} has Pod with status ${phase}    DEBUG
            RETURN
        END
    END

    Fail    No pod for deployment ${deployment_name} has status ${expected_status}

Job should complete successfully
    [Documentation]    Waits for a Job to complete successfully
    [Arguments]    ${job_name}    ${namespace}    ${timeout}=5 min

    Log    Waiting for Job ${job_name} to complete    DEBUG
    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify Job completed    ${job_name}    ${namespace}

Verify Job completed
    [Documentation]    Helper keyword to verify Job completion (used with polling)
    [Arguments]    ${job_name}    ${namespace}

    Log    Checking Job completion status for ${job_name}    TRACE
    ${job}=    Job should exist in namespace    ${job_name}    ${namespace}
    ${status}=    Get From Dictionary    ${job}    status

    # Check if job has succeeded
    ${succeeded}=    Get From Dictionary    ${status}    succeeded    default=0
    Should Be True    ${succeeded} > 0
    ...    msg=Job ${job_name} has not completed successfully yet. Status: ${status}
    Log    Job ${job_name} completed successfully    INFO

Job should fail
    [Documentation]    Waits for a Job to fail
    [Arguments]    ${job_name}    ${namespace}    ${timeout}=5 min

    Log    Waiting for Job ${job_name} to fail    DEBUG
    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify Job failed    ${job_name}    ${namespace}

Verify Job failed
    [Documentation]    Helper keyword to verify Job failure (used with polling)
    [Arguments]    ${job_name}    ${namespace}

    Log    Checking Job failure status for ${job_name}    TRACE
    ${job}=    Job should exist in namespace    ${job_name}    ${namespace}
    ${status}=    Get From Dictionary    ${job}    status

    # Check if job has failed
    ${failed}=    Get From Dictionary    ${status}    failed    default=0
    Should Be True    ${failed} > 0
    ...    msg=Job ${job_name} has not failed yet. Status: ${status}
    Log    Job ${job_name} failed as expected    INFO

ResourceQuota should exist in namespace
    [Documentation]    Verifies that at least one ResourceQuota exists in the namespace
    ...    Returns the first ResourceQuota object as a dictionary
    [Arguments]    ${namespace}

    ${result}=    Run Process    kubectl    get    resourcequota
    ...    -n    ${namespace}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get ResourceQuota in namespace ${namespace}. Error: ${result.stderr}

    ${quotas_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    ${quotas}=    Get From Dictionary    ${quotas_json}    items
    ${count}=    Get Length    ${quotas}

    Should Be True    ${count} > 0
    ...    msg=No ResourceQuota found in namespace ${namespace}

    RETURN    ${quotas[0]}

RoleBinding should exist in namespace
    [Documentation]    Verifies that at least one RoleBinding exists in the namespace
    [Arguments]    ${namespace}

    ${result}=    Run Process    kubectl    get    rolebinding
    ...    -n    ${namespace}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get RoleBinding in namespace ${namespace}. Error: ${result.stderr}

    ${bindings_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    ${bindings}=    Get From Dictionary    ${bindings_json}    items
    ${count}=    Get Length    ${bindings}

    Should Be True    ${count} > 0
    ...    msg=No RoleBinding found in namespace ${namespace}

Namespace should have label
    [Documentation]    Verifies that a namespace has a specific label with expected value
    [Arguments]    ${namespace}    ${label_key}    ${expected_value}

    ${result}=    Run Process    kubectl    get    namespace    ${namespace}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to get namespace ${namespace}. Error: ${result.stderr}

    ${ns_json}=    Evaluate    json.loads(r'''${result.stdout}''')    modules=json
    ${labels}=    Get From Dictionary    ${ns_json['metadata']}    labels    default={}

    Dictionary Should Contain Key    ${labels}    ${label_key}
    ...    msg=Namespace ${namespace} does not have label ${label_key}

    ${actual_value}=    Get From Dictionary    ${labels}    ${label_key}
    Should Be Equal    ${actual_value}    ${expected_value}
    ...    msg=Label ${label_key} has value ${actual_value}, expected ${expected_value}

MinIO credentials should exist in namespace
    [Documentation]    Verifies that minio-credentials secret exists in the namespace
    ...    Returns True if secret exists, False otherwise
    [Arguments]    ${namespace}

    ${result}=    Run Process    kubectl    get    secret    minio-credentials
    ...    -n    ${namespace}
    ...    stdout=DEVNULL    stderr=PIPE

    ${exists}=    Evaluate    ${result.rc} == 0
    RETURN    ${exists}

Ensure MinIO credentials exist in namespace
    [Documentation]    Ensures minio-credentials secret exists in the namespace
    ...    Copies from kaiwo namespace if missing. This is required for workspace deployments.
    ...    Logs a warning if copy fails due to permissions but secret already exists.
    [Arguments]    ${namespace}

    Log    Checking MinIO credentials in namespace ${namespace}    DEBUG

    # Check if secret already exists
    ${exists}=    MinIO credentials should exist in namespace    ${namespace}
    IF    ${exists}
        Log    MinIO credentials already exist in namespace ${namespace}    DEBUG
        RETURN
    END

    Log    MinIO credentials missing, copying from kaiwo namespace    INFO

    # Copy secret from kaiwo namespace
    ${get_result}=    Run Process    kubectl    get    secret    minio-credentials
    ...    -n    kaiwo
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${get_result.rc}    0
    ...    msg=Failed to get minio-credentials from kaiwo namespace. Error: ${get_result.stderr}

    # Remove metadata fields that shouldn't be copied and use create instead of apply
    ${clean_result}=    Run Process    bash    -c
    ...    echo '${get_result.stdout}' | jq 'del(.metadata.namespace, .metadata.resourceVersion, .metadata.uid, .metadata.creationTimestamp, .metadata.ownerReferences, .metadata.annotations)' | kubectl create -n ${namespace} -f -
    ...    shell=True
    ...    stderr=PIPE

    Should Be Equal As Integers    ${clean_result.rc}    0
    ...    msg=Failed to copy minio-credentials to namespace ${namespace}. Error: ${clean_result.stderr}

    Log    MinIO credentials copied to namespace ${namespace}    INFO

Remove MinIO credentials from namespace
    [Documentation]    Removes minio-credentials secret from the namespace if it exists
    ...    Used for testing workspace behavior without MinIO credentials
    [Arguments]    ${namespace}

    Log    Removing MinIO credentials from namespace ${namespace}    DEBUG

    ${result}=    Run Process    kubectl    delete    secret    minio-credentials
    ...    -n    ${namespace}
    ...    --ignore-not-found=true
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to delete minio-credentials from namespace ${namespace}. Error: ${result.stderr}

    Log    MinIO credentials removed from namespace ${namespace}    INFO

User PVC should exist in namespace
    [Documentation]    Verifies that user PVC exists in the namespace
    ...    Returns True if PVC exists, False otherwise
    [Arguments]    ${user_id}    ${namespace}

    ${pvc_name}=    Set Variable    pvc-${user_id}

    ${result}=    Run Process    kubectl    get    pvc    ${pvc_name}
    ...    -n    ${namespace}
    ...    stdout=DEVNULL    stderr=PIPE

    ${exists}=    Evaluate    ${result.rc} == 0
    RETURN    ${exists}

Ensure user PVC exists in namespace
    [Documentation]    Ensures user-specific PVC exists in the namespace
    ...    Creates PVC if missing. This is required for workspace deployments.
    [Arguments]    ${user_id}    ${namespace}

    ${pvc_name}=    Set Variable    pvc-${user_id}
    Log    Checking user PVC ${pvc_name} in namespace ${namespace}    DEBUG

    # Check if PVC already exists
    ${exists}=    User PVC should exist in namespace    ${user_id}    ${namespace}
    IF    ${exists}
        Log    User PVC ${pvc_name} already exists in namespace ${namespace}    DEBUG
        RETURN
    END

    Log    User PVC ${pvc_name} missing, creating it    INFO

    # Create PVC using kubectl with proper escaping
    ${yaml}=    Catenate    SEPARATOR=\n
    ...    apiVersion: v1
    ...    kind: PersistentVolumeClaim
    ...    metadata:
    ...    ${SPACE}${SPACE}name: ${pvc_name}
    ...    ${SPACE}${SPACE}namespace: ${namespace}
    ...    spec:
    ...    ${SPACE}${SPACE}accessModes:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}- ReadWriteOnce
    ...    ${SPACE}${SPACE}resources:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}requests:
    ...    ${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}${SPACE}storage: 100Gi
    ...    ${SPACE}${SPACE}storageClassName: mlstorage

    ${result}=    Run Process    bash    -c
    ...    cat <<'EOF' | kubectl apply -f -\n${yaml}\nEOF
    ...    shell=True
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to create user PVC ${pvc_name} in namespace ${namespace}. Error: ${result.stderr}

    Log    User PVC ${pvc_name} created in namespace ${namespace}    INFO

Remove user PVC from namespace
    [Documentation]    Removes user PVC from the namespace if it exists
    ...    Used for cleanup or testing workspace behavior without PVC
    [Arguments]    ${user_id}    ${namespace}

    ${pvc_name}=    Set Variable    pvc-${user_id}
    Log    Removing user PVC ${pvc_name} from namespace ${namespace}    DEBUG

    ${result}=    Run Process    kubectl    delete    pvc    ${pvc_name}
    ...    -n    ${namespace}
    ...    --ignore-not-found=true
    ...    stderr=PIPE

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to delete user PVC ${pvc_name} from namespace ${namespace}. Error: ${result.stderr}

    Log    User PVC ${pvc_name} removed from namespace ${namespace}    INFO
