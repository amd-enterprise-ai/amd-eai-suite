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
@{SKIP_KINDS}               ServiceAccount


*** Keywords ***
Service endpoint
    [Documentation]    Returns full service URL with proper protocol. Automatically uses internal endpoints when running inside k8s
    [Arguments]             ${service}              ${micro_service}        ${force_external}=${FALSE}

    # Auto-detect if we're running in Kubernetes
    ${in_cluster} =         Run Keyword And Return Status                   File Should Exist       /var/run/secrets/kubernetes.io/serviceaccount/token
    ${use_internal} =       Set Variable            ${in_cluster}

    # Allow forcing external endpoints even when in cluster if needed
    IF    ${force_external}
        ${use_internal} =       Set Variable            ${FALSE}
    END

    ${host} =               Run Keyword If          ${use_internal}         Internal Host For       ${service}              ${micro_service}
    ...                     ELSE                    External Host For       ${service}              ${micro_service}

    IF    "localhost" in $host or ${use_internal}
        RETURN                  http://${host}
    ELSE
        RETURN                  https://${host}
    END
