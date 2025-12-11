# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation    Keywords for Keycloak authentication
Library          Process
Library          OperatingSystem

*** Variables ***
${AUTH_TOOL_PATH}    ${EXECDIR}/../../../../tools/auth/get_service_account_token.py

*** Keywords ***
Get Keycloak Token
    [Documentation]    Get an OAuth2 token from Keycloak using current kubectl context
    [Arguments]    ${use_service_account}=${FALSE}    ${client_id}=${EMPTY}    ${client_secret}=${EMPTY}

    IF    ${use_service_account}
        Set Environment Variable    SA_CLIENT_ID    ${client_id}
        Set Environment Variable    SA_CLIENT_SECRET    ${client_secret}
    END

    ${result}=    Run Process    python3    ${AUTH_TOOL_PATH}
    ...    shell=True
    ...    stdout=PIPE
    ...    stderr=PIPE

    IF    ${result.rc} != 0
        Log    Failed to get token: ${result.stderr}    ERROR
        Fail    Could not retrieve Keycloak token
    END

    IF    ${use_service_account}
        Remove Environment Variable    SA_CLIENT_ID
        Remove Environment Variable    SA_CLIENT_SECRET
    END

    [Return]    ${result.stdout.strip()}

Get Service Account Token
    [Documentation]    Get a service account token from Keycloak
    [Arguments]    ${client_id}    ${client_secret}
    ${token}=    Get Keycloak Token    use_service_account=${TRUE}
    ...    client_id=${client_id}
    ...    client_secret=${client_secret}
    [Return]    ${token}

Get User Token
    [Documentation]    Get a user token from Keycloak using current kubectl context
    ${token}=    Get Keycloak Token
    [Return]    ${token}
