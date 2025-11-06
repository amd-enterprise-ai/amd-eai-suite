# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       End to end tests for catalog service

Resource            resources/deployment.resource
Resource            resources/catalog_keywords.resource
Resource            resources/api/health.resource

Suite Setup         Setup Catalog Service
Suite Teardown      Apps are undeployed


*** Keywords ***
Setup Catalog Service
    [Documentation]    Sets up catalog service and verifies it's healthy
    Apps "catalog" are deployed

    # Use longer wait time if apps were actually deployed, shorter if using existing namespace
    ${wait_time} =          Set Variable If         ${NAMESPACE_WAS_CREATED}                        2 min                   10 s
    Log                     Using wait time ${wait_time} for health check (namespace was created: ${NAMESPACE_WAS_CREATED})                         console=yes

    Wait until keyword succeeds                     ${wait_time}            200 ms                  Verify catalog health
