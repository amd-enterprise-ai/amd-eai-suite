# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       BDD keywords for autoscaling UI features.
...                 Composes page-level interactions into business-meaningful keywords
...                 suitable for Given-When-Then test cases.
...
...                 Layer: Feature (tests import this, NOT page resources directly)
Resource            common/session.resource
Resource            pages/models_page.resource
Resource            pages/workloads_page.resource
Resource            pages/autoscaling_page.resource


*** Keywords ***
# =============================================================================
# Given keywords (preconditions)
# =============================================================================

Project for deployed AIM is selected
    [Documentation]    Selects the project that owns the deployed AIM.
    ...                Extracts the project name from TEST_PROJECT and selects it via the toolbar.

    Project "${TEST_PROJECT}[name]" is selected

# =============================================================================
# When keywords (actions)
# =============================================================================

User enables autoscaling in deploy drawer
    [Documentation]    Enables autoscaling by clicking the toggle in the deploy drawer.

    Click autoscaling toggle
    Wait for autoscaling fields

User opens autoscaling settings
    [Documentation]    Opens the autoscaling settings drawer from the workload details page.

    Click settings button on scaling card
    Wait for deployment settings drawer

# =============================================================================
# Then keywords (verification)
# =============================================================================

Autoscaling toggle should be visible
    [Documentation]    Verifies that the autoscaling toggle is visible in the deploy drawer.

    Wait for autoscaling toggle

Autoscaling toggle should be enabled
    [Documentation]    Verifies that the autoscaling toggle is in the enabled state.

    ${is_enabled}=    Check autoscaling toggle state
    Should Be True    ${is_enabled}    msg=Autoscaling toggle should be enabled

Autoscaling fields should be visible
    [Documentation]    Verifies that all autoscaling configuration fields are visible:
    ...                replica range, scaling metric, and target value.

    Wait for autoscaling fields

Workload details should show autoscaling card
    [Documentation]    Verifies that the autoscaling status card is visible on workload details page.

    ${text}=    Get scaling status card text
    Should Not Be Empty    ${text}

Autoscaling card should show replica range "${min}" to "${max}"
    [Documentation]    Verifies that the scaling card displays the correct replica range.

    ${text}=    Get scaling status card text
    Should Contain    ${text}    ${min}
    Should Contain    ${text}    ${max}

Autoscaling card should show metric "${metric}"
    [Documentation]    Verifies that the scaling card displays the correct scaling metric.

    ${text}=    Get scaling metric text
    Should Contain    ${text}    ${metric}

Autoscaling card should show target value "${target_value}"
    [Documentation]    Verifies that the scaling card displays the correct target value.

    ${text}=    Get target value text
    Should Contain    ${text}    ${target_value}

Deployment settings drawer should be open
    [Documentation]    Verifies that the deployment settings drawer is visible
    ...                and contains the autoscaling toggle.

    Wait for deployment settings drawer
    ${has_toggle}=    Check deployment settings drawer has autoscaling toggle
    Should Be True    ${has_toggle}    msg=Settings drawer should contain the autoscaling toggle
