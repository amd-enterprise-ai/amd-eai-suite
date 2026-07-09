# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for API key metrics dashboard UI features.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Uses the AIWB HTTP API to create API keys (to obtain the key ID needed
...                 for direct URL navigation), then drives the browser for UI verification.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Library             DateTime
Library             Collections
Resource            common/session.resource
Resource            pages/api_keys_page.resource
Resource            resources/api/api_keys_api.resource


*** Keywords ***
# =============================================================================
# Suite setup
# =============================================================================

Initialize API Key Metrics Suite
    [Documentation]    Generates a unique API key name prefix for this suite run.

    ${epoch}=    Get Current Date    result_format=epoch
    ${suffix}=    Evaluate    int(${epoch})
    VAR    ${TEST_METRICS_KEY_PREFIX}    e2e-metrics-key-${suffix}    scope=SUITE

# =============================================================================
# Given keywords (preconditions)
# =============================================================================

An API key exists for the project
    [Documentation]    Creates an API key via the AIWB API and stores the key ID and name
    ...                as test variables for subsequent navigation and verification.
    ...                Depends on ${TEST_PROJECT} being set by "a ready project with user access exists".
    ...                A random suffix is added to ensure unique key names per test call.

    ${random}=    Evaluate    __import__('random').randint(10000, 99999)
    VAR    ${key_name}    ${TEST_METRICS_KEY_PREFIX}-${random}

    ${empty_meta}=    Create Dictionary
    @{empty_aims}=    Create List
    ${key_data}=    Create Dictionary
    ...    displayName=${key_name}
    ...    ttl=24h
    ...    renewable=${True}
    ...    numUses=${0}
    ...    meta=${empty_meta}
    ...    aimIds=${empty_aims}

    VAR    ${project}    ${TEST_PROJECT}[name]
    Create api session    aiwb
    ${response}=    api_keys_api.Create api key    ${key_data}    project=${project}    expected_status=200
    VAR    ${key_info}    ${response.json()}

    VAR    ${TEST_API_KEY_ID}    ${key_info}[id]    scope=TEST
    VAR    ${TEST_API_KEY_NAME}    ${key_info}[displayName]    scope=TEST

# =============================================================================
# When keywords (actions)
# =============================================================================

User is on API key metrics page
    [Documentation]    Navigates directly to the metrics page for the test API key.
    ...                Depends on ${TEST_PROJECT}, ${TEST_API_KEY_ID}, and ${UI_BASE_URL} being set.

    Navigate to API key metrics page    ${UI_BASE_URL}    ${TEST_PROJECT}[name]    ${TEST_API_KEY_ID}

User changes time range to 7 days
    [Documentation]    Clicks the "7 days" tab in the time range selector on the metrics page.

    Click 7 day time range tab

# =============================================================================
# Then keywords (verification)
# =============================================================================

API key metrics page should be visible
    [Documentation]    Verifies the metrics page loaded with the correct API key name in the header.

    API key name should be visible in metrics header    ${TEST_API_KEY_NAME}

Stat cards should be visible on metrics page
    [Documentation]    Verifies the usage statistics cards are visible on the metrics page.

    Stat cards should be present on metrics page

Chart sections should be visible on metrics page
    [Documentation]    Verifies both chart sections (inference requests and token consumption)
    ...                are present on the metrics page.

    Inference requests chart should be visible
    Token consumption chart should be visible

7 day time range should be selected
    [Documentation]    Verifies the "7 days" tab is the active selection in the time range selector.

    7 day tab should be selected
