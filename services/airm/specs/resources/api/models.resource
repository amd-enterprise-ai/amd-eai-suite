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
Resource            aims.resource


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
        Log                     POST ${endpoint} with data: ${model_data}       DEBUG
        ${response}=            POST On Session         ${API_SESSION}          ${endpoint}             json=${model_data}      headers=${headers}      expected_status=${expected_status}              params=${params}
        Log                     Model creation response: status=${response.status_code}                 DEBUG
        IF    ${response.status_code} in [200, 201]
            ${response_json}=       Set Variable            ${response.json()}
            ${model_id}=        Get From Dictionary     ${response_json}        id
            ${model_name}=      Get From Dictionary     ${response_json}        name
            Log                     Created model ${model_id} (${model_name})     INFO
        END
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
    ...    cluster_id (str): Optional cluster ID to filter by (default: TEST_PROJECT_ID)
    ...
    ...    Return:
    ...    response: API response containing the model details
    ...
    ...    Raise:
    ...    HTTPError: If the model is not found or request fails
    [Arguments]             ${model_id}             ${expected_status}=any                          ${project_id}=${TEST_PROJECT_ID}
    Create api session
    # Verify that project_id is not None
    IF    $project_id == $None
        FAIL                    project_id cannot be None when calling Get model
    END

    # Create params dictionary with project_id
    ${params}=              Create Dictionary       project_id=${project_id}

    TRY
        Log                     GET /models/${model_id} with params: ${params}  DEBUG
        ${response}=            Safe Get Request          /models/${model_id}     expected_status=${expected_status}              params=${params}
        Log                     Get model response: status=${response.status_code}                      DEBUG
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
    ...                     ${sort_by}=created_at                           ${model_type}=${None}                           ${status}=${None}       ${expected_status}=any                          ${project_id}=${TEST_PROJECT_ID}
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

    IF    "${name}" != "${None}"    Set to dictionary    ${params}    name=${name}
    IF    "${model_type}" != "${None}"    Set to dictionary    ${params}    model_type=${model_type}
    IF    "${status}" != "${None}"    Set to dictionary    ${params}    onboarding_status=${status}

    TRY
        Log                     GET /models with params: ${params}              DEBUG
        ${response}=            Safe Get Request          /models                 params=${params}        expected_status=${expected_status}
        Log                     List models response: status=${response.status_code}                    DEBUG
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
    [Arguments]             ${model_id}             ${model_data}           ${expected_status}=any                          ${project_id}=${TEST_PROJECT_ID}
    Create api session
    IF    $project_id == $None
        # Verify that project_id is not None
        FAIL                    project_id cannot be None when calling Delete model
    END

    ${params}=              Create Dictionary       project_id=${project_id}
    TRY
        Log                     PUT /models/${model_id} with data: ${model_data}                        DEBUG
        ${response}=            PUT on session          ${API_SESSION}          /models/${model_id}     json=${model_data}      expected_status=${expected_status}              params=${params}
        Log                     Modify model response: status=${response.status_code}                   DEBUG
        IF    ${response.status_code} == 200
            Log                     Modified model ${model_id}      INFO
        END
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
    [Arguments]             ${model_id}             ${expected_status}=any                          ${project_id}=${TEST_PROJECT_ID}
    Create api session
    IF    $project_id == $None
        # Verify that project_id is not None
        FAIL                    project_id cannot be None when calling Delete model
    END

    ${params}=              Create Dictionary       project_id=${project_id}

    TRY
        Log                     DELETE /models/${model_id}      DEBUG
        ${response}=            Safe Delete Request       /models/${model_id}     expected_status=${expected_status}              params=${params}
        Log                     Delete model response: status=${response.status_code}                   DEBUG
        IF    ${response.status_code} == 204
            Log                     Deleted model ${model_id}       INFO
        END
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        ${error_msg}=           Set Variable            Failed to delete model ${model_id} (${error}). Response: ${error.response.text}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    ${error_msg}
    END

List models from external endpoint
    [Documentation]    Lists models from an external LLM inference endpoint
    ...    Makes an HTTP GET request to /v1/models to verify compatibility with standard LLM API format
    ...    Validates that the response contains a "data" field with the list of available models
    [Arguments]             ${external_host}        ${workload_id}=${None}    ${api_key}=${None}
    # Create a temporary session for the external endpoint
    ${session_name}=        Set Variable If         $workload_id is not None                aim_external_${workload_id}             aim_external_temp

    # Remove any trailing slashes from external_host
    ${clean_host}=          Evaluate                $external_host.rstrip('/')
    ${models_url}=          Set Variable            ${clean_host}/v1/models

    Create Session          ${session_name}         ${clean_host}           verify=False

    # Add Authorization header if API key provided
    ${headers}=             Create Dictionary
    IF    "${api_key}" != "${None}"
        Set To Dictionary   ${headers}              Authorization=Bearer ${api_key}
        Log                 Using API key authentication for external endpoint    DEBUG
    END

    ${response}=            GET On Session          ${session_name}         /v1/models              expected_status=200     timeout=180    headers=${headers}

    # Verify the response follows standard LLM API format with "data" field containing model list
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain 'data' field with model list

    # Extract and return the models list
    ${models}=              Get From Dictionary     ${json}                 data
    ${model_count}=         Get Length              ${models}
    RETURN                  ${models}

Model Supports Chat
    [Documentation]    Checks if a model supports chat interface based on metadata tags.
    ...                Returns ${True} if model supports chat, ${False} otherwise.
    ...                Uses the org.amd.silogen.model.tags field from AIM labels.
    [Arguments]    ${aim_id}

    # Get AIM details to check labels
    ${response}=    Get AIM    ${aim_id}    expected_status=200
    ${aim_data}=    Set Variable    ${response.json()}

    # Extract tags from labels
    ${labels}=    Get From Dictionary    ${aim_data}    labels
    ${tags}=    Get From Dictionary    ${labels}    org.amd.silogen.model.tags    default=${EMPTY}

    # Check if 'chat' is in the comma-separated tags
    ${supports_chat}=    Run Keyword And Return Status    Should Contain    ${tags}    chat

    Log    Model ${aim_id} tags: '${tags}' (supports chat: ${supports_chat})    INFO
    RETURN    ${supports_chat}

Run Chat Inference
    [Documentation]    Runs a chat inference request using /v1/chat/completions endpoint.
    ...                Uses OpenAI-compatible chat completions API format.
    ...                Tests instruction-following capability (chat models should follow instructions).
    [Arguments]    ${external_host}    ${model_id}    ${workload_id}    ${api_key}=${None}

    # Create session for external endpoint
    ${session_name}=    Set Variable If    $workload_id is not None    aim_external_${workload_id}    aim_external_temp
    ${clean_host}=    Evaluate    $external_host.rstrip('/')
    Create Session    ${session_name}    ${clean_host}    verify=False

    ${headers}=    Create Dictionary    Content-Type=application/json

    # Add Authorization header if API key provided
    IF    "${api_key}" != "${None}"
        Set To Dictionary    ${headers}    Authorization=Bearer ${api_key}
        Log    Using API key authentication for chat inference    DEBUG
    END

    # Chat API uses messages array - test instruction following
    ${messages}=    Create List
    ${user_message}=    Create Dictionary    role=user    content=Say hello and stop
    Append To List    ${messages}    ${user_message}

    ${body}=    Create Dictionary
    ...    model=${model_id}
    ...    messages=${messages}
    ...    max_tokens=20
    ...    temperature=0.7

    ${response}=    POST On Session    ${session_name}    /v1/chat/completions
    ...    headers=${headers}    json=${body}    expected_status=200    timeout=120
    ${json}=    Set Variable    ${response.json()}

    # Verify response structure (OpenAI chat completions format)
    Dictionary Should Contain Key    ${json}    choices    msg=Response should contain choices array
    ${choices}=    Get From Dictionary    ${json}    choices
    Should Be True    isinstance($choices, list)    msg=Choices should be a list
    Should Not Be Empty    ${choices}    msg=Choices array should not be empty

    ${first_choice}=    Get From List    ${choices}    0
    Dictionary Should Contain Key    ${first_choice}    message    msg=Choice should contain message
    ${message}=    Get From Dictionary    ${first_choice}    message
    Dictionary Should Contain Key    ${message}    content    msg=Message should contain content

    ${content}=    Get From Dictionary    ${message}    content
    Log    Chat inference response: ${content}    INFO

    # Verify the response contains "hello" (case-insensitive)
    ${content_lower}=    Convert To Lower Case    ${content}
    Should Contain    ${content_lower}    hello    msg=Chat model should respond with 'hello' when instructed to say hello

    RETURN    ${content}

Run Completion Inference
    [Documentation]    Runs a completion inference request using /v1/completions endpoint.
    ...                Uses OpenAI-compatible completions API format.
    ...                Tests text continuation capability with HTML structure.
    ...                Uses HTML prompt to avoid language-specific issues.
    [Arguments]    ${external_host}    ${model_id}    ${workload_id}    ${api_key}=${None}

    # Create session for external endpoint
    ${session_name}=    Set Variable If    $workload_id is not None    aim_external_${workload_id}    aim_external_temp
    ${clean_host}=    Evaluate    $external_host.rstrip('/')
    Create Session    ${session_name}    ${clean_host}    verify=False

    ${headers}=    Create Dictionary    Content-Type=application/json

    # Add Authorization header if API key provided
    IF    "${api_key}" != "${None}"
        Set To Dictionary    ${headers}    Authorization=Bearer ${api_key}
        Log    Using API key authentication for completion inference    DEBUG
    END

    # Completion API uses prompt string - test HTML continuation (language-agnostic)
    # Incomplete HTML list that should be continued with more list items
    ${body}=    Create Dictionary
    ...    model=${model_id}
    ...    prompt=<html><body><ul><li>Item 1</li><li>Item 2</li><li>Item
    ...    max_tokens=30
    ...    temperature=0.7

    ${response}=    POST On Session    ${session_name}    /v1/completions
    ...    headers=${headers}    json=${body}    expected_status=200    timeout=120
    ${json}=    Set Variable    ${response.json()}

    # Verify response structure (OpenAI completions format)
    Dictionary Should Contain Key    ${json}    choices    msg=Response should contain choices array
    ${choices}=    Get From Dictionary    ${json}    choices
    Should Be True    isinstance($choices, list)    msg=Choices should be a list
    Should Not Be Empty    ${choices}    msg=Choices array should not be empty

    ${first_choice}=    Get From List    ${choices}    0
    Dictionary Should Contain Key    ${first_choice}    text    msg=Choice should contain text field

    ${text}=    Get From Dictionary    ${first_choice}    text
    Log    Completion inference response: ${text}    INFO

    # Verify the response contains HTML tags (continuation of HTML structure)
    # Check for common HTML closing tags or continuation patterns
    ${text_lower}=    Convert To Lower Case    ${text}
    ${has_li}=    Run Keyword And Return Status    Should Contain    ${text_lower}    </li>
    ${has_ul}=    Run Keyword And Return Status    Should Contain    ${text_lower}    </ul>
    ${has_html_tag}=    Evaluate    ${has_li} or ${has_ul}
    Should Be True    ${has_html_tag}    msg=Completion model should continue HTML structure with tags like </li> or </ul>

    RETURN    ${text}

Delete AIRM API key
    [Documentation]    Deletes an API key.
    ...
    ...    Args:
    ...    api_key_id (str): ID of the API key to delete
    ...    project_id (str): Project ID for the operation
    ...
    ...    Return:
    ...    response: API response from the delete operation
    [Arguments]    ${api_key_id}    ${project_id}

    Create api session
    ${endpoint}=    Catalog endpoint    api-keys/${api_key_id}
    ${params}=    Create Dictionary    project_id=${project_id}

    Log    DELETE ${endpoint}    DEBUG
    ${response}=    DELETE On Session    ${API_SESSION}    ${endpoint}
    ...    params=${params}    expected_status=204

    IF    ${response.status_code} == 204
        Log    Deleted API key ${api_key_id}    INFO
    END

    RETURN    ${response}
