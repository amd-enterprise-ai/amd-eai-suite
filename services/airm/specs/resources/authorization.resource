# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Library     DateTime
Library     Process
Library     ../libraries/KubeconfigAuth.py
Library     OperatingSystem
Resource    deployment.resource
Resource    api/common.resource


*** Variables ***
${AUTH_TOKEN}           ${None}
${TOKEN_TIMESTAMP}      ${None}
${TOKEN_TTL}            3600    # Token time-to-live in seconds (1 hour)


*** Keywords ***
Authorization token
    [Documentation]    Get authorization token with automatic refresh from kubectl config.
    ...                Uses kubectl config to fetch tokens automatically without requiring
    ...                KEYCLOAK_TOKEN environment variable.
    Log                     Fetching token using kubectl config    DEBUG
    ${token} =              Get Authorization Token
    RETURN                  ${token}

Refresh authorization token
    [Documentation]    Force refresh of the authorization token.
    ...                Clears cached token and gets a fresh one from Keycloak.
    ...                Use this after operations that change user permissions (e.g., project membership).
    Clear Token Cache
    ${token} =              Get Authorization Token
    Log                     Token refreshed with updated claims    INFO
    RETURN                  ${token}

Refresh kubectl and API tokens
    [Documentation]    Forces kubectl to refresh OIDC token and refreshes API session
    ...                This is needed after adding users to Keycloak groups because groups
    ...                are embedded in JWT at authentication time and don't update automatically
    ...                Clears kubectl cache, refreshes API token, and recreates API session
    # Clear kubectl OIDC token cache
    ${result} =             Run Process             rm                      -rf                     ~/.kube/cache/oidc-login/    shell=True
    Log                     Cleared kubectl OIDC token cache    INFO
    # Refresh the API authorization token using KubeconfigAuth
    Refresh authorization token
    # Recreate the API session with new token
    Recreate api session
    Log                     Fully refreshed kubectl and API tokens with updated group claims    INFO

# Legacy token fetching using silodev (kept for reference)

Authorization token silodev
    [Documentation]    Ensures that the token is available with caching using silodev.
    ${current_time} =       Get Current Date

    # Check if we have a valid cached token
    IF    $AUTH_TOKEN is not None and $TOKEN_TIMESTAMP is not None
        ${time_diff} =          Subtract Date From Date                         ${current_time}         ${TOKEN_TIMESTAMP}
        # If token is still valid (less than TOKEN_TTL seconds old), return it
        IF    ${time_diff} < ${TOKEN_TTL}
            Log                     Using cached auth token (age: ${time_diff}s)    DEBUG
            RETURN                  ${AUTH_TOKEN}
        END
        Log                     Cached token expired (age: ${time_diff}s), fetching new token    DEBUG
    END

    # Token doesn't exist or is expired, get a new one
    Log                     Fetching new auth token via silodev    DEBUG
    ${result} =             Run process             silodev                 auth                    token
    IF    ${result.rc} != 0
        Fail                    Failed to get auth token: stderr: ${result.stderr}, stdout: ${result.stdout}
    END

    # Cache the token and timestamp
    VAR    ${AUTH_TOKEN}    ${result.stdout}    scope=global
    VAR    ${TOKEN_TIMESTAMP}    ${current_time}    scope=global
    Log                     Auth token fetched and cached    DEBUG
    RETURN                  ${result.stdout}
