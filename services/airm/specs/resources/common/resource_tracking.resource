# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

# (c) Copyright 2024 Advanced Micro Devices, Inc. All rights reserved
*** Settings ***
Documentation    Common utilities for tracking created resources during tests
Library          Collections
Library          String
Resource         ../api/projects.resource

*** Keywords ***
# These handle all variations like:
# - Initialize Project Tracking
# - Initialize Secret ID Tracking
# - Initialize storage ID tracking
# - Clean Up All Created Projects
# - Clean Up All Created Workloads Via API

Initialize ${resource_type} Tracking
    [Documentation]    Resets the tracking list for any resource type (e.g., Project, Workload)
    ${variable_name}=    Set Variable    CREATED_${resource_type.upper().replace(' ', '_')}_IDS
    @{empty_list}=    Create List
    Set Suite Variable    ${${variable_name}}    ${empty_list}
    Log    ${resource_type} tracking initialized (${variable_name})    DEBUG

Initialize ${resource_type} ID Tracking
    [Documentation]    Alternative pattern with "ID" in name (e.g., Secret ID, Workspace ID)
    ${clean_type}=    Set Variable    ${resource_type.replace(' ID', '')}
    Initialize ${clean_type} Tracking

Initialize storage ID tracking
    [Documentation]    Special case for lowercase "storage" (exact match for compatibility)
    Initialize storage Tracking

Generic Clean Up All Created ${resource_type}
    [Documentation]    Deletes all resources of given type (e.g., Projects, Secrets)
    ${clean_type}=    Set Variable    ${resource_type.replace(' Via API', '')}
    ${variable_name}=    Set Variable    CREATED_${clean_type.upper()}_IDS
    ${tracking_list}=    Get Variable Value    ${${variable_name}}    ${EMPTY}

    ${count}=    Get Length    ${tracking_list}
    IF    ${count} == 0
        Log    No ${clean_type}s to clean up    DEBUG
        RETURN
    END
    Log    Cleaning up ${count} ${clean_type}(s)    INFO

    # Determine delete keyword - special case for Workspaces
    ${delete_keyword}=    Set Variable If
    ...    '${clean_type.lower()}' == 'workspace'    Delete workload
    ...    Delete ${clean_type.lower()}

    FOR    ${resource_id}    IN    @{${variable_name}}
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


# Special case for projects with extended cleanup
Clean Up All Project Resources
    [Documentation]    Projects may have cascading deletes and need special handling
    ...    This is the actual implementation for project cleanup
    ${tracking_list}=    Get Variable Value    ${CREATED_PROJECT_IDS}    ${EMPTY}

    ${count}=    Get Length    ${tracking_list}
    IF    ${count} == 0
        Log    No projects to clean up    DEBUG
        RETURN
    END
    Log    Cleaning up ${count} projects and their resources    INFO

    FOR    ${project_id}    IN    @{CREATED_PROJECT_IDS}
        TRY
            Log    Deleting project ${project_id} and associated resources    DEBUG
            Delete project    ${project_id}    expected_status=any
        EXCEPT    AS    ${error}
            Log    Failed to delete project ${project_id}: ${error}    WARN
        END
    END

    @{empty_list}=    Create List
    Set Suite Variable    ${CREATED_PROJECT_IDS}    ${empty_list}
    Log    Project cleanup complete    INFO

# Workload cleanup keywords
Clean Up All Created Workloads
    [Documentation]    Clean up all created workload resources including helm releases
    ${workload_list}=    Get Variable Value    ${CREATED_WORKLOAD_IDS}    ${EMPTY}
    ${release_list}=    Get Variable Value    ${CREATED_HELM_RELEASES}    ${EMPTY}
    ${wcount}=    Get Length    ${workload_list}
    ${rcount}=    Get Length    ${release_list}
    Log    Cleaning up ${rcount} helm releases and ${wcount} AIRM workloads    INFO

    # Clean up helm releases
    FOR    ${release_info}    IN    @{CREATED_HELM_RELEASES}
        ${parts}=    Split String    ${release_info}    :::
        ${release_name}=    Get From List    ${parts}    0
        ${namespace}=    Get From List    ${parts}    1

        TRY
            Log    Deleting helm release ${release_name} in namespace ${namespace}    DEBUG
            Uninstall workload via helm    ${release_name}    ${namespace}
            Log    Deleted helm release ${release_name}    INFO
        EXCEPT    AS    ${error}
            Log    Failed to delete helm release ${release_name}: ${error}    WARN
        END
    END

    # Clean up workloads via API
    Clean Up All Created Workloads Via API

    # Clear the helm release tracking list
    @{empty_releases}=    Create List
    Set Suite Variable    ${CREATED_HELM_RELEASES}    ${empty_releases}
    Log    Workload cleanup complete    INFO

Clean Up All Created Workloads Via API
    [Documentation]    Clean up all created workload resources via API
    ${tracking_list}=    Get Variable Value    ${CREATED_WORKLOAD_IDS}    ${EMPTY}
    ${count}=    Get Length    ${tracking_list}
    Log    Cleaning up ${count} Workload(s) via API    INFO

    FOR    ${workload_id}    IN    @{CREATED_WORKLOAD_IDS}
        TRY
            Delete workload    ${workload_id}    expected_status=any
            Log    Deleted Workload ${workload_id}    INFO
        EXCEPT
            Log    Failed to delete Workload ${workload_id}    WARN
        END
    END

    @{empty_list}=    Create List
    Set Suite Variable    ${CREATED_WORKLOAD_IDS}    ${empty_list}
    Log    Workload cleanup complete    INFO

# These keywords delegate to the actual implementation to avoid pattern conflicts
Clean Up All Created Projects
    [Documentation]    Wrapper that delegates to the actual project cleanup implementation
    ...    This avoids conflict with the generic pattern Clean Up All Created ${resource_type}s
    Clean Up All Project Resources

# The following keywords now use the generic pattern
Clean Up All Created Storage
    [Documentation]    Clean up all created storage resources using generic pattern
    Generic Clean Up All Created Storage

Clean Up All Created Secrets
    [Documentation]    Clean up all created secret resources using generic pattern
    Generic Clean Up All Created Secret

Clean Up All Created Charts
    [Documentation]    Clean up all created chart resources using generic pattern
    Generic Clean Up All Created Chart

Clean Up All Created Datasets
    [Documentation]    Clean up all created dataset resources using generic pattern
    Generic Clean Up All Created Dataset
