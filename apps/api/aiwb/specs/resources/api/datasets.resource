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
Resource            resources/api/common.resource
Resource            resources/airm_projects.resource


*** Variables ***
${HEADERS_JSON}         Content-Type=application/json
${HEADERS_MULTIPART}    Content-Type=multipart/form-data


*** Keywords ***
Datasets endpoint
    [Documentation]    Return the full datasets endpoint url with namespace
    [Arguments]             ${namespace}            ${dataset_id}=${None}                           ${action}=${None}
    ${base_endpoint}=       Service API Endpoint    aiwb    endpoint=namespaces/${namespace}/datasets
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
    [Documentation]    DEPRECATED: Use Upload dataset instead.
    ...    The AIWB API only supports dataset creation via file upload (POST /upload).
    ...    This keyword is kept for backward compatibility but will fail if used.
    ...
    ...    Args:
    ...    dataset_data (dict): Dataset creation parameters (NOT SUPPORTED)
    ...    namespace (str): Namespace for the request
    ...
    ...    Return:
    ...    response: API response (will be 404 or 405 - endpoint doesn't exist)
    ...
    ...    Raise:
    ...    HTTPError: Method not supported by AIWB API
    [Arguments]             ${dataset_data}         ${namespace}            ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=            Datasets endpoint       namespace=${namespace}
    Log                     POST ${endpoint} with data: ${dataset_data} - NOTE: This endpoint does not exist in AIWB API!     WARN
    ${response}=            Safe Post Request         ${endpoint}             json=${dataset_data}    expected_status=${expected_status}
    Log                     Dataset creation response: status=${response.status_code}               DEBUG
    IF    ${response.status_code} in [200, 201]
        ${response_json}=       Set Variable            ${response.json()}
        ${dataset_id}=      Get From Dictionary     ${response_json}        id
        ${dataset_name}=    Get From Dictionary     ${response_json}        name
        Log                     Created dataset ${dataset_id} (${dataset_name})                         INFO
    END
    RETURN                  ${response}

Upload dataset
    [Documentation]    Upload a new dataset from a JSONL file.
    ...
    ...    Args:
    ...    jsonl_file_path (str): Path to the JSONL file to upload
    ...    name (str): Name of the dataset
    ...    description (str): Optional description
    ...    dataset_type (str): Optional DatasetType
    ...    namespace (str): Namespace for the request
    ...
    ...    Returns:
    ...    response: API response containing the created dataset
    ...
    ...    Raises:
    ...    HTTPError: If dataset upload fails
    ...    IOError: If the JSONL file cannot be read
    [Arguments]             ${jsonl_file_path}      ${name}                 ${namespace}            ${description}=${None}                          ${dataset_type}=${None}                         ${expected_status}=any

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

    ${endpoint}=            Datasets endpoint       action=upload           namespace=${namespace}
    ${access_token}=        Authorization token
    &{headers}=             Create Dictionary       Authorization=Bearer ${access_token}

    Log                     POST ${endpoint} with data: ${data}             DEBUG
    ${response}=            POST                    ${endpoint}             headers=${headers}      data=${data}            files=${files}          expected_status=${expected_status}
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
    ...    namespace (str): Namespace for the request
    ...
    ...    Return:
    ...    response: API response containing the dataset details
    ...
    ...    Raise:
    ...    HTTPError: If the dataset is not found or request fails
    [Arguments]             ${dataset_id}           ${namespace}            ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=            Datasets endpoint       namespace=${namespace}    dataset_id=${dataset_id}
    Log                     GET ${endpoint}         DEBUG
    ${response}=            Safe Get Request          ${endpoint}             expected_status=${expected_status}
    Log                     Get dataset response: status=${response.status_code}                    DEBUG
    RETURN                  ${response}

List datasets
    [Documentation]    List datasets with optional filtering.
    ...
    ...    Args:
    ...    type (str, optional): Filter by DatasetType (e.g., Fine-tuning, Evaluation)
    ...    name (str, optional): Filter by dataset name (exact match)
    ...    namespace (str): Namespace for the request
    ...
    ...    Returns:
    ...    response: API response containing DatasetsResponse with "data" key containing list of datasets
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]             ${namespace}            ${type}=${None}         ${name}=${None}         ${expected_status}=any
    Create api session    aiwb

    ${params}=              Create Dictionary

    IF    "${type}" != "${None}"    Set to dictionary    ${params}    type=${type}
    IF    "${name}" != "${None}"    Set to dictionary    ${params}    name=${name}

    ${endpoint}=            Datasets endpoint       namespace=${namespace}
    Log                     GET ${endpoint} with params: ${params}          DEBUG
    ${response}=            Safe Get Request          ${endpoint}             params=${params}        expected_status=${expected_status}
    Log                     List datasets response: status=${response.status_code}                  DEBUG
    IF    ${response.status_code} == 200
        ${response_json}=       Set Variable            ${response.json()}
        ${datasets}=        Get From Dictionary     ${response_json}        data
        ${count}=           Get Length              ${datasets}
        Log                     Listed ${count} datasets                INFO
    END
    RETURN                  ${response}

List datasets with type filter
    [Documentation]    Retrieves datasets filtered by the specified type
    [Arguments]             ${dataset_type}         ${namespace}
    Create api session    aiwb
    ${endpoint}=            Datasets endpoint       namespace=${namespace}

    ${params}=              Create Dictionary       type=${dataset_type}
    ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=any
    RETURN                  ${response}

List datasets with name filter
    [Documentation]    Retrieves datasets filtered by the specified name
    [Arguments]             ${name}                 ${namespace}
    Create api session    aiwb
    ${endpoint}=            Datasets endpoint       namespace=${namespace}

    ${params}=              Create Dictionary       name=${name}
    ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=any
    RETURN                  ${response}

Modify dataset
    [Documentation]    NOT SUPPORTED: The AIWB API does not support dataset modification.
    ...    This keyword is kept for backward compatibility but will always fail.
    ...    The API has no PUT/PATCH endpoint for datasets - they are immutable after creation.
    ...
    ...    Args:
    ...    dataset_id (str): UUID of the dataset to modify
    ...    dataset_data (dict): Updated dataset parameters (NOT SUPPORTED)
    ...    namespace (str): Namespace for the request
    ...
    ...    Returns:
    ...    response: API response (will be 404 or 405 - endpoint doesn't exist)
    ...
    ...    Raises:
    ...    HTTPError: Method not supported by AIWB API
    [Arguments]             ${dataset_id}           ${dataset_data}         ${namespace}            ${expected_status}=any
    Create API session    aiwb

    ${endpoint}=            Datasets endpoint       namespace=${namespace}    dataset_id=${dataset_id}
    Log                     PUT ${endpoint} with data: ${dataset_data} - NOTE: This endpoint does not exist in AIWB API!      WARN
    ${response}=            Safe Put Request          ${endpoint}             json=${dataset_data}    expected_status=${expected_status}
    Log                     Modify dataset response: status=${response.status_code}                 DEBUG
    IF    ${response.status_code} == 200
        Log                     Modified dataset ${dataset_id}  INFO
    END
    RETURN                  ${response}

Delete dataset
    [Documentation]    Delete a specific dataset.
    ...
    ...    Args:
    ...    dataset_id (str): UUID of the dataset to delete
    ...    delete_from_storage (bool): Whether to delete from S3 as well
    ...    namespace (str): Namespace for the request
    ...
    ...    Returns:
    ...    response: API response (contains deletion status)
    ...
    ...    Raises:
    ...    HTTPError: If the dataset is not found or deletion fails
    [Arguments]             ${dataset_id}           ${namespace}            ${delete_from_storage}=${False}                 ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=            Datasets endpoint       namespace=${namespace}    dataset_id=${dataset_id}
    Log                     DELETE ${endpoint}      DEBUG
    ${response}=            Safe Delete Request       ${endpoint}             expected_status=${expected_status}
    Log                     Delete dataset response: status=${response.status_code}                 DEBUG
    IF    ${response.status_code} == 204
        Log                     Deleted dataset ${dataset_id}   INFO
    END
    RETURN                  ${response}

Batch delete datasets
    [Documentation]    Delete multiple datasets in a batch.
    ...
    ...    Args:
    ...    dataset_ids (list): List of dataset UUIDs to delete
    ...    namespace (str): Namespace for the request
    ...
    ...    Returns:
    ...    response: API response with status 200 containing list of deleted UUIDs
    ...
    ...    Raises:
    ...    HTTPError: If the request fails or any dataset is not found
    [Arguments]             ${dataset_ids}          ${namespace}            ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=            Datasets endpoint       action=delete           namespace=${namespace}
    ${data}=                Create dictionary       ids=${dataset_ids}
    Log                     POST ${endpoint} with data: ${data}             DEBUG
    ${response}=            Safe Post Request         ${endpoint}             json=${data}            expected_status=${expected_status}
    Log                     Batch delete datasets response: status=${response.status_code}         DEBUG
    IF    ${response.status_code} == 200
        ${count}=               Get Length              ${dataset_ids}
        Log                     Batch deleted ${count} datasets         INFO
    END
    RETURN                  ${response}

Download dataset
    [Documentation]    Download the content of a specific dataset.
    ...
    ...    Args:
    ...    dataset_id (str): UUID of the dataset to download
    ...    namespace (str): Namespace for the request
    ...
    ...    Returns:
    ...    response: API response containing the dataset file content
    ...
    ...    Raises:
    ...    HTTPError: If the dataset is not found or download fails
    [Arguments]             ${dataset_id}           ${namespace}            ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=            Datasets endpoint       namespace=${namespace}    dataset_id=${dataset_id}    action=download
    Log                     GET ${endpoint}         DEBUG
    ${response}=            Safe Get Request          ${endpoint}             expected_status=${expected_status}
    Log                     Download dataset response: status=${response.status_code}               DEBUG
    IF    ${response.status_code} == 200
        Log                     Downloaded dataset ${dataset_id}        INFO
    END
    RETURN                  ${response}
