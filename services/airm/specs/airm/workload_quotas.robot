# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for workload quota enforcement.
...                 Phase 2: Quota enforcement testing.
...                 Verifies that project quotas properly limit workload submission.
...                 Tests CPU, memory, and resource exhaustion scenarios.
Resource            ../resources/airm_workloads.resource
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            ../resources/api/common.resource
Library             Collections
Test Setup          Run Keywords
...                 Initialize Project Tracking    AND
...                 Initialize Workload Tracking
Test Teardown       Run Keywords
...                 Clean Up All Created Workloads    AND
...                 Clean Up All Created Projects


*** Test Cases ***
Workload within CPU quota should run
    [Documentation]    Verify that a workload within CPU quota runs successfully
    ...    Creates a project with limited CPU quota and submits a workload that fits
    [Tags]    workload    quota    cpu    kubectl    skip

    Given a ready project with CPU quota "500" and user access exists
    And a workload with CPU quota "100m" is prepared

    When test workload is submitted via helm

    Then workload should exist in AIRM
    And workload status should transition to "Running"
    And workload status should transition to "Complete"

Workload exceeding CPU quota should be pending
    [Documentation]    Verify that a workload exceeding CPU quota stays pending
    ...    Creates a project with limited CPU quota and submits a workload that exceeds it
    [Tags]    workload    quota    cpu    negative    kubectl    skip

    Given a ready project with CPU quota "50" and user access exists
    And a workload with CPU quota "200m" is prepared

    When test workload is submitted via helm

    Then workload should exist in AIRM
    And workload should be pending due to quota

Workload within memory quota should run
    [Documentation]    Verify that a workload within memory quota runs successfully
    ...    Creates a project with limited memory quota and submits a workload that fits
    [Tags]    workload    quota    memory    kubectl    skip

    Given a ready project with memory quota "1073741824" and user access exists
    And a workload with memory quota "128Mi" is prepared

    When test workload is submitted via helm

    Then workload should exist in AIRM
    And workload status should transition to "Running"
    And workload status should transition to "Complete"

Workload exceeding memory quota should be pending
    [Documentation]    Verify that a workload exceeding memory quota stays pending
    ...    Creates a project with limited memory quota and submits a workload that exceeds it
    [Tags]    workload    quota    memory    negative    kubectl    skip

    Given a ready project with memory quota "67108864" and user access exists
    And a workload with memory quota "256Mi" is prepared

    When test workload is submitted via helm

    Then workload should exist in AIRM
    And workload should be pending due to quota
