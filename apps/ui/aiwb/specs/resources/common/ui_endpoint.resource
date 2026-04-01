# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       UI endpoint discovery for frontend E2E tests.
...                 Resolves the AIWB UI base URL from environment variable or kubeconfig context.
...                 Unlike API endpoints that use port-forwarding, browser tests need real external
...                 URLs because OAuth redirect URIs must match the actual hostname.
Library             OperatingSystem
Library             Process
Library             String


*** Variables ***
# Override via environment variable: AIWB_UI_URL=https://aiwbui.app-dev.silogen.ai
${AIWB_UI_URL}      ${EMPTY}


*** Keywords ***
AIWB UI endpoint
    [Documentation]    Returns the AIWB UI base URL.
    ...                Checks AIWB_UI_URL environment variable first, then derives from kubectl context.
    ...                Browser tests must use the real external URL (not port-forwarded localhost)
    ...                because the OAuth login redirect must match the registered redirect URI.

    # Return cached value if already resolved
    IF    "${AIWB_UI_URL}" != "${EMPTY}"
        RETURN    ${AIWB_UI_URL}
    END

    # Check environment variable
    ${env_url}=    Get Environment Variable    AIWB_UI_URL    default=${EMPTY}
    IF    "${env_url}" != "${EMPTY}"
        VAR    ${AIWB_UI_URL}    ${env_url}    scope=SUITE
        RETURN    ${env_url}
    END

    # Derive from kubectl context cluster domain
    ${url}=    Derive UI URL from kubectl context
    VAR    ${AIWB_UI_URL}    ${url}    scope=SUITE
    RETURN    ${url}

Derive UI URL from kubectl context
    [Documentation]    Derives the AIWB UI URL from the current kubectl context.
    ...                Extracts the cluster domain from the API server URL and constructs
    ...                the UI endpoint using the naming convention: aiwbui.<cluster-domain>.
    ...                Example: https://k8s.app-dev.silogen.ai:6443 → https://aiwbui.app-dev.silogen.ai

    ${result}=    Run Process    kubectl    config    view    --minify    -o    jsonpath\={.clusters[0].cluster.server}
    IF    ${result.rc} != 0
        Fail    Failed to get cluster server from kubectl config: ${result.stderr}
    END

    # Extract cluster domain: https://k8s.app-dev.silogen.ai:6443 → app-dev.silogen.ai
    VAR    ${server}    ${result.stdout}
    # Get hostname without protocol and port
    ${hostname}=    Evaluate    "${server}".split("//")[1].split(":")[0]
    # Remove first subdomain prefix to get cluster domain
    ${dot_index}=    Evaluate    "${hostname}".index(".")
    ${domain}=    Evaluate    "${hostname}"[${dot_index}+1:]

    VAR    ${url}    https://aiwbui.${domain}
    Log    Derived AIWB UI URL: ${url} (from server: ${server})    INFO
    RETURN    ${url}
