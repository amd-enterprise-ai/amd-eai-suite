# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level AIWB namespace testing keywords.
...                 Provides business-logic level keywords for testing AIWB namespace operations.
...                 Uses the low-level API keywords from api/namespaces.resource to implement
...                 higher-level testing scenarios for namespace listing, stats, metrics,
...                 chattable resources, and access control.
Resource            api/namespaces.resource
Resource            resources/airm_projects.resource
Resource            aiwb_common.resource
Library             Collections
Library             DateTime


*** Keywords ***
# When-step keywords (used by namespaces.robot)

List namespaces request is sent
    [Documentation]    Sends request to list all accessible namespaces.
    ...    Sets: TEST_RESPONSE
    ${response}=    List AIWB Namespaces    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Namespace stats request is sent
    [Documentation]    Sends request to get namespace stats for the current project.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB Namespace Stats    ${namespace}    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Namespace metrics request is sent
    [Documentation]    Sends request to get paginated namespace metrics.
    ...    Supports optional page, page_size, and workload_type filter.
    ...    Sets: TEST_RESPONSE
    [Arguments]    ${page}=${None}    ${page_size}=${None}    ${workload_type}=${None}
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB Namespace Metrics
    ...    ${namespace}
    ...    page=${page}
    ...    page_size=${page_size}
    ...    workload_type=${workload_type}
    ...    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Namespace metric request is sent for "${metric_name}"
    [Documentation]    Sends request to get a specific namespace metric with a valid date range.
    ...    Uses a 1-hour window ending at current time.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${end}=    Get Current Date    time_zone=UTC    result_format=%Y-%m-%dT%H:%M:%SZ
    ${start}=    Evaluate    (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')    modules=datetime
    ${response}=    Get AIWB Namespace Metric    ${namespace}    ${metric_name}    ${start}    ${end}    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Namespace metric request is sent with invalid date range
    [Documentation]    Sends a namespace metric request with an intentionally invalid date range.
    ...    Supports three violation types:
    ...    - start_after_end: start is after end
    ...    - start_too_old: start is more than 30 days ago
    ...    - end_in_future: end is in the future
    ...    Sets: TEST_RESPONSE
    [Arguments]    ${violation_type}
    ${namespace}=    Get Project Namespace

    IF    "${violation_type}" == "start_after_end"
        ${end}=    Evaluate    (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')    modules=datetime
        ${start}=    Evaluate    (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')    modules=datetime
    ELSE IF    "${violation_type}" == "start_too_old"
        ${start}=    Evaluate    (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=31)).strftime('%Y-%m-%dT%H:%M:%SZ')    modules=datetime
        ${end}=    Evaluate    (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')    modules=datetime
    ELSE IF    "${violation_type}" == "end_in_future"
        ${start}=    Evaluate    (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')    modules=datetime
        ${end}=    Evaluate    (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')    modules=datetime
    ELSE
        Fail    Unknown violation type: ${violation_type}. Expected: start_after_end, start_too_old, end_in_future
    END

    ${response}=    Get AIWB Namespace Metric    ${namespace}    gpu_device_utilization    ${start}    ${end}    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Chattable resources request is sent
    [Documentation]    Sends request to get chattable resources for the current project namespace.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB Chattable Resources    ${namespace}    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}

# When-step keywords (used by cross_service.robot)

AIWB namespaces are listed
    [Documentation]    Lists all AIWB namespaces for the current user.
    ...    Sets: TEST_RESPONSE
    ${response}=    List AIWB Namespaces    expected_status=200
    Set Test Variable    ${TEST_RESPONSE}    ${response}

AIWB namespace stats are requested
    [Documentation]    Requests stats for the current project's namespace.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB Namespace Stats    ${namespace}    expected_status=200
    Set Test Variable    ${TEST_RESPONSE}    ${response}

# Then-step keywords (used by namespaces.robot)

Response should contain namespace list
    [Documentation]    Verifies response contains a list of namespace strings in the "data" key.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    data
    ${namespaces}=    Get From Dictionary    ${body}    data
    ${is_list}=    Evaluate    isinstance($namespaces, list)
    Should Be True    ${is_list}    msg=Response 'data' field is not a list: ${namespaces}

Namespace list should include project namespace
    [Documentation]    Verifies the namespace list includes the current project's namespace.
    ${namespace}=    Get Project Namespace
    VAR    ${body}    ${TEST_RESPONSE.json()}
    ${namespaces}=    Get From Dictionary    ${body}    data
    Should Contain    ${namespaces}    ${namespace}
    ...    msg=Project namespace '${namespace}' not found in namespace list: ${namespaces}

Namespace list should not include inaccessible project namespace
    [Documentation]    Verifies the namespace list does NOT include the inaccessible project namespace.
    ...    Requires TEST_UNAUTHORIZED_NAMESPACE to be set.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    ${namespaces}=    Get From Dictionary    ${body}    data
    Should Not Contain    ${namespaces}    ${TEST_UNAUTHORIZED_NAMESPACE}
    ...    msg=Inaccessible namespace '${TEST_UNAUTHORIZED_NAMESPACE}' was found in namespace list

Response should contain namespace stats structure
    [Documentation]    Verifies the response has the expected namespace stats structure.
    ...    Expected fields: namespace, total, statusCounts
    VAR    ${body}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    namespace
    Dictionary Should Contain Key    ${body}    total
    Dictionary Should Contain Key    ${body}    statusCounts
    ${total}=    Get From Dictionary    ${body}    total
    ${total_int}=    Convert To Integer    ${total}
    Should Be True    ${total_int} >= 0    msg=Total count should be non-negative, got ${total_int}

Response should contain paginated metrics structure
    [Documentation]    Verifies the response has the expected paginated metrics structure.
    ...    Expected fields: data (list), total, page, pageSize, totalPages
    VAR    ${body}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    data
    Dictionary Should Contain Key    ${body}    total
    Dictionary Should Contain Key    ${body}    page
    Dictionary Should Contain Key    ${body}    pageSize
    Dictionary Should Contain Key    ${body}    totalPages
    ${data}=    Get From Dictionary    ${body}    data
    ${is_list}=    Evaluate    isinstance($data, list)
    Should Be True    ${is_list}    msg=Response 'data' field is not a list

Response should contain chattable structure
    [Documentation]    Verifies the response has the expected chattable response structure.
    ...    Expected fields: aimServices (list), workloads (list)
    VAR    ${body}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    aimServices
    Dictionary Should Contain Key    ${body}    workloads
    ${aim_services}=    Get From Dictionary    ${body}    aimServices
    ${workloads}=    Get From Dictionary    ${body}    workloads
    ${aim_is_list}=    Evaluate    isinstance($aim_services, list)
    ${wl_is_list}=    Evaluate    isinstance($workloads, list)
    Should Be True    ${aim_is_list}    msg=aimServices is not a list
    Should Be True    ${wl_is_list}    msg=workloads is not a list

# Then-step keywords (used by cross_service.robot)

AIWB namespace list should contain project namespace
    [Documentation]    Verifies the namespace list contains the current project's namespace.
    ...    Requires: TEST_PROJECT (set by project setup keywords), TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${namespaces_list}=    Set Variable    ${TEST_RESPONSE.json()['data']}
    List Should Contain Value    ${namespaces_list}    ${namespace}
    ...    msg=Namespace ${namespace} not found in AIWB namespace list

AIWB namespace stats response should contain namespace
    [Documentation]    Verifies the namespace stats response contains the project namespace.
    ...    Requires: TEST_PROJECT (set by project setup keywords), TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response_json}=    Set Variable    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${response_json}    namespace
    Should Be Equal As Strings    ${response_json}[namespace]    ${namespace}
    ...    msg=Stats response namespace does not match expected ${namespace}

AIWB namespace list should not contain "${namespace}"
    [Documentation]    Verifies the namespace list does NOT contain the specified namespace.
    ...    Requires: TEST_RESPONSE
    ${namespaces_list}=    Set Variable    ${TEST_RESPONSE.json()['data']}
    List Should Not Contain Value    ${namespaces_list}    ${namespace}
    ...    msg=Namespace ${namespace} should NOT be in AIWB namespace list but was found

AIWB namespace list should not contain unauthorized namespace
    [Documentation]    Verifies the namespace list does NOT contain the unauthorized project's namespace.
    ...    Requires: TEST_UNAUTHORIZED_NAMESPACE, TEST_RESPONSE
    Variable Should Exist    ${TEST_UNAUTHORIZED_NAMESPACE}
    ...    msg=No unauthorized project created yet. Use 'A project without user access exists' first.
    AIWB namespace list should not contain "${TEST_UNAUTHORIZED_NAMESPACE}"

AIWB namespace stats should be denied for "${namespace}"
    [Documentation]    Verifies that requesting stats for the specified namespace returns 403.
    ${response}=    Get AIWB Namespace Stats    ${namespace}    expected_status=403
    Log    AIWB namespace stats correctly denied for ${namespace}    INFO

AIWB namespace stats should be denied for unauthorized namespace
    [Documentation]    Verifies that requesting stats for the unauthorized project's namespace returns 403.
    ...    Requires: TEST_UNAUTHORIZED_NAMESPACE
    Variable Should Exist    ${TEST_UNAUTHORIZED_NAMESPACE}
    ...    msg=No unauthorized project created yet. Use 'A project without user access exists' first.
    AIWB namespace stats should be denied for "${TEST_UNAUTHORIZED_NAMESPACE}"

# Precondition keywords

A project without user access exists
    [Documentation]    Creates a project WITHOUT adding the current user.
    ...    The user will not have access to this project's namespace.
    ...    Waits for the project to reach Ready state.
    ...    Sets: TEST_UNAUTHORIZED_NAMESPACE
    ...    Preserves: TEST_PROJECT_ID, TEST_PROJECT (restored after creation)

    # Save current project context so we can restore it
    ${saved_project_id}=    Get Variable Value    ${TEST_PROJECT_ID}    ${None}
    ${saved_project}=    Get Variable Value    ${TEST_PROJECT}    ${None}

    # Create project without user access
    Create Project With Validation

    # Capture the unauthorized namespace (namespace = project name)
    ${unauthorized_namespace}=    Get From Dictionary    ${TEST_PROJECT}    name
    Set Test Variable    ${TEST_UNAUTHORIZED_NAMESPACE}    ${unauthorized_namespace}
    Log    Created unauthorized project with namespace: ${unauthorized_namespace}    INFO

    # Restore the original project context
    IF    $saved_project_id != $None
        Set Test Variable    ${TEST_PROJECT_ID}    ${saved_project_id}
        Set Test Variable    ${TEST_PROJECT}    ${saved_project}
    END
