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
Is Running In Cluster
    [Documentation]    Check if code is running inside a Kubernetes cluster.
    ...                Returns True if service account token file exists, False otherwise.
    ${in_cluster}=      Run Keyword And Return Status    File Should Exist    /var/run/secrets/kubernetes.io/serviceaccount/token
    RETURN              ${in_cluster}

Service endpoint
    [Documentation]    Returns full service URL with proper protocol. Automatically uses internal endpoints when running inside k8s
    [Arguments]             ${service}              ${micro_service}        ${force_external}=${FALSE}

    # Auto-detect if we're running in Kubernetes
    ${in_cluster} =         Is Running In Cluster
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

Get Domain From Cluster
    [Documentation]    Retrieves the base domain from the cluster by reading the Gateway listener hostname.
    ...                The Gateway defines listeners with hostnames like *.app-dev.silogen.ai.
    ...                Returns the domain (e.g., app-dev.silogen.ai) or None if not found.
    ...                Result is cached in a suite variable after first successful lookup.

    # Return cached domain if already resolved
    ${cached}=    Get Variable Value    ${CLUSTER_DOMAIN}    ${EMPTY}
    IF    "${cached}" != ""
        RETURN    ${cached}
    END

    TRY
        # Get domain from the Gateway's HTTPS listener hostname (e.g., *.app-dev.silogen.ai)
        ${result}=    Run Process    kubectl    get    gateway    https
        ...          -n    kgateway-system    -o    jsonpath\={.spec.listeners[0].hostname}    timeout=10s

        IF    ${result.rc} == 0 and "${result.stdout}" != ""
            ${hostname}=    Set Variable    ${result.stdout}
            # Strip wildcard prefix (*.) if present
            ${domain}=      Evaluate    $hostname.lstrip('*.')
            Log    Discovered domain from Gateway: ${domain}    level=INFO
            Set Suite Variable    ${CLUSTER_DOMAIN}    ${domain}
            RETURN    ${domain}
        END

        Log    Could not retrieve domain from Gateway    level=WARN
        RETURN    ${None}
    EXCEPT    AS    ${error}
        Log    Failed to query Gateway for domain: ${error}    level=WARN
        RETURN    ${None}
    END
