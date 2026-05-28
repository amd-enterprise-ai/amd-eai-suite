# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for AIRM cluster management and detail views.
...
...                 These tests verify that admin users can view and manage clusters,
...                 including cluster list with status and allocation info, cluster detail
...                 with nodes and GPU metrics, search filtering, kubeconfig display,
...                 connect wizard, cluster workloads, and cluster edit form.

Resource            resources/common/browser_setup.resource
Resource            resources/clusters.resource

Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
Cluster list displays connected clusters with status and allocation
    [Documentation]    Verify that admin can see connected clusters with status indicators
    ...                and GPU allocation information.
    [Tags]    ui    airm    clusters    smoke

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    Then connected clusters should be listed with status indicators
    And GPU allocation information should be shown per cluster

Cluster detail shows statistics and nodes
    [Documentation]    Verify that opening a cluster detail shows statistics cards,
    ...                a list of nodes, and GPU utilization chart.
    [Tags]    ui    airm    clusters    detail

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    When the user opens a cluster detail view
    Then cluster statistics should be displayed
    And cluster nodes should be listed
    And GPU utilization chart should be shown

Node detail shows GPU device information
    [Documentation]    Verify that navigating to a specific node from the cluster detail
    ...                shows node specs and GPU device metrics.
    [Tags]    ui    airm    clusters    nodes    gpu

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    When the user opens a cluster detail view
    And the user navigates to a specific node
    Then node information should be displayed
    And GPU device metrics should be shown

Admin filters clusters by name
    [Documentation]    Verify that the search filter narrows the cluster list
    ...                to matching clusters only.
    [Tags]    ui    airm    clusters    search

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    When the user searches for a cluster by name
    Then only matching clusters should be shown in the list

Admin views kubeconfig for a cluster
    [Documentation]    Verify that the kubeconfig drawer displays YAML configuration
    ...                content for a cluster.
    [Tags]    ui    airm    clusters    kubeconfig

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    When the user opens a cluster detail view
    And the user opens the kubeconfig view
    Then the kubeconfig YAML content should be displayed

Admin opens the connect cluster wizard
    [Documentation]    Verify that the connect cluster wizard opens with registration
    ...                instructions when the admin clicks the connect button.
    [Tags]    ui    airm    clusters    connect

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    When the user opens the connect cluster wizard
    Then the wizard should display the registration instructions

Admin views workloads for a cluster
    [Documentation]    Verify that the admin can navigate to the cluster workloads page
    ...                and see workload information or empty state.
    [Tags]    ui    airm    clusters    workloads

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    When the user opens a cluster detail view
    And the user navigates to the cluster workloads page
    Then cluster workloads should be listed with status information

Admin opens the edit cluster form
    [Documentation]    Verify that the edit cluster drawer shows form fields
    ...                for workbench URL and kube API URL.
    [Tags]    ui    airm    clusters    edit

    Given an admin user is logged in to AIRM
    And the user is on the clusters page
    When the user opens a cluster detail view
    And the user edits the cluster
    Then the edit cluster drawer should be visible with form fields
