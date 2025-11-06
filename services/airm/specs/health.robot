# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API health endpoint.
...                 Verifies the API health check functionality works correctly.
Resource            resources/catalog_keywords.resource


*** Test Cases ***
Health Check Returns OK Status
    [Documentation]    Verify that health check endpoint returns OK status
    [Tags]                  smoke                   health

    Given catalog service is running
    When health check is performed
    Then response status should be 200
    And response should contain "OK"
