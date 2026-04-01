# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for AIM catalog browsing and deployment wizard UI.
...
...                 These tests verify catalog display, model metadata, deployment wizard
...                 interactions, and incompatibility indicators. They do NOT require GPU
...                 hardware or active deployments (except where noted).
...
...                 Suite Efficiency Design:
...                 Uses Suite Setup/Teardown for project tracking and cleanup. Each test
...                 declares its own preconditions via Given steps. Catalog browsing tests
...                 skip deployment for fast execution.

# UI resources (feature layer + browser setup)
Resource            resources/common/browser_setup.resource
Resource            resources/aims.resource
Resource            resources/workloads.resource

# API resources (infrastructure preconditions, resolved via pythonpath)
Resource            resources/aiwb_aims.resource
Resource            resources/airm_projects.resource

Suite Setup         Initialize Project Tracking
Suite Teardown      Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
# =============================================================================
# Browse Catalog UI (SDA-2364, SDA-3121)
# =============================================================================

AIM catalog page displays model cards with metadata
    [Documentation]    Verify that the AIM catalog page loads and displays model cards
    ...                with essential metadata: version count, description, and tags.
    [Tags]    ui    aims    catalog    smoke

    Given a ready project with user access exists
    And an AIM exists in system
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on models page
    Then catalog should display AIM cards
    And catalog should show description text
    And AIM card "${TEST_AIM_DISPLAY_NAME}" should show metadata

AIM catalog cards show version count and deploy button
    [Documentation]    Verify that each AIM card shows the number of available versions
    ...                and provides a Deploy action button.
    [Tags]    ui    aims    catalog    smoke

    Given a ready project with user access exists
    And an AIM exists in system
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on models page
    Then AIM card "${TEST_AIM_DISPLAY_NAME}" should show version count
    And AIM card "${TEST_AIM_DISPLAY_NAME}" should show deploy button

Incompatible models are visually distinguished in catalog
    [Documentation]    Verify that models incompatible with the current hardware show
    ...                an unsupported banner. This test always passes - it validates
    ...                the mechanism exists when incompatible models are present.
    [Tags]    ui    aims    catalog    smoke

    Given a ready project with user access exists
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on models page
    Then unsupported models should be visually distinguished

# =============================================================================
# Deploy Through Wizard (SDA-2368, SDA-2878, SDA-3134)
# =============================================================================

Deploy drawer shows model info and deployment settings
    [Documentation]    Verify that opening the deploy drawer for an AIM shows the model
    ...                title, description, version selector, and deployment settings section.
    [Tags]    ui    aims    deploy    catalog

    Given a ready project with user access exists
    And an AIM exists in system
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on models page
    When user opens deploy drawer for "${TEST_AIM_DISPLAY_NAME}"
    Then deploy drawer should be open
    And deploy drawer should show model info for "${TEST_AIM_DISPLAY_NAME}"
    And deploy drawer should show version and settings

# =============================================================================
# Deployment Status & Management (SDA-2383)
# =============================================================================

Deployed models list shows active deployments with status
    [Documentation]    Verify that the Deployed Models tab shows all active deployments
    ...                with their status indicators.
    [Tags]    ui    aims    workloads    deployed    gpu

    Given a ready project with user access exists
    And AIM is deployed
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on models page
    When user views deployed models
    Then deployed models table should have entries

AIM details page shows logs and metrics access
    [Documentation]    Verify that the AIM details page provides access to logs and
    ...                shows the performance metric for the deployment.
    [Tags]    ui    aims    workloads    details    gpu

    Given a ready project with user access exists
    And AIM is deployed
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on workloads page
    When user opens inference workload details
    Then workload details should show logs button
    And workload details should show performance metric

Deployments list shows workloads with status indicators
    [Documentation]    Verify the workloads dashboard shows inference workloads with
    ...                status indicators.
    [Tags]    ui    aims    workloads    deployed    gpu

    Given a ready project with user access exists
    And AIM is deployed
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    When user is on workloads page
    Then deployed workloads list should have entries
    And inference workload should show status in list
