# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Shared UI session keywords for login and navigation.
...                 These cross-cutting concerns are used by all feature resources.
Resource            login.resource
Resource            navigation.resource
Resource            ui_endpoint.resource


*** Keywords ***
An admin user is logged in to AIRM
    [Documentation]    BDD alias for admin login. Use in Given steps for natural language flow.
    Admin user is logged in

Admin user is logged in
    [Documentation]    Logs in to AIRM via Keycloak as admin and sets the base URL for navigation.
    ...                Expects a browser to already be open (via Test Setup).

    ${url}=    AIRM UI endpoint
    VAR    ${UI_BASE_URL}    ${url}    scope=TEST
    Log in via Keycloak    ${url}

Team member user is logged in
    [Documentation]    Logs in to AIRM via Keycloak as team member and sets the base URL.
    ...                Team member has restricted role-based access.
    ...                Expects a browser to already be open (via Test Setup).

    ${url}=    AIRM UI endpoint
    VAR    ${UI_BASE_URL}    ${url}    scope=TEST
    Log in as team member via Keycloak    ${url}
