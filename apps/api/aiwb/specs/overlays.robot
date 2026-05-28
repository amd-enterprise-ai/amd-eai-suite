# Copyright (c) Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API overlays endpoints.
...                 Verifies overlay creation, listing, retrieval, update, and deletion operations.
Resource            resources/aiwb_overlays.resource
Test Setup          Initialize Overlay Test Environment
Test Teardown       Clean Up Overlay Test Environment


*** Test Cases ***
Create new overlay
    [Documentation]    Verify that a new overlay can be created for an existing chart
    [Tags]                  overlays                create                  smoke

    Given required overlay files exist
    When create overlay request is sent
    Then response status should be 201
    And overlay should exist in system

List overlays
    [Documentation]    Verify that overlays can be listed
    [Tags]                  overlays                list                    smoke

    Given multiple overlays exist
    When list overlays request is sent
    Then response status should be 200
    And response data should not be empty

List overlays filtered by chart
    [Documentation]    Verify that overlays can be filtered by chart ID
    [Tags]                  overlays                list

    Given an overlay exists
    When list overlays filtered by chart request is sent
    Then response status should be 200
    And response data should not be empty

Get overlay by ID
    [Documentation]    Verify that an overlay can be retrieved by its ID
    [Tags]                  overlays                get                     smoke

    Given an overlay exists
    When get overlay request is sent
    Then response status should be 200
    And response should contain overlay with chart ID

Update overlay
    [Documentation]    Verify that an existing overlay can be updated with a new file
    [Tags]                  overlays                update

    Given an overlay exists
    When update overlay request is sent
    Then response status should be 200

Delete overlay
    [Documentation]    Verify that an existing overlay can be deleted
    [Tags]                  overlays                delete

    Given an overlay exists
    When delete overlay request is sent
    Then response status should be 204
    And the overlay should not exist in system

Delete non-existent overlay returns 404
    [Documentation]    Verify proper error when deleting non-existent overlay
    [Tags]                  overlays                delete                  negative

    Given an overlay does not exist
    When delete overlay request is sent
    Then response status should be 404

Batch delete overlays
    [Documentation]    Verify that multiple overlays can be deleted in a single request
    [Tags]                  overlays                delete

    Given multiple overlays exist
    When batch delete overlays request is sent
    Then response status should be 204
