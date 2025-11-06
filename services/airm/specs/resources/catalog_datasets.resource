# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level dataset testing keywords.
...                 Provides business-logic level keywords for testing dataset operations.
...                 Uses the low-level API keywords from api/datasets.resource to implement
...                 higher-level testing scenarios. This is the main interface that
...                 test cases should use.
Resource            api/datasets.resource
Resource            catalog_projects.resource
Resource            test_data.resource
Library             Collections
Library             String
Library             OperatingSystem


*** Variables ***
${QUERY_PARAMS}             ${None} # Default value, will be overwritten by Project ID query params
@{CREATED_DATASET_IDS}      # Define CREATED_DATASET_IDS as an empty list


*** Keywords ***
Initialize Dataset Tracking
    [Documentation]    Resets the list of created datasets
    ...    This keyword should be used in a test suite setup to ensure
    ...    the tracking list starts empty for each test suite
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_DATASET_IDS}                          ${empty_list}
    Log                     Dataset tracking initialized. CREATED_DATASET_IDS: ${CREATED_DATASET_IDS}                       level=DEBUG

Create dataset request is sent
    [Documentation]    Sends request to create a dataset using prepared test data
    [Arguments]             ${params}=${QUERY_PARAMS}
    ${response}=            Create dataset          ${TEST_DATASET_DATA}    expected_status=201     params=${params}
    Set Test Variable       ${response}             ${response}

    # Debug: Log the actual response content
    Log                     Response status: ${response.status_code}        level=INFO
    Log                     Response content: ${response.json()}            level=INFO

    ${dataset_id}=          Get from dictionary     ${response.json()}      id
    Set test variable       ${TEST_DATASET_ID}      ${dataset_id}
    # Track created dataset ID for teardown
    Append To List          ${CREATED_DATASET_IDS}                          ${dataset_id}
    Log                     Added dataset ${dataset_id} to cleanup list: ${CREATED_DATASET_IDS}     level=DEBUG

Upload dataset request is sent
    [Documentation]    Sends request to upload a dataset using prepared test data
    [Arguments]             ${params}=${QUERY_PARAMS}
    ${response}=            Upload dataset
    ...                     jsonl_file_path=${TEST_DATASET_FILE}
    ...                     name=${TEST_DATASET_NAME}
    ...                     description=${TEST_DATASET_DESCRIPTION}
    ...                     dataset_type=${TEST_DATASET_TYPE}
    ...                     params=${params}
    ...                     expected_status=200
    Set Test Variable       ${response}             ${response}
    ${dataset_id}=          Get from dictionary     ${response.json()}      id
    Set test variable       ${TEST_DATASET_ID}      ${dataset_id}
    # Track created dataset ID for teardown
    Append To List          ${CREATED_DATASET_IDS}                          ${dataset_id}
    Log                     Added dataset ${dataset_id} to cleanup list: ${CREATED_DATASET_IDS}     level=DEBUG

Finetune dataset exists
    [Documentation]    Creates a finetune dataset for testing and stores its ID as a test variable
    Valid dataset data is prepared
    Create dataset request is sent
    Response status should be 201
    Dataset should exist in database  # Verify creation

A dataset exists
    [Documentation]    Creates a dataset via API and stores its ID as a test variable
    ...    This is a precondition keyword that:
    ...    1. Prepares valid dataset data
    ...    2. Creates the dataset via API
    ...    3. Stores the ID for later use in test variable ${TEST_DATASET_ID}
    Valid dataset data is prepared
    Create dataset request is sent
    Dataset should exist in database  # Verify creation

A dataset is uploaded
    [Documentation]    Uploads a dataset via API and stores its ID as a test variable
    ...    This is a precondition keyword that:
    ...    1. Prepares valid dataset upload data
    ...    2. Uploads the dataset via API
    ...    3. Stores the ID for later use in test variable ${TEST_DATASET_ID}
    Valid dataset upload data is prepared
    Upload dataset request is sent
    Dataset should exist in database  # Verify creation

Dataset should exist in database
    [Documentation]    Verify dataset exists in database by fetching it via API
    ${dataset_id}=          Set Variable            ${TEST_DATASET_ID}
    ${db_response}=         Get dataset             ${dataset_id}           expected_status=200

    # Log verification for debugging
    Log                     Verifying dataset ${dataset_id} exists via API                          level=INFO

    # Verify basic fields
    Dictionary should contain key                   ${db_response.json()}                           id
    Dictionary should contain value                 ${db_response.json()}                           ${dataset_id}
    Dictionary should contain key                   ${db_response.json()}                           name
    Dictionary should contain key                   ${db_response.json()}                           created_at
    Dictionary should contain key                   ${db_response.json()}                           updated_at

Dataset should exist in database with correct properties
    [Documentation]    Verify dataset exists in database with expected properties by comparing API response to database
    ${dataset_id}=          Set Variable            ${TEST_DATASET_ID}
    ${db_response}=         Get dataset             ${dataset_id}           expected_status=200

    # Compare all fields between response and database
    ${response_json}=       Set variable            ${response.json()}
    ${db_json}=             Set variable            ${db_response.json()}

    # Log verification for debugging
    Log                     Verifying dataset ${dataset_id} database consistency                    level=INFO

    # Verify all fields match
    FOR    ${key}    IN    id    name    description    type    author    created_at    updated_at    path
        ${response_value}=      Get from dictionary     ${response_json}        ${key}                  default=${None}
        ${db_value}=            Get from dictionary     ${db_json}              ${key}                  default=${None}

        # Allow None vs empty string for optional fields
        IF    "${response_value}" == "${None}" and "${db_value}" == ""
            CONTINUE
        END
        IF    "${db_value}" == "${None}" and "${response_value}" == ""
            CONTINUE
        END

        Should be equal         ${response_value}       ${db_value}
        ...                     Field ${key} does not match between response and database. API: "${response_value}", DB: "${db_value}"
    END

The dataset should not exist in database
    [Documentation]    Verifies the dataset no longer exists in database
    ${dataset_id}=          Set Variable            ${TEST_DATASET_ID}
    ${db_response}=         Get dataset             ${dataset_id}           expected_status=404
    Log                     Dataset ${dataset_id} no longer exists in database (404 Not Found) as expected

Multiple datasets exist
    [Documentation]    Creates multiple datasets for testing list endpoints
    [Arguments]             ${count}=3

    FOR    ${index}    IN RANGE    ${count}
        Log                     Creating dataset ${index+1} of ${count}
        Valid dataset data is prepared
        Create dataset request is sent
    END
    Log                     Successfully created ${count} datasets: ${CREATED_DATASET_IDS}

    # Verify that the expected number of datasets were created by listing them
    List datasets request is sent
    Response should contain at least ${count} datasets

List datasets request is sent
    [Documentation]    Sends request to list datasets with optional filters
    [Arguments]             ${type}=${None}         ${name}=${None}

    ${response}=            List datasets           type=${type}            name=${name}            expected_status=200     params=${QUERY_PARAMS}
    Set Test Variable       ${response}             ${response}

List datasets request is sent with type "${dataset_type}"
    [Documentation]    Sends a request to list datasets filtered by type
    ${response}=            List datasets with type filter                  ${dataset_type}         params=${QUERY_PARAMS}
    Set test variable       ${response}             ${response}

List datasets request is sent with name "${name}"
    [Documentation]    Sends a request to list datasets filtered by name
    ${response}=            List datasets with name filter                  ${name}                 params=${QUERY_PARAMS}
    Set test variable       ${response}             ${response}

A dataset does not exist
    [Documentation]    Sets up a non-existent dataset ID for testing
    ${dataset_id}=          Evaluate                str(uuid.uuid4())       modules=uuid
    Set test variable       ${TEST_DATASET_ID}      ${dataset_id}

Modify Dataset Request Is Sent
    [Documentation]    Sends request to modify an existing dataset (description only, as name is immutable)
    [Arguments]             ${new_desc}
    ${dataset_data}=        Create dictionary       description=${new_desc}

    # Debug logging
    Log                     Sending modify request for dataset ${TEST_DATASET_ID}                   level=INFO
    Log                     Modify data: ${dataset_data}                    level=INFO

    ${response}=            Modify dataset          ${TEST_DATASET_ID}      ${dataset_data}         expected_status=200     params=${QUERY_PARAMS}
    Set test variable       ${response}             ${response}

    # Debug the response
    Log                     Modify response status: ${response.status_code}                         level=INFO
    Log                     Modify response body: ${response.json()}        level=INFO

Delete dataset request is sent
    [Documentation]    Sends a request to delete a dataset
    ${response}=            Delete dataset          ${TEST_DATASET_ID}      expected_status=any     params=${QUERY_PARAMS}
    Set test variable       ${response}             ${response}

Batch delete datasets request is sent
    [Documentation]    Sends a request to delete multiple datasets using the list stored in ${CREATED_DATASET_IDS}
    ${response}=            Batch delete datasets                           ${CREATED_DATASET_IDS}                          params=${QUERY_PARAMS}                          expected_status=204
    Set test variable       ${response}             ${response}

Send download dataset request and expect status
    [Documentation]    Sends a request to download a dataset and expect a specific status
    [Arguments]             ${status}               ${dataset_id}=${TEST_DATASET_ID}
    ${response}=            Download dataset        ${dataset_id}           expected_status=${status}                       params=${QUERY_PARAMS}
    Set test variable       ${response}             ${response}

Download dataset request is sent
    [Documentation]    Sends a request to download a dataset's content expecting status 200
    Send download dataset request and expect status                         200

Dataset name in database should be "${expected_name}"
    [Documentation]    Verifies dataset name is updated in database
    ${db_response}=         Get dataset             ${TEST_DATASET_ID}      expected_status=200

    # Debug logging
    Log                     Expected name: ${expected_name}                 level=INFO
    Log                     Database response: ${db_response.json()}        level=INFO
    Log                     Actual name in DB: ${db_response.json()['name']}                        level=INFO

    Dictionary should contain item                  ${db_response.json()}                           name                    ${expected_name}

Dataset description in database should be "${expected_desc}"
    [Documentation]    Verifies dataset description is updated in database
    ${db_response}=         Get dataset             ${TEST_DATASET_ID}      expected_status=200
    Dictionary should contain item                  ${db_response.json()}                           description             ${expected_desc}

Response should contain datasets list
    [Documentation]    Verifies response contains a list of datasets
    ${body}=                Set variable            ${response.json()}
    ${is_list}=             Evaluate                isinstance(${body}, list)
    Should Be True          ${is_list}              msg=Response body is not a list: ${body}
    ${count}=               Get length              ${body}
    Should be true          ${count} >= 0           msg=Dataset list is unexpectedly empty or invalid

Response should contain at least ${expected_count} datasets
    [Documentation]    Verifies response list contains at least the expected number of datasets
    ${datasets}=            Set variable            ${response.json()}
    ${count}=               Get length              ${datasets}
    Should be true          ${count} >= ${expected_count}                   msg=Expected at least ${expected_count} datasets, but found ${count}

Response should contain only datasets with type "${expected_type}"
    [Documentation]    Verifies all datasets in the response list have the specified type
    ${datasets}=            Set variable            ${response.json()}
    Should Not Be Empty     ${datasets}             msg=Dataset list is empty, cannot verify type filter.
    FOR    ${dataset}    IN    @{datasets}
        Dictionary should contain item                  ${dataset}              type                    ${expected_type}
    END

Response should contain only datasets with name "${expected_name}"
    [Documentation]    Verifies all datasets in the response list have the specified name
    ${datasets}=            Set variable            ${response.json()}
    Should Not Be Empty     ${datasets}             msg=Dataset list is empty, cannot verify name filter.
    FOR    ${dataset}    IN    @{datasets}
        Dictionary should contain item                  ${dataset}              name                    ${expected_name}
    END

Response should contain deletion confirmation
    [Documentation]    Verifies the delete response indicates success
    Dictionary should contain key                   ${response.json()}      status
    Dictionary should contain key                   ${response.json()}      message
    Should Be Equal         ${response.json()['status']}                    success

Response should contain downloaded file content
    [Documentation]    Verifies the download response contains non-empty content and correct headers
    Should Not Be Empty     ${response.content}     msg=Downloaded file content is empty.
    Dictionary Should Contain Key                   ${response.headers}     Content-Disposition
    Dictionary Should Contain Key                   ${response.headers}     Content-Type
    Should Contain          ${response.headers['Content-Disposition']}      attachment; filename=
    Should Contain          ${response.headers['Content-Type']}             application/jsonl

Downloaded content should match uploaded file
    [Documentation]    Verifies the downloaded content matches the original uploaded file
    ${expected_content}=    Get Binary File         ${TEST_DATASET_FILE}
    Should Be Equal         ${response.content}     ${expected_content}

Clean Up All Created Datasets
    [Documentation]    Deletes all datasets created during test execution
    ...    This keyword should be used in a test suite teardown to ensure
    ...    all datasets created during testing are cleaned up properly.
    ${count}=               Get Length              ${CREATED_DATASET_IDS}

    # Skip if no datasets were created or list is empty
    Return From Keyword If                          ${count} == 0           No datasets to clean up
    Log                     Cleaning up ${count} datasets: ${CREATED_DATASET_IDS}                   level=INFO

    # Try batch delete first, but fall back to individual deletes if it fails
    TRY
        ${response}=            Batch delete datasets                           ${CREATED_DATASET_IDS}                          params=${QUERY_PARAMS}                          expected_status=any
        Log                     Batch delete completed successfully             level=INFO
    EXCEPT    AS    ${error}
        Log                     Batch delete failed: ${error}. Trying individual deletes...             level=WARN
        # Fall back to deleting each dataset individually
        FOR    ${dataset_id}    IN    @{CREATED_DATASET_IDS}
            TRY
                Log                     Deleting dataset ${dataset_id}                  level=INFO
                Delete dataset          ${dataset_id}           expected_status=any     params=${QUERY_PARAMS}
                Log                     Successfully deleted dataset ${dataset_id}      level=INFO
            EXCEPT    AS    ${delete_error}
                Log                     Failed to delete dataset ${dataset_id}: ${delete_error}                 level=WARN
            END
        END
    END

    # Reset the list of created datasets
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_DATASET_IDS}                          ${empty_list}
    Log                     Dataset cleanup complete. CREATED_DATASET_IDS reset to: ${CREATED_DATASET_IDS}                  level=INFO
