# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation    Generic resource tracking and cleanup utilities.
...    Provides lazy-initializing tracking keywords and universal cleanup.
...    App-specific cleanup files import this and add domain-specific cleanup logic.
Library          Collections
Library          String


*** Keywords ***
Track ${resource_type} For Cleanup
    [Documentation]    Track a resource ID for cleanup with auto-initialization.
    ...    Creates the tracking list if it doesn't exist yet.
    ...    Also registers the resource type for universal cleanup.
    [Arguments]    ${resource_id}
    ${variable_name}=    Set Variable    CREATED_${resource_type.upper().replace(' ', '_')}_IDS
    ${tracking_list}=    Get Variable Value    ${${variable_name}}    ${None}
    IF    $tracking_list is None
        @{tracking_list}=    Create List
        Set Suite Variable    ${${variable_name}}    ${tracking_list}
    END
    Append To List    ${${variable_name}}    ${resource_id}
    # Register type in master list for universal cleanup
    ${types}=    Get Variable Value    ${TRACKED_RESOURCE_TYPES}    ${None}
    IF    $types is None
        @{types}=    Create List
        Set Suite Variable    ${TRACKED_RESOURCE_TYPES}    ${types}
    END
    ${already}=    Evaluate    "${resource_type.upper().replace(' ', '_')}" in $types
    IF    not ${already}
        Append To List    ${TRACKED_RESOURCE_TYPES}    ${resource_type.upper().replace(' ', '_')}
    END
    Log    Tracking ${resource_type} ${resource_id} for cleanup    DEBUG

Clean Up All Tracked Resources
    [Documentation]    Clean up all resources tracked during the test suite.
    ...    Iterates all tracked resource types and calls generic cleanup for each.
    ...    Tolerates failures from cascading deletes (e.g. project deletion already removed workloads).
    ${types}=    Get Variable Value    ${TRACKED_RESOURCE_TYPES}    ${None}
    IF    $types is None    RETURN
    ${count}=    Get Length    ${types}
    IF    ${count} == 0    RETURN    END
    FOR    ${type}    IN    @{types}
        TRY
            Generic Clean Up All Created ${type}
        EXCEPT    AS    ${error}
            Log    Cleanup for ${type} failed (may be expected from cascading deletes): ${error}    WARN
        END
    END

Generic Clean Up All Created ${resource_type}
    [Documentation]    Deletes all resources of given type (e.g., Projects, Secrets)
    ${clean_type}=    Set Variable    ${resource_type.replace(' Via API', '')}
    ${variable_name}=    Set Variable    CREATED_${clean_type.upper()}_IDS
    ${tracking_list}=    Get Variable Value    ${${variable_name}}    ${None}
    IF    $tracking_list is None    RETURN
    ${count}=    Get Length    ${tracking_list}
    IF    ${count} == 0    RETURN    END
    Log    Cleaning up ${count} ${clean_type}(s)    INFO

    ${delete_keyword}=    Set Variable    Delete ${clean_type.lower()}

    FOR    ${resource_id}    IN    @{tracking_list}
        TRY
            Log    Deleting ${clean_type} ${resource_id}    DEBUG
            Run Keyword    ${delete_keyword}    ${resource_id}    expected_status=any
        EXCEPT    AS    ${error}
            Log    Failed to delete ${clean_type} ${resource_id}: ${error}    WARN
        END
    END

    @{empty_list}=    Create List
    Set Suite Variable    ${${variable_name}}    ${empty_list}
    Log    ${clean_type} cleanup complete    INFO

Generic Clean Up All Created ${resource_type} Via API
    [Documentation]    Alternative pattern with "Via API" suffix (e.g., Workloads Via API)
    Generic Clean Up All Created ${resource_type}
