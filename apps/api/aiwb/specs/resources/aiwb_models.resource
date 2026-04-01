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
Resource            resources/api/workloads.resource
Resource            resources/airm_projects.resource
Resource            resources/common/resource_tracking.resource
Resource            aiwb_common.resource


*** Variables ***
${TEST_MODEL_ID}            ${None}
${TEST_MODEL_NAME}          test-model
${TEST_BASE_MODEL_ID}       ${None}
${TEST_MODEL_DATA}                ${None}
@{CREATED_MODEL_IDS}        # List to track created model IDs for cleanup


*** Keywords ***
Valid base model data is prepared
    [Documentation]    Prepares valid base model test data
    # Ensure we have a project to work with
    Project exists in system

    ${random_suffix}=       Generate Random String                          8                       [LETTERS][NUMBERS]
    ${model_name}=          Set Variable            test-model-${random_suffix}
    Set Test Variable       ${TEST_MODEL_NAME}      ${model_name}

    ${namespace}=           Get Project Namespace
    ${model_data}=          Create Dictionary
    ...                     type=BaseModel
    ...                     name=${model_name}
    ...                     model_weights_path=default-bucket/models/${namespace}/models/${model_name}
    ...                     canonical_name=${model_name}
    Set Test Variable       ${TEST_MODEL_DATA}            ${model_data}

Create model request is sent
    [Documentation]    Sends request to create a model using prepared test data and the project ID
    ${endpoint}=            Models endpoint
    ${query_params}=        Create Dictionary       project_id=${TEST_PROJECT_ID}
    ${response}=            Safe Post Request         ${endpoint}             json=${TEST_MODEL_DATA}       params=${query_params}
    Set Test Variable       ${TEST_RESPONSE}             ${response}

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

    ${model_id}=            Get from dictionary     ${TEST_RESPONSE.json()}      id
    Set test variable       ${TEST_BASE_MODEL_ID}                           ${model_id}

    # Verify model was actually created
    ${namespace}=           Get Project Namespace
    ${verify_response}=     Get model               ${model_id}             namespace=${namespace}   expected_status=200
    Log                     Base model ${model_id} (${TEST_MODEL_NAME}) successfully created and verified                         INFO

Multiple models exist in system
    [Documentation]    Creates multiple models of different types for testing
    [Arguments]             ${base_model_count}=2                           ${adapter_count}=2

    @{created_base_models}=                         Create list
    @{created_adapters}=    Create list

    Log                     Creating ${base_model_count} base models and ${adapter_count} adapters for testing           INFO

    FOR    ${index}    IN RANGE    ${base_model_count}
        Log                     Creating base model ${index+1} of ${base_model_count}               DEBUG
        Valid base model data is prepared
        Create model request is sent
        Response status should be 201

        ${model_id}=            Get from dictionary     ${TEST_RESPONSE.json()}      id
        Append to list          ${created_base_models}                          ${model_id}

        IF    ${index} == 0
            Set test variable       ${TEST_BASE_MODEL_ID}                           ${model_id}
            Log                     Set base model ID for adapter creation: ${model_id}             DEBUG
        END
    END

    FOR    ${index}    IN RANGE    ${adapter_count}
        Log                     Creating adapter ${index+1} of ${adapter_count}                 DEBUG

        # Verify we have a base model ID before attempting adapter creation
        Should not be empty     ${TEST_BASE_MODEL_ID}                           Cannot create adapter: No base model ID available

        Valid adapter data is prepared
        Create model request is sent
        Response status should be 201

        ${model_id}=            Get from dictionary     ${TEST_RESPONSE.json()}      id
        Append to list          ${created_adapters}     ${model_id}
    END

    Log                     Successfully created ${base_model_count} base models and ${adapter_count} adapters               INFO

List models request is sent
    [Documentation]    Sends request to list models with filters
    [Arguments]             ${model_type}=${None}                           ${status}=${None}       ${page}=1               ${page_size}=10
    ${namespace}=           Get Project Namespace
    ${response}=            Get Models              namespace=${namespace}   page=${page}            page_size=${page_size}                          model_type=${model_type}                        status=${status}
    Set Test Variable       ${TEST_RESPONSE}             ${response}

Model exists in system
    [Documentation]    Creates a model for modification testing and stores its ID as a test variable
    Valid base model data is prepared
    Create model request is sent
    Response status should be 201

    ${model_id}=            Get from dictionary     ${TEST_RESPONSE.json()}      id
    Set test variable       ${TEST_MODEL_ID}        ${model_id}

    # Verify model was actually created by making a separate verification call
    ${namespace}=           Get Project Namespace
    ${response}=            Get model               ${model_id}             namespace=${namespace}   expected_status=200

Model with name "${name}" does not exist in system
    [Documentation]    Ensures a model with the given name does not exist in the system
    ...    If a model with the name exists, it will be deleted

    ${namespace}=           Get Project Namespace
    # List models with the given name to check if it exists
    ${response}=            Get Models              namespace=${namespace}   name=${name}
    ${models}=              Set Variable            ${response.json()}
    ${count}=               Get Length              ${models}

    # If models with this name exist, delete the first one found
    IF    ${count} > 0
        Log                     Found model with name "${name}" - will delete it                        INFO
        ${model_to_delete}=     Get From List           ${models}               0
        ${model_id}=            Get From Dictionary     ${model_to_delete}      id
        ${delete_response}=     Delete model            ${model_id}             namespace=${namespace}   expected_status=204

        # Verify the model was deleted
        ${verify_response}=     Get model               ${model_id}             namespace=${namespace}   expected_status=404
        Log                     Successfully deleted model with name "${name}" (ID: ${model_id})        INFO
    ELSE
        Log                     No model with name "${name}" exists - no deletion needed                DEBUG
    END

A model does not exist
    [Documentation]    Sets up a non-existent model ID for testing
    ${model_id}=            Evaluate                str(uuid.uuid4())       modules=uuid
    Set test variable       ${TEST_MODEL_ID}        ${model_id}

Modify model request is sent with name "${new_name}" and type "${type}"
    [Documentation]    Sends request to modify an existing model with new name and type
    ${namespace}=           Get Project Namespace
    ${model_data}=          Create dictionary       name=${new_name}        type=${type}
    ${response}=            Modify model            ${TEST_MODEL_ID}        ${model_data}           namespace=${namespace}
    Set test variable       ${TEST_RESPONSE}             ${response}

Delete model request is sent
    [Documentation]    Sends a request to delete a model
    ${namespace}=           Get Project Namespace
    ${response}=            Delete model            ${TEST_MODEL_ID}        namespace=${namespace}
    Set test variable       ${TEST_RESPONSE}             ${response}

Model name in database should be "${expected_name}"
    [Documentation]    Verifies model name is updated in database
    ${namespace}=           Get Project Namespace
    ${db_response}=         Get model               ${TEST_MODEL_ID}        namespace=${namespace}
    Response should contain "${expected_name}"

The model should not exist in database
    [Documentation]    Verifies the model no longer exists in database
    ${model_id}=            Set Variable            ${TEST_MODEL_ID}

    ${namespace}=           Get Project Namespace
    ${db_response}=         Get model               ${model_id}             namespace=${namespace}   expected_status=404

List models request is sent with type "${model_type}" and status "${status}"
    [Documentation]    Sends request to list models with type and status filters
    ${namespace}=           Get Project Namespace
    ${response}=            Get models              namespace=${namespace}   model_type=${model_type}                        status=${status}
    Set test variable       ${TEST_RESPONSE}             ${response}

Finetune request is sent with data
    [Documentation]    Sends a finetune request with provided data (may be invalid for error testing).
    ...                Sets TEST_RESPONSE for status verification.
    [Arguments]             ${model_name}           ${finetune_data}
    ${namespace}=           Get Project Namespace
    ${response}=            Finetune model          ${model_name}           ${finetune_data}
    ...                     namespace=${namespace}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

A finetune request is sent
    [Documentation]    Sends a finetune request using a HuggingFace model name.
    ...                Uses namespace-based endpoint: /namespaces/{namespace}/models/{model_id}/finetune
    ...
    ...                Schema fields (from FinetuneCreate):
    ...                - name: Name of the finetuning job and resulting model
    ...                - dataset_id: UUID of the dataset
    ...                - epochs: Number of epochs (default: 1)
    ...                - learning_rate: Learning rate (default: 1.41421)
    ...                - batch_size: Batch size (default: 2)
    ...                - hf_token_secret_name: Optional HF token secret name
    Should Not Be Empty     ${TEST_DATASET_ID}      msg=Dataset ID is required for finetuning.
    ${namespace}=           Get Project Namespace

    ${random_suffix}=       Generate random string                          8                       [LETTERS][NUMBERS]
    ${model_name}=          Set Variable            finetuned-model-${random_suffix}
    # Use HuggingFace model name directly as model_id in the endpoint
    ${base_model_name}=     Set Variable            TinyLlama/TinyLlama-1.1B-Chat-v1.0

    # Generate finetune data matching FinetuneCreate schema (minimal defaults for fast execution)
    ${finetune_data}=       Create Dictionary
    ...                     name=${model_name}
    ...                     dataset_id=${TEST_DATASET_ID}
    ...                     batch_size=2
    ...                     learning_rate=1.41421
    ...                     epochs=1

    Log                     Sending finetune request for HuggingFace model: ${base_model_name}           DEBUG
    ${response}=            Finetune model          ${base_model_name}      ${finetune_data}
    ...                     expected_status=202     namespace=${namespace}
    Set Test Variable       ${TEST_RESPONSE}             ${response}
    Log                     Finetune request response: ${response.json()}                   DEBUG

    # The response should be a ModelResponse containing the created model
    ${response_data}=       Set Variable            ${response.json()}
    ${model_id}=            Get From Dictionary     ${response_data}        id
    Set Test Variable       ${TEST_MANAGED_MODEL_ID}                        ${model_id}

    # Store model for cleanup
    Append To List          ${CREATED_MODEL_IDS}    ${model_id}
    Log                     Added finetuned model ${model_id} to cleanup list              DEBUG

Clean Up All Created Models
    [Documentation]    Deletes all models created during test execution
    ...    This keyword should be used in a test suite teardown to ensure
    ...    all models created during testing are cleaned up properly.
    ...    Note: Models require project_id for deletion, so this has a special implementation
    ${count}=               Get Length              ${CREATED_MODEL_IDS}

    # Skip if no models were created or list is empty
    IF    ${count} == 0
        Log                     No models to clean up                           DEBUG
        RETURN
    END

    Log                     Cleaning up ${count} models: ${CREATED_MODEL_IDS}                       INFO

    ${namespace}=           Get Project Namespace
    # Delete each model individually
    FOR    ${model_id}    IN    @{CREATED_MODEL_IDS}
        TRY
            Log                     Deleting model ${model_id}                      DEBUG
            Delete model            model_id=${model_id}    namespace=${namespace}   expected_status=any     project_id=${TEST_PROJECT_ID}
        EXCEPT    AS    ${error}
            Log                     Failed to delete model ${model_id}: ${error}    WARN
        END
    END

    # Reset the list of created models
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_MODEL_IDS}    ${empty_list}
    Log                     Model cleanup complete. CREATED_MODEL_IDS reset to: ${CREATED_MODEL_IDS}                        INFO

A finetuning workload exists
    [Documentation]    Idempotent: ensures a finetuning workload exists.
    ...    Sets TEST_FINETUNING_WORKLOAD_ID and TEST_MANAGED_MODEL_ID as test variables.
    ...    Uses suite-level cache to avoid re-querying the API across tests, but always
    ...    sets test-level variables so each test has explicit preconditions.
    # Check suite cache first — avoids redundant API queries across tests
    ${cached_workload_id}=    Get Variable Value    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${None}
    ${cached_model_id}=       Get Variable Value    ${_CACHED_FINETUNED_MODEL_ID}        ${None}
    IF    $cached_workload_id != $None and $cached_model_id != $None
        Set Test Variable    ${TEST_FINETUNING_WORKLOAD_ID}    ${cached_workload_id}
        Set Test Variable    ${TEST_MANAGED_MODEL_ID}          ${cached_model_id}
        Log    Reusing cached finetuning workload: ${cached_workload_id}, model: ${cached_model_id}    DEBUG
        RETURN
    END
    # Check if a FINE_TUNING workload already exists in namespace
    ${workload_id}=    Find finetuning workload in namespace
    IF    $workload_id != $None
        Set Test Variable     ${TEST_FINETUNING_WORKLOAD_ID}    ${workload_id}
        Set Suite Variable    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${workload_id}
        # Resolve model ID from namespace — find the most recent finetuned model
        ${model_id}=    Find finetuned model in namespace
        Should Not Be Equal    ${model_id}    ${None}    msg=Found finetuning workload but no finetuned model in namespace
        Set Test Variable     ${TEST_MANAGED_MODEL_ID}    ${model_id}
        Set Suite Variable    ${_CACHED_FINETUNED_MODEL_ID}    ${model_id}
        RETURN
    END
    # No workload found — trigger finetune
    Finetune dataset exists
    A finetune request is sent
    # A finetune request is sent sets TEST_MANAGED_MODEL_ID as test variable
    # Find the workload created by the finetune
    ${workload_id}=    Find finetuning workload in namespace
    Should Not Be Equal    ${workload_id}    ${None}    msg=No FINE_TUNING workload found after finetune request
    Set Test Variable     ${TEST_FINETUNING_WORKLOAD_ID}    ${workload_id}
    # Cache both IDs for subsequent tests
    Set Suite Variable    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${workload_id}
    Set Suite Variable    ${_CACHED_FINETUNED_MODEL_ID}        ${TEST_MANAGED_MODEL_ID}

Find finetuning workload in namespace
    [Documentation]    Finds a non-terminal FINE_TUNING workload in the current namespace.
    ...    Skips workloads in terminal states (Deleted, Failed, Complete).
    ...    Returns workload ID if found, ${None} otherwise.
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workloads    namespace=${namespace}    workload_type=FINE_TUNING
    IF    ${response.status_code} != 200
        RETURN    ${None}
    END
    ${workloads}=    Set Variable    ${response.json()['data']}
    FOR    ${workload}    IN    @{workloads}
        ${status}=    Get From Dictionary    ${workload}    status
        IF    "${status}" not in ["Deleted", "Failed", "Complete"]
            ${id}=    Get From Dictionary    ${workload}    id
            Log    Found active finetuning workload: ${id} (status=${status})    DEBUG
            RETURN    ${id}
        END
    END
    RETURN    ${None}

Find finetuned model in namespace
    [Documentation]    Finds a finetuned model in the current namespace by name prefix.
    ...    Finetuned models are created with names like "finetuned-model-XXXXXXXX".
    ...    Returns model ID if found, ${None} otherwise.
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}
    IF    ${response.status_code} != 200
        RETURN    ${None}
    END
    # Response may be a plain list or wrapped in {'data': [...]}
    ${json}=    Set Variable    ${response.json()}
    ${is_dict}=    Evaluate    isinstance($json, dict)
    IF    ${is_dict}
        ${models}=    Set Variable    ${json['data']}
    ELSE
        ${models}=    Set Variable    ${json}
    END
    FOR    ${model}    IN    @{models}
        ${name}=    Get From Dictionary    ${model}    name
        ${is_finetuned}=    Evaluate    '''${name}'''.startswith('finetuned-model-')
        IF    ${is_finetuned}
            ${id}=    Get From Dictionary    ${model}    id
            RETURN    ${id}
        END
    END
    RETURN    ${None}

Finetuned model should have expected fields
    [Documentation]    Verifies the finetuned model has expected fields (id, name, onboarding_status).
    ...    Fetches the model by TEST_MANAGED_MODEL_ID and checks key fields exist.
    Should Not Be Equal    ${TEST_MANAGED_MODEL_ID}    ${None}    msg=No finetuned model ID set
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    ${TEST_MANAGED_MODEL_ID}    expected_status=200    namespace=${namespace}
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    id
    Dictionary Should Contain Key    ${json}    name
    Dictionary Should Contain Key    ${json}    onboarding_status

Finetuning workload should reach status "${target_status}"
    [Documentation]    Polls AIWB workload endpoint until status matches target.
    ...    Checks for terminal error states between polls to fail fast instead of
    ...    waiting the full timeout when the workload has already failed.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}    msg=No finetuning workload ID set
    IF    "${target_status}" == "Complete"
        VAR    ${timeout}     15 min
        VAR    ${interval}    15 sec
    ELSE
        VAR    ${timeout}     5 min
        VAR    ${interval}    10 sec
    END
    ${deadline}=    Evaluate    time.time() + (15*60 if "${target_status}" == "Complete" else 5*60)    modules=time
    WHILE    True
        ${status}=    Get AIWB workload status    ${TEST_FINETUNING_WORKLOAD_ID}
        IF    "${status}" == "${target_status}"
            Log    Workload reached target status: ${status}    INFO
            RETURN
        END
        # Fail fast on terminal states — no point retrying
        IF    "${status}" in ["Failed", "Complete", "Deleted"] and "${target_status}" not in ["Failed", "Complete", "Deleted"]
            Fail    Workload ${TEST_FINETUNING_WORKLOAD_ID} entered terminal state: ${status} (expected ${target_status})
        END
        ${now}=    Evaluate    time.time()    modules=time
        IF    ${now} >= ${deadline}
            Fail    Workload did not reach ${target_status} within timeout. Last status: ${status}
        END
        Sleep    ${interval}
    END

Get AIWB workload status
    [Documentation]    Returns the current status string of a workload.
    [Arguments]    ${workload_id}
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workload    ${workload_id}    namespace=${namespace}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${status}=    Get From Dictionary    ${json}    status
    Log    Workload ${workload_id}: status=${status}    DEBUG
    RETURN    ${status}

Finetuned model onboarding status should be "${target_status}"
    [Documentation]    Polls model endpoint until onboarding_status matches target.
    ...    Fails fast if onboarding status reaches a terminal error state.
    Should Not Be Equal    ${TEST_MANAGED_MODEL_ID}    ${None}    msg=No finetuned model ID set
    ${deadline}=    Evaluate    time.time() + 10*60    modules=time
    WHILE    True
        ${status}=    Get model onboarding status    ${TEST_MANAGED_MODEL_ID}
        IF    "${status}" == "${target_status}"
            Log    Model onboarding reached target status: ${status}    INFO
            RETURN
        END
        IF    "${status}" == "failed" and "${target_status}" != "failed"
            Fail    Model ${TEST_MANAGED_MODEL_ID} onboarding failed (expected ${target_status})
        END
        ${now}=    Evaluate    time.time()    modules=time
        IF    ${now} >= ${deadline}
            Fail    Model onboarding did not reach ${target_status} within 10 minutes. Last status: ${status}
        END
        Sleep    10 sec
    END

Get model onboarding status
    [Documentation]    Returns the current onboarding_status string of a model.
    [Arguments]    ${model_id}
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    ${model_id}    expected_status=200    namespace=${namespace}
    ${json}=    Set Variable    ${response.json()}
    ${status}=    Get From Dictionary    ${json}    onboarding_status
    Log    Model ${model_id}: onboarding_status=${status}    DEBUG
    RETURN    ${status}

Setup Finetuning Suite
    [Documentation]    Initialize tracking for finetuning resource cleanup.
    ...    Models, datasets, and workloads are namespace-scoped and cascade-deleted
    ...    when the project is deleted. Model tracking is still needed because
    ...    A finetune request is sent appends to CREATED_MODEL_IDS.
    Initialize Project Tracking
    Initialize Model Tracking
    Initialize Dataset Tracking

Teardown Finetuning Suite
    [Documentation]    Clean up by deleting the project. Project deletion cascades namespace
    ...    deletion which removes all namespace-scoped resources (models, datasets, workloads).
    Clean Up All Created Projects
