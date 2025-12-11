# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for workload submission via kubectl.
...                 Phase 1: Basic workload lifecycle testing.
...                 Verifies workload status transitions (PENDING → RUNNING → COMPLETE/FAILED/TERMINATED).
...                 Uses kubectl/helm for workload submission to test the full pipeline.
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
Submit simple workload and verify completion
    [Documentation]    Verify that a simple workload completes successfully
    ...    Tests project provisioning, K8s resource creation, and status transitions
    [Tags]    workload    lifecycle    kubectl    skip

    # Project Setup and Provisioning
    Given a ready project with user access exists

    # Workload Preparation
    And a simple test workload is prepared

    # Workload Submission
    When test workload is submitted via helm

    # PRIMARY VERIFICATION: Kubernetes Resources
    Then Job should exist in project namespace
    And airm_workloads.Pod should exist for Job
    And Pod should transition to "Running"
    And airm_workloads.Job should complete successfully

    # SECONDARY VERIFICATION: AIRM Auto-Discovery (informational)
    And workload SHOULD be discovered by AIRM

Submit workload that fails
    [Documentation]    Verify that a workload failure is properly detected
    ...    Tests project provisioning and workload failure detection
    [Tags]    workload    lifecycle    failure    kubectl    skip

    # Project Setup and Provisioning
    Given a ready project with user access exists

    # Workload Preparation
    And a failing workload is prepared

    # Workload Submission
    When test workload is submitted via helm

    # PRIMARY VERIFICATION: Kubernetes Resources
    Then Job should exist in project namespace
    And airm_workloads.Pod should exist for Job
    And airm_workloads.Job should fail

    # SECONDARY VERIFICATION: AIRM Auto-Discovery (informational)
    And workload SHOULD be discovered by AIRM

Submit long-running workload and terminate it
    [Documentation]    Verify that workload termination works correctly
    ...    Tests Deployment creation and termination
    [Tags]    workload    lifecycle    termination    kubectl    skip

    # Project Setup and Provisioning
    Given a ready project with user access exists

    # Workload Preparation
    And a long-running workload is prepared

    # Workload Submission
    When test workload is submitted via helm

    # PRIMARY VERIFICATION: Kubernetes Resources
    Then Deployment should exist in project namespace
    And Pod should exist for Deployment
    And Deployment Pod should transition to "Running"

    # Termination Test
    When workload is terminated

    # SECONDARY VERIFICATION: AIRM Auto-Discovery (informational)
    And workload SHOULD be discovered by AIRM

Delete workload and verify cleanup
    [Documentation]    Verify that workload deletion works correctly
    ...    Tests K8s resource creation and cleanup via helm uninstall
    [Tags]    workload    lifecycle    deletion    kubectl    skip

    # Project Setup and Provisioning
    Given a ready project with user access exists

    # Workload Preparation
    And a simple test workload is prepared

    # Workload Submission
    When test workload is submitted via helm

    # PRIMARY VERIFICATION: Kubernetes Resources
    Then Job should exist in project namespace

    # Deletion Test
    When workload is deleted via kubectl

    # SECONDARY VERIFICATION: AIRM Auto-Discovery (informational)
    And workload SHOULD be discovered by AIRM
