# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level kubectl keywords for workload management.
...                 Provides direct kubectl and helm command wrappers for managing workloads.
...                 This is part of the kubectl layer that handles direct Kubernetes operations.
Library             Process
Library             Collections
Library             String
Library             OperatingSystem
Library             BuiltIn


*** Keywords ***
Install workload via helm
    [Documentation]    Install a workload using helm template + kubectl apply
    ...    This approach avoids helm release tracking issues and is more reliable for testing
    ...    Returns the helm release name for later cleanup
    [Arguments]    ${chart_path}    ${release_name}    ${namespace}    ${values}=${None}

    # Build helm template command
    ${helm_cmd}=    Set Variable    helm template ${release_name} ${chart_path} --namespace ${namespace}

    IF    $values is not None
        FOR    ${key}    ${value}    IN    &{values}
            ${helm_cmd}=    Set Variable    ${helm_cmd} --set ${key}=${value}
        END
    END

    Log    Templating workload: ${helm_cmd}    INFO
    ${result}=    Run Process    ${helm_cmd}    shell=True

    IF    ${result.rc} != 0
        Log    Helm template failed: ${result.stderr}    ERROR
        FAIL    Failed to template helm chart: ${result.stderr}
    END

    Log    Helm template successful, applying via kubectl    DEBUG

    # Save the rendered YAML to a temporary file
    ${temp_file}=    Set Variable    /tmp/workload-${release_name}.yaml
    Create File    ${temp_file}    ${result.stdout}

    # Apply the rendered YAML
    ${kubectl_cmd}=    Set Variable    kubectl apply -f ${temp_file} --namespace ${namespace}
    ${apply_result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${apply_result.rc} != 0
        Log    Kubectl apply failed: ${apply_result.stderr}    ERROR
        Remove File    ${temp_file}
        FAIL    Failed to apply workload via kubectl: ${apply_result.stderr}
    END

    Log    Kubectl apply output: ${apply_result.stdout}    INFO

    # Store the temp file path for cleanup
    Set Test Variable    ${TEMP_WORKLOAD_FILE_${release_name}}    ${temp_file}

    RETURN    ${release_name}

Uninstall workload via helm
    [Documentation]    Uninstall a workload using kubectl delete (from helm template approach)
    [Arguments]    ${release_name}    ${namespace}

    # Check if we have the temp file from installation
    ${temp_file_var}=    Set Variable    TEMP_WORKLOAD_FILE_${release_name}
    ${temp_file_exists}=    Run Keyword And Return Status    Variable Should Exist    ${${temp_file_var}}

    IF    ${temp_file_exists}
        ${temp_file}=    Get Variable Value    ${${temp_file_var}}
        ${file_exists}=    Run Keyword And Return Status    File Should Exist    ${temp_file}

        IF    ${file_exists}
            # Delete using the same YAML that was applied
            ${kubectl_cmd}=    Set Variable    kubectl delete -f ${temp_file} --namespace ${namespace} --ignore-not-found=true
            Log    Deleting workload using saved YAML: ${kubectl_cmd}    INFO
            ${result}=    Run Process    ${kubectl_cmd}    shell=True

            # Clean up the temp file
            Remove File    ${temp_file}

            IF    ${result.rc} != 0
                Log    Kubectl delete failed: ${result.stderr}    WARN
                RETURN    ${False}
            END

            Log    Kubectl delete output: ${result.stdout}    INFO
            RETURN    ${True}
        END
    END

    # Fallback: delete by labels (helm template adds app.kubernetes.io/instance label)
    # Only delete common resource types that workloads typically create
    Log    Temp file not found, using label-based deletion for ${release_name}    INFO
    ${kubectl_cmd}=    Set Variable    kubectl delete job,deployment,pod,service,configmap,secret -l app.kubernetes.io/instance=${release_name} --namespace ${namespace} --ignore-not-found=true
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    # Don't fail on permission errors - just log them
    IF    ${result.rc} != 0
        Log    Kubectl label-based delete had issues: ${result.stderr}    WARN
        # Check if there were actual errors vs just permission warnings
        ${has_real_errors}=    Run Keyword And Return Status    Should Contain    ${result.stderr}    Error from server (NotFound)
        IF    not ${has_real_errors}
            Log    Deletion completed with permission warnings (expected for restricted users)    INFO
            RETURN    ${True}
        END
        RETURN    ${False}
    END

    Log    Kubectl label-based delete output: ${result.stdout}    INFO
    RETURN    ${True}

Get workload status from kubectl
    [Documentation]    Get the status of a Kubernetes resource using kubectl
    ...    Returns the status phase or condition
    [Arguments]    ${resource_type}    ${resource_name}    ${namespace}

    ${kubectl_cmd}=    Set Variable    kubectl get ${resource_type} ${resource_name} -n ${namespace} -o jsonpath='{.status.phase}'
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${result.rc} != 0
        Log    Failed to get status: ${result.stderr}    DEBUG
        RETURN    Unknown
    END

    RETURN    ${result.stdout}

Get job status from kubectl
    [Documentation]    Get the status of a Kubernetes Job
    ...    Returns a status string: Pending, Running, Complete, or Failed
    [Arguments]    ${job_name}    ${namespace}

    # Check if job exists first
    ${kubectl_check}=    Set Variable    kubectl get job ${job_name} -n ${namespace} 2>&1
    ${check_result}=    Run Process    ${kubectl_check}    shell=True

    IF    ${check_result.rc} != 0
        Log    Job does not exist yet: ${job_name}    DEBUG
        RETURN    NotFound
    END

    # Get job conditions
    ${kubectl_cmd}=    Set Variable    kubectl get job ${job_name} -n ${namespace} -o jsonpath='{.status.conditions[?(@.type=="Complete")].status} {.status.conditions[?(@.type=="Failed")].status} {.status.active} {.status.succeeded} {.status.failed}'
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${result.rc} != 0
        Log    Failed to get job status: ${result.stderr}    DEBUG
        RETURN    Unknown
    END

    ${status_info}=    Set Variable    ${result.stdout}
    ${parts}=    Split String    ${status_info}

    # Get values with proper error handling for Robot Framework Collections library
    ${parts_length}=    Get Length    ${parts}
    ${complete}=    Run Keyword If    ${parts_length} > 0    Get From List    ${parts}    0    ELSE    Set Variable    ${EMPTY}
    ${failed}=    Run Keyword If    ${parts_length} > 1    Get From List    ${parts}    1    ELSE    Set Variable    ${EMPTY}
    ${active}=    Run Keyword If    ${parts_length} > 2    Get From List    ${parts}    2    ELSE    Set Variable    0
    ${succeeded}=    Run Keyword If    ${parts_length} > 3    Get From List    ${parts}    3    ELSE    Set Variable    0
    ${failed_count}=    Run Keyword If    ${parts_length} > 4    Get From List    ${parts}    4    ELSE    Set Variable    0

    IF    '${complete}' == 'True'
        RETURN    Complete
    ELSE IF    '${failed}' == 'True' or '${failed_count}' != '0'
        RETURN    Failed
    ELSE IF    '${active}' != '0' and '${active}' != ''
        RETURN    Running
    ELSE
        RETURN    Pending
    END

Get pod pending reason
    [Documentation]    Get the reason why a pod is pending
    ...    Useful for verifying quota enforcement
    [Arguments]    ${pod_name}    ${namespace}

    ${kubectl_cmd}=    Set Variable    kubectl get pod ${pod_name} -n ${namespace} -o jsonpath='{.status.conditions[?(@.type=="PodScheduled")].reason} {.status.conditions[?(@.type=="PodScheduled")].message}'
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${result.rc} != 0
        Log    Failed to get pod pending reason: ${result.stderr}    DEBUG
        RETURN    Unknown
    END

    RETURN    ${result.stdout}

Wait for resources to be ready
    [Documentation]    Wait for kubectl-applied resources to be ready
    ...    Polls kubectl to verify resources exist and are in expected state
    [Arguments]    ${release_name}    ${namespace}    ${timeout}=2 min

    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Verify resources are ready    ${release_name}    ${namespace}

Verify resources are ready
    [Documentation]    Verify kubectl-applied resources are ready (used with polling)
    [Arguments]    ${release_name}    ${namespace}

    # Check if any resources with the release label exist
    ${kubectl_cmd}=    Set Variable    kubectl get all -l app.kubernetes.io/instance=${release_name} -n ${namespace} --no-headers
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${result.rc} != 0
        FAIL    Resources not ready: ${result.stderr}
    END

    # If no output, no resources found
    IF    '${result.stdout.strip()}' == ''
        FAIL    No resources found for release ${release_name}
    END

    Log    Resources ready for ${release_name}: ${result.stdout}    DEBUG

Get pods for job
    [Documentation]    Get pod names associated with a job
    [Arguments]    ${job_name}    ${namespace}

    ${kubectl_cmd}=    Set Variable    kubectl get pods -n ${namespace} --selector=job-name=${job_name} -o jsonpath='{.items[*].metadata.name}'
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${result.rc} != 0
        Log    Failed to get pods for job: ${result.stderr}    DEBUG
        RETURN    @{EMPTY}
    END

    ${pod_names}=    Split String    ${result.stdout}
    RETURN    @{pod_names}

Check if resource exists
    [Documentation]    Check if a Kubernetes resource exists
    [Arguments]    ${resource_type}    ${resource_name}    ${namespace}

    ${kubectl_cmd}=    Set Variable    kubectl get ${resource_type} ${resource_name} -n ${namespace} 2>&1
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${result.rc} == 0
        RETURN    ${True}
    ELSE
        RETURN    ${False}
    END

Delete kubernetes resource
    [Documentation]    Delete a Kubernetes resource using kubectl
    [Arguments]    ${resource_type}    ${resource_name}    ${namespace}

    ${kubectl_cmd}=    Set Variable    kubectl delete ${resource_type} ${resource_name} -n ${namespace} --ignore-not-found=true
    ${result}=    Run Process    ${kubectl_cmd}    shell=True

    IF    ${result.rc} != 0
        Log    Failed to delete resource: ${result.stderr}    WARN
        RETURN    ${False}
    END

    Log    Deleted ${resource_type} ${resource_name}    INFO
    RETURN    ${True}
