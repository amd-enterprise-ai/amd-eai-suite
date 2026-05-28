# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Suite-level setup keywords for AIRM frontend E2E tests.
Resource            ui_endpoint.resource


*** Keywords ***
Validate UI test prerequisites
    [Documentation]    Resolves the AIRM UI endpoint to validate connectivity.
    ...                Fails early if the endpoint cannot be determined.

    ${url}=    AIRM UI endpoint
    Log    AIRM UI URL: ${url}    INFO
