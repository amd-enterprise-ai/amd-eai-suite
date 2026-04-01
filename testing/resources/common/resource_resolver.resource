# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Resource resolver keywords.
...                 Provides clean syntax for resolving resource IDs, objects, and attributes.
Library             BuiltIn
Library             Collections


*** Keywords ***
The ${resource_type:[a-zA-Z]+}
    [Documentation]    Get resource ID from test variables with validation and clear error messages.
    ...
    ...    This is the REQUIRED pattern for accessing resources created by earlier keywords.
    ...    Always use this instead of directly accessing TEST_* variables.
    ...
    ...    **How it works:**
    ...    - Returns resource ID from TEST_<RESOURCE_TYPE>_ID variable
    ...    - Validates the variable exists (prevents silent failures)
    ...    - Provides clear error message if resource not created yet
    ...    - Supports explicit ID override via id= argument
    ...
    ...    **Common usage (implicit reference):**
    ...    ```robot
    ...    Given project "test-project" exists    # Sets TEST_PROJECT_ID
    ...    Then project should be ready
    ...        ${project_id}=    The project      # Gets TEST_PROJECT_ID
    ...    ```
    ...
    ...    **Explicit reference when needed:**
    ...    ```robot
    ...    Given project "test-1" exists
    ...    And project "test-2" exists
    ...    Then project should be ready
    ...        ${id}=    The project    id=${specific_project_id}
    ...    ```
    ...
    ...    **Supported resource types:**
    ...    workload, project, model, dataset, chart, cluster, secret, storage, workspace, aim
    ...
    ...    **Benefits:**
    ...    - Clear errors: "Project ID required but not provided. Either pass id= argument or ensure project was created..."
    ...    - Type-safe: Won't silently use undefined variables
    ...    - Single point of control for resource resolution
    ...    - Self-documenting: Tests show dependencies clearly
    ...
    ...    **Error handling:**
    ...    - Fails with actionable message if resource not created
    ...    - Suggests using "Given ${resource_type} exists" first
    ...    - Shows exact variable name that should be set
    [Arguments]    ${id}=${None}

    # Construct the TEST variable name (e.g., TEST_WORKLOAD_ID)
    ${var_name}=    Set Variable    TEST_${resource_type.upper()}_ID

    # Get the fallback value from TEST variable (or None if doesn't exist)
    ${fallback}=    Get Variable Value    ${${var_name}}    ${None}

    # Choose provided ID or fallback
    ${resolved_id}=    Set Variable If    $id != $None    ${id}    ${fallback}

    # Validate we have an ID
    Should Not Be Empty    ${resolved_id}
    ...    msg=${resource_type.capitalize()} ID required but not provided. Either pass id= argument or ensure ${resource_type} was created and tracked in ${var_name}

    RETURN    ${resolved_id}

The ${resource_type:[a-zA-Z]+} object
    [Documentation]    Get the full cached resource object from test variables.
    ...
    ...    Returns the dictionary stored in TEST_<RESOURCE_TYPE> variable.
    ...    This is the full object (e.g., API response body) cached by creation keywords.
    ...
    ...    Use this when you need more than just the ID — e.g., project name, namespace, status.
    ...
    ...    **Usage:**
    ...    ```robot
    ...    ${project}=    The project object    # Gets ${TEST_PROJECT} dict
    ...    ${name}=       Get From Dictionary    ${project}    name
    ...    ```
    ...
    ...    **Setting the object (in creation keywords):**
    ...    ```robot
    ...    Set Test Variable    ${TEST_PROJECT}    ${project_dict}
    ...    ```
    [Arguments]    ${resource}=${None}

    ${var_name}=    Set Variable    TEST_${resource_type.upper()}
    ${fallback}=    Get Variable Value    ${${var_name}}    ${None}
    ${resolved}=    Set Variable If    $resource != $None    ${resource}    ${fallback}

    Should Not Be Empty    ${resolved}
    ...    msg=${resource_type.capitalize()} object required but not provided. Either pass object directly or ensure ${resource_type} was created and tracked in ${var_name}

    RETURN    ${resolved}
