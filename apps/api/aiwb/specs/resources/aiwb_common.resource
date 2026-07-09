# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Shared AIWB keywords used across multiple resource files.
...                 Contains utility keywords that don't belong to any specific domain.
Resource            resources/common/resource_resolver.resource
Resource            api/health.resource
Library             Collections


*** Keywords ***
AIWB service is running
    [Documentation]    Verifies that AIWB service is running and healthy.
    Verify AIWB health

Get Project Namespace
    [Documentation]    Returns the Kubernetes namespace for the current test project.
    ...    Decouples AIWB from AIRM project internals -- if namespace derivation changes,
    ...    only this keyword needs updating.
    ${project}=    The project object
    ${namespace}=    Get From Dictionary    ${project}    name
    RETURN    ${namespace}

The response is a paginated list with page metadata
    [Documentation]    Verifies the response carries the nested paginated envelope
    ...    (data list plus a pagination object with page, pageSize, total).
    ...    Internal assertion helper; tests should prefer the behavioural
    ...    keyword `The result is returned page by page` instead.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    data
    Dictionary Should Contain Key    ${body}    pagination
    ${pagination}=    Get From Dictionary    ${body}    pagination
    Dictionary Should Contain Key    ${pagination}    page
    Dictionary Should Contain Key    ${pagination}    pageSize
    Dictionary Should Contain Key    ${pagination}    total
    ${data}=    Get From Dictionary    ${body}    data
    ${is_list}=    Evaluate    isinstance($data, list)
    Should Be True    ${is_list}    msg=Response 'data' field is not a list

The result is returned page by page
    [Documentation]    Behavioural wrapper: verifies the call succeeded and the
    ...    items are returned in pages rather than as one flat list. Used by
    ...    scenarios so they don't have to mention response codes or envelope
    ...    shapes — those stay in the keyword layer.
    Should be equal as integers    ${TEST_RESPONSE.status_code}    200
    The response is a paginated list with page metadata

The result reflects the requested page
    [Documentation]    Behavioural wrapper for scenarios that navigate between
    ...    pages: asserts the response's reported page number matches what
    ...    the user just requested.
    [Arguments]    ${expected_page}
    VAR    ${body}    ${TEST_RESPONSE.json()}
    ${pagination}=    Get From Dictionary    ${body}    pagination
    ${actual_page}=    Get From Dictionary    ${pagination}    page
    Should Be Equal As Integers    ${actual_page}    ${expected_page}
