# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API AIMs endpoints.
...                 Provides direct API operation wrappers for the /aims endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Library             BuiltIn
Resource            common.resource


*** Variables ***
@{DEPLOYED_AIMS_LIST}       # List to track all deployed AIMs for cleanup


*** Keywords ***
AIMs endpoint
    [Documentation]    Return the full AIMs endpoint url
    ${endpoint}=            Catalog endpoint        aims
    RETURN                  ${endpoint}

Get AIM
    [Documentation]    Retrieve a specific AIM by ID (does not require project_id)
    ...
    ...    Args:
    ...    aim_id (str): UUID of the AIM to retrieve
    ...
    ...    Return:
    ...    response: API response containing the AIM details
    [Arguments]             ${aim_id}               ${expected_status}=any
    Create api session
    TRY
        ${endpoint}=            AIMs endpoint
        ${response}=            Safe Get Request        ${endpoint}/${aim_id}                           expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to get AIM ${aim_id}: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

List AIMs
    [Documentation]    List all available AIMs (requires project_id as query parameter)
    ...
    ...    Args:
    ...    project_id (str): Required project ID for filtering AIMs
    ...
    ...    Return:
    ...    response: API response containing list of AIMs
    [Arguments]             ${project_id}           ${expected_status}=any
    Create api session
    ${params}=              Create dictionary       project_id=${project_id}
    TRY
        ${endpoint}=            AIMs endpoint
        ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to list AIMs: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

Deploy AIM
    [Documentation]    Deploy an AIM by ID (requires project_id as query parameter)
    ...
    ...    Args:
    ...    aim_id (str): UUID of the AIM to deploy
    ...    deploy_data (dict): Deployment configuration
    ...    project_id (str): Required project ID for deployment
    ...
    ...    Return:
    ...    response: API response containing the workload details
    [Arguments]             ${aim_id}               ${deploy_data}          ${project_id}           ${expected_status}=any
    Create api session
    # Track this AIM for cleanup before attempting deployment
    Append To List          ${DEPLOYED_AIMS_LIST}   ${aim_id}
    ${params}=              Create dictionary       project_id=${project_id}
    TRY
        ${endpoint}=            AIMs endpoint
        ${response}=            Safe Post Request       ${endpoint}/${aim_id}/deploy                    json=${deploy_data}     params=${params}                                expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to deploy AIM ${aim_id}: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END

Undeploy AIM
    [Documentation]    Undeploy an AIM by ID (requires project_id as query parameter)
    ...
    ...    Args:
    ...    aim_id (str): UUID of the AIM to undeploy
    ...    project_id (str): Required project ID where AIM is deployed
    ...
    ...    Return:
    ...    response: API response
    [Arguments]             ${aim_id}               ${project_id}           ${expected_status}=any
    Create api session
    ${params}=              Create dictionary       project_id=${project_id}
    TRY
        ${endpoint}=            AIMs endpoint
        ${response}=            Safe Post Request       ${endpoint}/${aim_id}/undeploy                  params=${params}        expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to undeploy AIM ${aim_id}: ${error}
        Log                     ${error_msg}            ERROR
        FAIL                    ${error_msg}
    END
