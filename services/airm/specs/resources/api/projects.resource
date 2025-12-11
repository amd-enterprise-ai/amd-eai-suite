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
    Create api session
    ${endpoint}=            Projects endpoint
    Log    API Request: GET ${endpoint}    DEBUG
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN                  ${response}

Get project
    [Documentation]    Get a specific project by ID
    [Arguments]             ${project_id}           ${expected_status}=any
    Create api session
    ${endpoint}=            Projects endpoint
    Log    API Request: GET ${endpoint}/${project_id}    DEBUG
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}/${project_id}                       expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN                  ${response}

Create project
    [Documentation]    Create a new project
    [Arguments]             ${project_data}         ${expected_status}=any
    Create api session
    ${endpoint}=            Projects endpoint
    Log    API Request: POST ${endpoint} - Body: ${project_data}    DEBUG
    ${response}=            POST On Session         ${API_SESSION}          ${endpoint}             json=${project_data}    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN                  ${response}

Delete project
    [Documentation]    Delete a specific project
    [Arguments]             ${project_id}           ${expected_status}=any
    Create api session
    ${endpoint}=            Projects endpoint
    Log    API Request: DELETE ${endpoint}/${project_id}    DEBUG
    ${response}=            DELETE On Session       ${API_SESSION}          ${endpoint}/${project_id}                       expected_status=${expected_status}
    Log    API Response: ${response.status_code}    DEBUG
    RETURN                  ${response}

Update project
    [Documentation]    Update an existing project
    [Arguments]             ${project_id}           ${project_data}         ${expected_status}=any
    Create api session
    ${endpoint}=            Projects endpoint
    Log    API Request: PUT ${endpoint}/${project_id} - Body: ${project_data}    DEBUG
    ${response}=            PUT On Session          ${API_SESSION}          ${endpoint}/${project_id}                       json=${project_data}    expected_status=${expected_status}
    Log    API Response: ${response.status_code} - Body: ${response.text}    DEBUG
    RETURN                  ${response}

Add users to project
    [Documentation]    Add users to a specific project
    [Arguments]             ${project_id}           ${user_ids}             ${expected_status}=any
    Create api session
    ${endpoint}=            Projects endpoint
    ${user_data}=           Create Dictionary       user_ids=${user_ids}
    Log    API Request: POST ${endpoint}/${project_id}/users - Body: ${user_data}    DEBUG
    ${response}=            POST On Session         ${API_SESSION}          ${endpoint}/${project_id}/users                 json=${user_data}       expected_status=${expected_status}
    Log    API Response: ${response.status_code}    DEBUG
    RETURN                  ${response}

Remove user from project
    [Documentation]    Remove a user from a specific project
    [Arguments]             ${project_id}           ${user_id}              ${expected_status}=any
    Create api session
    ${endpoint}=            Projects endpoint
    Log    API Request: DELETE ${endpoint}/${project_id}/users/${user_id}    DEBUG
    ${response}=            DELETE On Session       ${API_SESSION}          ${endpoint}/${project_id}/users/${user_id}      expected_status=${expected_status}
    Log    API Response: ${response.status_code}    DEBUG
    RETURN                  ${response}
