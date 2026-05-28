# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIRM API metrics endpoints.
...                 Provides direct API operation wrappers for metrics endpoints across
...                 organization, cluster, project, and workload scopes.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource


*** Keywords ***
# =============================================================================
# Cluster-level metrics
# =============================================================================

Get cluster GPU device utilization
    [Documentation]    Get cluster-wide GPU device utilization timeseries.
    [Arguments]    ${cluster_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=clusters/${cluster_id}/metrics/gpu_device_utilization
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get cluster workloads metrics
    [Documentation]    Get paginated workload metrics for a cluster.
    ...    Requires platform administrator access.
    [Arguments]    ${cluster_id}    ${expected_status}=any    ${page}=1    ${page_size}=10

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=clusters/${cluster_id}/workloads/metrics
    ${params}=    Create Dictionary    page=${page}    pageSize=${page_size}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

# =============================================================================
# Project-level metrics
# =============================================================================

Get project GPU device utilization
    [Documentation]    Get project GPU device utilization timeseries.
    [Arguments]    ${project_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=projects/${project_id}/metrics/gpu_device_utilization
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get project GPU memory utilization
    [Documentation]    Get project GPU memory utilization timeseries.
    [Arguments]    ${project_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=projects/${project_id}/metrics/gpu_memory_utilization
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get project workloads metrics
    [Documentation]    Get paginated workload metrics for a project.
    [Arguments]    ${project_id}    ${expected_status}=any    ${page}=1    ${page_size}=10

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=projects/${project_id}/workloads/metrics
    ${params}=    Create Dictionary    page=${page}    pageSize=${page_size}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get project average wait time
    [Documentation]    Get average workload wait time for a project.
    [Arguments]    ${project_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=projects/${project_id}/metrics/average_wait_time
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get project average GPU idle time
    [Documentation]    Get average GPU idle time for a project.
    [Arguments]    ${project_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=projects/${project_id}/metrics/average_gpu_idle_time
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

# =============================================================================
# Workload-level metrics
# =============================================================================

Get workload VRAM utilization
    [Documentation]    Get per-GPU VRAM utilization timeseries for a workload.
    [Arguments]    ${workload_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=workloads/${workload_id}/metrics/gpu-devices/vram-utilization
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get workload GPU utilization
    [Documentation]    Get per-GPU GPU core activity timeseries for a workload.
    [Arguments]    ${workload_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=workloads/${workload_id}/metrics/gpu-devices/gpu-utilization
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get workload power usage
    [Documentation]    Get per-GPU power usage timeseries for a workload.
    [Arguments]    ${workload_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=workloads/${workload_id}/metrics/gpu-devices/power-usage
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get workload metrics details
    [Documentation]    Get workload information card details (static info, timeline, resources).
    [Arguments]    ${workload_id}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Service API Endpoint    airm    endpoint=workloads/${workload_id}/metrics
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    RETURN    ${response}
