# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation    Generic resource lifecycle keywords for status polling, verification, and deletion waiting.
...    These eliminate duplicated polling/status-checking patterns across services.
...    Each service wraps these with domain-specific keyword names (BDD style).
Library          Collections
Library          String

*** Keywords ***
Wait For Resource Status
    [Documentation]    Poll a resource until its status field matches the expected value.
    ...    Uses the provided GET keyword to fetch the resource by ID.
    ...    Extra keyword arguments are forwarded to the GET keyword (e.g., namespace).
    ...    Args:
    ...        get_keyword - Name of the keyword to call (e.g., "Get project", "Get secret")
    ...        resource_id - The resource identifier to pass to the GET keyword
    ...        expected_status - The status value to wait for
    ...        timeout - Maximum time to wait (default: 2 min)
    ...        interval - Polling interval (default: 5 sec)
    ...        status_field - JSON field name containing the status (default: status)
    [Arguments]    ${get_keyword}    ${resource_id}    ${expected_status}    ${timeout}=2 min    ${interval}=5 sec    ${status_field}=status    &{kwargs}
    Wait Until Keyword Succeeds    ${timeout}    ${interval}
    ...    Verify Resource Status    ${get_keyword}    ${resource_id}    ${expected_status}    status_field=${status_field}    &{kwargs}

Verify Resource Status
    [Documentation]    Fetch a resource and verify its status field matches expected value.
    ...    Raises assertion error if status does not match (for use with polling).
    ...    Extra keyword arguments are forwarded to the GET keyword (e.g., namespace).
    [Arguments]    ${get_keyword}    ${resource_id}    ${expected_status}    ${status_field}=status    &{kwargs}
    ${response}=    Run Keyword    ${get_keyword}    ${resource_id}    &{kwargs}    expected_status=200
    VAR    ${data}    ${response.json()}
    ${actual_status}=    Get From Dictionary    ${data}    ${status_field}
    Should Be Equal As Strings    ${actual_status}    ${expected_status}    ignore_case=True
    ...    msg=Expected ${status_field} '${expected_status}', got '${actual_status}'
    Log    Resource ${resource_id}: ${status_field}=${actual_status}    DEBUG

Resource Status Should Be One Of
    [Documentation]    Verify a resource's status is one of the expected values (case-insensitive).
    ...    Fetches fresh state using the provided GET keyword.
    ...    Extra keyword arguments are forwarded to the GET keyword (e.g., namespace).
    ...    Args:
    ...        get_keyword - Name of the GET keyword
    ...        resource_id - The resource identifier
    ...        expected_statuses - Comma-separated list of acceptable statuses (e.g., "Pending, Running")
    ...        status_field - JSON field name containing the status (default: status)
    [Arguments]    ${get_keyword}    ${resource_id}    ${expected_statuses}    ${status_field}=status    &{kwargs}
    ${response}=    Run Keyword    ${get_keyword}    ${resource_id}    &{kwargs}    expected_status=200
    VAR    ${data}    ${response.json()}
    ${actual_status}=    Get From Dictionary    ${data}    ${status_field}

    @{raw_list}=    Split String    ${expected_statuses}    ,
    VAR    ${actual_lower}    ${actual_status.lower()}
    VAR    ${found}    ${False}
    FOR    ${expected}    IN    @{raw_list}
        ${stripped}=    Strip String    ${expected}
        VAR    ${expected_lower}    ${stripped.lower()}
        IF    '${actual_lower}' == '${expected_lower}'
            VAR    ${found}    ${True}
            BREAK
        END
    END
    Should Be True    ${found}
    ...    msg=Expected ${status_field} one of [${expected_statuses}], got '${actual_status}'
    Log    Resource ${resource_id}: ${status_field}=${actual_status} (matches one of: ${expected_statuses})    DEBUG
    RETURN    ${actual_status}

Wait For Resource Deletion
    [Documentation]    Poll until a resource returns 404 (fully deleted).
    ...    Extra keyword arguments are forwarded to the GET keyword (e.g., namespace).
    ...    Args:
    ...        get_keyword - Name of the GET keyword
    ...        resource_id - The resource identifier
    ...        timeout - Maximum time to wait (default: 1 min)
    ...        interval - Polling interval (default: 5 sec)
    [Arguments]    ${get_keyword}    ${resource_id}    ${timeout}=1 min    ${interval}=5 sec    &{kwargs}
    Wait Until Keyword Succeeds    ${timeout}    ${interval}
    ...    Resource Should Not Exist    ${get_keyword}    ${resource_id}    &{kwargs}

Resource Should Not Exist
    [Documentation]    Verify a resource returns 404 (does not exist).
    ...    Extra keyword arguments are forwarded to the GET keyword (e.g., namespace).
    [Arguments]    ${get_keyword}    ${resource_id}    &{kwargs}
    ${response}=    Run Keyword    ${get_keyword}    ${resource_id}    &{kwargs}    expected_status=any
    Should Be Equal As Integers    ${response.status_code}    404
    ...    msg=Resource still exists (status ${response.status_code})
    Log    Resource ${resource_id} confirmed deleted (404)    DEBUG
