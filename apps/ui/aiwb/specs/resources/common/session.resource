# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Shared UI session keywords for login and project selection.
...                 These cross-cutting concerns are used by all feature resources.
Resource            login.resource
Resource            navigation.resource
Resource            ui_endpoint.resource


*** Keywords ***
User is logged in
    [Documentation]    Logs in to AIWB via Keycloak and sets the base URL for navigation.
    ...                Expects a browser to already be open (via Test Setup).

    ${url}=    AIWB UI endpoint
    Set Test Variable    ${UI_BASE_URL}    ${url}
    Log in via Keycloak    ${url}

Project "${project_name}" is selected
    [Documentation]    Selects the given project from the header project selector.

    Select project    ${project_name}
