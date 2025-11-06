# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level common API testing utilities.
...                 Provides base functionality for constructing API URLs and other
...                 shared utilities used by specific API endpoint resources.
...                 This is the lowest layer of the testing hierarchy.
Resource            ../catalog_keywords.resource
Resource            ../test_data.resource
Resource            ../authorization.resource
Resource            ../deployment.resource
Library             RequestsLibrary


*** Variables ***
${API_SESSION}          ${None}
${CATALOG_ENDPOINT}     ${None}


*** Keywords ***
Catalog endpoint
    [Documentation]    Returns the full endpoint url for a catalog api endpoint with caching
    [Arguments]             ${endpoint}=${None}
    # Use cached endpoint if available
    IF    $CATALOG_ENDPOINT is not None
        Log                     Using cached catalog endpoint ${CATALOG_ENDPOINT}
        ${base_url}=            Set Variable            ${CATALOG_ENDPOINT}
    ELSE
        Log                     Start: Resolving catalog endpoint
        ${base_url}=            Service endpoint        airm                    airm-api
        VAR    ${CATALOG_ENDPOINT}    ${base_url}    scope=global
        Log                     End: Using resolved catalog endpoint ${base_url}
    END

    IF    $endpoint is not None
        RETURN                  ${base_url}/v1/${endpoint}
    END
    RETURN                  ${base_url}/v1

Create api session
    [Documentation]    Creates a session to the API if it doesn't exist
    IF    $API_SESSION is not None    RETURN
    ${base_url}=            Catalog endpoint
    ${access_token} =       Authorization token
    &{headers} =            Create dictionary       Content-Type=application/json                   Authorization=Bearer ${access_token}
    Create session          catalog_api             ${base_url}             headers=${headers}      verify=true
    Set suite variable      ${API_SESSION}          catalog_api

Log Current User Groups
    [Documentation]    Queries the /v1/user_groups endpoint and logs the response.
    Create API Session
    ${endpoint}=            Set Variable            /v1/user_groups # Assuming base URL is handled by Create API Session
    TRY
        ${response}=            Get On Session          ${API_SESSION}          ${endpoint}             expected_status=any
        Log To Console          \nUser Groups Response (Status: ${response.status_code}):\n${response.text}\n
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to get user groups: ${error}             ERROR
        Log To Console          ERROR: Failed to get user groups: ${error}
    END
