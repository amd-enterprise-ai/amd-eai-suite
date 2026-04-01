# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Generic API endpoint resolution for any service.
...                 Provides a parameterized keyword that resolves a service's API base URL
...                 by trying the public HTTPS domain first and falling back to port-forward.
...                 The resolved URL is cached per service per suite.
Resource            ../deployment.resource
Library             RequestsLibrary
Library             Collections


*** Variables ***
# Per-service base URL cache: dictionary mapping service name to resolved base URL.
# Populated on first call per service, avoids repeated kubectl and health check calls.
&{SERVICE_BASE_URLS}


*** Keywords ***
Service API Endpoint
    [Documentation]    Returns the full API endpoint URL for the given service.
    ...                Tries public HTTPS domain first (discovered from cluster),
    ...                falls back to port-forward if unavailable.
    ...                Base URL is resolved once per suite per service and cached.
    ...
    ...                Args:
    ...                - service_name: Service identifier (e.g., "airm", "aiwb")
    ...                - endpoint: Optional path appended after /v1/ (e.g., "health", "projects")
    ...
    ...                Examples:
    ...                | ${url}= | Service API Endpoint | airm |                  | # => https://airmapi.domain/v1 |
    ...                | ${url}= | Service API Endpoint | airm | endpoint=health  | # => https://airmapi.domain/v1/health |
    ...                | ${url}= | Service API Endpoint | aiwb | endpoint=charts  | # => https://aiwbapi.domain/v1/charts |
    [Arguments]    ${service_name}    ${endpoint}=${None}

    # Return cached base URL if already resolved for this service
    ${cached}=    Get From Dictionary    ${SERVICE_BASE_URLS}    ${service_name}    default=${EMPTY}
    IF    "${cached}" != ""
        IF    $endpoint is not None
            RETURN    ${cached}/v1/${endpoint}
        END
        RETURN    ${cached}/v1
    END

    # First call for this service: resolve and cache the base URL
    ${in_cluster}=    Is Running In Cluster

    IF    ${in_cluster}
        # Running inside the cluster - use internal service URL directly
        ${base_url}=        Service endpoint    ${service_name}    ${service_name}-api
        Set Suite Variable  ${USING_EXTERNAL_ENDPOINT}    ${FALSE}
        Log                 Running in-cluster, using internal endpoint: ${base_url}    level=INFO
    ELSE
        ${discovered_domain}=    Get Domain From Cluster

        IF    "${discovered_domain}" != "None"
            # Use discovered public HTTPS endpoint - fail if not accessible
            VAR    ${public_url}       https://${service_name}api.${discovered_domain}
            TRY
                ${test_response}=   GET             ${public_url}/v1/health    expected_status=200    timeout=10
                Log                 Public endpoint accessible: ${public_url}    level=INFO
            EXCEPT    AS    ${error}
                Fail    ${service_name} public endpoint ${public_url}/v1/health is not accessible. Error: ${error}
            END
            VAR    ${base_url}      ${public_url}
            Set Suite Variable  ${USING_EXTERNAL_ENDPOINT}    ${TRUE}
        ELSE
            # Could not discover domain, use port-forward directly
            Log                 Could not discover public domain for ${service_name}, using port-forward    level=WARN
            ${base_url}=        Service endpoint    ${service_name}    ${service_name}-api
            Set Suite Variable  ${USING_EXTERNAL_ENDPOINT}    ${FALSE}
        END
    END

    # Cache the resolved base URL for this service
    Set To Dictionary       ${SERVICE_BASE_URLS}    ${service_name}    ${base_url}
    Set Suite Variable      &{SERVICE_BASE_URLS}

    IF    $endpoint is not None
        RETURN    ${base_url}/v1/${endpoint}
    END
    RETURN    ${base_url}/v1
