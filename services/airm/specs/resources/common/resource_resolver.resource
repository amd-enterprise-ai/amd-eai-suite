# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Resource ID resolver keywords.
...                 Provides clean syntax for resolving resource IDs with validation.
Library             BuiltIn


*** Keywords ***
The ${resource_type:[a-zA-Z]+}
    [Documentation]    Generic resource ID resolver with validation
    ...    Resolves resource ID from provided argument or TEST variable
    ...    Usage: ${id}= The workload id=${workload_id}
    ...    Usage: ${id}= The project id=${project_id}
    ...    Supports: workload, project, model, dataset, chart, cluster, etc.
    [Arguments]    ${id}=${None}

    # Construct the TEST variable name (e.g., TEST_WORKLOAD_ID)
    ${var_name}=    Set variable    TEST_${resource_type.upper()}_ID

    # Get the fallback value from TEST variable (or None if doesn't exist)
    ${fallback}=    Get variable value    ${${var_name}}    ${None}

    # Choose provided ID or fallback
    ${resolved_id}=    Set variable if    "${id}" != "${None}"    ${id}    ${fallback}

    # Validate we have an ID
    Should not be empty    ${resolved_id}
    ...    msg=${resource_type.capitalize()} ID required but not provided. Either pass id= argument or ensure ${resource_type} was created and tracked in ${var_name}

    RETURN    ${resolved_id}
