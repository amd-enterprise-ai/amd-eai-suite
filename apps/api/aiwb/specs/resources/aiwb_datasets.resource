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
Resource    resources/airm_projects.resource
Resource    resources/aiwb_test_data.resource
Resource    resources/common/resource_tracking.resource
Resource    aiwb_common.resource
Library             Collections
Library             String
Library             OperatingSystem


*** Variables ***
@{CREATED_DATASET_IDS}      # Define CREATED_DATASET_IDS as an empty list


*** Keywords ***
# Initialize Dataset Tracking is now imported from common/resource_tracking.resource

Create dataset request is sent
    [Documentation]    DEPRECATED: Sends request to create a dataset using POST to base endpoint.
    ...    NOTE: This will fail because AIWB API does not support POST to base /datasets endpoint.
    ...    Use "Upload dataset request is sent" instead for actual dataset creation.
    [Arguments]             ${namespace}=${None}
    IF    $namespace == $None
        ${namespace}=    Get Project Namespace
    END
    ${response}=            Create dataset          ${TEST_DATASET}         expected_status=any     namespace=${namespace}
    Set Test Variable       ${TEST_RESPONSE}             ${response}

    # Only try to extract ID if we somehow got a success response
    IF    ${response.status_code} in [200, 201]
        ${dataset_id}=          Get from dictionary     ${response.json()}      id
        Set test variable       ${TEST_DATASET_ID}      ${dataset_id}
        Append To List          ${CREATED_DATASET_IDS}                          ${dataset_id}
        Log                     Added dataset ${dataset_id} to cleanup list: ${CREATED_DATASET_IDS}     DEBUG
    ELSE
        Log                     Create dataset failed with status ${response.status_code} - endpoint not supported     WARN
    END

Upload dataset request is sent
    [Documentation]    Sends request to upload a dataset using prepared test data
    [Arguments]             ${namespace}=${None}
    IF    $namespace == $None
        ${namespace}=    Get Project Namespace
    END
    ${response}=            Upload dataset
    ...                     jsonl_file_path=${TEST_DATASET_FILE}
    ...                     name=${TEST_DATASET}[name]
    ...                     description=${TEST_DATASET}[description]
    ...                     dataset_type=${TEST_DATASET}[type]
    ...                     namespace=${namespace}
    ...                     expected_status=200
    Set Test Variable       ${TEST_RESPONSE}             ${response}
    ${dataset_id}=          Get from dictionary     ${response.json()}      id
    Set test variable       ${TEST_DATASET_ID}      ${dataset_id}
    Append To List          ${CREATED_DATASET_IDS}                          ${dataset_id}
    Log                     Added dataset ${dataset_id} to cleanup list: ${CREATED_DATASET_IDS}     DEBUG

Finetune dataset exists
    [Documentation]    Creates a finetune dataset for testing and stores its ID as a test variable
    Valid dataset upload data is prepared
    Upload dataset request is sent
    Response status should be 200
    Dataset should exist in database  # Verify creation

A dataset exists
    [Documentation]    Creates a dataset via API and stores its ID as a test variable
    ...    This is a precondition keyword that:
    ...    1. Prepares valid dataset upload data
    ...    2. Uploads the dataset via API (only supported method in AIWB)
    ...    3. Stores the ID for later use in test variable ${TEST_DATASET_ID}
    Valid dataset upload data is prepared
    Upload dataset request is sent
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
    ${namespace}=           Get Project Namespace
    ${db_response}=         Get dataset             ${dataset_id}           namespace=${namespace}   expected_status=200

    Log                     Verifying dataset ${dataset_id} exists via API                          DEBUG

    # Verify basic fields
    Dictionary should contain key                   ${db_response.json()}                           id
    Dictionary should contain value                 ${db_response.json()}                           ${dataset_id}
    Dictionary should contain key                   ${db_response.json()}                           name
    Dictionary should contain key                   ${db_response.json()}                           created_at
    Dictionary should contain key                   ${db_response.json()}                           updated_at

The dataset should not exist in database
    [Documentation]    Verifies the dataset no longer exists in database
    ${dataset_id}=          Set Variable            ${TEST_DATASET_ID}
    ${namespace}=           Get Project Namespace
    ${db_response}=         Get dataset             ${dataset_id}           namespace=${namespace}   expected_status=404
    Log                     Dataset ${dataset_id} no longer exists in database (404 Not Found) as expected            DEBUG

Multiple datasets exist
    [Documentation]    Creates multiple datasets for testing list endpoints
    ...    Note: This keyword only creates datasets. Tests are responsible for their own verification.
    [Arguments]             ${count}=3

    FOR    ${index}    IN RANGE    ${count}
        Log                     Creating dataset ${index+1} of ${count}         DEBUG
        Valid dataset upload data is prepared
        Upload dataset request is sent
    END
    Log                     Successfully created ${count} datasets: ${CREATED_DATASET_IDS}                  INFO

List datasets request is sent
    [Documentation]    Sends request to list datasets with optional filters
    [Arguments]             ${type}=${None}         ${name}=${None}
    ${namespace}=           Get Project Namespace
    ${response}=            List datasets           type=${type}            name=${name}            expected_status=200     namespace=${namespace}
    Set Test Variable       ${TEST_RESPONSE}             ${response}

List datasets request is sent with type "${dataset_type}"
    [Documentation]    Sends a request to list datasets filtered by type
    ${namespace}=           Get Project Namespace
    ${response}=            List datasets with type filter                  ${dataset_type}         namespace=${namespace}
    Set test variable       ${TEST_RESPONSE}             ${response}

List datasets request is sent with name "${name}"
    [Documentation]    Sends a request to list datasets filtered by name
    ${namespace}=           Get Project Namespace
    ${response}=            List datasets with name filter                  ${name}                 namespace=${namespace}
    Set test variable       ${TEST_RESPONSE}             ${response}

A dataset does not exist
    [Documentation]    Sets up a non-existent dataset ID for testing
    ${dataset_id}=          Evaluate                str(uuid.uuid4())       modules=uuid
    Set test variable       ${TEST_DATASET_ID}      ${dataset_id}

Modify Dataset Request Is Sent
    [Documentation]    NOT SUPPORTED: Sends request to modify an existing dataset.
    ...    This keyword is kept for backward compatibility but will always fail.
    ...    The AIWB API does not support modifying datasets - they are immutable after creation.
    [Arguments]             ${new_desc}
    ${dataset_data}=        Create dictionary       description=${new_desc}

    Log                     Sending modify request for dataset ${TEST_DATASET_ID} - NOTE: This will fail, endpoint not supported!                   WARN
    ${namespace}=           Get Project Namespace
    ${response}=            Modify dataset          ${TEST_DATASET_ID}      ${dataset_data}         expected_status=any     namespace=${namespace}
    Set test variable       ${TEST_RESPONSE}             ${response}

Delete dataset request is sent
    [Documentation]    Sends a request to delete a dataset
    ${namespace}=           Get Project Namespace
    ${response}=            Delete dataset          ${TEST_DATASET_ID}      expected_status=any     namespace=${namespace}
    Set test variable       ${TEST_RESPONSE}             ${response}

Batch delete datasets request is sent
    [Documentation]    Sends a request to delete multiple datasets using the list stored in ${CREATED_DATASET_IDS}
    ${namespace}=           Get Project Namespace
    ${response}=            Batch delete datasets                           ${CREATED_DATASET_IDS}                          namespace=${namespace}                                   expected_status=200
    Set test variable       ${TEST_RESPONSE}             ${response}

Clean Up Dataset Test Resources
    [Documentation]    Clean up all dataset resources created during tests.
    ...    Resolves namespace from test state and passes it explicitly to API keywords.
    ${tracking_list}=       Get Variable Value    ${CREATED_DATASET_IDS}    ${EMPTY}
    ${count}=               Get Length    ${tracking_list}
    IF    ${count} == 0
        Log                 No datasets to clean up    DEBUG
        RETURN
    END
    Log                     Cleaning up ${count} dataset(s)    INFO
    ${namespace}=           Get Project Namespace
    FOR    ${dataset_id}    IN    @{CREATED_DATASET_IDS}
        TRY
            Delete dataset    ${dataset_id}    ${namespace}    expected_status=any
            Log               Deleted dataset ${dataset_id}    INFO
        EXCEPT    AS    ${error}
            Log               Failed to delete dataset ${dataset_id}: ${error}    WARN
        END
    END
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_DATASET_IDS}    ${empty_list}

Send download dataset request and expect status
    [Documentation]    Sends a request to download a dataset and expect a specific status
    [Arguments]             ${status}               ${dataset_id}=${TEST_DATASET_ID}
    ${namespace}=           Get Project Namespace
    ${response}=            Download dataset        ${dataset_id}           expected_status=${status}                       namespace=${namespace}
    Set test variable       ${TEST_RESPONSE}             ${response}

Download dataset request is sent
    [Documentation]    Sends a request to download a dataset's content expecting status 200
    Send download dataset request and expect status                         200

Response should contain datasets list
    [Documentation]    Verifies response contains a list of datasets
    ${body}=                Set variable            ${TEST_RESPONSE.json()}
    ${datasets}=            Get from dictionary     ${body}                 data
    ${is_list}=             Evaluate                isinstance(${datasets}, list)
    Should Be True          ${is_list}              msg=Response body 'data' field is not a list: ${datasets}
    ${count}=               Get length              ${datasets}
    Should be true          ${count} >= 0           msg=Dataset list is unexpectedly empty or invalid

Response should contain at least ${expected_count} datasets
    [Documentation]    Verifies response list contains at least the expected number of datasets
    ${body}=                Set variable            ${TEST_RESPONSE.json()}
    ${datasets}=            Get from dictionary     ${body}                 data
    ${count}=               Get length              ${datasets}
    Should be true          ${count} >= ${expected_count}                   msg=Expected at least ${expected_count} datasets, but found ${count}

Response should contain only datasets with type "${expected_type}"
    [Documentation]    Verifies all datasets in the response list have the specified type
    ${body}=                Set variable            ${TEST_RESPONSE.json()}
    ${datasets}=            Get from dictionary     ${body}                 data
    Should Not Be Empty     ${datasets}             msg=Dataset list is empty, cannot verify type filter.
    FOR    ${dataset}    IN    @{datasets}
        Dictionary should contain item                  ${dataset}              type                    ${expected_type}
    END

Response should contain only datasets with name "${expected_name}"
    [Documentation]    Verifies all datasets in the response list have the specified name
    ${body}=                Set variable            ${TEST_RESPONSE.json()}
    ${datasets}=            Get from dictionary     ${body}                 data
    Should Not Be Empty     ${datasets}             msg=Dataset list is empty, cannot verify name filter.
    FOR    ${dataset}    IN    @{datasets}
        Dictionary should contain item                  ${dataset}              name                    ${expected_name}
    END

Response should contain downloaded file content
    [Documentation]    Verifies the download response contains non-empty content and correct headers
    Should Not Be Empty     ${TEST_RESPONSE.content}     msg=Downloaded file content is empty.
    Dictionary Should Contain Key                   ${TEST_RESPONSE.headers}     Content-Disposition
    Dictionary Should Contain Key                   ${TEST_RESPONSE.headers}     Content-Type
    Should Contain          ${TEST_RESPONSE.headers['Content-Disposition']}      attachment; filename=
    Should Contain          ${TEST_RESPONSE.headers['Content-Type']}             application/jsonl

Downloaded content should match uploaded file
    [Documentation]    Verifies the downloaded content matches the original uploaded file
    ${expected_content}=    Get Binary File         ${TEST_DATASET_FILE}
    Should Be Equal         ${TEST_RESPONSE.content}     ${expected_content}

Get dataset request is sent for "${dataset_id}"
    [Documentation]    Get a specific dataset and store the response as test variable.
    ${namespace}=           Get Project Namespace
    ${response}=            Get dataset             ${dataset_id}           namespace=${namespace}   expected_status=200
    Set Test Variable       ${TEST_RESPONSE}             ${response}
