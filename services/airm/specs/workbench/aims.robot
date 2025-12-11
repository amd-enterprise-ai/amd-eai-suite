# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for AIRM API AIMs endpoints.
...                 Verifies AIM deployment, listing, undeployment and management operations.
...                 These tests cover the core functionality of the AIMs API including:
...                 - Listing available AIMs
...                 - Deploying AIMs with external access
...                 - Viewing AIM deployment status
...                 - Undeploying AIMs
...                 - Viewing AIM workload analytics
Resource            ../resources/catalog_aims.resource
Resource            ../resources/catalog_keywords.resource
Resource            ../resources/airm_projects.resource
Test Teardown       Cleanup AIM After Test


*** Test Cases ***
List available AIMs
    [Documentation]    Verify that users can see a list of available AIMs with proper structure
    [Tags]                  aims                    list                    smoke

    Given Project exists in system
    When List AIMs request is sent
    Then response status should be 200
    And Response should contain AIM list
    And Response should contain at least 1 AIMs
    And AIMs in list should have required fields

Get specific AIM by ID
    [Documentation]    Verify that a specific AIM can be retrieved by its ID
    [Tags]                  aims                    get

    Given An AIM exists in system
    When Get AIM request is sent
    Then response status should be 200
    And Response should contain AIM details

Deploy AIM creates workload
    [Documentation]    Verify that deploying an AIM creates a workload and returns workload ID
    ...    Tests that the deployment request is accepted and a workload is created in the database
    [Tags]                  aims                    deploy                  smoke                   gpu

    Given An AIM exists in system
    And Project exists in system
    And Valid AIM deploy data is prepared
    When Deploy AIM request is sent
    Then response status should be 202
    And Response should contain workload ID
    And AIM workload should exist in database

Deployed AIM starts running
    [Documentation]    Verify that a deployed AIM workload reaches Running status
    [Tags]                  aims                    deploy                  status                  gpu

    Given AIM is deployed
    Then Deployed AIM reaches Running state

Deployed AIM is accessible externally
    [Documentation]    Verify that a running AIM workload has external endpoint and is accessible
    ...    Tests that:
    ...    - Workload has external_host
    ...    - External endpoint responds (currently without authentication enforcement)
    ...    - Endpoint follows standard LLM API format (/v1/models)
    ...
    ...    NOTE: Authentication is not currently enforced on external AIM endpoints.
    ...    Unauthenticated requests succeed. This test verifies endpoint accessibility.
    ...    Once authentication is enforced, update this test to verify auth requirements.
    [Tags]                  aims                    deploy                  external                gpu

    Given AIM is deployed and running
    Then AIM workload should be accessible externally
    And External endpoint should return available models

List AIMs shows deployed AIM with correct fields
    [Documentation]    Verify that listing AIMs shows deployed AIM with complete information
    ...    Tests that deployed AIMs include AIM details, workload deployment info, and resource metrics in the list view
    [Tags]                  aims                    list                    deployment-status       gpu

    Given AIM is deployed and running
    When List AIMs request is sent
    Then response status should be 200
    And Response should contain AIM list
    And AIM should have active workload deployment
    And AIM list endpoint should include workload details

Undeploy deployed AIM
    [Documentation]    Verify that a deployed AIM can be undeployed
    ...    Tests that the AIM workload is removed from database AND Kubernetes
    [Tags]                  aims                    undeploy                kubectl                 gpu

    Given AIM is deployed
    And AIM deployment should exist in kubernetes
    When Undeploy AIM request is sent
    Then response status should be 204
    And Deployed workload should be removed
    And AIM deployment should not exist in kubernetes
    And AIM should not have active workload deployment

View deployed AIM workload logs
    [Documentation]    Verify that users can view logs for a running AIM workload
    ...    Tests that logs have proper structure with timestamp, level, and message
    [Tags]                  aims                    workload                logs                    gpu

    Given AIM is deployed and running
    When logs are requested from AIM workload
    Then response status should be 200
    And Response should contain log entries

View deployed AIM workload details
    [Documentation]    Verify that users can view detailed information about a running AIM workload
    ...    Tests that workload details include status, output, allocated resources (GPU count, VRAM), and AIM-specific fields
    [Tags]                  aims                    workload                details                 gpu

    Given AIM is deployed and running
    When workload details are requested
    Then response status should be 200
    And AIM workload detail endpoint should be complete
