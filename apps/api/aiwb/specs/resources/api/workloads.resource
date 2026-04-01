# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIWB workloads endpoints.
...                 Provides API operations for workload lifecycle via AIWB.
...                 Uses namespace-scoped endpoints: /namespaces/{namespace}/workloads/
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource


*** Keywords ***
AIWB Workloads endpoint
    [Documentation]    Return the full AIWB workloads endpoint URL
    ...    Pattern: /namespaces/{namespace}/workloads
    [Arguments]    ${namespace}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=namespaces/${namespace}/workloads
    RETURN    ${endpoint}

Get AIWB workload
    [Documentation]    Retrieve a specific workload by ID via AIWB API
    ...    Uses: GET /namespaces/{namespace}/workloads/{workload_id}
    [Arguments]    ${workload_id}    ${namespace}    ${expected_status}=any    ${params}=${None}
    Create api session    aiwb
    ${endpoint}=    AIWB Workloads endpoint    ${namespace}
    Log    GET ${endpoint}/${workload_id}    DEBUG
    IF    $params is not None
        ${response}=    Safe Get Request    ${endpoint}/${workload_id}    params=${params}    expected_status=${expected_status}
    ELSE
        ${response}=    Safe Get Request    ${endpoint}/${workload_id}    expected_status=${expected_status}
    END
    Log    Get AIWB workload response: status=${response.status_code}    DEBUG
    RETURN    ${response}

Get AIWB workloads
    [Documentation]    List workloads in namespace via AIWB API
    ...    Uses: GET /namespaces/{namespace}/workloads
    ...    Optional filters: workload_type, status_filter
    [Arguments]    ${namespace}    ${workload_type}=${None}    ${status_filter}=${None}    ${expected_status}=any
    Create api session    aiwb
    ${params}=    Create Dictionary

    IF    "${workload_type}" != "${None}"    Set To Dictionary    ${params}    workload_type=${workload_type}
    IF    "${status_filter}" != "${None}"    Set To Dictionary    ${params}    status_filter=${status_filter}

    ${endpoint}=    AIWB Workloads endpoint    ${namespace}
    Log    GET ${endpoint} with params: ${params}    DEBUG
    ${response}=    Safe Get Request    ${endpoint}    params=${params}    expected_status=${expected_status}
    Log    List AIWB workloads response: status=${response.status_code}    DEBUG
    RETURN    ${response}

Delete AIWB workload
    [Documentation]    Delete a specific workload via AIWB API
    ...    Uses: DELETE /namespaces/{namespace}/workloads/{workload_id}
    [Arguments]    ${workload_id}    ${namespace}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    AIWB Workloads endpoint    ${namespace}
    Log    DELETE ${endpoint}/${workload_id}    DEBUG
    ${response}=    Safe Delete Request    ${endpoint}/${workload_id}    expected_status=${expected_status}
    Log    Delete AIWB workload response: status=${response.status_code}    DEBUG
    RETURN    ${response}
