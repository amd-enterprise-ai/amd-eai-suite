# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keycloak browser login flow for UI E2E tests.
...                 Handles the three-step login: NextAuth → Keycloak email → password → redirect.
...                 Credentials are extracted from the kubeconfig OIDC configuration.
Library             ../../libraries/UICredentials.py


*** Variables ***
${LOGIN_TIMEOUT}    30s


*** Keywords ***
Log in via Keycloak
    [Documentation]    Performs full browser login via Keycloak using kubeconfig credentials.
    ...                Navigates directly to /api/auth/signin to bypass JS redirect delay,
    ...                then completes Keycloak OAuth flow: username → password → redirect.
    ...                Expects a browser page to already be open.
    [Arguments]    ${base_url}

    ${username}=    Get UI Username
    ${password}=    Get UI Password

    Go To    ${base_url}/api/auth/signin

    # Step 1: NextAuth page - click "Sign in with Keycloak"
    Wait For Elements State    button >> text="Sign in with Keycloak"    visible    timeout=${LOGIN_TIMEOUT}
    Click    button >> text="Sign in with Keycloak"

    # Step 2: Keycloak login form - enter username/email and submit
    Wait For Elements State    css=#username    visible    timeout=${LOGIN_TIMEOUT}
    Fill Text    css=#username    ${username}
    Click    css=#kc-login

    # Step 3: Enter password and submit
    Wait For Elements State    css=#password    visible    timeout=${LOGIN_TIMEOUT}
    Fill Text    css=#password    ${password}
    Click    css=#kc-login

    # Wait for redirect back to the app (main content loads)
    Wait For Elements State    css=main    visible    timeout=${LOGIN_TIMEOUT}
    Log    Successfully logged in as ${username}    INFO
