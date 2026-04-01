# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       S3 test operations using Kubernetes Jobs.
...                 Provides keywords to perform real S3 read/write/cleanup operations
...                 via Kubernetes Jobs running Python with boto3.
Library             Process
Library             Collections
Library             String
Library             OperatingSystem


*** Variables ***
${S3_JOB_TIMEOUT}       60s
${S3_JOB_POLL_INTERVAL}    2s


*** Keywords ***
Submit S3 Writer Job
    [Documentation]    Submit a Kubernetes Job to write data to S3
    ...    This modifies the s3-writer-job.yaml template with actual values
    ...    and submits it to the specified namespace.
    ...
    ...    Arguments:
    ...    - namespace: Kubernetes namespace (project name)
    ...    - storage_config_map_name: Name of the ConfigMap with storage info
    ...    - secret_name: Name of the ExternalSecret with credentials
    ...    - access_key_name: Key name in secret for access key
    ...    - secret_key_name: Key name in secret for secret key
    ...    - test_data_key: S3 object key (e.g., e2e-test-storage-123/file.txt)
    ...    - test_data_content: Content to write
    ...
    ...    Returns: Job name
    [Arguments]    ${namespace}    ${storage_config_map_name}    ${secret_name}    ${access_key_name}    ${secret_key_name}    ${test_data_key}    ${test_data_content}    ${random_suffix}

    ${job_name}=    Set Variable    s3-writer-test-${random_suffix}
    ${manifest_path}=    Set Variable    ${CURDIR}/../test_data/manifests/s3-writer-job.yaml

    # Read the manifest template
    ${manifest}=    Get File    ${manifest_path}

    # Replace placeholders
    ${manifest}=    Replace String    ${manifest}    STORAGE_CONFIG_MAP_NAME    ${storage_config_map_name}
    ${manifest}=    Replace String    ${manifest}    SECRET_NAME_PLACEHOLDER    ${secret_name}
    ${manifest}=    Replace String    ${manifest}    ACCESS_KEY_NAME_PLACEHOLDER    ${access_key_name}
    ${manifest}=    Replace String    ${manifest}    SECRET_KEY_NAME_PLACEHOLDER    ${secret_key_name}
    ${manifest}=    Replace String    ${manifest}    name: s3-writer-test-job    name: ${job_name}
    ${manifest}=    Replace String    ${manifest}    value: "PLACEHOLDER"    value: "${test_data_key}"    count=1
    ${manifest}=    Replace String    ${manifest}    value: "PLACEHOLDER"    value: "${test_data_content}"    count=1

    # Write to temp file
    ${temp_file}=    Set Variable    /tmp/${job_name}.yaml
    Create File    ${temp_file}    ${manifest}

    # Apply the Job
    ${result}=    Run Process    kubectl apply -f ${temp_file} -n ${namespace}    shell=True
    Should Be Equal As Integers    ${result.rc}    0    msg=Failed to submit S3 writer job: ${result.stderr}

    Log    Submitted S3 writer job: ${job_name} in namespace: ${namespace}    INFO

    RETURN    ${job_name}

Submit S3 Reader Job
    [Documentation]    Submit a Kubernetes Job to read and verify data from S3
    ...    Similar to Submit S3 Writer Job but for reading/verification
    [Arguments]    ${namespace}    ${storage_config_map_name}    ${secret_name}    ${access_key_name}    ${secret_key_name}    ${test_data_key}    ${expected_content}    ${random_suffix}

    ${job_name}=    Set Variable    s3-reader-test-${random_suffix}
    ${manifest_path}=    Set Variable    ${CURDIR}/../test_data/manifests/s3-reader-job.yaml

    ${manifest}=    Get File    ${manifest_path}

    ${manifest}=    Replace String    ${manifest}    STORAGE_CONFIG_MAP_NAME    ${storage_config_map_name}
    ${manifest}=    Replace String    ${manifest}    SECRET_NAME_PLACEHOLDER    ${secret_name}
    ${manifest}=    Replace String    ${manifest}    ACCESS_KEY_NAME_PLACEHOLDER    ${access_key_name}
    ${manifest}=    Replace String    ${manifest}    SECRET_KEY_NAME_PLACEHOLDER    ${secret_key_name}
    ${manifest}=    Replace String    ${manifest}    name: s3-reader-test-job    name: ${job_name}
    ${manifest}=    Replace String    ${manifest}    value: "PLACEHOLDER"    value: "${test_data_key}"    count=1
    ${manifest}=    Replace String    ${manifest}    value: "PLACEHOLDER"    value: "${expected_content}"    count=1

    ${temp_file}=    Set Variable    /tmp/${job_name}.yaml
    Create File    ${temp_file}    ${manifest}

    ${result}=    Run Process    kubectl apply -f ${temp_file} -n ${namespace}    shell=True
    Should Be Equal As Integers    ${result.rc}    0    msg=Failed to submit S3 reader job: ${result.stderr}

    Log    Submitted S3 reader job: ${job_name} in namespace: ${namespace}    INFO

    RETURN    ${job_name}

Submit S3 Cleanup Job
    [Documentation]    Submit a Kubernetes Job to cleanup e2e test data from S3
    [Arguments]    ${namespace}    ${storage_config_map_name}    ${secret_name}    ${access_key_name}    ${secret_key_name}    ${random_suffix}

    ${job_name}=    Set Variable    s3-cleanup-test-${random_suffix}
    ${manifest_path}=    Set Variable    ${CURDIR}/../test_data/manifests/s3-cleanup-job.yaml

    ${manifest}=    Get File    ${manifest_path}

    ${manifest}=    Replace String    ${manifest}    STORAGE_CONFIG_MAP_NAME    ${storage_config_map_name}
    ${manifest}=    Replace String    ${manifest}    SECRET_NAME_PLACEHOLDER    ${secret_name}
    ${manifest}=    Replace String    ${manifest}    ACCESS_KEY_NAME_PLACEHOLDER    ${access_key_name}
    ${manifest}=    Replace String    ${manifest}    SECRET_KEY_NAME_PLACEHOLDER    ${secret_key_name}
    ${manifest}=    Replace String    ${manifest}    name: s3-cleanup-test-job    name: ${job_name}

    ${temp_file}=    Set Variable    /tmp/${job_name}.yaml
    Create File    ${temp_file}    ${manifest}

    ${result}=    Run Process    kubectl apply -f ${temp_file} -n ${namespace}    shell=True
    Should Be Equal As Integers    ${result.rc}    0    msg=Failed to submit S3 cleanup job: ${result.stderr}

    Log    Submitted S3 cleanup job: ${job_name} in namespace: ${namespace}    INFO

    RETURN    ${job_name}

Wait For Job Completion
    [Documentation]    Wait for a Kubernetes Job to complete (succeed or fail)
    [Arguments]    ${job_name}    ${namespace}    ${timeout}=${S3_JOB_TIMEOUT}

    Wait Until Keyword Succeeds    ${timeout}    ${S3_JOB_POLL_INTERVAL}
    ...    Check Job Completed    ${job_name}    ${namespace}

    Log    Job ${job_name} completed    INFO

Check Job Completed
    [Documentation]    Helper keyword to check if a Job has completed
    [Arguments]    ${job_name}    ${namespace}

    ${kubectl_cmd}=    Set Variable    kubectl get job ${job_name} -n ${namespace} -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}'
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    ${complete_status}=    Set Variable    ${result.stdout}

    ${kubectl_cmd}=    Set Variable    kubectl get job ${job_name} -n ${namespace} -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}'
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    ${failed_status}=    Set Variable    ${result.stdout}

    Should Be True    '${complete_status}' == 'True' or '${failed_status}' == 'True'
    ...    msg=Job ${job_name} not yet completed (Complete=${complete_status}, Failed=${failed_status})

Verify Job Succeeded
    [Documentation]    Verify that a Job completed successfully.
    ...    Captures job logs and status before asserting, so failures include diagnostics.
    [Arguments]    ${job_name}    ${namespace}

    # Capture job status for diagnostics
    ${status_cmd}=    Set Variable
    ...    kubectl get job ${job_name} -n ${namespace} -o jsonpath='{.status.conditions[*].type}: {.status.conditions[*].message}'
    ${status_result}=    Run Process    ${status_cmd}    shell=True

    # Capture pod logs before asserting so failures show what went wrong
    ${logs}=    Set Variable    (no logs captured)
    ${pod_cmd}=    Set Variable
    ...    kubectl get pods -n ${namespace} -l job-name\=${job_name} -o jsonpath='{.items[0].metadata.name}'
    ${pod_result}=    Run Process    ${pod_cmd}    shell=True
    IF    '${pod_result.stdout}' != '${EMPTY}'
        ${log_result}=    Run Process
        ...    kubectl logs ${pod_result.stdout} -n ${namespace}    shell=True
        ${logs}=    Set Variable    ${log_result.stdout}
    END

    # Now check success
    ${succeeded_cmd}=    Set Variable
    ...    kubectl get job ${job_name} -n ${namespace} -o jsonpath='{.status.succeeded}'
    ${result}=    Run Process    ${succeeded_cmd}    shell=True
    Should Be Equal    ${result.stdout}    1
    ...    msg=Job ${job_name} did not succeed.\nJob status: ${status_result.stdout}\nPod logs:\n${logs}

    Log    Job ${job_name} succeeded    INFO

Get Job Logs
    [Documentation]    Get logs from a completed Job's pod
    [Arguments]    ${job_name}    ${namespace}

    # Get the pod name for this job
    ${kubectl_cmd}=    Set Variable    kubectl get pods -n ${namespace} -l job-name\=${job_name} -o jsonpath='{.items[0].metadata.name}'
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    ${pod_name}=    Set Variable    ${result.stdout}

    Should Not Be Empty    ${pod_name}    msg=No pod found for job ${job_name}

    # Get logs from the pod
    ${kubectl_cmd}=    Set Variable    kubectl logs ${pod_name} -n ${namespace}
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    ${logs}=    Set Variable    ${result.stdout}

    Log    Job ${job_name} logs:\n${logs}    INFO

    RETURN    ${logs}

Delete Job
    [Documentation]    Delete a Kubernetes Job and its pods
    [Arguments]    ${job_name}    ${namespace}

    ${kubectl_cmd}=    Set Variable    kubectl delete job ${job_name} -n ${namespace} --ignore-not-found\=true
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    Log    Deleted job ${job_name}: ${result.stdout}    DEBUG

Generate Random Suffix
    [Documentation]    Generate a random suffix for unique resource names
    ${timestamp}=    Evaluate    int(__import__('time').time())
    ${random}=    Evaluate    __import__('random').randint(1000, 9999)
    ${suffix}=    Set Variable    ${timestamp}-${random}
    RETURN    ${suffix}

Create Storage ConfigMap For Local Testing
    [Documentation]    Create ConfigMap for storage in local development (Agent doesn't run)
    ...    This ConfigMap would normally be created by the Agent
    [Arguments]    ${namespace}    ${config_map_name}    ${bucket_url}    ${access_key_name}    ${secret_key_name}    ${secret_name}

    ${manifest}=    Catenate    SEPARATOR=\n
    ...    apiVersion: v1
    ...    kind: ConfigMap
    ...    metadata:
    ...    ${SPACE}${SPACE}name: ${config_map_name}
    ...    ${SPACE}${SPACE}namespace: ${namespace}
    ...    data:
    ...    ${SPACE}${SPACE}BUCKET_URL: "${bucket_url}"
    ...    ${SPACE}${SPACE}ACCESS_KEY_NAME: "${access_key_name}"
    ...    ${SPACE}${SPACE}SECRET_KEY_NAME: "${secret_key_name}"
    ...    ${SPACE}${SPACE}SECRET_NAME: "${secret_name}"

    ${temp_file}=    Set Variable    /tmp/storage-configmap-${config_map_name}.yaml
    Create File    ${temp_file}    ${manifest}

    ${kubectl_cmd}=    Set Variable    kubectl apply -f ${temp_file} -n ${namespace}
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    Should Be Equal As Integers    ${result.rc}    0    msg=Failed to create ConfigMap: ${result.stderr}

    Log    Created ConfigMap ${config_map_name} in namespace ${namespace}    INFO

Create ExternalSecret For Local Testing
    [Documentation]    Create ExternalSecret for storage credentials in local development
    ...    This ExternalSecret would normally be created by the Agent
    ...    For local testing, we create a regular Secret with the same credentials
    ...    Reads Minio credentials from the cluster secret to avoid hardcoding
    [Arguments]    ${namespace}    ${secret_name}    ${access_key_name}    ${secret_key_name}

    # Read Minio credentials from the cluster secret rather than hardcoding
    ${minio_creds}=    Get Minio Credentials From Cluster

    ${manifest}=    Catenate    SEPARATOR=\n
    ...    apiVersion: v1
    ...    kind: Secret
    ...    metadata:
    ...    ${SPACE}${SPACE}name: ${secret_name}
    ...    ${SPACE}${SPACE}namespace: ${namespace}
    ...    type: Opaque
    ...    stringData:
    ...    ${SPACE}${SPACE}${access_key_name}: "${minio_creds}[user]"
    ...    ${SPACE}${SPACE}${secret_key_name}: "${minio_creds}[password]"

    ${temp_file}=    Set Variable    /tmp/storage-secret-${secret_name}.yaml
    Create File    ${temp_file}    ${manifest}

    ${kubectl_cmd}=    Set Variable    kubectl apply -f ${temp_file} -n ${namespace}
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    Should Be Equal As Integers    ${result.rc}    0    msg=Failed to create Secret: ${result.stderr}

    Log    Created Secret ${secret_name} in namespace ${namespace}    INFO

Delete Storage Resources For Local Testing
    [Documentation]    Delete ConfigMap and Secret created for local testing
    [Arguments]    ${namespace}    ${config_map_name}    ${secret_name}

    ${kubectl_cmd}=    Set Variable    kubectl delete configmap ${config_map_name} -n ${namespace} --ignore-not-found=true
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    Log    Deleted ConfigMap ${config_map_name}: ${result.stdout}    DEBUG

    ${kubectl_cmd}=    Set Variable    kubectl delete secret ${secret_name} -n ${namespace} --ignore-not-found=true
    ${result}=    Run Process    ${kubectl_cmd}    shell=True
    Log    Deleted Secret ${secret_name}: ${result.stdout}    DEBUG

Get Minio Credentials From Cluster
    [Documentation]    Reads Minio root credentials from the cluster secret.
    ...    Parses the config.env from minio-tenant-default/default-minio-tenant-env-configuration.
    ...    Returns a dictionary with 'user' and 'password' keys.

    # Extract MINIO_ROOT_USER from the secret
    ${user_result}=    Run Process
    ...    kubectl get secret default-minio-tenant-env-configuration -n minio-tenant-default -o jsonpath\='{.data.config\\.env}' | base64 -d | grep 'MINIO_ROOT_USER\=' | head -1 | sed 's/.*MINIO_ROOT_USER\=//' | tr -d '"'
    ...    shell=True
    Should Be Equal As Integers    ${user_result.rc}    0
    ...    msg=Failed to read Minio user from cluster: ${user_result.stderr}
    Should Not Be Empty    ${user_result.stdout}
    ...    msg=MINIO_ROOT_USER not found in cluster secret

    # Extract MINIO_ROOT_PASSWORD from the secret
    ${password_result}=    Run Process
    ...    kubectl get secret default-minio-tenant-env-configuration -n minio-tenant-default -o jsonpath\='{.data.config\\.env}' | base64 -d | grep 'MINIO_ROOT_PASSWORD\=' | head -1 | sed 's/.*MINIO_ROOT_PASSWORD\=//' | tr -d '"'
    ...    shell=True
    Should Be Equal As Integers    ${password_result.rc}    0
    ...    msg=Failed to read Minio password from cluster: ${password_result.stderr}
    Should Not Be Empty    ${password_result.stdout}
    ...    msg=MINIO_ROOT_PASSWORD not found in cluster secret

    &{credentials}=    Create Dictionary
    ...    user=${user_result.stdout}
    ...    password=${password_result.stdout}

    Log    Retrieved Minio credentials for user: ${user_result.stdout}    DEBUG

    RETURN    ${credentials}
