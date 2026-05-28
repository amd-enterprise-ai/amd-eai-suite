# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIWB API namespace endpoints.
...                 Provides direct API operation wrappers for the /namespaces endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource


*** Keywords ***
AIWB Namespaces Endpoint
    [Documentation]    Return the full namespaces endpoint URL with optional namespace and action.
    [Arguments]    ${namespace}=${None}    ${action}=${None}
    ${base_endpoint}=    Service API Endpoint    aiwb    endpoint=namespaces
    IF    $namespace is not None and $action is not None
        RETURN    ${base_endpoint}/${namespace}/${action}
    ELSE IF    $namespace is not None
        RETURN    ${base_endpoint}/${namespace}
    ELSE
        RETURN    ${base_endpoint}
    END

List AIWB Namespaces
    [Documentation]    List all namespaces via AIWB API.
    ...
    ...    Args:
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing ListResponse[str] with "data" key
    [Arguments]    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    AIWB Namespaces Endpoint

    Log    GET ${endpoint}    DEBUG

    ${response}=    Safe Get Request    ${endpoint}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}

Get AIWB Namespace Stats
    [Documentation]    Get stats for a specific namespace via AIWB API.
    ...
    ...    Args:
    ...    namespace (str): Kubernetes namespace
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing NamespaceStatsCounts
    [Arguments]    ${namespace}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    AIWB Namespaces Endpoint    namespace=${namespace}    action=stats

    Log    GET ${endpoint}    DEBUG

    ${response}=    Safe Get Request    ${endpoint}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}

Get AIWB Namespace Metrics
    [Documentation]    Get paginated workload metrics for a namespace via AIWB API.
    ...
    ...    Args:
    ...    namespace (str): Namespace name
    ...    page (int): Page number (1-indexed)
    ...    page_size (int): Items per page
    ...    workload_type (str): Filter by workload type
    ...    status_filter (str): Filter by status
    ...    sort_by (str): Field to sort by
    ...    sort_order (str): Sort direction (asc/desc)
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing NamespaceWorkloadMetricsListPaginated
    [Arguments]    ${namespace}    ${page}=${None}    ${page_size}=${None}    ${workload_type}=${None}    ${status_filter}=${None}    ${sort_by}=${None}    ${sort_order}=${None}    ${expected_status}=any
    Create api session    aiwb

    ${params}=    Create Dictionary
    IF    $page is not None             Set To Dictionary    ${params}    page=${page}
    IF    $page_size is not None        Set To Dictionary    ${params}    pageSize=${page_size}
    IF    $workload_type is not None    Set To Dictionary    ${params}    workloadType=${workload_type}
    IF    $status_filter is not None    Set To Dictionary    ${params}    statusFilter=${status_filter}
    IF    $sort_by is not None          Set To Dictionary    ${params}    sortBy=${sort_by}
    IF    $sort_order is not None       Set To Dictionary    ${params}    sortOrder=${sort_order}

    ${endpoint}=    AIWB Namespaces Endpoint    namespace=${namespace}    action=metrics

    Log    GET ${endpoint} with params: ${params}    DEBUG

    ${response}=    Safe Get Request    ${endpoint}    params=${params}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}

Get AIWB Namespace Metric
    [Documentation]    Get a specific aggregated metric for a namespace via AIWB API.
    ...
    ...    Args:
    ...    namespace (str): Namespace name
    ...    metric (str): Metric name (e.g., gpu_device_utilization)
    ...    start (str): Start time in ISO 8601 format
    ...    end (str): End time in ISO 8601 format
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing MetricsTimeseries
    [Arguments]    ${namespace}    ${metric}    ${start}    ${end}    ${expected_status}=any
    Create api session    aiwb

    ${params}=    Create Dictionary    start=${start}    end=${end}

    ${endpoint}=    AIWB Namespaces Endpoint    namespace=${namespace}    action=metrics/${metric}

    Log    GET ${endpoint} with params: ${params}    DEBUG

    ${response}=    Safe Get Request    ${endpoint}    params=${params}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}

Get AIWB Chattable Resources
    [Documentation]    Get chattable resources in a namespace via AIWB API.
    ...
    ...    Args:
    ...    namespace (str): Namespace name
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing ChattableResponse
    [Arguments]    ${namespace}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    AIWB Namespaces Endpoint    namespace=${namespace}    action=chattable

    Log    GET ${endpoint}    DEBUG

    ${response}=    Safe Get Request    ${endpoint}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}
