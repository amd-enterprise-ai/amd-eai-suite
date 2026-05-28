# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for AIRM S3 storage management.
...
...                 These tests verify the storage lifecycle through the UI:
...                 listing storages, creating S3 storage, assigning to projects,
...                 and deleting storage. Data preconditions are set up via API.

Resource            resources/common/browser_setup.resource
Resource            resources/common/suite_setup.resource
Resource            resources/storages.resource

Suite Setup         Initialize storage test suite
Suite Teardown      Clean Up All Tracked Resources
Test Setup          Open test browser
Test Teardown       Close test browser


*** Keywords ***
Initialize storage test suite
    [Documentation]    Validates UI prerequisites and creates shared API resources
    ...                needed by all storage tests: an S3-scoped secret.

    Validate UI test prerequisites


*** Test Cases ***
Admin views storages list with type and status
    [Documentation]    Verify that an admin can view the storages page with entries
    ...                showing their type and status columns.
    [Tags]    ui    airm    storages    list    smoke

    Given an admin user is on the storages page
    Then storages should be listed with type and status columns

Admin creates S3 storage through the UI
    [Documentation]    Verify that an admin can create a new S3 storage by filling
    ...                in the form with name, bucket URL, and selecting a secret.
    [Tags]    ui    airm    storages    create

    Given an S3 storage secret exists via API
    And an admin user is on the storages page
    When the user creates a new S3 storage with bucket URL and secret
    Then the new storage should appear in the storages list

Admin assigns storage to a project
    [Documentation]    Verify that an admin can assign a storage to a project
    ...                and the assignment is reflected in the storages list.
    [Tags]    ui    airm    storages    assign

    Given a ready project exists via API
    And an S3 storage secret exists via API
    And an unassigned storage exists via API
    And an admin user is on the storages page
    When the user assigns the storage to the project
    Then the storage should show a project assignment

Admin deletes a storage
    [Documentation]    Verify that an admin can delete a storage that is not
    ...                assigned to any project, and it disappears from the list.
    [Tags]    ui    airm    storages    delete

    Given an S3 storage secret exists via API
    And an unassigned storage exists via API
    And an admin user is on the storages page
    When the user deletes the storage and confirms
    Then the storage should not be in the list
