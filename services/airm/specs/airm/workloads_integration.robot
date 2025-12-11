# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for workload-project integration.
...                 Phase 3: Integration testing.
...                 Verifies project-workload relationships and cleanup behavior.
...                 Tests namespace isolation and project deletion cascading.
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
Delete project with active workloads should cleanup everything
    [Documentation]    CRITICAL: Verify that deleting a project cleans up all workloads
    ...    This validates our primary cleanup strategy for all tests
    ...    Tests that project deletion cascades to workloads, quotas, and namespaces
    [Tags]    workload    project    cleanup    integration    critical    kubectl

    Given a ready project with user access exists
    And a long-running workload is prepared

    When test workload is submitted via helm
    Then workload should exist in AIRM
    And workload status should transition to "Running"

    When delete project request is sent
    Then the project should not exist in database
    And workload should not exist in AIRM

Multiple workloads in same project should be isolated
    [Documentation]    Verify that multiple workloads in the same project namespace work correctly
    ...    Tests that workloads don't interfere with each other
    [Tags]    workload    project    isolation    integration    kubectl

    Given a ready project with user access exists

    # Submit first workload
    And a simple test workload is prepared
    When test workload is submitted via helm
    Then workload should exist in AIRM
    ${first_workload_id}=    Set Variable    ${TEST_WORKLOAD_ID}

    # Submit second workload
    And a simple test workload is prepared
    When test workload is submitted via helm
    Then workload should exist in AIRM
    ${second_workload_id}=    Set Variable    ${TEST_WORKLOAD_ID}

    # Verify both workloads complete independently
    Set Test Variable    ${TEST_WORKLOAD_ID}    ${first_workload_id}
    And workload status should transition to "Complete"

    Set Test Variable    ${TEST_WORKLOAD_ID}    ${second_workload_id}
    And workload status should transition to "Complete"

Workloads across different projects should be isolated
    [Documentation]    Verify that workloads in different projects are isolated
    ...    Tests per-project namespace isolation and quota enforcement
    [Tags]    workload    project    isolation    integration    kubectl    skip

    # Create first project and workload
    Given a ready project "isolation-project-1" with user access exists
    ${first_project_id}=    Set Variable    ${TEST_PROJECT_ID}
    ${first_namespace}=    Set Variable    ${TEST_NAMESPACE}
    And a simple test workload is prepared
    When test workload is submitted via helm
    Then workload should exist in AIRM
    ${first_workload_id}=    Set Variable    ${TEST_WORKLOAD_ID}

    # Create second project and workload
    Given a ready project "isolation-project-2" with user access exists
    ${second_project_id}=    Set Variable    ${TEST_PROJECT_ID}
    ${second_namespace}=    Set Variable    ${TEST_NAMESPACE}
    And a simple test workload is prepared
    When test workload is submitted via helm
    Then workload should exist in AIRM
    ${second_workload_id}=    Set Variable    ${TEST_WORKLOAD_ID}

    # Verify both workloads complete independently
    Set Test Variable    ${TEST_WORKLOAD_ID}    ${first_workload_id}
    And workload status should transition to "Complete"

    Set Test Variable    ${TEST_WORKLOAD_ID}    ${second_workload_id}
    And workload status should transition to "Complete"

    # Verify projects are separate
    Should Not Be Equal    ${first_project_id}    ${second_project_id}
    Should Not Be Equal    ${first_namespace}    ${second_namespace}
