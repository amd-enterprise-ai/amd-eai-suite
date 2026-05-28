# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Cross-service integration tests for AIRM and AIWB.
...                 Verifies that AIWB correctly interacts with AIRM-managed
...                 projects and namespaces, including access control enforcement.

Resource            resources/aiwb_common.resource
Resource            resources/aiwb_namespaces.resource
Resource            resources/airm_projects.resource
Resource            resources/airm_keywords.resource

Suite Teardown      Clean Up All Created Projects


*** Test Cases ***
Both services health checks pass
    [Documentation]    Verify both AIRM and AIWB services are healthy independently
    [Tags]    smoke    health    cross-service
    Given AIRM service is running
    And AIWB service is running

AIWB lists namespaces including AIRM-managed project
    [Documentation]    Verify AIWB namespace list includes a project managed by AIRM
    [Tags]    smoke    cross-service    namespaces
    Given a ready project with user access exists
    When AIWB namespaces are listed
    Then AIWB namespace list should contain project namespace

AIWB namespace stats available for AIRM-managed project
    [Documentation]    Verify AIWB can retrieve namespace stats for an AIRM-managed project
    [Tags]    cross-service    namespaces
    Given a ready project with user access exists
    When AIWB namespace stats are requested
    Then AIWB namespace stats response should contain namespace

AIWB denies access to unauthorized namespace
    [Documentation]    Verify AIWB enforces access control on namespace operations
    [Tags]    cross-service    namespaces
    Given a ready project with user access exists
    And a project without user access exists
    When AIWB namespaces are listed
    Then AIWB namespace list should contain project namespace
    And AIWB namespace list should not contain unauthorized namespace
    And AIWB namespace stats should be denied for unauthorized namespace
