# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level cluster testing keywords for AIRM.
...                 Provides business-logic level keywords for working with clusters in tests.
Resource            api/clusters.resource
Resource            resources/api/common.resource
Library             Collections


*** Keywords ***
A cluster exists in system
    [Documentation]    Ensures a cluster exists and sets its ID as a test variable
    ...    Selects the first healthy cluster with GPUs, or falls back to first cluster if none found
    ${response}=    Get clusters    expected_status=200
    ${clusters_data}=    Set Variable    ${response.json()}
    ${clusters}=    Set variable    ${clusters_data['data']}

    ${cluster_count}=    Get Length    ${clusters}
    Should Be True    ${cluster_count} > 0    msg=No clusters found in system. At least one cluster is required.

    # Find first healthy cluster with GPUs
    VAR    ${test_cluster}    ${None}
    FOR    ${c}    IN    @{clusters}
        IF    '${c['status']}' == 'healthy' and ${c['available_resources']['gpu_count']} > 0
            ${test_cluster}=    Set variable    ${c}
            BREAK
        END
    END

    # Fallback to first cluster if no healthy cluster found
    IF    ${test_cluster} is ${None}
        ${test_cluster}=    Set variable    ${clusters[0]}
        Log    No healthy cluster with GPUs found, using first available cluster    WARN
    END

    Set Test Variable    ${TEST_CLUSTER_ID}    ${test_cluster['id']}
    Set Test Variable    ${TEST_CLUSTER_NAME}    ${test_cluster['name']}
    Log    Using cluster: ${TEST_CLUSTER_NAME} (ID: ${TEST_CLUSTER_ID})

Get cluster GPU capacity
    [Documentation]    Returns TOTAL PHYSICAL GPU CAPACITY from first healthy cluster with GPUs.
    ...    This is the total number of GPUs physically available in the cluster hardware.
    ...
    ...    IMPORTANT: This does NOT account for quotas or workload usage - it's pure hardware capacity.
    ...
    ...    Example: If cluster has 16 physical GPUs, this returns 16 regardless of:
    ...    - How many GPUs are allocated to project quotas (could be 0-16)
    ...    - How many GPUs are currently in use by running workloads (could be 0-16)
    ${response}=    Get clusters    expected_status=200
    ${response_json}=    Set variable    ${response.json()}
    ${clusters}=    Set variable    ${response_json['data']}

    # Find first healthy cluster with GPUs
    VAR    ${cluster}    ${None}
    FOR    ${c}    IN    @{clusters}
        IF    '${c['status']}' == 'healthy' and ${c['available_resources']['gpu_count']} > 0
            ${cluster}=    Set variable    ${c}
            BREAK
        END
    END

    # Fallback to first cluster if no healthy cluster found
    IF    ${cluster} is ${None}
        ${cluster}=    Set variable    ${clusters[0]}
    END

    ${gpu_count}=    Set variable    ${cluster['available_resources']['gpu_count']}
    Log    Cluster ${cluster['name']} has ${gpu_count} total GPUs    INFO
    RETURN    ${gpu_count}

Verify Cluster Has Available Resources
    [Documentation]    Pre-flight check to verify cluster has sufficient QUOTA-UNALLOCATED resources.
    ...    Fails fast with clear message if insufficient quota capacity available.
    ...
    ...    IMPORTANT: This checks QUOTA allocation, not physical workload usage!
    ...    "Remaining" means: total capacity - sum of all project quotas
    ...
    ...    Args:
    ...        min_cpu_cores: Minimum CPU cores needed (default: 5 for quota tests)
    ...        min_memory_gb: Minimum memory in GB needed (default: 5 for quota tests)
    ...        min_storage_gb: Minimum storage in GB needed (default: 5 for quota tests)
    ...
    ...    Calculates: remaining_resources = available_resources - allocated_resources
    ...    Where "allocated" = sum of all project quotas assigned via AIRM API (NOT running workloads)
    ...
    ...    This prevents wasting time on quota tests that will fail because all quota slots
    ...    have been assigned to existing projects, even if those GPUs aren't physically in use.
    [Arguments]    ${min_cpu_cores}=5    ${min_memory_gb}=5    ${min_storage_gb}=5

    # Get cluster resources
    ${response}=    Get clusters    expected_status=200
    ${clusters_data}=    Set Variable    ${response.json()}
    ${clusters}=    Set Variable    ${clusters_data['data']}

    Should Not Be Empty    ${clusters}    msg=No clusters found in system

    ${cluster}=    Set Variable    ${clusters[0]}
    ${available}=    Set Variable    ${cluster['available_resources']}
    ${allocated}=    Set Variable    ${cluster['allocated_resources']}

    # Calculate REMAINING (unallocated) resources
    ${remaining_cpu_milli}=    Evaluate    ${available['cpu_milli_cores']} - ${allocated['cpu_milli_cores']}
    ${remaining_memory}=    Evaluate    ${available['memory_bytes']} - ${allocated['memory_bytes']}
    ${remaining_storage}=    Evaluate    ${available['ephemeral_storage_bytes']} - ${allocated['ephemeral_storage_bytes']}
    ${remaining_gpu}=    Evaluate    ${available['gpu_count']} - ${allocated['gpu_count']}

    # Convert to human-readable values
    ${remaining_cpu_cores}=    Evaluate    ${remaining_cpu_milli} / 1000
    ${remaining_memory_gb}=    Evaluate    ${remaining_memory} / 1073741824
    ${remaining_storage_gb}=    Evaluate    ${remaining_storage} / 1073741824

    ${total_cpu_cores}=    Evaluate    ${available['cpu_milli_cores']} / 1000
    ${total_memory_gb}=    Evaluate    ${available['memory_bytes']} / 1073741824
    ${total_storage_gb}=    Evaluate    ${available['ephemeral_storage_bytes']} / 1073741824

    Log    Cluster total capacity: ${total_cpu_cores} CPU cores, ${total_memory_gb} GB memory, ${total_storage_gb} GB storage, ${available['gpu_count']} GPUs    INFO
    Log    Cluster remaining (unallocated): ${remaining_cpu_cores} CPU cores, ${remaining_memory_gb} GB memory, ${remaining_storage_gb} GB storage, ${remaining_gpu} GPUs    INFO

    # Check if sufficient REMAINING resources available
    ${has_cpu}=    Evaluate    ${remaining_cpu_cores} >= ${min_cpu_cores}
    ${has_memory}=    Evaluate    ${remaining_memory_gb} >= ${min_memory_gb}
    ${has_storage}=    Evaluate    ${remaining_storage_gb} >= ${min_storage_gb}

    # Build error message if insufficient
    ${error_parts}=    Create List
    IF    not ${has_cpu}
        Append To List    ${error_parts}    CPU (need ${min_cpu_cores} cores, remaining ${remaining_cpu_cores})
    END
    IF    not ${has_memory}
        Append To List    ${error_parts}    Memory (need ${min_memory_gb} GB, remaining ${remaining_memory_gb})
    END
    IF    not ${has_storage}
        Append To List    ${error_parts}    Storage (need ${min_storage_gb} GB, remaining ${remaining_storage_gb})
    END

    ${error_count}=    Get Length    ${error_parts}
    IF    ${error_count} > 0
        ${error_msg}=    Catenate    SEPARATOR=, ${SPACE}    @{error_parts}
        Fail    Insufficient REMAINING cluster resources for quota tests: ${error_msg}. Clean up old projects or skip quota tests.
    END

    Log    ✓ Cluster has sufficient remaining resources for quota tests    INFO
