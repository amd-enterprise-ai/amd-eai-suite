# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Quota management within Projects.
...                 Verifies quota allocation, updates, and validation.
...                 Note: Quotas are managed as part of projects and don't have standalone endpoints.
...
...                 EXCEPTION: This suite uses Test Teardown instead of Suite Teardown
...                 to ensure quota resources are released after each test. This balances
...                 test isolation with performance, preventing quota accumulation issues.
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            ../resources/api/common.resource
Library             Collections
Suite Setup         Verify Cluster Has Available Resources    min_cpu_cores=4    min_memory_gb=4    min_storage_gb=4
Test Setup          Initialize Project Tracking
Test Teardown       Clean Up All Created Projects
Suite Teardown      Clean Up All Created Projects


*** Test Cases ***
Create project with minimum quota
    [Documentation]    Verify that a project can be created with minimum quota allocation
    ...    Note: Project creation is asynchronous, test waits for full provisioning
    [Tags]    quotas    create    minimum

    Given a cluster exists in system
    And minimum quota data is prepared
    And valid project data with quota is prepared
    When create project request is sent
    Then response status should be 200
    And project quota should match minimum values

Create project with custom quota
    [Documentation]    Verify that a project can be created with custom quota allocation
    ...    Note: Project creation is asynchronous, test waits for full provisioning
    [Tags]    quotas    create    custom

    Given a cluster exists in system
    And custom quota data is prepared
    And valid project data with quota is prepared
    When create project request is sent
    Then response status should be 200
    And project quota should match custom values

Increase project quota
    [Documentation]    Verify that project quota can be increased via PUT /projects/{id}
    [Tags]    quotas    update    increase

    Given a cluster exists in system
    And a project exists with minimum quota
    And increased quota data is prepared
    When update project request is sent
    Then response status should be 200
    And project quota in database should match increased values

Decrease project quota
    [Documentation]    Verify that project quota can be decreased via PUT /projects/{id}
    [Tags]    quotas    update    decrease

    Given a cluster exists in system
    And a project exists with custom quota
    And decreased quota data is prepared
    When update project request is sent
    Then response status should be 200
    And project quota in database should match decreased values

Update quota CPU allocation
    [Documentation]    Verify that CPU quota allocation can be updated independently
    [Tags]    quotas    update    cpu

    Given a cluster exists in system
    And a project exists
    And updated CPU quota is prepared
    When update project request is sent
    Then response status should be 200
    And project CPU quota in database should match updated value

Update quota memory allocation
    [Documentation]    Verify that memory quota allocation can be updated independently
    [Tags]    quotas    update    memory

    Given a cluster exists in system
    And a project exists
    And updated memory quota is prepared
    When update project request is sent
    Then response status should be 200
    And project memory quota in database should match updated value

Update quota GPU allocation
    [Documentation]    Verify that GPU quota allocation can be updated independently
    [Tags]    quotas    update    gpu

    Given a cluster exists in system
    And a project exists
    And updated GPU quota is prepared
    When update project request is sent
    Then response status should be 200
    And project GPU quota in database should match updated value

Verify quota status after creation
    [Documentation]    Verify that quota status is properly set after project creation
    ...    Note: Project creation is asynchronous, test waits for full provisioning
    [Tags]    quotas    status    smoke

    Given a cluster exists in system
    And valid project data is prepared
    When create project request is sent
    Then response status should be 200
    And quota should have valid status
    And response should contain key "quota"
    And quota status should be one of "active, pending, provisioning, Ready"
