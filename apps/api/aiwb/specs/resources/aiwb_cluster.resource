# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Business-logic keywords for cluster runtime profile catalog APIs.
Resource            api/cluster.resource
Resource            resources/airm_projects.resource
Library             Collections


*** Keywords ***
The user requests the aim-engine image catalog
    [Documentation]    Fetches aim-engine image families for runtime profile selection.
    ${response}=    List aim image families    expected_status=200
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The user requests cluster accelerators
    [Documentation]    Fetches accelerator products available on the cluster.
    ${response}=    List cluster accelerators    expected_status=200
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The aim-engine image catalog includes automatic selection
    [Documentation]    Verifies Automatic is offered with no fixed repository.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    ${data}=    Get From Dictionary    ${body}    data
    VAR    ${automatic}    ${None}
    FOR    ${family}    IN    @{data}
        ${family_id}=    Get From Dictionary    ${family}    familyId
        IF    '${family_id}' == 'automatic'
            VAR    ${automatic}    ${family}
            BREAK
        END
    END
    Should Not Be Equal    ${automatic}    ${None}    msg=Automatic image family missing from catalog
    ${repository}=    Get From Dictionary    ${automatic}    repository
    Should Be Equal    ${repository}    ${None}

The aim-engine image catalog lists the aim-base family
    [Documentation]    Verifies aim-base is present with repository and tag metadata.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    ${data}=    Get From Dictionary    ${body}    data
    VAR    ${aim_base}    ${None}
    FOR    ${family}    IN    @{data}
        ${family_id}=    Get From Dictionary    ${family}    familyId
        IF    '${family_id}' == 'aim-base'
            VAR    ${aim_base}    ${family}
            BREAK
        END
    END
    Should Not Be Equal    ${aim_base}    ${None}    msg=aim-base image family missing from catalog
    Dictionary Should Contain Key    ${aim_base}    displayName
    Dictionary Should Contain Key    ${aim_base}    repository
    Dictionary Should Contain Key    ${aim_base}    tags
    ${tags}=    Get From Dictionary    ${aim_base}    tags
    Should Not Be Empty    ${tags}    msg=aim-base should expose at least one image tag

Accelerators are returned as a list
    [Documentation]    Verifies the response uses the standard data list envelope.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    data
    ${data}=    Get From Dictionary    ${body}    data
    ${is_list}=    Evaluate    isinstance($data, list)
    Should Be True    ${is_list}    msg=Accelerators response data is not a list

Each accelerator entry describes a product and capacity
    [Documentation]    When accelerators are present, each entry has product and count fields.
    VAR    ${body}    ${TEST_RESPONSE.json()}
    ${data}=    Get From Dictionary    ${body}    data
    FOR    ${entry}    IN    @{data}
        Dictionary Should Contain Key    ${entry}    deviceId
        Dictionary Should Contain Key    ${entry}    productName
        Dictionary Should Contain Key    ${entry}    allocatableCount
    END
