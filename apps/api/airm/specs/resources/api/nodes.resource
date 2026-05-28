# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIRM API cluster node endpoints.
...                 Provides direct API operation wrappers for the /clusters/{id}/nodes endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource


*** Keywords ***
Cluster nodes endpoint
    [Documentation]    Return the full cluster nodes endpoint URL.
    ...                Builds /clusters/{cluster_id}/nodes or /clusters/{cluster_id}/nodes/{node_id}.
    [Arguments]    ${cluster_id}    ${node_id}=${None}

    ${base_endpoint}=    Service API Endpoint    airm    endpoint=clusters
    IF    $node_id is not None
        RETURN    ${base_endpoint}/${cluster_id}/nodes/${node_id}
    ELSE
        RETURN    ${base_endpoint}/${cluster_id}/nodes
    END

Node metrics endpoint
    [Documentation]    Return the full node metrics endpoint URL for a specific metric path.
    ...                Example paths: gpu-utilization/core-utilization, power-usage, temperature/junction
    [Arguments]    ${cluster_id}    ${node_id}    ${metric_path}

    ${node_endpoint}=    Cluster nodes endpoint    ${cluster_id}    ${node_id}
    RETURN    ${node_endpoint}/metrics/${metric_path}

Get cluster nodes
    [Documentation]    List all nodes in a cluster.
    [Arguments]    ${cluster_id}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Cluster nodes endpoint    ${cluster_id}
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    RETURN    ${response}

Get cluster node
    [Documentation]    Get a single node by ID.
    [Arguments]    ${cluster_id}    ${node_id}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Cluster nodes endpoint    ${cluster_id}    ${node_id}
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    RETURN    ${response}

Get node GPU devices
    [Documentation]    Get GPU device snapshot metrics for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Cluster nodes endpoint    ${cluster_id}    ${node_id}
    ${response}=    Safe Get Request    ${endpoint}/gpu-devices    expected_status=${expected_status}
    RETURN    ${response}

Get node GPU utilization
    [Documentation]    Get GPU core utilization timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    gpu-utilization/core-utilization
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node GPU memory utilization
    [Documentation]    Get GPU memory (VRAM) utilization timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    gpu-utilization/memory-utilization
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node GPU clock speed
    [Documentation]    Get GPU clock speed timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    gpu-utilization/clock-speed
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node power usage
    [Documentation]    Get GPU power usage timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    power-usage
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node junction temperature
    [Documentation]    Get GPU junction temperature timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    temperature/junction
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node memory temperature
    [Documentation]    Get GPU memory temperature timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    temperature/memory
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node PCIe bandwidth
    [Documentation]    Get PCIe bandwidth timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    pcie/bandwidth
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node PCIe efficiency
    [Documentation]    Get PCIe efficiency timeseries for a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${start}    ${end}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Node metrics endpoint    ${cluster_id}    ${node_id}    pcie/efficiency
    ${params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

Get node workloads metrics
    [Documentation]    Get workloads with GPU metrics running on a node.
    [Arguments]    ${cluster_id}    ${node_id}    ${expected_status}=any

    Create api session    airm
    ${endpoint}=    Cluster nodes endpoint    ${cluster_id}    ${node_id}
    ${response}=    Safe Get Request    ${endpoint}/workloads/metrics    expected_status=${expected_status}
    RETURN    ${response}
