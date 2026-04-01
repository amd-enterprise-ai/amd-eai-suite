# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for AIRM API health endpoint.
...                 Verifies the API health check functionality works correctly.
Resource            resources/airm_keywords.resource


*** Test Cases ***
Health Check Returns OK Status
    [Documentation]    Verify that health check endpoint returns OK status
    [Tags]                  smoke                   health

    Given AIRM service is running
    When health check is performed
    Then response status should be 200
    And response should contain "OK"
