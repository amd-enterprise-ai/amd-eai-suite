# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# (c) Copyright 2024 Advanced Micro Devices, Inc. All rights reserved
*** Settings ***
Documentation    Common utilities for response validation and status checking
Library          Collections
Library          BuiltIn

*** Keywords ***
Wait for resource status
    [Documentation]    Generic keyword to wait for any resource to reach a specific status
    [Arguments]    ${get_keyword}    ${resource_id}    ${expected_status}    ${timeout}=2 min    ${interval}=5 sec
    Log    Waiting for resource ${resource_id} to reach status ${expected_status}    DEBUG
    Wait Until Keyword Succeeds    ${timeout}    ${interval}
    ...    Verify resource has status    ${get_keyword}    ${resource_id}    ${expected_status}

Verify resource has status
    [Documentation]    Helper to verify resource status (used with polling)
    [Arguments]    ${get_keyword}    ${resource_id}    ${expected_status}
    Log    Checking resource ${resource_id} status    TRACE
    ${response}=    Run Keyword    ${get_keyword}    ${resource_id}    expected_status=200
    ${status}=    Get From Dictionary    ${response.json()}    status
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Resource status is ${status}, expected ${expected_status}
    Log    Resource ${resource_id} has status ${status}    DEBUG

Get resource by ID from list
    [Documentation]    Gets a single resource by ID from a list endpoint (workaround for missing GET by ID)
    [Arguments]    ${list_keyword}    ${resource_id}    ${list_key}    ${expected_status}=200
    Log    Looking up resource ${resource_id} from list    DEBUG
    ${list_response}=    Run Keyword    ${list_keyword}
    ${resources_list}=    Get From Dictionary    ${list_response.json()}    ${list_key}

    FOR    ${resource}    IN    @{resources_list}
        ${id}=    Get From Dictionary    ${resource}    id
        IF    "${id}" == "${resource_id}"
            Log    Found resource ${resource_id} in list    DEBUG
            # Create a mock response object to match expected interface
            ${mock_response}=    Evaluate    type('MockResponse', (), {'json': lambda self: ${resource}, 'status_code': ${expected_status}})()
            RETURN    ${mock_response}
        END
    END

    # Handle 404 case
    Log    Resource ${resource_id} not found in list    DEBUG
    ${mock_404}=    Evaluate    type('MockResponse', (), {'json': lambda self: {"error": "Not found"}, 'status_code': 404})()
    RETURN    ${mock_404}

Resource should have project assignments
    [Documentation]    Verifies a resource has the expected number of project assignments
    [Arguments]    ${resource_id}    ${expected_count}    ${get_keyword}    ${assignments_key}=projects
    Log    Verifying project assignments for resource ${resource_id}    DEBUG
    ${response}=    Run Keyword    ${get_keyword}    ${resource_id}    expected_status=200
    ${assignments}=    Get From Dictionary    ${response.json()}    ${assignments_key}
    ${actual_count}=    Get Length    ${assignments}
    Should Be Equal As Integers    ${actual_count}    ${expected_count}
    ...    msg=Expected ${expected_count} project assignments, found ${actual_count}
    Log    Resource ${resource_id} has ${actual_count} project assignments (expected: ${expected_count})    DEBUG

Resource status should be
    [Documentation]    Generic status verification for any resource
    [Arguments]    ${resource}    ${expected_status}
    ${status}=    Get From Dictionary    ${resource}    status
    Log    Verifying resource status: ${status} == ${expected_status}    DEBUG
    Should Be Equal    ${status}    ${expected_status}
    ...    msg=Expected status ${expected_status}, but got ${status}
