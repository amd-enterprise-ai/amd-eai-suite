# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIWB cluster catalog endpoints.
...                 Provides HTTP wrappers for runtime profile option APIs.
Library             RequestsLibrary
Resource            resources/api/common.resource


*** Keywords ***
Aim images endpoint
    [Documentation]    Return the aim-engine image family catalog endpoint URL.
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=cluster/aim-images
    RETURN    ${endpoint}

Cluster accelerators endpoint
    [Documentation]    Return the cluster accelerators catalog endpoint URL.
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=cluster/accelerators
    RETURN    ${endpoint}

List aim image families
    [Documentation]    GET the config-driven aim-engine image family catalog.
    [Arguments]    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Aim images endpoint
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    RETURN    ${response}

List cluster accelerators
    [Documentation]    GET accelerator products detected on ready cluster nodes.
    [Arguments]    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Cluster accelerators endpoint
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    RETURN    ${response}
