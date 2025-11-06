# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level model testing keywords.
...                 Provides business-logic level keywords for testing model operations.
...                 Uses the low-level API keywords from api/models.resource to implement
...                 higher-level testing scenarios. This is the main interface that
...                 test cases should use.
Resource            api/models.resource
Resource            api/finetuning.resource
Resource            catalog_projects.resource


*** Variables ***
${TEST_MODEL_ID}            ${None}
${TEST_MODEL_NAME}          test-model
${TEST_BASE_MODEL_ID}       ${None}
${TEST_DATA}                ${None}
@{CREATED_MODEL_IDS}        # List to track created model IDs for cleanup


*** Keywords ***
Valid base model data is prepared
    [Documentation]    Prepares valid base model test data
    # Ensure we have a project to work with
    Project exists in system

    ${random_suffix}=       Generate Random String                          8                       [LETTERS][NUMBERS]
    ${model_name}=          Set Variable            test-model-${random_suffix}
    Set Test Variable       ${TEST_MODEL_NAME}      ${model_name}

    ${model_data}=          Create Dictionary
    ...                     type=BaseModel
    ...                     name=${model_name}
    ...                     model_weights_path=default-bucket/models/${CURRENT_PROJECT_SLUG}/models/${model_name}
    ...                     canonical_name=${model_name}
    Set Test Variable       ${TEST_DATA}            ${model_data}

Valid merged model data is prepared
    [Documentation]    Prepares valid merged model test data
    [Arguments]             ${base_model_id}=${TEST_BASE_MODEL_ID}
    ${random_suffix}=       Generate Random String                          8                       [LETTERS][NUMBERS]
    ${model_name}=          Set Variable            test-merged-model-${random_suffix}
    Set Test Variable       ${TEST_MODEL_NAME}      ${model_name}

    Should Not Be Empty     ${base_model_id}        msg=base_model_id is required for merged model
    ${model_data}=          Create Dictionary
    ...                     type=MergedModel
    ...                     name=${model_name}
    ...                     model_weights_path=default-bucket/models/${CURRENT_PROJECT_SLUG}/models/${model_name}
    ...                     base_model_id=${base_model_id}
    Set Test Variable       ${TEST_DATA}            ${model_data}

Create model request is sent
    [Documentation]    Sends request to create a model using prepared test data and the project ID from catalog_projects.resource
    ${endpoint}=            Models endpoint
    ${query_params}=        Create Dictionary       project_id=${CURRENT_PROJECT_ID}
    ${response}=            Post on session         ${API_SESSION}          ${endpoint}             json=${TEST_DATA}       params=${query_params}
    Set Test Variable       ${response}             ${response}

    # Track created model ID for cleanup
    ${model_id}=            Get from dictionary     ${response.json()}      id
    Append To List          ${CREATED_MODEL_IDS}    ${model_id}
    Log                     Added model ${model_id} to cleanup list: ${CREATED_MODEL_IDS}           level=DEBUG

Base model exists in system
    [Documentation]    Creates a base model and stores its ID as a test variable
    ...    This is a precondition keyword that:
    ...    1. Prepares valid base model data
    ...    2. Creates the model via API
    ...    3. Stores the ID for later use in test variable
    Valid base model data is prepared
    Create model request is sent
    Response status should be 201

    ${model_id}=            Get from dictionary     ${response.json()}      id
    Set test variable       ${TEST_BASE_MODEL_ID}                           ${model_id}

    # Verify model was actually created
    ${verify_response}=     Get model               ${model_id}             expected_status=200
    Log                     Base model ${model_id} (${TEST_MODEL_NAME}) successfully created and verified

Base model for finetuning exists in system
    [Documentation]    Creates a base model for finetuning and stores its ID as a test variable
    ...    This is a precondition keyword that:
    ...    1. Prepares valid base model data
    ...    2. Creates the model via API
    ...    3. Stores the ID for later use in test variable
    ${response}=            Get models              name=TinyLlama/TinyLlama-1.1B-Chat-v1.0
    ${models}=              Set Variable            ${response.json()}
    Run Keyword If          not $models             Fail                    Existing Tiny Llama with name TinyLlama/TinyLlama-1.1B-Chat-v1.0 doesn't exist on the cluster
    ${model}=               Get from list           ${models}               0

    Log                     Base model ${model} successfully verified
    Set Test Variable       ${TEST_BASE_MODEL_ID}                           ${model['id']}

Model should exist in database with correct properties
    [Documentation]    Verify model exists in database with expected properties by comparing API response to database
    ${model_id}=            Get from dictionary     ${response.json()}      id
    ${db_response}=         Get model               ${model_id}             expected_status=200

    # Compare all fields between response and database
    ${response_json}=       Set variable            ${response.json()}
    ${db_json}=             Set variable            ${db_response.json()}

    # Log verification for debugging
    Log                     Verifying model ${model_id} database consistency                        level=INFO

    # Verify all fields match
    FOR    ${key}    IN    id    name    type    onboarding_status    model_weights_path    created_at    updated_at
        ${response_value}=      Get from dictionary     ${response_json}        ${key}
        ${db_value}=            Get from dictionary     ${db_json}              ${key}
        Should be equal         ${response_value}       ${db_value}
        ...                     Field ${key} does not match between response and database. API: "${response_value}", DB: "${db_value}"
    END

Response should contain base model reference
    [Documentation]    Verifies response contains reference to correct base model
    [Arguments]             ${expected_id}
    Dictionary should contain value                 ${response.json()}      ${expected_id}

Response should contain rank
    [Documentation]    Verifies response contains correct rank value
    [Arguments]             ${expected_rank}
    Dictionary should contain value                 ${response.json()}      ${expected_rank}

Adapter should be linked to correct base model
    [Documentation]    Verifies adapter is properly linked to its base model
    ${model_id}=            Get from dictionary     ${response.json()}      id
    ${db_response}=         Get model               ${model_id}
    Dictionary should contain key                   ${db_response.json()}                           base_model
    ${base_id}=             Get from dictionary     ${db_response.json()['base_model']}             id
    Should be equal         ${base_id}              ${TEST_BASE_MODEL_ID}

Multiple models exist in system
    [Documentation]    Creates multiple models of different types for testing
    [Arguments]             ${base_model_count}=2                           ${adapter_count}=2

    # Track created models for better reporting
    @{created_base_models}=                         Create list
    @{created_adapters}=    Create list
    Set test variable       ${CREATED_BASE_MODELS}                          ${created_base_models}
    Set test variable       ${CREATED_ADAPTERS}     ${created_adapters}

    Log                     Creating ${base_model_count} base models and ${adapter_count} adapters for testing

    # Create base models
    FOR    ${index}    IN RANGE    ${base_model_count}
        Log                     Creating base model ${index+1} of ${base_model_count}
        Valid base model data is prepared
        Create model request is sent
        Response status should be 201

        # Store the first base model ID for adapter creation
        ${model_id}=            Get from dictionary     ${response.json()}      id
        Append to list          ${CREATED_BASE_MODELS}                          ${model_id}

        IF    ${index} == 0
            Set test variable       ${TEST_BASE_MODEL_ID}                           ${model_id}
            Log                     Set base model ID for adapter creation: ${model_id}
        END
    END

    # Create adapters
    FOR    ${index}    IN RANGE    ${adapter_count}
        Log                     Creating adapter ${index+1} of ${adapter_count}

        # Verify we have a base model ID before attempting adapter creation
        Should not be empty     ${TEST_BASE_MODEL_ID}                           Cannot create adapter: No base model ID available

        Valid adapter data is prepared
        Create model request is sent
        Response status should be 201

        ${model_id}=            Get from dictionary     ${response.json()}      id
        Append to list          ${CREATED_ADAPTERS}     ${model_id}
    END

    Log                     Successfully created ${base_model_count} base models and ${adapter_count} adapters

List models request is sent
    [Documentation]    Sends request to list models with filters
    [Arguments]             ${model_type}=${None}                           ${status}=${None}       ${page}=1               ${page_size}=10
    ${response}=            Get Models              page=${page}            page_size=${page_size}                          model_type=${model_type}                        status=${status}
    Set Test Variable       ${response}             ${response}

Models with different states exist
    [Documentation]    Creates models in different states for testing stats
    [Arguments]             ${ready_count}=2        ${pending_count}=3      ${failed_count}=1

    # Track created models by status for better reporting
    @{ready_models}=        Create list
    @{pending_models}=      Create list
    @{failed_models}=       Create list
    Set test variable       ${READY_MODELS}         ${ready_models}
    Set test variable       ${PENDING_MODELS}       ${pending_models}
    Set test variable       ${FAILED_MODELS}        ${failed_models}

    Log                     Creating models with different states: ${ready_count} ready, ${pending_count} pending, ${failed_count} failed

    # Create ready models
    FOR    ${index}    IN RANGE    ${ready_count}
        Log                     Creating ready model ${index+1} of ${ready_count}
        Valid base model data is prepared
        Set to dictionary       ${TEST_DATA}            onboarding_status=ready
        Create model request is sent
        Response status should be 201

        ${model_id}=            Get from dictionary     ${response.json()}      id
        Append to list          ${READY_MODELS}         ${model_id}
    END

    # Create pending models (default state)
    FOR    ${index}    IN RANGE    ${pending_count}
        Log                     Creating pending model ${index+1} of ${pending_count}
        Valid base model data is prepared
        Create model request is sent
        Response status should be 201

        ${model_id}=            Get from dictionary     ${response.json()}      id
        Append to list          ${PENDING_MODELS}       ${model_id}
    END

    # Create failed models
    FOR    ${index}    IN RANGE    ${failed_count}
        Log                     Creating failed model ${index+1} of ${failed_count}
        Valid base model data is prepared
        Set to dictionary       ${TEST_DATA}            onboarding_status=failed
        Create model request is sent
        Response status should be 201

        ${model_id}=            Get from dictionary     ${response.json()}      id
        Append to list          ${FAILED_MODELS}        ${model_id}
    END

    # Count models for verification
    ${ready_created}=       Get length              ${READY_MODELS}
    ${pending_created}=     Get length              ${PENDING_MODELS}
    ${failed_created}=      Get length              ${FAILED_MODELS}

    # Verify we have the expected number of models
    Should be equal as integers                     ${ready_created}        ${ready_count}          msg=Expected ${ready_count} ready models but created ${ready_created}
    Should be equal as integers                     ${pending_created}      ${pending_count}        msg=Expected ${pending_count} pending models but created ${pending_created}
    Should be equal as integers                     ${failed_created}       ${failed_count}         msg=Expected ${failed_count} failed models but created ${failed_created}

    # Store counts for verification in test variables instead of suite variables
    Set test variable       ${EXPECTED_DEPLOYED}    ${ready_count}
    Set test variable       ${EXPECTED_PENDING}     ${pending_count}
    Set test variable       ${EXPECTED_INCOMPLETE}                          ${failed_count}
    ${total}=               Evaluate                ${ready_count}+${pending_count}+${failed_count}
    Set test variable       ${EXPECTED_TOTAL}       ${total}

    Log                     Successfully created models with different states: ${ready_count} ready, ${pending_count} pending, ${failed_count} failed

Get model stats request is sent
    [Documentation]    Sends request to get model statistics
    ${response}=            Get Models Stats
    Set Test Variable       ${response}             ${response}

Response should contain total models count
    [Documentation]    Verifies total models count in stats response
    Dictionary should contain key                   ${response.json()}      total_models
    ${total}=               Get from dictionary     ${response.json()}      total_models
    Should be equal as integers                     ${total}                ${EXPECTED_TOTAL}

Response should contain deployed models count
    [Documentation]    Verifies deployed models count in stats response
    Dictionary should contain key                   ${response.json()}      deployed_models
    ${deployed}=            Get from dictionary     ${response.json()}      deployed_models
    Should be equal as integers                     ${deployed}             ${EXPECTED_DEPLOYED}

Response should contain incomplete models count
    [Documentation]    Verifies incomplete models count in stats response
    Dictionary should contain key                   ${response.json()}      incomplete_models
    ${incomplete}=          Get from dictionary     ${response.json()}      incomplete_models
    Should be equal as integers                     ${incomplete}           ${EXPECTED_INCOMPLETE}

Model exists in system
    [Documentation]    Creates a model for modification testing and stores its ID as a test variable
    Valid base model data is prepared
    Create model request is sent
    Response status should be 201

    ${model_id}=            Get from dictionary     ${response.json()}      id
    Set test variable       ${TEST_MODEL_ID}        ${model_id}

    # Verify model was actually created by making a separate verification call
    ${response}=            Get model               ${model_id}             expected_status=200

Model with name "${name}" does not exist in system
    [Documentation]    Ensures a model with the given name does not exist in the system
    ...    If a model with the name exists, it will be deleted

    # List models with the given name to check if it exists
    ${response}=            Get Models              name=${name}
    ${models}=              Set Variable            ${response.json()}
    ${count}=               Get Length              ${models}

    # If models with this name exist, delete the first one found
    IF    ${count} > 0
        Log                     Found model with name "${name}" - will delete it                        level=INFO
        ${model_to_delete}=     Get From List           ${models}               0
        ${model_id}=            Get From Dictionary     ${model_to_delete}      id
        ${delete_response}=     Delete model            ${model_id}             expected_status=204

        # Verify the model was deleted
        ${verify_response}=     Get model               ${model_id}             expected_status=404
        Log                     Successfully deleted model with name "${name}" (ID: ${model_id})        level=INFO
    ELSE
        Log                     No model with name "${name}" exists - no deletion needed                level=INFO
    END

A model does not exist
    [Documentation]    Sets up a non-existent model ID for testing
    ${model_id}=            Evaluate                str(uuid.uuid4())       modules=uuid
    Set test variable       ${TEST_MODEL_ID}        ${model_id}

Modify model request is sent with name "${new_name}" and type "${type}"
    [Documentation]    Sends request to modify an existing model with new name and type
    ${model_data}=          Create dictionary       name=${new_name}        type=${type}
    ${response}=            Modify model            ${TEST_MODEL_ID}        ${model_data}
    Set test variable       ${response}             ${response}

Delete model request is sent
    [Documentation]    Sends a request to delete a model
    ${response}=            Delete model            ${TEST_MODEL_ID}
    Set test variable       ${response}             ${response}

Model name in database should be "${expected_name}"
    [Documentation]    Verifies model name is updated in database
    ${db_response}=         Get model               ${TEST_MODEL_ID}
    Response should contain "${expected_name}"

The model should not exist in database
    [Documentation]    Verifies the model no longer exists in database
    ${model_id}=            Set Variable            ${TEST_MODEL_ID}

    ${db_response}=         Get model               ${model_id}             expected_status=404

List models request is sent with type "${model_type}" and status "${status}"
    [Documentation]    Sends request to list models with type and status filters
    ${response}=            Get models              model_type=${model_type}                        status=${status}
    Set test variable       ${response}             ${response}

A finetune request is sent
    [Documentation]    Sends a finetune request using the base model data
    Should Not Be Empty     ${TEST_BASE_MODEL_ID}                           msg=Base model ID is required for finetuning.
    Should Not Be Empty     ${TEST_DATASET_ID}      msg=Dataset ID is required for finetuning.
    ${random_suffix}=       Generate random string                          8                       [LETTERS][NUMBERS]
    ${model_name}=          Set Variable            finetuned-model-${random_suffix}
    # Generate finetune data with correct model_weights_path format
    ${finetune_data}=       Create Dictionary
    ...                     name=${model_name}
    ...                     dataset_path=${TEST_DATASET_PATH}
    ...                     batch_size=16
    ...                     learning_rate=0.001
    ...                     epochs=5
    ...                     dataset_id=${TEST_DATASET_ID}
    ...                     model_weights_path=default-bucket/models/${CURRENT_PROJECT_SLUG}/models/${model_name}

    Log                     Sending finetune request for base model ID: ${TEST_BASE_MODEL_ID} with data: ${finetune_data}
    ${response}=            Send Finetune Request                           model_id=${TEST_BASE_MODEL_ID}                  finetune_data=${finetune_data}                  params=${QUERY_PARAMS}                          expected_status=202
    Set Test Variable       ${response}             ${response}
    Log                     message=Finetune request response: ${response.json()}                   level=DEBUG
    Set Test Variable       ${TEST_WORKLOAD_ID}     ${response.json()['id']}
    Set Test Variable       ${TEST_MANAGED_MODEL_ID}                        ${response.json()['model_id']}
    # Extract model_weights_path from the associated model object
    ${model_weights_path}=                          Get From Dictionary     ${response.json()['model']}                     model_weights_path
    Set Test Variable       ${MODEL_WEIGHTS_PATH}                           ${model_weights_path}

The merged model is retrieved
    [Documentation]    Retrieves the merged model using the model_id from the finetune request response.
    ${merged_model_id}=     Get From Dictionary     ${response.json()}      model_id
    Should Not Be Empty     ${merged_model_id}      msg=Merged model ID is required to retrieve the model.

    ${retrieved_response}=                          Get model               ${merged_model_id}      expected_status=200
    Set Test Variable       ${response}             ${retrieved_response}

The workflow is retrieved
    [Documentation]    Retrieves the workflow using the ID from the finetune request response.
    Should Not Be Empty     ${TEST_WORKLOAD_ID}     msg=Workflow ID is required to retrieve the workflow.
    ${retrieved_response}=                          Get menaged workload    ${TEST_WORKLOAD_ID}     expected_status=200     params=${QUERY_PARAMS}
    Set Test Variable       ${response}             ${retrieved_response}

Initialize Model Tracking
    [Documentation]    Resets the list of created models
    ...    This keyword should be used in a test suite setup to ensure
    ...    the tracking list starts empty for each test suite
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_MODEL_IDS}    ${empty_list}
    Log                     Model tracking initialized. CREATED_MODEL_IDS: ${CREATED_MODEL_IDS}     level=DEBUG

Register Model For Cleanup
    [Documentation]    Manually registers a model ID to be cleaned up later
    ...    Useful when models are created through methods that don't
    ...    automatically track them in the CREATED_MODEL_IDS list
    [Arguments]             ${model_id}
    Append To List          ${CREATED_MODEL_IDS}    ${model_id}
    Log                     Manually added model ${model_id} to cleanup list: ${CREATED_MODEL_IDS}                          level=DEBUG

Clean Up All Created Models
    [Documentation]    Deletes all models created during test execution
    ...    This keyword should be used in a test suite teardown to ensure
    ...    all models created during testing are cleaned up properly.
    ${count}=               Get Length              ${CREATED_MODEL_IDS}

    # Skip if no models were created or list is empty
    Return From Keyword If                          ${count} == 0           No models to clean up

    Log                     Cleaning up ${count} models: ${CREATED_MODEL_IDS}                       level=INFO

    # Delete each model individually
    FOR    ${model_id}    IN    @{CREATED_MODEL_IDS}
        TRY
            Log                     Deleting model ${model_id}                      level=INFO
            Delete model            model_id=${model_id}    expected_status=any     project_id=${CURRENT_PROJECT_ID}
            Log                     Successfully deleted model ${model_id}          level=INFO
        EXCEPT    AS    ${error}
            Log                     Failed to delete model ${model_id}: ${error}    level=WARN
        END
    END

    # Reset the list of created models
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_MODEL_IDS}    ${empty_list}
    Log                     Model cleanup complete. CREATED_MODEL_IDS reset to: ${CREATED_MODEL_IDS}                        level=INFO
