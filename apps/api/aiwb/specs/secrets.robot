# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       AIWB Secrets management and AIRM autodiscovery integration.
...                 Tests AIWB secret CRUD operations, use case filtering,
...                 and cross-service autodiscovery with AIRM.

Library             TestPrefix

Resource            resources/aiwb_common.resource
Resource            resources/aiwb_secrets.resource
Resource            resources/airm_projects.resource
Resource            resources/airm_secrets.resource

Suite Setup         Initialize Project Tracking
Suite Teardown      Clean Up All Created Projects
Test Setup          Run Keywords
...                 Initialize AIWB Secret Tracking
...                 AND    Initialize Secret ID Tracking
Test Teardown       Run Keywords
...                 Clean Up All Created AIWB Secrets
...                 AND    Clean Up All Created Secrets


*** Test Cases ***
Create secret via AIWB API
    [Documentation]    Verify creating a secret via AIWB API
    [Tags]    secret    smoke    create

    Given a ready project with user access exists
    When a secret "test-secret" with use case "HuggingFace" is created via AIWB
    Then AIWB secret "test-secret" should exist

List secrets for namespace
    [Documentation]    Verify listing secrets returns all AIWB-managed secrets
    [Tags]    secret    smoke    list

    Given a ready project with user access exists
    And a secret "secret-one" is created via AIWB
    And a secret "secret-two" is created via AIWB
    When AIWB secrets are listed
    Then AIWB secret list should contain "2" secrets

Filter secrets by use case
    [Documentation]    Verify use_case filtering returns only matching secrets
    [Tags]    secret    list

    Given a ready project with user access exists
    And a secret "hf-token" with use case "HuggingFace" is created via AIWB
    And a secret "pull-secret" with use case "ImagePullSecret" is created via AIWB
    And a secret "generic-secret" with use case "Generic" is created via AIWB
    When AIWB secrets filtered by use case "HuggingFace" should return "1" results

Get secret details
    [Documentation]    Verify getting a specific secret by name
    [Tags]    secret    smoke    get

    Given a ready project with user access exists
    And a secret "detail-test" with use case "S3" is created via AIWB
    Then AIWB secret "detail-test" should exist

Delete secret via AIWB API
    [Documentation]    Verify deleting a secret removes it
    [Tags]    secret    smoke    delete

    Given a ready project with user access exists
    And a secret "to-delete" is created via AIWB
    When AIWB secret "to-delete" is deleted
    Then AIWB secret "to-delete" should not exist

Cannot create duplicate secret name
    [Documentation]    Verify 409 when creating a secret with the same name
    [Tags]    secret    create

    Given a ready project with user access exists
    And a secret "unique-name" is created via AIWB
    Then creating duplicate AIWB secret "unique-name" should fail

AIWB-created secret is discovered by AIRM
    [Documentation]    Verify AIRM autodiscovery finds AIWB-created secrets
    [Tags]    secret    autodiscovery

    Given a ready project with user access exists
    When a secret "cross-service" with use case "HuggingFace" is created via AIWB
    Then AIWB secret should be discovered by AIRM

AIWB-deleted secret is removed from AIRM
    [Documentation]    Verify AIRM removes secret after AIWB deletes it
    [Tags]    secret    autodiscovery    delete

    Given a ready project with user access exists
    And a secret "delete-cross" with use case "Generic" is created via AIWB
    And AIWB secret should be discovered by AIRM
    When AIWB secret "delete-cross" is deleted
    Then AIWB secret should be removed from AIRM

AIWB-created secret survives AIRM pod restart
    [Documentation]    Verify no duplicates after AIRM controller restart
    [Tags]    secret    autodiscovery    restart

    Given a ready project with user access exists
    And a secret "restart-test" is created via AIWB
    And AIWB secret should be discovered by AIRM
    When AIRM agent pod is restarted
    And AIRM agent pod should be ready
    Then AIWB auto-discovered secret should not be duplicated
