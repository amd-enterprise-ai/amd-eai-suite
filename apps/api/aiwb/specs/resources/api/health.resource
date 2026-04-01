# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Keywords for interacting with the Catalog API health endpoint.
...                 Provides health check functionality for the catalog service.
Library             RequestsLibrary
Resource            resources/api/common.resource

*** Keywords ***
Get AIWB health status
    [Documentation]    Make a health check api request for AIWB service
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
    Create api session    aiwb
    ${endpoint}=            Service API Endpoint    aiwb    endpoint=health
    ${response}=            Safe Get Request        ${endpoint}             expected_status=${expected_status}
    RETURN                  ${response}

Verify AIWB health
    [Documentation]    Verifies AIWB service is healthy with retries
    ${response}=            Get AIWB health status
    Status should be        200                     ${response}
    Dictionary should contain value                 ${response.json()}      OK
