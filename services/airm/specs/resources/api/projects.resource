# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keywords for interacting with the Projects API endpoints.
...                 Provides low-level keywords for managing projects through the API.
...                 Includes operations for listing, creating, and deleting projects.
Library             RequestsLibrary
Library             Collections
Resource            common.resource


*** Keywords ***
Projects endpoint
    [Documentation]    Returns the full projects endpoint URL
    ${endpoint}=            Catalog endpoint        projects
    RETURN                  ${endpoint}

Get projects
    [Documentation]    Get list of all projects for the user's organization
    [Arguments]             ${expected_status}=any
    Create API Session
    ${endpoint}=            Projects endpoint
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             expected_status=${expected_status}
    RETURN                  ${response}

Get project
    [Documentation]    Get a specific project by ID
    [Arguments]             ${project_id}           ${expected_status}=any
    Create API Session
    ${endpoint}=            Projects endpoint
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}/${project_id}                       expected_status=${expected_status}
    RETURN                  ${response}

Create project
    [Documentation]    Create a new project
    [Arguments]             ${project_data}         ${expected_status}=any
    Create API Session
    ${endpoint}=            Projects endpoint
    ${response}=            POST On Session         ${API_SESSION}          ${endpoint}             json=${project_data}    expected_status=${expected_status}
    RETURN                  ${response}

Delete project
    [Documentation]    Delete a specific project
    [Arguments]             ${project_id}           ${expected_status}=any
    Create API Session
    ${endpoint}=            Projects endpoint
    ${response}=            DELETE On Session       ${API_SESSION}          ${endpoint}/${project_id}                       expected_status=${expected_status}
    RETURN                  ${response}

Add users to project
    [Documentation]    Add users to a specific project
    [Arguments]             ${project_id}           ${user_ids}             ${expected_status}=any
    Create API Session
    ${endpoint}=            Projects endpoint
    ${user_data}=           Create Dictionary       user_ids=${user_ids}
    ${response}=            POST On Session         ${API_SESSION}          ${endpoint}/${project_id}/users                 json=${user_data}       expected_status=${expected_status}
    RETURN                  ${response}
