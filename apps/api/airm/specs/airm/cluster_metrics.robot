# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       E2E test scenarios for cluster-level GPU metrics via the AIRM API.
...                 Covers cluster GPU utilization timeseries and cluster workload metrics.
Resource            ../resources/airm_metrics.resource
Resource            ../resources/airm_clusters.resource
Library             Collections


*** Test Cases ***
# =============================================================================
# Cluster GPU device utilization timeseries
# =============================================================================

Cluster GPU device utilization returns valid timeseries response
    [Documentation]    Verify the cluster GPU device utilization endpoint returns 200
    ...    with a valid timeseries structure containing labels and datasets.
    [Tags]    metrics    clusters    smoke

    Given a cluster exists in system

    When cluster GPU device utilization is requested

    Then response should have valid timeseries structure

# =============================================================================
# Cluster workloads metrics (admin-only)
# =============================================================================

Cluster workloads metrics returns valid paginated response
    [Documentation]    Verify the cluster workloads metrics endpoint returns 200
    ...    with a paginated response containing workload data and total count.
    ...    Note: This endpoint requires platform administrator access.
    [Tags]    metrics    clusters    workloads    admin

    Given a cluster exists in system

    When cluster workloads metrics are requested

    Then response should have valid workloads with metrics structure
