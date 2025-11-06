# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Library     Process
Library     ../libraries/TestRunId.py
Library     ../libraries/StringUtils.py
Library     ../libraries/KubeConnection.py
Library     DateTime
Library     Collections
Library     OperatingSystem


*** Variables ***
${USE_DEFAULT_NAMESPACE}    ${TRUE}     # this is set to the empty string or overridden by the string "True" if set on the command line with -d.
${NAMESPACE_PREFIX}         ${EMPTY}    # this is optionally set to an arbitrary prefix unless the USE_DEFAULT_NAMESPACE is set to "True"
${NAMESPACE_WAS_CREATED}    ${FALSE}    # this is a string. set to "True" if the namespace was created by this test run
@{SKIP_KINDS}               ServiceAccount


*** Keywords ***
Get namespace prefix
    [Documentation]    Returns namespace prefix for Kubernetes namespaces.
    ...    The prefix is determined in one of three ways:
    ...    1. If USE_DEFAULT_NAMESPACE is True, returns empty string to use default k8s namespace
    ...    2. If NAMESPACE_PREFIX is set, uses that specific prefix
    ...    3. Otherwise generates a unique time-based test run id as the prefix
    IF    $USE_DEFAULT_NAMESPACE
        RETURN                  ${EMPTY}
    END
    IF    "${NAMESPACE_PREFIX}" != ""
        RETURN                  ${NAMESPACE_PREFIX}
    END
    ${test_run_id} =        Test run id
    RETURN                  ${test_run_id}

Service endpoint
    [Documentation]    Returns full service URL with proper protocol. Automatically uses internal endpoints when running inside k8s
    [Arguments]             ${service}              ${micro_service}        ${prefix}=${namespace_prefix}                   ${force_external}=${FALSE}

    # Auto-detect if we're running in Kubernetes
    ${in_cluster} =         Run Keyword And Return Status                   File Should Exist       /var/run/secrets/kubernetes.io/serviceaccount/token
    ${use_internal} =       Set Variable            ${in_cluster}

    # Allow forcing external endpoints even when in cluster if needed
    IF    ${force_external}
        ${use_internal} =       Set Variable            ${FALSE}
    END

    ${host} =               Run Keyword If          ${use_internal}         Internal Host For       ${service}              ${micro_service}        ${prefix}
    ...                     ELSE                    External Host For       ${service}              ${micro_service}        prefix=${prefix}

    IF    "localhost" in $host or ${use_internal}
        RETURN                  http://${host}
    ELSE
        RETURN                  https://${host}
    END

Namespace ${namespace} Exists
    ${result} =             Run Process             kubectl                 get                     namespace               ${namespace}
    RETURN                  ${result.rc} == 0

Apps ${app_names} are deployed
    ${date1} =              Get Current Date
    ${app_names_list} =     English list            ${app_names}
    ${app_count} =          Get Length              ${app_names_list}
    IF    not $USE_DEFAULT_NAMESPACE
        IF    $NAMESPACE_PREFIX != ""
            Set global variable     ${namespace_prefix}     ${NAMESPACE_PREFIX}
        ELSE
            ${test_run_id} =        Test run id
            Set global variable     ${namespace_prefix}     ${test_run_id}
        END
        Log                     Using namespace prefix ${namespace_prefix}.     console=yes
        @{apps_to_deploy} =     Create List
        FOR    ${app}    IN    @{app_names_list}
            ${ns_exists} =          Namespace ${namespace_prefix}-${app} Exists
            IF    not ${ns_exists}
                ${apps_to_deploy} =     Create List             @{apps_to_deploy}       ${app}
            ELSE
                Log                     Namespace ${namespace_prefix}-${app} already exists.                    console=yes
            END
        END
        ${deploy_count} =       Get Length              ${apps_to_deploy}
        IF    ${deploy_count} > 0
            IF    ${deploy_count} == 1
                Log                     Deploying app ${apps_to_deploy}[0]              console=yes
            ELSE
                Log                     Deploying apps @{apps_to_deploy}                console=yes
            END
            # Deploy apps             ${namespace_prefix}     ${apps_to_deploy}       timeout=1200
            Fail                   Deployment step is currently disabled. Would deploy apps ${apps_to_deploy} with prefix ${namespace_prefix}
            Set Suite Variable      ${NAMESPACE_WAS_CREATED}                        ${TRUE}
        ELSE
            Log                     All namespaces already exist.                   console=yes
            Set Suite Variable      ${NAMESPACE_WAS_CREATED}                        ${FALSE}
        END
    END

    IF    ${app_count} == 1
        Log                     App ${app_names} is deployed                    console=yes
    ELSE
        Log                     Apps ${app_names} are deployed                  console=yes
    END
    ${date2} =              Get Current Date
    ${actiontime} =         Subtract Date From Date                         ${date2}                ${date1}

    # Log appropriate message based on whether apps were actually deployed
    IF    ${NAMESPACE_WAS_CREATED}
        Log                     Deploying apps took ${actiontime}               console=yes
    ELSE
        Log                     Checking existing apps took ${actiontime}       console=yes
    END

Apps are undeployed
    Log                     NAMESPACE_WAS_CREATED variable = ${NAMESPACE_WAS_CREATED}.
    IF    $NAMESPACE_WAS_CREATED
        ${date1} =              Get Current Date
        ${result} =             Run process             silodev                 services                undeploy                --prefix                ${namespace_prefix}
        IF    ${result.rc} != 0
            Fail
            ...                     Undeploying apps failed (return code ${result.rc}): stderr: ${result.stderr}, stdout: ${result.stdout}
        ELSE
            ${date2} =              Get Current Date
            ${actiontime} =         Subtract Date From Date                         ${date2}                ${date1}
            Log                     Undeploying apps took ${actiontime}             console=yes
        END
    ELSE
        Log                     Skipping undeploying services since the namespace was not created by this test run.             console=yes
    END
