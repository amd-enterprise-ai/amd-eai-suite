# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API models endpoints.
...                 Provides direct API operation wrappers for the /models endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
...                 Higher-level test logic should use catalog_models.resource instead.
Library             RequestsLibrary
Library             Collections
Library             OperatingSystem
Resource            common.resource


*** Variables ***
${HEADERS}      Content-Type=application/json


*** Keywords ***
Models endpoint
    [Documentation]    Return the full models endpoint url
    ${endpoint}=            Catalog endpoint        models
    RETURN                  ${endpoint}


*** Keywords ***
Create model
    [Documentation]    Create a new model using the provided data
    ...
    ...    Args:
    ...    model_data (dict): Model creation parameters including:
    ...    - name: Model name
    ...    - type: Model type (BaseModel or MergedModel)
    ...    - model_weights_path: Optional path to weights
    ...    - base_model_id: Required for MergedModel type
    ...
    ...    Return:
    ...    response: API response containing the created model
    ...
    ...    Raise:
    ...    HTTPError: If the API request fails
    [Arguments]             ${model_data}           ${expected_status}=any                          ${params}=${None}
    Create api session
    TRY
        ${endpoint}=            Models endpoint
        ${headers}=             Create Dictionary       Content-Type=application/json
        ${response}=            POST On Session         ${API_SESSION}          ${endpoint}             json=${model_data}      headers=${headers}      expected_status=${expected_status}              params=${params}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to create model: ${error}                ERROR                   console=yes
        FAIL                    Model creation failed: ${error}
    END

Get model
    [Documentation]    Retrieve a specific model by ID
    ...
    ...    Args:
    ...    model_id (str): UUID of the model to retrieve
    ...    expected_status (str): Expected HTTP status code (default: any)
    ...    cluster_id (str): Optional cluster ID to filter by (default: CURRENT_PROJECT_ID)
    ...
    ...    Return:
    ...    response: API response containing the model details
    ...
    ...    Raise:
    ...    HTTPError: If the model is not found or request fails
    [Arguments]             ${model_id}             ${expected_status}=any                          ${project_id}=${CURRENT_PROJECT_ID}
    Create api session
    # Verify that project_id is not None
    IF    $project_id == $None
        FAIL                    project_id cannot be None when calling Get model
    END

    # Create params dictionary with project_id
    ${params}=              Create Dictionary       project_id=${project_id}

    TRY
        ${response}=            Get on session          ${API_SESSION}          /models/${model_id}     expected_status=${expected_status}              params=${params}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_detail}=        Set variable            ${EMPTY}

        # Extract more detailed error info when available
        TRY
            ${error_text}=          Set variable            ${error.response.text}
            ${error_detail}=        Set variable            \nStatus code: ${error.response.status_code}\nResponse: ${error_text}
        EXCEPT
            ${error_detail}=        Set variable            \nNo additional error details available.
        END

        ${error_msg}=           Set variable            Failed to get model ${model_id}: ${error}${error_detail}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    Model retrieval failed: ${error}${error_detail}
    END

Get models
    [Documentation]    List models with optional filtering.
    ...
    ...    Args:
    ...    page (int): Page number for pagination (default: 1)
    ...    page_size (int): Number of items per page (default: 10)
    ...    name (str, optional): Filter by model name
    ...    sort_order (str): Sort direction - asc or desc (default: desc)
    ...    sort_by (str): Field to sort by - created_at or name (default: created_at)
    ...    model_type (str, optional): Filter by BaseModel or Adapter
    ...    status (str, optional): Filter by deployment status
    ...
    ...    Returns:
    ...    response: API response containing list of models
    ...
    ...    Raises:
    ...    HTTPError: If the API request fails
    [Arguments]             ${page}=1               ${page_size}=10         ${name}=${None}         ${sort_order}=desc
    ...                     ${sort_by}=created_at                           ${model_type}=${None}                           ${status}=${None}       ${expected_status}=any                          ${project_id}=${CURRENT_PROJECT_ID}
    Create api session

    IF    $project_id == $None
        FAIL                    project_id cannot be None when calling Get model
    END

    ${params}=              Create dictionary
    ...                     page=${page}
    ...                     page_size=${page_size}
    ...                     sort_order=${sort_order}
    ...                     sort_by=${sort_by}
    ...                     project_id=${project_id}

    # Add optional filters if provided
    IF    "${name}" != "${None}"    Set to dictionary    ${params}    name=${name}
    IF    "${model_type}" != "${None}"    Set to dictionary    ${params}    model_type=${model_type}
    IF    "${status}" != "${None}"    Set to dictionary    ${params}    onboarding_status=${status}

    TRY
        ${response}=            Get on session          ${API_SESSION}          /models                 params=${params}        expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to list models: ${error}                 ERROR
        FAIL                    Model listing failed: ${error}
    END

Modify model
    [Documentation]    Update an existing model.
    ...
    ...    Args:
    ...    model_id (str): UUID of the model to modify
    ...    model_data (dict): Updated model parameters
    ...
    ...    Returns:
    ...    response: API response containing the updated model
    ...
    ...    Raises:
    ...    HTTPError: If the model is not found or update fails
    [Arguments]             ${model_id}             ${model_data}           ${expected_status}=any                          ${project_id}=${CURRENT_PROJECT_ID}
    Create API Session
    IF    $project_id == $None
        # Verify that project_id is not None
        FAIL                    project_id cannot be None when calling Delete model
    END

    ${params}=              Create Dictionary       project_id=${project_id}
    TRY
        ${response}=            PUT on session          ${API_SESSION}          /models/${model_id}     json=${model_data}      expected_status=${expected_status}              params=${params}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to modify model ${model_id}: ${error}    ERROR
        FAIL                    Model modification failed: ${error}
    END

Delete model
    [Documentation]    Delete a specific model.
    ...
    ...    Args:
    ...    model_id (str): UUID of the model to delete
    ...
    ...    Returns:
    ...    response: API response (empty on success)
    ...
    ...    Raises:
    ...    HTTPError: If the model is not found or deletion fails
    [Arguments]             ${model_id}             ${expected_status}=any                          ${project_id}=${CURRENT_PROJECT_ID}
    Create API Session
    IF    $project_id == $None
        # Verify that project_id is not None
        FAIL                    project_id cannot be None when calling Delete model
    END

    ${params}=              Create Dictionary       project_id=${project_id}

    TRY
        ${response}=            Delete on session       ${API_SESSION}          /models/${model_id}     expected_status=${expected_status}              params=${params}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to delete model ${model_id} (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR                   console=yes  # Keep console output for failures
        FAIL                    ${error_msg}
    END
