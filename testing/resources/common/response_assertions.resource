# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Generic HTTP response assertion keywords.
...                 Provides response validation keywords used across all test suites.
...                 These are service-agnostic and work with any RequestsLibrary response.
Library             String
Library             Collections


*** Keywords ***
Response status should be ${expected_status:[0-9]+}
    [Documentation]    Verify the response status code and log error details on failure
    TRY
        Status should be        ${expected_status}      ${TEST_RESPONSE}
    EXCEPT    AS    ${error}
        ${body}=                Set Variable            ${TEST_RESPONSE.text}
        ${error_msg}=           Set Variable            Response status was ${TEST_RESPONSE.status_code} but expected ${expected_status}.\nResponse URL: ${TEST_RESPONSE.url}\nResponse headers: ${TEST_RESPONSE.headers}\nResponse body: ${body}
        Log                     ${error_msg}            ERROR
        Fail                    ${error_msg}
    END

Response should contain status "${expected_status}"
    [Documentation]    Verify the response contains expected status
    Dictionary should contain value                 ${TEST_RESPONSE.json()}      ${expected_status}

Response should contain "${expected_value}"
    [Documentation]    Verifies response contains an expected value
    TRY
        Dictionary should contain value                 ${TEST_RESPONSE.json()}      ${expected_value}
    EXCEPT    AS    ${error}
        ${response_json}=       Set Variable            ${TEST_RESPONSE.json()}
        ${error_msg}=           Set Variable            Response does not contain expected value '${expected_value}'.\nActual response content: ${response_json}\nRequest URL: ${TEST_RESPONSE.url}
        Log                     ${error_msg}            ERROR                   console=yes
        Fail                    ${error_msg}
    END

Response should contain value "${expected_value}"
    [Documentation]    Verifies response contains an expected value (alias for consistency)
    Response should contain "${expected_value}"

Response should contain key "${expected_key}"
    [Documentation]    Verifies response contains an expected key
    TRY
        Dictionary should contain key                   ${TEST_RESPONSE.json()}      ${expected_key}
    EXCEPT    AS    ${error}
        ${error_msg}=           Set Variable            Response is missing required key '${expected_key}'.\nResponse body: ${TEST_RESPONSE.text}\nRequest URL: ${TEST_RESPONSE.url}
        Log                     ${error_msg}            ERROR                   console=yes
        Fail                    ${error_msg}
    END

List response should contain key "${expected_key}"
    [Documentation]    Verifies all items in response contain the expected key
    ${json_list}=    Set Variable    ${TEST_RESPONSE.json()}
    FOR    ${item}    IN    @{json_list}
        TRY
            Dictionary Should Contain Key                   ${item}                 ${expected_key}
        EXCEPT    AS    ${error}
            ${error_msg}=           Set Variable            Response item is missing required key '${expected_key}'.\nItem: ${item}\nFull Response: ${TEST_RESPONSE.text}\nURL: ${TEST_RESPONSE.url}
            Log                     ${error_msg}            ERROR                   console=yes
            Fail                    ${error_msg}
        END
    END

Total count should be greater than ${expected}
    [Documentation]    Verifies total_count is greater than expected value
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    ${data}=                Get From Dictionary     ${json}                 data
    ${total}=               Get length              ${data}
    Should be true          ${total} >= ${expected}
