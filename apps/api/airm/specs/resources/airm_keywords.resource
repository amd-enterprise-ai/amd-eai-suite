# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       AIRM-specific test verification keywords.
...                 Provides health check and service-specific assertion keywords
...                 for AIRM test scenarios.
Resource            api/health.resource
Resource            api/workloads.resource
Resource            airm_workloads.resource
Resource            airm_projects.resource
Resource            resources/common/response_assertions.resource


*** Keywords ***
AIRM service is running
    [Documentation]    Verifies that AIRM service is running and healthy
    Verify AIRM health


Health check is performed
    [Documentation]    Perform a health check and store response
    ${response}=            Get health status
    Set Test Variable       ${TEST_RESPONSE}             ${response}
    RETURN    ${response}
