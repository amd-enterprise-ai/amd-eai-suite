# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API datasets endpoints.
...                 Verifies dataset creation, upload, listing, modification, download, and deletion operations.
Resource    resources/aiwb_test_data.resource
Resource    resources/airm_keywords.resource
Resource    resources/aiwb_datasets.resource
Resource    resources/api/common.resource
Resource    resources/airm_projects.resource
Library             Collections
Test Setup          Initialize Dataset Tracking
Test Teardown       Clean Up Dataset Test Resources


*** Test Cases ***
Create dataset
    [Documentation]    UNSUPPORTED: Verify that a new dataset can be created via POST /datasets
    ...    NOTE: AIWB API does not support POST to base /datasets endpoint.
    ...    This test documents the unsupported endpoint. Use "Upload dataset" test instead.
    [Tags]                  datasets                create                  negative

    Given a ready project with user access exists
    and valid dataset data is prepared
    When create dataset request is sent
    Then response status should be 405  # Method Not Allowed - endpoint exists but POST not supported

Upload dataset
    [Documentation]    Verify that a new dataset can be uploaded via POST /datasets/upload
    [Tags]                  datasets                upload                  smoke
    Given a ready project with user access exists
    And valid dataset upload data is prepared
    When upload dataset request is sent
    Then response status should be 200
    And response should contain "${TEST_DATASET}[name]"
    And response should contain key "path"
    And dataset should exist in database

List datasets
    [Documentation]    Verify that datasets can be listed via GET /datasets
    [Tags]                  datasets                list                    smoke
    Given a ready project with user access exists
    And multiple datasets exist
    When list datasets request is sent
    Then response status should be 200
    And response should contain datasets list
    And response should contain at least 3 datasets

List datasets with type filter
    [Documentation]    Verify that datasets can be filtered by type via GET /datasets?type=...
    [Tags]                  datasets                list                    filtering               type
    Given a ready project with user access exists
    And multiple datasets exist
    And a dataset exists  # Create one more with a known type
    When list datasets request is sent with type "${TEST_DATASET}[type]"
    Then response status should be 200
    And response should contain datasets list
    And response should contain only datasets with type "${TEST_DATASET}[type]"

List datasets with name filter
    [Documentation]    Verify that datasets can be filtered by name via GET /datasets?name=...
    [Tags]                  datasets                list                    filtering               name
    Given a ready project with user access exists
    And a dataset exists
    When list datasets request is sent with name "${TEST_DATASET}[name]"
    Then response status should be 200
    And response should contain datasets list
    And response should contain only datasets with name "${TEST_DATASET}[name]"

Get specific dataset
    [Documentation]    Verify that a specific dataset can be retrieved by ID via GET /datasets/{id}
    [Tags]                  datasets                get                     smoke
    Given a ready project with user access exists
    And a dataset exists
    When get dataset request is sent for "${TEST_DATASET_ID}"
    Then response status should be 200
    And response should contain "${TEST_DATASET}[name]"
    And response should contain key "id"
    And response should contain value "${TEST_DATASET_ID}"

Modify existing dataset
    [Documentation]    UNSUPPORTED: Verify that an existing dataset can be modified via PUT /datasets/{id}
    ...    NOTE: AIWB API does not support modifying datasets - they are immutable after creation.
    ...    This test documents the unsupported endpoint.
    [Tags]                  datasets                modify                  negative
    Given a ready project with user access exists
    And a dataset exists
    And Prepare updated dataset data
    When Modify Dataset Request Is Sent             ${TEST_UPDATED_DS_DESC}
    Then response status should be 405  # Method Not Allowed - endpoint exists but PUT not supported

Download dataset content
    [Documentation]    Verify that the content of an uploaded dataset can be downloaded via GET /datasets/{id}/download
    [Tags]                  datasets                download                smoke
    Given a ready project with user access exists
    And a dataset is uploaded
    When download dataset request is sent
    Then response status should be 200
    And response should contain downloaded file content
    And downloaded content should match uploaded file

Delete non-existent dataset
    [Documentation]    Verify idempotent delete behavior for non-existent dataset via DELETE /datasets/{id}
    ...    NOTE: AIWB returns 204 for idempotent delete (same as existing dataset)
    [Tags]                  datasets                delete                  negative
    Given a ready project with user access exists
    And a dataset does not exist
    When delete dataset request is sent
    Then response status should be 204  # AIWB returns 204 for idempotent delete

Delete existing dataset
    [Documentation]    Verify that an existing dataset can be deleted via DELETE /datasets/{id}
    [Tags]                  datasets                delete                  smoke
    Given a ready project with user access exists
    And a dataset exists
    When delete dataset request is sent
    Then response status should be 204  # API returns 204 NO CONTENT
    And the dataset should not exist in database

Batch delete datasets
    [Documentation]    Verify that multiple datasets can be deleted via POST /datasets/delete
    [Tags]                  datasets                delete                  batch
    Given a ready project with user access exists
    And multiple datasets exist
    When batch delete datasets request is sent
    Then response status should be 200
    # Note: API returns 200 with list of deleted IDs, not 204
