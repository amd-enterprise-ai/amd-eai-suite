# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for namespace management, dashboard stats and metrics.
...                 Verifies namespace listing, stats, metrics, chattable resources,
...                 and access control operations.
Resource            resources/airm_keywords.resource
Resource            resources/airm_projects.resource
Resource            resources/aiwb_namespaces.resource
Library             Collections
Suite Teardown      Clean Up All Tracked Resources


*** Test Cases ***
List accessible namespaces
    [Documentation]    Verify that accessible namespaces are returned for the user.
    [Tags]    namespaces    list    smoke
    Given a ready project with user access exists
    When list namespaces request is sent
    Then response status should be 200
    And response should contain namespace list
    And namespace list should include project namespace

Get namespace stats returns resource counts
    [Documentation]    Verify that namespace stats return resource counts grouped by status.
    [Tags]    namespaces    stats    smoke
    Given a ready project with user access exists
    When namespace stats request is sent
    Then response status should be 200
    And response should contain namespace stats structure

Get namespace metrics returns paginated workload list
    [Documentation]    Verify that namespace metrics return a paginated list of workloads.
    [Tags]    namespaces    metrics    smoke
    Given a ready project with user access exists
    When namespace metrics request is sent
    Then response status should be 200
    And response should contain paginated metrics structure

Get namespace metrics with pagination parameters
    [Documentation]    Verify that namespace metrics accept pagination parameters.
    [Tags]    namespaces    metrics
    Given a ready project with user access exists
    When namespace metrics request is sent    page=1    page_size=5
    Then response status should be 200
    And response should contain paginated metrics structure

Get namespace metrics with workload type filter
    [Documentation]    Verify that namespace metrics accept workload type filter.
    [Tags]    namespaces    metrics
    Given a ready project with user access exists
    When namespace metrics request is sent    workload_type=INFERENCE
    Then response status should be 200
    And response should contain paginated metrics structure

Get namespace GPU utilization metric
    [Documentation]    Verify that GPU utilization metric can be queried for a namespace.
    [Tags]    namespaces    metrics    gpu
    Given a ready project with user access exists
    When namespace metric request is sent for "gpu_device_utilization"
    Then response status should be 200

Get namespace GPU memory utilization metric
    [Documentation]    Verify that GPU memory utilization metric can be queried for a namespace.
    [Tags]    namespaces    metrics    gpu
    Given a ready project with user access exists
    When namespace metric request is sent for "gpu_memory_utilization"
    Then response status should be 200

Namespace metric rejects start after end
    [Documentation]    Verify that the API rejects metrics requests where start is after end.
    [Tags]    namespaces    metrics    smoke    negative
    Given a ready project with user access exists
    When namespace metric request is sent with invalid date range    start_after_end
    Then response status should be 400

Namespace metric rejects start too far in the past
    [Documentation]    Verify that the API rejects metrics requests where start is older than 30 days.
    [Tags]    namespaces    metrics    smoke    negative
    Given a ready project with user access exists
    When namespace metric request is sent with invalid date range    start_too_old
    Then response status should be 400

Namespace metric rejects end in the future
    [Documentation]    Verify that the API rejects metrics requests where end is in the future.
    [Tags]    namespaces    metrics    smoke    negative
    Given a ready project with user access exists
    When namespace metric request is sent with invalid date range    end_in_future
    Then response status should be 400

Get chattable resources in namespace
    [Documentation]    Verify that chattable resources can be listed for a namespace.
    [Tags]    namespaces    chattable    smoke
    Given a ready project with user access exists
    When chattable resources request is sent
    Then response status should be 200
    And response should contain chattable structure

Namespace listing excludes projects without user access
    [Documentation]    Verify that namespace listing only includes namespaces the user has access to.
    [Tags]    namespaces    list    smoke    access-control
    Given a ready project with user access exists
    And a project without user access exists
    When list namespaces request is sent
    Then response should contain namespace list
    And namespace list should include project namespace
    And namespace list should not include inaccessible project namespace
