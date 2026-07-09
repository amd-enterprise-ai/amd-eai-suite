# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Cross-service integration tests for AIRM and AIWB.
...                 Verifies that AIWB correctly interacts with AIRM-managed
...                 projects, including access control enforcement.

Resource            resources/aiwb_common.resource
Resource            resources/aiwb_projects.resource
Resource            resources/airm_projects.resource
Resource            resources/airm_keywords.resource

Suite Teardown      Clean Up All Created Projects


*** Test Cases ***
Both services health checks pass
    [Documentation]    Verify both AIRM and AIWB services are healthy independently
    [Tags]    smoke    health    cross-service
    Given AIRM service is running
    And AIWB service is running

AIWB lists projects including AIRM-managed project
    [Documentation]    Verify AIWB project list includes a project managed by AIRM
    [Tags]    smoke    cross-service    projects
    Given a ready project with user access exists
    When AIWB projects are listed
    Then AIWB project list should contain current project

AIWB project workload stats available for AIRM-managed project
    [Documentation]    Verify AIWB can retrieve project workload stats for an AIRM-managed project
    [Tags]    cross-service    projects
    Given a ready project with user access exists
    When AIWB project workload stats are requested
    Then AIWB project workload stats response should contain project

AIWB denies access to unauthorized project
    [Documentation]    Verify AIWB enforces access control on project operations
    [Tags]    cross-service    projects
    Given a ready project with user access exists
    And a project without user access exists
    When AIWB projects are listed
    Then AIWB project list should contain current project
    And AIWB project list should not contain unauthorized project
    And AIWB project workload stats should be denied for unauthorized project
