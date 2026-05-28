# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       E2E test scenarios for project-level GPU metrics via the AIRM API.
...                 Covers project GPU utilization, workload metrics, wait time, and idle time.
Resource            ../resources/airm_metrics.resource
Resource            ../resources/airm_projects.resource
Library             Collections
Test Teardown       Clean Up All Tracked Resources


*** Test Cases ***
# =============================================================================
# Project GPU device utilization timeseries
# =============================================================================

Project GPU device utilization returns valid timeseries response
    [Documentation]    Verify the project GPU device utilization endpoint returns 200
    ...    with a valid timeseries structure containing labels and datasets.
    [Tags]    metrics    projects    smoke

    Given a ready project with user access exists

    When project GPU device utilization is requested

    Then response should contain GPU device utilization series

# =============================================================================
# Project GPU memory utilization timeseries
# =============================================================================

Project GPU memory utilization returns valid timeseries response
    [Documentation]    Verify the project GPU memory utilization endpoint returns 200
    ...    with a valid timeseries structure containing labels and datasets.
    [Tags]    metrics    projects

    Given a ready project with user access exists

    When project GPU memory utilization is requested

    Then response should contain GPU memory utilization series

# =============================================================================
# Project workloads metrics
# =============================================================================

Project workloads metrics returns valid paginated response
    [Documentation]    Verify the project workloads metrics endpoint returns 200
    ...    with a paginated response containing workload data and total count.
    [Tags]    metrics    projects    workloads

    Given a ready project with user access exists

    When project workloads metrics are requested

    Then response should have valid workloads with metrics structure

# =============================================================================
# Project average wait time
# =============================================================================

Project average wait time returns valid scalar response
    [Documentation]    Verify the project average wait time endpoint returns 200
    ...    with a scalar value and time range.
    [Tags]    metrics    projects

    Given a ready project with user access exists

    When project average wait time is requested

    Then response should have valid scalar with range structure

# =============================================================================
# Project average GPU idle time
# =============================================================================

Project average GPU idle time returns valid scalar response
    [Documentation]    Verify the project average GPU idle time endpoint returns 200
    ...    with a scalar value and time range.
    [Tags]    metrics    projects

    Given a ready project with user access exists

    When project average GPU idle time is requested

    Then response should have valid scalar with range structure
