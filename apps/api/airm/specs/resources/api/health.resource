# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keywords for interacting with the AIRM API health endpoint.
...                 Provides health check functionality for the AIRM service.
Library             RequestsLibrary
Resource            resources/api/common.resource


*** Keywords ***
Get health status
    [Documentation]    Make a health check api request for AIRM service
    ...
    ...    Args:
    ...    expected_status: Expected http status code
    ...
    ...    Returns:
    ...    response: The health check api response
    ...
    ...    Raises:
    ...    HTTPError: If health check fails unexpectedly
    [Arguments]             ${expected_status}=any
    Create api session    airm
    ${endpoint}=            Service API Endpoint    airm    endpoint=health
    TRY
        ${response}=            Safe Get Request        ${endpoint}             expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Health check failed for AIRM service: ${error}
        Log                     ${error_msg}            ERROR                   console=yes  # Keep console output for failures
        FAIL                    ${error_msg}
    END

Verify AIRM health
    [Documentation]    Verifies AIRM service is healthy with retries
    ${response}=            Get health status
    Status should be        200                     ${response}
    Dictionary should contain value                 ${response.json()}      OK
