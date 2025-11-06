# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Library     DateTime
Library     ../libraries/KeycloakAuth.py
Resource    deployment.resource


*** Variables ***
${AUTH_TOKEN}           ${None}
${TOKEN_TIMESTAMP}      ${None}
${TOKEN_TTL}            3600    # Token time-to-live in seconds (1 hour)


*** Keywords ***
Authorization token
    [Documentation]    Ensures that the token is available with caching.
    # Check if KEYCLOAK_TOKEN environment variable is set to avoid unnecessary Keycloak connection
    ${env_token}=           Get Environment Variable                        KEYCLOAK_TOKEN          default=${EMPTY}
    IF    '${env_token}' != '${EMPTY}'
        Log                     Using KEYCLOAK_TOKEN from environment variable, skipping Keycloak connection
        RETURN                  ${env_token}
    ELSE
        Log                     No KEYCLOAK_TOKEN found, establishing connection to Keycloak
        # Use the KeycloakAuth library to get the token using ConfigMap URL
        ${token} =              Get Authorization Token
    END
    RETURN                  ${token}

# Legacy token fetching using silodev (kept for reference)

Authorization token silodev
    [Documentation]    Ensures that the token is available with caching using silodev.
    ${current_time} =       Get Current Date

    # Check if we have a valid cached token
    IF    $AUTH_TOKEN is not None and $TOKEN_TIMESTAMP is not None
        ${time_diff} =          Subtract Date From Date                         ${current_time}         ${TOKEN_TIMESTAMP}
        # If token is still valid (less than TOKEN_TTL seconds old), return it
        IF    ${time_diff} < ${TOKEN_TTL}
            Log                     Using cached auth token
            RETURN                  ${AUTH_TOKEN}
        END
    END

    # Token doesn't exist or is expired, get a new one
    ${result} =             Run process             silodev                 auth                    token
    IF    ${result.rc} != 0
        Fail                    Failed to get auth token: stderr: ${result.stderr}, stdout: ${result.stdout}
    END

    # Cache the token and timestamp
    VAR    ${AUTH_TOKEN}    ${result.stdout}    scope=global
    VAR    ${TOKEN_TIMESTAMP}    ${current_time}    scope=global
    Log                     Using new auth token
    RETURN                  ${result.stdout}
