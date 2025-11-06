# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API datasets endpoints.
...                 Verifies dataset creation, upload, listing, modification, download, and deletion operations.
Resource            resources/catalog_keywords.resource
Resource            resources/catalog_datasets.resource
Resource            resources/test_data.resource
Resource            resources/api/common.resource
Resource            resources/catalog_projects.resource
Library             Collections
Test Setup          Initialize Dataset Tracking
Test Teardown       Clean Up All Created Datasets


*** Test Cases ***
Create dataset
    [Documentation]    Verify that a new dataset can be created via POST /datasets
    [Tags]                  datasets                create                  smoke

    Given Project exists in system
    and valid dataset data is prepared
    When create dataset request is sent
    Then response status should be 201
    And response should contain "${TEST_DATASET_DERIVED_NAME}"
    And response should contain key "created_at"
    And dataset should exist in database

Upload dataset
    [Documentation]    Verify that a new dataset can be uploaded via POST /datasets/upload
    [Tags]                  datasets                upload                  smoke
    Given Project exists in system
    And valid dataset upload data is prepared
    When upload dataset request is sent
    Then response status should be 200
    And response should contain "${TEST_DATASET_NAME}"
    And response should contain key "path"
    And dataset should exist in database

List datasets
    [Documentation]    Verify that datasets can be listed via GET /datasets
    [Tags]                  datasets                list                    smoke
    Given Project exists in system
    And multiple datasets exist
    When list datasets request is sent
    Then response status should be 200
    And response should contain datasets list
    And response should contain at least 3 datasets

List datasets with type filter
    [Documentation]    Verify that datasets can be filtered by type via GET /datasets?type=...
    [Tags]                  datasets                list                    filtering               type
    Given Project exists in system
    And multiple datasets exist
    And a dataset exists  # Create one more with a known type
    When list datasets request is sent with type "${TEST_DATASET_TYPE}"
    Then response status should be 200
    And response should contain datasets list
    And response should contain only datasets with type "${TEST_DATASET_TYPE}"

List datasets with name filter
    [Documentation]    Verify that datasets can be filtered by name via GET /datasets?name=...
    [Tags]                  datasets                list                    filtering               name
    Given Project exists in system
    And a dataset exists
    When list datasets request is sent with name "${TEST_DATASET_DERIVED_NAME}"
    Then response status should be 200
    And response should contain datasets list
    And response should contain only datasets with name "${TEST_DATASET_DERIVED_NAME}"

Get specific dataset
    [Documentation]    Verify that a specific dataset can be retrieved by ID via GET /datasets/{id}
    [Tags]                  datasets                get                     smoke
    Given Project exists in system
    And a dataset exists
    When get dataset request is sent for "${TEST_DATASET_ID}"
    Then response status should be 200
    And response should contain "${TEST_DATASET_DERIVED_NAME}"
    And response should contain key "id"
    And response should contain value "${TEST_DATASET_ID}"

Modify existing dataset
    [Documentation]    Verify that an existing dataset can be modified via PUT /datasets/{id}
    ...    Note: Only description can be updated as dataset names are immutable after creation
    [Tags]                  datasets                modify                  smoke
    Given Project exists in system
    And a dataset exists
    And Prepare updated dataset data
    When Modify Dataset Request Is Sent             ${TEST_UPDATED_DS_DESC}
    Then response status should be 200
    And dataset name in database should be "${TEST_DATASET_DERIVED_NAME}"
    And dataset description in database should be "${TEST_UPDATED_DS_DESC}"

Download dataset content
    [Documentation]    Verify that the content of an uploaded dataset can be downloaded via GET /datasets/{id}/download
    [Tags]                  datasets                download                smoke
    Given Project exists in system
    And a dataset is uploaded
    When download dataset request is sent
    Then response status should be 200
    And response should contain downloaded file content
    And downloaded content should match uploaded file

Download created dataset without content returns 404
    [Documentation]    Verify downloading a dataset created via POST /datasets (no content) returns 404.
    ...    XFAIL: Currently returns 500 due to server-side error (Issue #XYZ).
    [Tags]                  datasets                download                negative                content
    Given Project exists in system
    And a dataset exists  # Creates metadata only via POST /datasets
    When Send download dataset request and expect status                    404
    Then response status should be 404

Delete non-existent dataset
    [Documentation]    Verify proper error when deleting non-existent dataset via DELETE /datasets/{id}
    [Tags]                  datasets                delete                  negative
    Given Project exists in system
    And a dataset does not exist
    When delete dataset request is sent
    Then response status should be 404

Delete existing dataset
    [Documentation]    Verify that an existing dataset can be deleted via DELETE /datasets/{id}
    [Tags]                  datasets                delete                  smoke
    Given Project exists in system
    And a dataset exists
    When delete dataset request is sent
    Then response status should be 204  # API returns 204 with status message
    And the dataset should not exist in database

Batch delete datasets
    [Documentation]    Verify that multiple datasets can be deleted via POST /datasets/delete
    [Tags]                  datasets                delete                  batch
    Given Project exists in system
    And multiple datasets exist
    When batch delete datasets request is sent
    Then response status should be 204  # API returns 200 with status message
    # Verification that they are gone could be added, but might be slow. Rely on single delete test.


*** Keywords ***
Get dataset request is sent for "${dataset_id}"
    [Documentation]    Helper keyword to get a specific dataset and store the response
    ${response}=            Get dataset             ${dataset_id}           expected_status=200
    Set Test Variable       ${response}             ${response}
