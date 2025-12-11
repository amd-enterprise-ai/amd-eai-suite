# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       End to end tests for catalog service

Resource            resources/deployment.resource
Resource            resources/catalog_keywords.resource
Resource            resources/api/health.resource
Resource            resources/authorization.resource

Suite Setup         Verify Catalog Service Health


*** Keywords ***
Verify Catalog Service Health
    [Documentation]    Verifies catalog service is healthy before running tests
    ...                Includes validation of authentication setup for better error reporting
    ...                Extended retry window (30s) allows port forward recreation if needed

    # First validate kubectl OIDC configuration
    Validate Kubectl Config

    # Then verify catalog service health with extended timeout for port forward recovery
    # Port forward recreation can take several seconds, so we need more time than 10s
    Wait until keyword succeeds    30 s    2 s    Verify catalog health
