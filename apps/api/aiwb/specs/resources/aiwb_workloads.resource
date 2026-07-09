# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Business-logic keywords for the AIWB workloads polymorphic view.
...                 The workloads router exposes only read operations across all
...                 capability types (inference, fine-tuning, workspaces). Capability
...                 mutations live on their own routers; the keywords below verify the
...                 polymorphic surface and confirm that removed mutations no longer
...                 respond from the workloads namespace.
Resource            api/workloads.resource
Resource            aiwb_common.resource
Library             Collections


*** Keywords ***
The user lists workloads in the project
    [Documentation]    Calls GET /projects/{project}/workloads and stores the response.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workloads    namespace=${namespace}    expected_status=200
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The polymorphic list returns entries for the project
    [Documentation]    Verifies the workloads response is a well-formed ListResponse.
    ...    Each entry exposes the type discriminator so consumers can route follow-up
    ...    calls to the appropriate capability endpoint.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    ${body}=    Set Variable    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    data
    ${data}=    Get From Dictionary    ${body}    data
    FOR    ${entry}    IN    @{data}
        Dictionary Should Contain Key    ${entry}    type
        Dictionary Should Contain Key    ${entry}    id
    END

The user lists workloads with a page size of ${page_size}
    [Documentation]    Calls GET /projects/{project}/workloads?pageSize=N and stores
    ...    the response. Used to exercise small page sizes so navigation can be
    ...    verified without seeding many workloads.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workloads    namespace=${namespace}    page_size=${page_size}
    ...    expected_status=200
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The user requests page ${page} with page size ${page_size}
    [Documentation]    Calls GET /projects/{project}/workloads?page=N&pageSize=M and
    ...    stores the response so the Then-step can assert the pagination metadata.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workloads    namespace=${namespace}    page=${page}
    ...    page_size=${page_size}    expected_status=200
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The response pagination metadata reflects page ${page} of size ${page_size}
    [Documentation]    Asserts the pagination block records the requested page and
    ...    page size; `total` is whatever the project happens to hold.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    ${pagination}=    Get From Dictionary    ${body}    pagination
    Should Be Equal As Integers    ${pagination}[page]    ${page}
    Should Be Equal As Integers    ${pagination}[pageSize]    ${page_size}

The user requests a removed workload mutation
    [Documentation]    Hits each removed workloads route once and stores the responses
    ...    so the Then-step can assert all three are gone.
    ...    Sets: TEST_REMOVED_ROUTE_RESPONSES
    ${namespace}=    Get Project Namespace
    ${chat_body}=    Create Dictionary    model=default    stream=${False}
    @{messages}=    Create List
    ${user_msg}=    Create Dictionary    role=user    content=hi
    Append To List    ${messages}    ${user_msg}
    Set To Dictionary    ${chat_body}    messages=${messages}
    ${chat}=    Send chat to AIWB workload    00000000-0000-0000-0000-000000000000
    ...    ${namespace}    ${chat_body}
    ${delete}=    Delete AIWB workload    00000000-0000-0000-0000-000000000000    ${namespace}
    ${chattable}=    List Chattable AIWB Workloads    ${namespace}
    VAR    &{responses}    chat=${chat}    delete=${delete}    chattable=${chattable}
    VAR    ${TEST_REMOVED_ROUTE_RESPONSES}    ${responses}    scope=TEST

The removed routes should no longer be served
    [Documentation]    Confirms each removed mutation is no longer available on the
    ...    workloads router. The exact status code differs by route because the
    ...    workloads router still serves overlapping GET paths:
    ...    - chat: 404 (no handler at .../{id}/chat)
    ...    - delete: 405 (only GET defined on .../{id})
    ...    - chattable: 422 ("chattable" collides with .../{id} and fails UUID parsing)
    ...    Consumers must use the capability endpoints instead
    ...    (inference/{id}, workspaces/{id}, fine-tuning/{id}, inference?capability=chat).
    VAR    &{expected_status}    chat=404    delete=405    chattable=422
    FOR    ${name}    IN    chat    delete    chattable
        ${response}=    Get From Dictionary    ${TEST_REMOVED_ROUTE_RESPONSES}    ${name}
        ${expected}=    Get From Dictionary    ${expected_status}    ${name}
        Should Be Equal As Integers    ${response.status_code}    ${expected}
        ...    msg=Expected ${name} route to return ${expected}, got ${response.status_code}
    END
