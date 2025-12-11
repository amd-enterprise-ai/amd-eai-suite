# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API datasets endpoints.
...                 Provides direct API operation wrappers for the /datasets endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Library             OperatingSystem
Resource            common.resource
Resource            ../airm_projects.resource


*** Variables ***
${HEADERS_JSON}         Content-Type=application/json
${HEADERS_MULTIPART}    Content-Type=multipart/form-data


*** Keywords ***
Datasets endpoint
    [Documentation]    Return the full datasets endpoint url
    [Arguments]             ${dataset_id}=${None}                           ${action}=${None}
    ${base_endpoint}=       Catalog endpoint        datasets
    IF    $dataset_id is not None and $action is not None
        RETURN                  ${base_endpoint}/${dataset_id}/${action}
    ELSE IF    $dataset_id is not None
        RETURN                  ${base_endpoint}/${dataset_id}
    ELSE IF    $action is not None
        RETURN                  ${base_endpoint}/${action}
    ELSE
        RETURN                  ${base_endpoint}
    END

Create dataset
    [Documentation]    Create a new dataset using the provided data
    ...
    ...    Args:
    ...    dataset_data (dict): Dataset creation parameters including:
    ...    - name: Dataset name
    ...    - description: Optional description
    ...    - type: Optional DatasetType (e.g., Finetuning, Evaluation)
    ...
    ...    Return:
    ...    response: API response containing the created dataset
    ...
    ...    Raise:
    ...    HTTPError: If the API request fails
    [Arguments]             ${dataset_data}         ${expected_status}=any                          ${params}=${None}
    Create api session

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    TRY
        ${endpoint}=            Datasets endpoint
        Log                     POST ${endpoint} with data: ${dataset_data}     DEBUG
        ${response}=            Safe Post Request         ${endpoint}             params=${params}        json=${dataset_data}    expected_status=${expected_status}
        Log                     Dataset creation response: status=${response.status_code}               DEBUG
        IF    ${response.status_code} in [200, 201]
            ${response_json}=       Set Variable            ${response.json()}
            ${dataset_id}=      Get From Dictionary     ${response_json}        id
            ${dataset_name}=    Get From Dictionary     ${response_json}        name
            Log                     Created dataset ${dataset_id} (${dataset_name})                         INFO
        END
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to create dataset: ${error}              ERROR
        FAIL                    Dataset creation failed: ${error}
    END

Upload dataset
    [Documentation]    Upload a new dataset from a JSONL file.
    ...
    ...    Args:
    ...    jsonl_file_path (str): Path to the JSONL file to upload
    ...    name (str): Name of the dataset
    ...    description (str): Optional description
    ...    dataset_type (str): Optional DatasetType
    ...    params (dict): Optional additional parameters for the request
    ...
    ...    Returns:
    ...    response: API response containing the created dataset
    ...
    ...    Raises:
    ...    HTTPError: If dataset upload fails
    ...    IOError: If the JSONL file cannot be read
    [Arguments]             ${jsonl_file_path}      ${name}                 ${description}=${None}                          ${params}=${None}       ${dataset_type}=${None}                         ${expected_status}=any

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    # Ensure the file exists and get content
    File Should Exist       ${jsonl_file_path}      msg=JSONL file not found: ${jsonl_file_path}
    ${jsonl_content}=       Get Binary File         ${jsonl_file_path}
    # Prepare form data
    ${data}=                Create Dictionary       name=${name}
    IF    $description is not None    Set To Dictionary    ${data}    description=${description}
    IF    $dataset_type is not None    Set To Dictionary    ${data}    type=${dataset_type}

    # Prepare file data for multipart upload (following the charts pattern)
    @{jsonl_file}=          Create List             data.jsonl              ${jsonl_content}
    &{files}=               Create Dictionary       jsonl=${jsonl_file}

    ${endpoint}=            Datasets endpoint       action=upload
    ${access_token}=        Authorization token
    &{headers}=             Create Dictionary       Authorization=Bearer ${access_token}

    Log                     POST ${endpoint} with data: ${data}             DEBUG
    ${response}=            POST                    ${endpoint}             headers=${headers}      data=${data}            files=${files}          expected_status=${expected_status}              params=${params}
    Log                     Upload dataset response: status=${response.status_code}                 DEBUG
    IF    ${response.status_code} in [200, 201]
        ${response_json}=       Set Variable            ${response.json()}
        ${dataset_id}=      Get From Dictionary     ${response_json}        id
        ${dataset_name}=    Get From Dictionary     ${response_json}        name
        Log                     Uploaded dataset ${dataset_id} (${dataset_name})                         INFO
    END
    RETURN                  ${response}

Get dataset
    [Documentation]    Retrieve a specific dataset by ID
    ...
    ...    Args:
    ...    dataset_id (str): UUID of the dataset to retrieve
    ...
    ...    Return:
    ...    response: API response containing the dataset details
    ...
    ...    Raise:
    ...    HTTPError: If the dataset is not found or request fails
    [Arguments]             ${dataset_id}           ${expected_status}=any                          ${project_id}=${TEST_PROJECT_ID}
    Create api session

    IF    $project_id == $None
        FAIL                    project_id cannot be None when calling Get dataset
    END
    ${params}=              Create Dictionary       project_id=${project_id}

    TRY
        ${endpoint}=            Datasets endpoint       ${dataset_id}
        Log                     GET ${endpoint} with params: ${params}          DEBUG
        ${response}=            Safe Get Request          ${endpoint}             expected_status=${expected_status}              params=${params}
        Log                     Get dataset response: status=${response.status_code}                    DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_detail}=        Set variable            ${EMPTY}
        TRY
            ${error_text}=          Set variable            ${error.response.text}
            ${error_detail}=        Set variable            \nStatus code: ${error.response.status_code}\nResponse: ${error_text}
        EXCEPT
            ${error_detail}=        Set variable            \nNo additional error details available.
        END
        ${error_msg}=           Set variable            Failed to get dataset ${dataset_id}: ${error}${error_detail}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    Dataset retrieval failed: ${error}${error_detail}
    END

List datasets
    [Documentation]    List datasets with optional filtering.
    ...
    ...    Args:
    ...    type (str, optional): Filter by DatasetType (e.g., Finetuning, Evaluation)
    ...    name (str, optional): Filter by dataset name (exact match)
    ...
    ...    Returns:
    ...    response: API response containing list of datasets
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]             ${type}=${None}         ${name}=${None}         ${expected_status}=any                          ${params}=${None}
    Create api session

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    IF    "${type}" != "${None}"    Set to dictionary    ${params}    type=${type}
    IF    "${name}" != "${None}"    Set to dictionary    ${params}    name=${name}

    TRY
        ${endpoint}=            Datasets endpoint
        Log                     GET ${endpoint} with params: ${params}          DEBUG
        ${response}=            Safe Get Request          ${endpoint}             params=${params}        expected_status=${expected_status}
        Log                     List datasets response: status=${response.status_code}                  DEBUG
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to list datasets: ${error}               ERROR
        FAIL                    Dataset listing failed: ${error}
    END

List datasets with type filter
    [Documentation]    Retrieves datasets filtered by the specified type
    [Arguments]             ${dataset_type}         ${params}=${None}
    ${endpoint}=            Datasets endpoint

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    Set To Dictionary       ${params}               type=${dataset_type}
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             params=${params}        expected_status=any
    Set test variable       ${response}             ${response}
    RETURN                  ${response}

List datasets with name filter
    [Documentation]    Retrieves datasets filtered by the specified name
    [Arguments]             ${name}                 ${params}=${None}
    ${endpoint}=            Datasets endpoint

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    Set To Dictionary       ${params}               name=${name}
    ${response}=            GET On Session          ${API_SESSION}          ${endpoint}             params=${params}        expected_status=any
    Set test variable       ${response}             ${response}
    RETURN                  ${response}

Modify dataset
    [Documentation]    Update an existing dataset.
    ...
    ...    Args:
    ...    dataset_id (str): UUID of the dataset to modify
    ...    dataset_data (dict): Updated dataset parameters (e.g., name, description)
    ...    params (dict, optional): Query parameters (e.g., for project_id)
    ...
    ...    Returns:
    ...    response: API response containing the updated dataset
    ...
    ...    Raises:
    ...    HTTPError: If the dataset is not found or update fails
    [Arguments]             ${dataset_id}           ${dataset_data}         ${expected_status}=any                          ${params}=${None}
    Create API session

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    TRY
        ${endpoint}=            Datasets endpoint       ${dataset_id}
        Log                     PUT ${endpoint} with data: ${dataset_data}      DEBUG
        ${response}=            Safe Put Request          ${endpoint}             params=${params}        json=${dataset_data}    expected_status=${expected_status}
        Log                     Modify dataset response: status=${response.status_code}                 DEBUG
        IF    ${response.status_code} == 200
            Log                     Modified dataset ${dataset_id}  INFO
        END
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to modify dataset ${dataset_id}: ${error} ERROR
        FAIL                    Dataset modification failed: ${error}
    END

Delete dataset
    [Documentation]    Delete a specific dataset.
    ...
    ...    Args:
    ...    dataset_id (str): UUID of the dataset to delete
    ...    delete_from_storage (bool): Whether to delete from S3 as well
    ...    params (dict, optional): Query parameters (e.g., for project_id)
    ...
    ...    Returns:
    ...    response: API response (contains deletion status)
    ...
    ...    Raises:
    ...    HTTPError: If the dataset is not found or deletion fails
    [Arguments]             ${dataset_id}           ${delete_from_storage}=${False}                 ${expected_status}=any                          ${params}=${None}
    Create api session

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    TRY
        ${endpoint}=            Datasets endpoint       ${dataset_id}
        Set To Dictionary       ${params}               delete_from_storage=${delete_from_storage}
        Log                     DELETE ${endpoint} with params: ${params}       DEBUG
        ${response}=            Safe Delete Request       ${endpoint}             params=${params}        expected_status=${expected_status}
        Log                     Delete dataset response: status=${response.status_code}                 DEBUG
        IF    ${response.status_code} == 204
            Log                     Deleted dataset ${dataset_id}   INFO
        END
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to delete dataset ${dataset_id} (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    ${error_msg}
    END

Batch delete datasets
    [Documentation]    Delete multiple datasets in a batch.
    ...
    ...    Args:
    ...    dataset_ids (list): List of dataset UUIDs to delete
    ...
    ...    Returns:
    ...    response: API response containing deletion status
    ...
    ...    Raises:
    ...    HTTPError: If the request fails
    [Arguments]             ${dataset_ids}          ${expected_status}=any                          ${params}=${None}
    Create api session

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    TRY
        ${endpoint}=            Datasets endpoint       action=delete
        ${data}=                Create dictionary       ids=${dataset_ids}
        Log                     POST ${endpoint} with data: ${data}             DEBUG
        ${response}=            Safe Post Request         ${endpoint}             json=${data}            expected_status=${expected_status}              params=${params}
        Log                     Batch delete datasets response: status=${response.status_code}         DEBUG
        IF    ${response.status_code} in [200, 204]
            ${count}=               Get Length              ${dataset_ids}
            Log                     Batch deleted ${count} datasets         INFO
        END
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to batch delete datasets (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    ${error_msg}
    END

Download dataset
    [Documentation]    Download the content of a specific dataset.
    ...
    ...    Args:
    ...    dataset_id (str): UUID of the dataset to download
    ...    params (dict, optional): Query parameters (e.g., for project_id)
    ...
    ...    Returns:
    ...    response: API response containing the dataset file content
    ...
    ...    Raises:
    ...    HTTPError: If the dataset is not found or download fails
    [Arguments]             ${dataset_id}           ${expected_status}=any                          ${params}=${None}
    Create api session

    # Initialize params with project_id if not provided
    IF    $params == $None
        ${params}=              Create Dictionary       project_id=${TEST_PROJECT_ID}
    END

    TRY
        ${endpoint}=            Datasets endpoint       ${dataset_id}           download
        Log                     GET ${endpoint}         DEBUG
        ${response}=            Safe Get Request          ${endpoint}             params=${params}        expected_status=${expected_status}
        Log                     Download dataset response: status=${response.status_code}               DEBUG
        IF    ${response.status_code} == 200
            Log                     Downloaded dataset ${dataset_id}        INFO
        END
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to download dataset ${dataset_id} (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    ${error_msg}
    END

Get Allowed Methods For Dataset Endpoint
    [Documentation]    Sends an OPTIONS request to a dataset endpoint and logs the Allow header.
    [Arguments]             ${dataset_id}           ${action}=${None}
    Create api session
    ${endpoint}=            Datasets endpoint       ${dataset_id}           ${action}
    TRY
        ${response}=            Options on session      ${API_SESSION}          ${endpoint}             expected_status=any
        Log                     OPTIONS response for ${endpoint}: Status=${response.status_code}
        IF    'Allow' in ${response.headers}
            ${allowed_methods}=     Set Variable            ${response.headers['Allow']}
            Log                     Allowed methods: ${allowed_methods}             console=yes
            RETURN                  ${allowed_methods}
        ELSE
            Log                     Allow header not found in OPTIONS response headers: ${response.headers}                         WARN
            RETURN                  ${None}
        END
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to send OPTIONS request to ${endpoint}: ${error}                 ERROR
        FAIL                    OPTIONS request failed: ${error}
    END

Verify Dataset API Methods
    [Documentation]    Checks if the running API supports PATCH for modify and GET for download.
    Create api session
    ${dummy_id}=            Set Variable            00000000-0000-0000-0000-000000000000
    ${endpoint_modify}=     Datasets endpoint       ${dummy_id}
    ${endpoint_download}=                           Datasets endpoint       ${dummy_id}             download

    ${patch_supported}=     Set Variable            ${False}
    ${get_supported}=       Set Variable            ${False}

    # Check Modify Endpoint
    TRY
        ${response_modify}=     Options on session      ${API_SESSION}          ${endpoint_modify}      expected_status=any
        Log                     OPTIONS for ${endpoint_modify}: Status=${response_modify.status_code}
        IF    'Allow' in ${response_modify.headers}
            Log                     Allow header for modify: ${response_modify.headers['Allow']}
            ${patch_supported}=     Run Keyword And Return Status                   Should Contain          ${response_modify.headers['Allow']}             PATCH
        ELSE
            Log                     Allow header missing for modify endpoint.       WARN
        END
    EXCEPT    *
        Log                     OPTIONS request failed for modify endpoint.     ERROR
    END

    # Check Download Endpoint
    TRY
        ${response_download}=                           Options on session      ${API_SESSION}          ${endpoint_download}    expected_status=any
        Log                     OPTIONS for ${endpoint_download}: Status=${response_download.status_code}
        IF    'Allow' in ${response_download.headers}
            Log                     Allow header for download: ${response_download.headers['Allow']}
            ${get_supported}=       Run Keyword And Return Status                   Should Contain          ${response_download.headers['Allow']}           GET
        ELSE
            Log                     Allow header missing for download endpoint.     WARN
        END
    EXCEPT    *
        Log                     OPTIONS request failed for download endpoint.                           ERROR
    END

    # Fail if methods not supported
    IF    not ${patch_supported}
        Fail                    API Check Failed: Running service at ${endpoint_modify} does not support PATCH (required for modify).
    END
    IF    not ${get_supported}
        Fail                    API Check Failed: Running service at ${endpoint_download} does not support GET (required for download).
    END
    Log                     API Method Check Passed: PATCH and GET supported as expected.           INFO
