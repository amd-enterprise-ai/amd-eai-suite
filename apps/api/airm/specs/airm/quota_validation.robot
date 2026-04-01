# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Quota validation.
...                 Verifies that the system correctly rejects invalid quota allocations
...                 that exceed cluster capacity or violate allocation constraints.
...
...                 IMPORTANT: These tests verify quota VALIDATION (not workload limits).
...                 Quotas are guarantees enforced via preemption, not hard limits on resource usage.
...                 These tests ensure the API rejects quota allocations that exceed cluster capacity.
...
...                 The validation is implemented in app/quotas/utils.py:validate_quota_against_available_cluster_resources()
...                 and called during project creation and updates in app/projects/service.py.
...
...                 NOTE: This suite uses Test Teardown (instead of Suite Teardown) to clean up
...                 projects after EACH test. This ensures a clean cluster state for accurate quota
...                 validation, as each test needs to calculate quotas based on current cluster capacity
...                 without interference from previous test projects.
Resource            ../resources/airm_projects.resource
Resource            ../resources/airm_clusters.resource
Resource            resources/api/common.resource
Resource            ../resources/airm_keywords.resource
Library             Collections
Suite Setup         Setup Quota Validation Suite
Test Setup          Initialize Project Tracking
Test Teardown       Clean Up All Created Projects With Wait


*** Test Cases ***
Create project with quota exceeding cluster CPU capacity
    [Documentation]    Verify that creating a project with CPU quota exceeding
    ...    cluster capacity is rejected with HTTP 400 ValidationException.
    ...    Tests the sum validation: all project quotas must not exceed cluster resources.
    [Tags]    quotas    validation    negative    cpu

    Given a cluster exists in system
    And quota exceeding cluster CPU capacity is prepared
    And valid project data with quota is prepared
    When create project request with validation is sent
    Then response status should be 400
    And response text should contain    CPU

Create project with quota exceeding cluster memory capacity
    [Documentation]    Verify that creating a project with memory quota exceeding
    ...    cluster capacity is rejected with HTTP 400 ValidationException.
    ...    Tests the sum validation: all project quotas must not exceed cluster resources.
    [Tags]    quotas    validation    negative    memory

    Given a cluster exists in system
    And quota exceeding cluster memory capacity is prepared
    And valid project data with quota is prepared
    When create project request with validation is sent
    Then response status should be 400
    And response text should contain    memory

Create project with quota exceeding cluster GPU capacity
    [Documentation]    Verify that creating a project with GPU quota exceeding
    ...    cluster capacity is rejected with HTTP 400 ValidationException.
    ...    Tests the sum validation: all project quotas must not exceed cluster resources.
    [Tags]    quotas    validation    negative    gpu

    Given a cluster exists in system
    And quota exceeding cluster GPU capacity is prepared
    And valid project data with quota is prepared
    When create project request with validation is sent
    Then response status should be 400
    And response text should contain    GPU

Create project with quota exceeding cluster storage capacity
    [Documentation]    Verify that creating a project with storage quota exceeding
    ...    cluster capacity is rejected with HTTP 400 ValidationException.
    ...    Tests the sum validation: all project quotas must not exceed cluster resources.
    [Tags]    quotas    validation    negative    storage

    Given a cluster exists in system
    And quota exceeding cluster storage capacity is prepared
    And valid project data with quota is prepared
    When create project request with validation is sent
    Then response status should be 400
    And response text should contain    storage

Update project quota to exceed cluster CPU capacity
    [Documentation]    Verify that updating a project's quota to exceed cluster
    ...    CPU capacity is rejected with HTTP 400 ValidationException.
    [Tags]    quotas    validation    negative    update    cpu

    Given a cluster exists in system
    And a project exists with minimum quota
    And quota exceeding cluster CPU capacity is prepared
    When update project request with validation is sent    expected_status=any
    Then response status should be 400
    And response text should contain    CPU

Sum of project quotas exceeds cluster capacity
    [Documentation]    Verify that when multiple projects exist, creating a new project
    ...    that would cause total allocated quotas to exceed cluster capacity is rejected.
    ...    Tests aggregate validation across all projects.
    [Tags]    quotas    validation    negative    aggregate

    Given a project exists consuming 60 percent of cluster CPU
    And quota consuming 110 percent of cluster CPU is prepared
    And valid project data with quota is prepared
    When create project request with validation is sent
    Then response status should be 400
    And response text should contain    CPU


*** Keywords ***
Quota exceeding cluster CPU capacity is prepared
    [Documentation]    Prepares quota data that exceeds total cluster CPU capacity
    ${response}=    Get clusters    expected_status=200
    ${cluster}=    Set Variable    ${response.json()['data'][0]}
    ${available_cpu}=    Set Variable    ${cluster['available_resources']['cpu_milli_cores']}
    ${allocated_cpu}=    Set Variable    ${cluster['allocated_resources']['cpu_milli_cores']}

    # Request 10% more than total cluster CPU capacity
    ${excessive_cpu}=    Evaluate    int(${available_cpu} * 1.1)

    ${quota_data}=    Prepare Quota
    ...    cpu_milli_cores=${excessive_cpu}
    ...    memory_bytes=1073741824
    ...    ephemeral_storage_bytes=1073741824
    ...    gpu_count=0

    ${new_total}=    Evaluate    ${allocated_cpu} + ${excessive_cpu}
    Log    Cluster available CPU: ${available_cpu}m, already allocated: ${allocated_cpu}m    DEBUG
    Log    Requesting excessive CPU quota: ${excessive_cpu}m (110% of ${available_cpu}m)    DEBUG
    Log    New total would be: ${allocated_cpu}m + ${excessive_cpu}m = ${new_total}m    DEBUG
    RETURN    ${quota_data}

Quota exceeding cluster memory capacity is prepared
    [Documentation]    Prepares quota data that exceeds total cluster memory capacity
    ${response}=    Get clusters    expected_status=200
    ${cluster}=    Set Variable    ${response.json()['data'][0]}
    ${available_memory}=    Set Variable    ${cluster['available_resources']['memory_bytes']}

    # Request 10% more than total cluster memory capacity
    ${excessive_memory}=    Evaluate    int(${available_memory} * 1.1)

    ${quota_data}=    Prepare Quota
    ...    cpu_milli_cores=1000
    ...    memory_bytes=${excessive_memory}
    ...    ephemeral_storage_bytes=1073741824
    ...    gpu_count=0

    Log    Prepared excessive memory quota: ${excessive_memory} bytes (cluster has ${available_memory})    DEBUG
    RETURN    ${quota_data}

Quota exceeding cluster GPU capacity is prepared
    [Documentation]    Prepares quota data that exceeds total cluster GPU capacity
    ${response}=    Get clusters    expected_status=200
    ${cluster}=    Set Variable    ${response.json()['data'][0]}
    ${available_gpu}=    Set Variable    ${cluster['available_resources']['gpu_count']}

    # Request 2 more GPUs than total cluster capacity
    ${excessive_gpu}=    Evaluate    int(${available_gpu} + 2)

    ${quota_data}=    Prepare Quota
    ...    cpu_milli_cores=1000
    ...    memory_bytes=1073741824
    ...    ephemeral_storage_bytes=1073741824
    ...    gpu_count=${excessive_gpu}

    Log    Prepared excessive GPU quota: ${excessive_gpu} GPUs (cluster has ${available_gpu})    DEBUG
    RETURN    ${quota_data}

Quota exceeding cluster storage capacity is prepared
    [Documentation]    Prepares quota data that exceeds total cluster storage capacity
    ${response}=    Get clusters    expected_status=200
    ${cluster}=    Set Variable    ${response.json()['data'][0]}
    ${available_storage}=    Set Variable    ${cluster['available_resources']['ephemeral_storage_bytes']}

    # Request 10% more than total cluster storage capacity
    ${excessive_storage}=    Evaluate    int(${available_storage} * 1.1)

    ${quota_data}=    Prepare Quota
    ...    cpu_milli_cores=1000
    ...    memory_bytes=1073741824
    ...    ephemeral_storage_bytes=${excessive_storage}
    ...    gpu_count=0

    Log    Prepared excessive storage quota: ${excessive_storage} bytes (cluster has ${available_storage})    DEBUG
    RETURN    ${quota_data}

A project exists consuming ${percentage} percent of cluster CPU
    [Documentation]    Creates a project that consumes specified percentage of REMAINING cluster CPU capacity

    ${response}=    Get clusters    expected_status=200
    ${cluster}=    Set Variable    ${response.json()['data'][0]}
    ${available_cpu}=    Set Variable    ${cluster['available_resources']['cpu_milli_cores']}
    ${allocated_cpu}=    Set Variable    ${cluster['allocated_resources']['cpu_milli_cores']}

    # Calculate remaining capacity
    ${remaining_cpu}=    Evaluate    ${available_cpu} - ${allocated_cpu}

    # Calculate percentage of REMAINING CPU
    ${percentage_decimal}=    Evaluate    ${percentage} / 100.0
    ${quota_cpu}=    Evaluate    int(${remaining_cpu} * ${percentage_decimal})

    ${quota_data}=    Prepare Quota
    ...    cpu_milli_cores=${quota_cpu}
    ...    memory_bytes=1073741824
    ...    ephemeral_storage_bytes=1073741824
    ...    gpu_count=0

    # Create project with this quota
    ${project_name}=    Test Name    quota-val-${percentage}pct
    ${project}=    Create Project With Validation    quota_data=${quota_data}    project_name=${project_name}

    Log    Created project consuming ${percentage}% of remaining CPU (${quota_cpu}m out of ${remaining_cpu}m remaining)    DEBUG
    RETURN    ${project}

Quota consuming ${percentage} percent of cluster CPU is prepared
    [Documentation]    Prepares quota data for specified percentage of REMAINING cluster CPU

    ${response}=    Get clusters    expected_status=200
    ${cluster}=    Set Variable    ${response.json()['data'][0]}
    ${available_cpu}=    Set Variable    ${cluster['available_resources']['cpu_milli_cores']}
    ${allocated_cpu}=    Set Variable    ${cluster['allocated_resources']['cpu_milli_cores']}

    # Calculate remaining capacity
    ${remaining_cpu}=    Evaluate    ${available_cpu} - ${allocated_cpu}

    # Calculate percentage of REMAINING CPU
    ${percentage_decimal}=    Evaluate    ${percentage} / 100.0
    ${quota_cpu}=    Evaluate    int(${remaining_cpu} * ${percentage_decimal})

    ${quota_data}=    Prepare Quota
    ...    cpu_milli_cores=${quota_cpu}
    ...    memory_bytes=1073741824
    ...    ephemeral_storage_bytes=1073741824
    ...    gpu_count=0

    Log    Prepared quota for ${percentage}% of remaining CPU (${quota_cpu}m out of ${remaining_cpu}m remaining)    DEBUG
    RETURN    ${quota_data}

Create project request with validation is sent
    [Documentation]    Sends create project request for validation tests
    ...    Used for negative validation tests that expect failures (e.g., HTTP 400)
    ...    Does not track project IDs as these requests are expected to fail
    ${response}=    Create project    ${TEST_PROJECT_DATA}    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}
    Log    Create project request returned status ${response.status_code}    DEBUG
    RETURN    ${response}

Update project request with validation is sent
    [Documentation]    Sends update project request with specified expected status
    ...    Used for negative validation tests that expect failures (e.g., HTTP 400)
    [Arguments]    ${expected_status}=200
    ${description}=    Set Variable    Updated project description for quota validation test
    ${updated_data}=    Create Dictionary    description=${description}    quota=${TEST_QUOTA_DATA}
    ${response}=    Update project    ${TEST_PROJECT_ID}    ${updated_data}    expected_status=${expected_status}
    Set Test Variable    ${TEST_RESPONSE}    ${response}
    Log    Update project request returned status ${response.status_code}    DEBUG
    RETURN    ${response}

Response text should contain
    [Documentation]    Verifies response text contains expected substring
    ...    Checks response.text for string occurrence (case-sensitive)
    [Arguments]    ${expected_text}
    Should Contain    ${TEST_RESPONSE.text}    ${expected_text}    msg=Response does not contain expected text '${expected_text}'. Actual: ${TEST_RESPONSE.text}

Setup Quota Validation Suite
    [Documentation]    Suite setup that verifies cluster has sufficient resources
    Verify Cluster Has Available Resources    min_cpu_cores=10    min_memory_gb=10    min_storage_gb=10
