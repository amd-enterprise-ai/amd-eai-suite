# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       E2E test scenarios for workload-level GPU metrics via the AIRM API.
...                 Covers per-workload GPU device metrics (VRAM, GPU utilization, power) and
...                 workload information card details.
Resource            ../resources/airm_metrics.resource
Resource            ../resources/airm_workloads.resource
Resource            ../resources/airm_projects.resource
Library             Collections
Test Teardown       Clean Up Workload Metrics Test Resources


*** Keywords ***
Clean Up Workload Metrics Test Resources
    [Documentation]    Clean up all resources created during workload metrics tests
    Clean Up All Created Workloads Via API
    Clean Up All Created Projects


*** Test Cases ***
# =============================================================================
# Workload GPU VRAM utilization
# =============================================================================

Workload VRAM utilization returns valid GPU device response
    [Documentation]    Verify the workload VRAM utilization endpoint returns 200
    ...    with per-GPU device data and time range.
    [Tags]    metrics    workloads    gpu

    Given a workload exists for metrics testing

    When workload VRAM utilization is requested

    Then response should contain workload VRAM utilization data

# =============================================================================
# Workload GPU utilization
# =============================================================================

Workload GPU utilization returns valid GPU device response
    [Documentation]    Verify the workload GPU utilization endpoint returns 200
    ...    with per-GPU device data and time range.
    [Tags]    metrics    workloads    gpu

    Given a workload exists for metrics testing

    When workload GPU utilization is requested

    Then response should contain workload GPU utilization data

# =============================================================================
# Workload GPU power usage
# =============================================================================

Workload power usage returns valid GPU device response
    [Documentation]    Verify the workload power usage endpoint returns 200
    ...    with per-GPU device data and time range.
    [Tags]    metrics    workloads    power

    Given a workload exists for metrics testing

    When workload power usage is requested

    Then response should contain workload power usage data

# =============================================================================
# Workload metrics details (info card)
# =============================================================================

Workload metrics details returns valid info card response
    [Documentation]    Verify the workload metrics endpoint returns 200
    ...    with basic info, cluster/resources, and timeline details.
    [Tags]    metrics    workloads    smoke

    Given a workload exists for metrics testing

    When workload metrics details are requested

    Then response should have valid workload metrics details
