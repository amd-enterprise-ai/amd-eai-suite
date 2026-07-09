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
Resource            api/aims.resource
Resource            api/finetuning.resource
Resource            resources/api/workloads.resource
Resource            resources/airm_projects.resource
Resource            resources/resource_tracking.resource
Resource            resources/common/resource_lifecycle.resource
Resource            aiwb_common.resource
Library             libraries/ModelCatalog.py
Library             AIMModelHelper


*** Variables ***
${TEST_MODEL_ID}            ${None}
${TEST_MODEL_NAME}          test-model
${TEST_BASE_MODEL_ID}       ${None}
${TEST_MODEL_DATA}                ${None}
@{CREATED_MODEL_IDS}        # List to track created model IDs for cleanup
${TEST_DUMMY_AIMMODEL_NAME}             ${None}


*** Keywords ***
Valid base model data is prepared
    [Documentation]    Prepares valid base model test data
    # Ensure we have a project to work with
    Project exists in system

    ${random_suffix}=       Generate Random String                          8                       [LOWER][NUMBERS]
    ${model_name}=          Set Variable            test-model-${random_suffix}
    Set Test Variable       ${TEST_MODEL_NAME}      ${model_name}

    ${namespace}=           Get Project Namespace
    ${model_data}=          Create Dictionary
    ...                     type=BaseModel
    ...                     name=${model_name}
    ...                     modelWeightsPath=default-bucket/models/${namespace}/models/${model_name}
    ...                     canonicalName=${model_name}
    Set Test Variable       ${TEST_MODEL_DATA}            ${model_data}

Create model request is sent
    [Documentation]    Sends request to create a model using prepared test data and the project ID
    ${endpoint}=            Models endpoint
    ${query_params}=        Create Dictionary       projectId=${TEST_PROJECT_ID}
    ${response}=            Safe Post Request         ${endpoint}             json=${TEST_MODEL_DATA}       params=${query_params}
    Set Test Variable       ${TEST_RESPONSE}             ${response}

    ${model_id}=            Get from dictionary     ${response.json()}      id
    Track Model For Cleanup    ${model_id}

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

    VAR    @{created_base_models}
    VAR    @{created_adapters}

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

Finetune request is sent with data
    [Documentation]    Sends a finetune request with provided data (may be invalid for error testing).
    ...                Sets TEST_RESPONSE for status verification.
    [Arguments]             ${model_name}           ${finetune_data}
    ${namespace}=           Get Project Namespace
    ${response}=            Finetune model          ${model_name}           ${finetune_data}
    ...                     namespace=${namespace}
    Set Test Variable       ${TEST_RESPONSE}        ${response}

Get smallest finetunable catalog model
    [Documentation]    Returns the canonicalName of the smallest open finetunable catalog model.
    ...    Prefers open models (non-gated) over models requiring HF token (meta-llama/, google/gemma).
    ...    Among open models, sorts by gpuCount then parameter count — picks the cheapest option.
    ...    Skips the test if no models are configured for this cluster.
    ${response}=    Get finetunable models    expected_status=200
    VAR    ${models}    ${response.json()['data']}
    IF    len($models) == 0
        Skip    No finetunable models are configured for this cluster — skipping GPU finetuning tests
    END
    ${canonical_name}=    Get Smallest Finetunable Model    ${models}
    Log    Selected smallest finetunable model: ${canonical_name}    INFO
    RETURN    ${canonical_name}

A finetune request is sent
    [Documentation]    Sends a finetune request using the smallest finetunable catalog model.
    ...                Selects the model dynamically from GET /finetunable so the test always
    ...                uses a cluster-supported model with pre-configured overlays.
    ...                Skips if no finetunable models are configured for this cluster.
    ...
    ...                Schema fields (from FineTuningJobRequest, wire names):
    ...                - baseModel: AIMModel UUID or HuggingFace canonical name (set by the API keyword)
    ...                - name: Name of the finetuning job and resulting model
    ...                - datasetId: UUID of the dataset
    ...                - epochs: Number of epochs (default: 1)
    ...                - learningRate: Learning rate (default: 1.41421)
    ...                - batchSize: Batch size (default: 2)
    Should Not Be Empty     ${TEST_DATASET_ID}      msg=Dataset ID is required for finetuning.
    ${namespace}=           Get Project Namespace

    ${random_suffix}=       Generate random string                          8                       [LOWER][NUMBERS]
    VAR    ${model_name}    finetuned-model-${random_suffix}
    ${base_model_name}=     Get smallest finetunable catalog model

    # Generate finetune data matching FinetuneCreate schema (minimal defaults for fast execution)
    ${finetune_data}=       Create Dictionary
    ...                     name=${model_name}
    ...                     datasetId=${TEST_DATASET_ID}
    ...                     batchSize=2
    ...                     learningRate=1.41421
    ...                     epochs=1

    Log                     Sending finetune request for catalog model: ${base_model_name}           DEBUG
    ${response}=            Finetune model          ${base_model_name}      ${finetune_data}
    ...                     expected_status=202     namespace=${namespace}
    Set Test Variable       ${TEST_RESPONSE}             ${response}
    Log                     Finetune request response: ${response.json()}                   DEBUG

    ${workload_id}=    Get From Dictionary    ${response.json()}    workloadId
    VAR    ${TEST_FINETUNING_WORKLOAD_ID}      ${workload_id}    scope=TEST
    # CR name is assigned by the finetuning engine (not known yet); resolved lazily via workload-id label.
    # No tracking needed — project teardown cascades namespace deletion which removes the AIMModel CR.
    VAR    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}           scope=TEST

Clean Up All Created Models
    [Documentation]    Deletes all models created during test execution
    ...    This keyword should be used in a test suite teardown to ensure
    ...    all models created during testing are cleaned up properly.
    ...    Note: Models require project_id for deletion, so this has a special implementation
    ${tracking_list}=       Get Variable Value      ${CREATED_MODEL_IDS}    ${None}
    IF    $tracking_list is None    RETURN
    ${count}=               Get Length              ${tracking_list}
    IF    ${count} == 0    RETURN    END

    Log                     Cleaning up ${count} models: ${CREATED_MODEL_IDS}                       INFO

    ${namespace}=           Get Project Namespace
    # Delete each model individually
    FOR    ${model_id}    IN    @{tracking_list}
        TRY
            Log                     Deleting model ${model_id}                      DEBUG
            Delete model            model_id=${model_id}    namespace=${namespace}   expected_status=any     project_id=${TEST_PROJECT_ID}
        EXCEPT    AS    ${error}
            Log                     Failed to delete model ${model_id}: ${error}    WARN
        END
    END

    # Reset the list of created models
    VAR    @{CREATED_MODEL_IDS}    scope=SUITE
    Log                     Model cleanup complete. CREATED_MODEL_IDS reset to: ${CREATED_MODEL_IDS}                        INFO

A finetuning workload exists
    [Documentation]    Idempotent: ensures a finetuning workload exists.
    ...    Sets TEST_FINETUNING_WORKLOAD_ID and TEST_FINETUNING_RESOURCE_NAME as test variables.
    ...    Uses suite-level cache to avoid re-querying the API across tests,
    ...    but always sets test-level variables so each test has explicit preconditions.
    ...    TEST_FINETUNING_RESOURCE_NAME may be ${None} if the workload is still Running
    ...    and the AIMModel CR has not been created yet — resolved lazily on subsequent calls.
    # Check suite cache first — avoids redundant API queries across tests
    ${cached_workload_id}=    Get Variable Value    ${_CACHED_FINETUNING_WORKLOAD_ID}     ${None}
    ${cached_resource_name}=  Get Variable Value    ${_CACHED_FINETUNING_RESOURCE_NAME}   ${None}
    IF    $cached_workload_id != $None
        # Resource name is None when the workload was still Running when first cached
        IF    $cached_resource_name is None
            TRY
                ${resolved}=    Get finetuned model resource name from workload    ${cached_workload_id}
                Log    Resolved AIMModel CR name: ${resolved}    DEBUG
                VAR    ${cached_resource_name}              ${resolved}
                VAR    ${_CACHED_FINETUNING_RESOURCE_NAME}  ${resolved}    scope=SUITE
            EXCEPT
                Log    AIMModel CR not yet created for workload ${cached_workload_id}    DEBUG
            END
        END
        VAR    ${TEST_FINETUNING_WORKLOAD_ID}      ${cached_workload_id}    scope=TEST
        VAR    ${TEST_FINETUNING_RESOURCE_NAME}    ${cached_resource_name}  scope=TEST
        Log    Reusing cached finetuning workload: ${cached_workload_id}, resource: ${cached_resource_name}    DEBUG
        RETURN
    END
    # Check if a FINE_TUNING workload already exists in namespace
    ${workload_id}=    Find finetuning workload in namespace
    IF    $workload_id != $None
        VAR    ${TEST_FINETUNING_WORKLOAD_ID}       ${workload_id}    scope=TEST
        VAR    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${workload_id}    scope=SUITE
        # Resolve the actual AIMModel CR name — deploy/template endpoints require the CR name,
        # not the workload UUID (only GET /models/{name} supports UUID label fallback)
        TRY
            ${resource_name}=    Get finetuned model resource name from workload    ${workload_id}
            Log    Resolved AIMModel CR name: ${resource_name} for workload ${workload_id}    DEBUG
        EXCEPT
            # AIMModel CR not yet created (workload still running) — resolved lazily on subsequent calls
            VAR    ${resource_name}    ${None}
            Log    AIMModel CR not found for workload ${workload_id}, will resolve later    DEBUG
        END
        VAR    ${TEST_FINETUNING_RESOURCE_NAME}       ${resource_name}    scope=TEST
        VAR    ${_CACHED_FINETUNING_RESOURCE_NAME}    ${resource_name}    scope=SUITE
        RETURN
    END
    # No workload found — trigger finetune
    Finetune dataset exists
    A finetune request is sent
    # Cache after A finetune request is sent, which sets TEST_FINETUNING_WORKLOAD_ID and TEST_FINETUNING_RESOURCE_NAME
    VAR    ${_CACHED_FINETUNING_WORKLOAD_ID}      ${TEST_FINETUNING_WORKLOAD_ID}    scope=SUITE
    VAR    ${_CACHED_FINETUNING_RESOURCE_NAME}    ${TEST_FINETUNING_RESOURCE_NAME}  scope=SUITE

Find finetuning workload in namespace
    [Documentation]    Finds a reusable FINE_TUNING workload in the current namespace.
    ...    Skips only permanently terminal states (Deleted, Failed) so Complete workloads
    ...    are reused on re-runs (their AIMModel CR still exists).
    ...    Returns workload ID if found, ${None} otherwise.
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIWB workloads    namespace=${namespace}    workload_type=FINE_TUNING
    IF    ${response.status_code} != 200
        RETURN    ${None}
    END
    ${workloads}=    Set Variable    ${response.json()['data']}
    FOR    ${workload}    IN    @{workloads}
        ${status}=    Get From Dictionary    ${workload}    status
        IF    "${status}" not in ["Deleted", "Deleting", "Failed"]
            ${id}=    Get From Dictionary    ${workload}    id
            Log    Found reusable finetuning workload: ${id} (status=${status})    DEBUG
            RETURN    ${id}
        END
    END
    RETURN    ${None}

Get finetuned model resource name from workload
    [Documentation]    Returns the AIMModel CR name for a finetuning workload.
    ...    Finds the model in the namespace model list by matching the workload ID label.
    ...    Fails if no matching AIMModel CR exists (e.g., workload still Running).
    [Arguments]    ${workload_id}
    ${namespace}=    Get Project Namespace
    ${models_response}=    Get models    namespace=${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${models_response.json()}    data
    FOR    ${model}    IN    @{models}
        ${wid}=    Evaluate    $model.get('metadata', {}).get('labels', {}).get('airm.silogen.ai/workload-id')
        IF    "${wid}" == "${workload_id}"
            ${resource_name}=    Get From Dictionary    ${model}[metadata]    name
            RETURN    ${resource_name}
        END
    END
    Fail    Could not find model with workload-id label=${workload_id} in the namespace model list

The finetuned model should appear in the namespace model list
    [Documentation]    Verifies the finetuned model appears in the K8s-based namespace model list.
    ...    The list combines in-progress finetuning jobs and completed AIMModel CRs.
    ...    Searches by workload ID label and checks that the expected response fields are present.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}    msg=No finetuning workload ID set
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${models}=    Get From Dictionary    ${json}    data
    FOR    ${model}    IN    @{models}
        ${wid}=    Evaluate    $model.get('metadata', {}).get('labels', {}).get('airm.silogen.ai/workload-id')
        IF    "${wid}" == "${TEST_FINETUNING_WORKLOAD_ID}"
            Dictionary Should Contain Key    ${model}    metadata
            Dictionary Should Contain Key    ${model}    status
            Dictionary Should Contain Key    ${model}[metadata]    name
            Log    Found model in list: name=${model['metadata']['name']} status=${model['status']['status']}    INFO
            RETURN
        END
    END
    Fail    Finetuning model with workload-id label=${TEST_FINETUNING_WORKLOAD_ID} not found in model list

Fine-tuned models are listed for the project
    [Documentation]    Lists fine-tuned models in the current project with no filters.
    ...    Sets: TEST_RESPONSE
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

Finetuned model should have expected fields
    [Documentation]    Verifies the finetuned model can be retrieved by resource name and has expected K8s-sourced fields.
    ...    Fetches the model by TEST_FINETUNING_RESOURCE_NAME and checks: metadata.name, status.
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}    msg=No finetuning resource name set
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    ${TEST_FINETUNING_RESOURCE_NAME}    expected_status=200    namespace=${namespace}
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    metadata
    Dictionary Should Contain Key    ${json}    status
    Dictionary Should Contain Key    ${json}[metadata]    name

Finetuning workload should reach status "${target_status}"
    [Documentation]    Polls the workloads API until the finetuning workload reaches the
    ...    target status. Fails if the workload enters a terminal Failed state.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}    msg=No finetuning workload ID set
    ${namespace}=    Get Project Namespace
    # 15 min for Complete (training takes ~10 min), 5 min for Running (admission only)
    IF    "${target_status}" == "Complete"
        VAR    ${timeout}    15 min
    ELSE
        VAR    ${timeout}    5 min
    END
    Wait Until Keyword Succeeds    ${timeout}    10 sec
    ...    Finetuning workload status should be    ${target_status}    ${namespace}

Finetuning workload status should be
    [Documentation]    Single-poll check used by Wait Until Keyword Succeeds.
    ...    Fails on terminal Failed state; returns normally if target or an allowed
    ...    intermediate state (Running→Complete transition) is reached.
    [Arguments]    ${target_status}    ${namespace}
    ${response}=    Get AIWB workload    ${TEST_FINETUNING_WORKLOAD_ID}    namespace=${namespace}
    ${status}=    Get From Dictionary    ${response.json()}    status
    IF    "${status}" == "Failed" and "${target_status}" != "Failed"
        Fail    Finetuning workload entered Failed state (expected ${target_status})
    END
    # Workload already Completed — it transited through Running
    IF    "${target_status}" == "Running" and "${status}" == "Complete"
        RETURN
    END
    Should Be Equal    ${status}    ${target_status}    Workload status: ${status}

Finetuned model onboarding status should be "${target_status}"
    [Documentation]    Polls the namespace model list until the finetuned model reaches the
    ...    target onboarding status. Searches by workload-id label so it works once the
    ...    AIMModel CR exists after training completes.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}    msg=No finetuning workload ID set
    ${namespace}=    Get Project Namespace
    # Map "ready" to the K8s AIMModel onboarding status value returned by the API
    VAR    ${k8s_status}    ${target_status}
    IF    "${target_status}" == "ready"
        VAR    ${k8s_status}    Ready
    END
    Wait Until Keyword Succeeds    10 min    10 sec
    ...    Finetuned model status should be    ${k8s_status}    ${target_status}    ${namespace}

Finetuned model status should be
    [Documentation]    Single-poll check used by Wait Until Keyword Succeeds.
    ...    Scans the model list for the entry matching TEST_FINETUNING_WORKLOAD_ID,
    ...    fails on terminal Failed state, returns normally on target status.
    [Arguments]    ${k8s_status}    ${display_status}    ${namespace}
    ${response}=    Get models    namespace=${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    FOR    ${model}    IN    @{models}
        ${wid}=    Evaluate    $model.get('metadata', {}).get('labels', {}).get('airm.silogen.ai/workload-id')
        IF    "${wid}" != "${TEST_FINETUNING_WORKLOAD_ID}"    CONTINUE
        ${status}=    Get From Dictionary    ${model}[status]    status
        IF    "${status}" == "${k8s_status}"
            RETURN
        END
        IF    "${status}" == "Failed" and "${k8s_status}" != "Failed"
            Fail    Finetuned model entered Failed status (expected ${display_status})
        END
        Fail    Finetuned model status is ${status} (waiting for ${display_status})
    END
    Fail    Finetuned model with workload-id ${TEST_FINETUNING_WORKLOAD_ID} not found yet

A dummy AIMModel CR exists in the namespace
    [Documentation]    Creates a minimal AIMModel CR in the project namespace via kubectl.
    ...    Simulates a completed fine-tuned model without requiring GPU or actual fine-tuning.
    ...    Idempotent: caches the CR name at suite level to avoid redundant kubectl calls.
    ...    Sets TEST_DUMMY_AIMMODEL_NAME for later use in assertions.
    [Arguments]    ${name}=dummy-finetuned-model
    # Check suite cache first — reuse across tests
    ${cached}=    Get Variable Value    ${_CACHED_DUMMY_AIMMODEL_NAME}    ${None}
    IF    $cached != $None
        VAR    ${TEST_DUMMY_AIMMODEL_NAME}    ${cached}    scope=TEST
        Log    Reusing cached dummy AIMModel CR: ${cached}    DEBUG
        RETURN
    END
    ${namespace}=    Get Project Namespace
    Apply Dummy AIMModel CR    ${name}    ${namespace}
    VAR    ${TEST_DUMMY_AIMMODEL_NAME}    ${name}    scope=TEST
    VAR    ${_CACHED_DUMMY_AIMMODEL_NAME}    ${name}    scope=SUITE
    Log    Created dummy AIMModel CR '${name}' in namespace ${namespace}    INFO

The dummy AIMModel should appear in the namespace model list
    [Documentation]    Verifies the dummy AIMModel CR appears in the namespace model list and exposes
    ...    the metadata.name and status.status fields downstream consumers depend on.
    Should Not Be Equal    ${TEST_DUMMY_AIMMODEL_NAME}    ${None}    msg=No dummy AIMModel name set
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}    expected_status=200
    VAR    ${json}    ${response.json()}
    ${models}=    Get From Dictionary    ${json}    data
    FOR    ${model}    IN    @{models}
        ${metadata}=    Get From Dictionary    ${model}    metadata
        ${name}=    Get From Dictionary    ${metadata}    name
        IF    "${name}" == "${TEST_DUMMY_AIMMODEL_NAME}"
            Dictionary Should Contain Key    ${model}    status
            ${status_obj}=    Get From Dictionary    ${model}    status
            ${status}=    Get From Dictionary    ${status_obj}    status
            Log    Found dummy model in list: name=${name} status=${status}    INFO
            RETURN
        END
    END
    Fail    Dummy AIMModel '${TEST_DUMMY_AIMMODEL_NAME}' not found in model list

The dummy AIMModel should be retrievable by resource name
    [Documentation]    Verifies the dummy AIMModel can be fetched by resource name and exposes
    ...    the expected metadata and status sections.
    Should Not Be Equal    ${TEST_DUMMY_AIMMODEL_NAME}    ${None}    msg=No dummy AIMModel name set
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    ${TEST_DUMMY_AIMMODEL_NAME}    expected_status=200    namespace=${namespace}
    VAR    ${json}    ${response.json()}
    Dictionary Should Contain Key    ${json}    metadata
    Dictionary Should Contain Key    ${json}    status
    ${metadata}=    Get From Dictionary    ${json}    metadata
    ${name}=    Get From Dictionary    ${metadata}    name
    Should Be Equal    ${name}    ${TEST_DUMMY_AIMMODEL_NAME}
    ${status_obj}=    Get From Dictionary    ${json}    status
    ${status}=    Get From Dictionary    ${status_obj}    status
    Log    Retrieved dummy model: name=${name} status=${status}    INFO

Getting a non-existent model should return 404
    [Documentation]    Verifies that requesting a model by a non-existent resource name returns 404.
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    nonexistent-model-xyz    expected_status=404    namespace=${namespace}

Resolve Fine-Tuned Model aimId
    [Documentation]    Read status.aimId for a fine-tuned AIMModel CR. Fails when
    ...    the controller has not yet populated the field — profile listing
    ...    cannot proceed until reconciliation completes.
    [Arguments]    ${resource_name}    ${namespace}
    ${response}=    Get model    ${resource_name}    expected_status=200    namespace=${namespace}
    ${status}=    Get From Dictionary    ${response.json()}    status
    ${aim_id}=    Get From Dictionary    ${status}    aimId    default=${None}
    Should Not Be Equal    ${aim_id}    ${None}
    ...    msg=AIMModel ${resource_name} has no status.aimId yet — engine has not reconciled
    RETURN    ${aim_id}

Fine-tuned model deployment configurations are available
    [Documentation]    Verifies deployment configurations exist for the ready finetuned model.
    ...    These are provisioned automatically once model onboarding completes.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set — call "A finetuning workload exists" first
    ${namespace}=    Get Project Namespace
    # status.aimId is populated asynchronously by the engine — poll until it appears.
    ${aim_id}=    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Resolve Fine-Tuned Model aimId    ${TEST_FINETUNING_RESOURCE_NAME}    ${namespace}
    ${response}=    List Fine-Tuned AIM Profiles
    ...    ${namespace}
    ...    aim_id=${aim_id}
    ...    expected_status=200
    VAR    ${json}    ${response.json()}
    ${profiles}=    Get From Dictionary    ${json}    data
    ${count}=    Get Length    ${profiles}
    Should Be True    ${count} > 0
    ...    msg=No deployment configurations found for fine-tuned model ${TEST_FINETUNING_RESOURCE_NAME}
    Log    Found ${count} deployment configurations for fine-tuned model ${TEST_FINETUNING_RESOURCE_NAME}    INFO

Fine-tuned model is deployed as an AIM service
    [Documentation]    Deploys the finetuned model via the inference capability endpoint.
    ...    Uses the same endpoint as cluster model deployment — the API auto-detects the model type.
    ...    Idempotent: reuses an existing AIMService for the model when present.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME
    ...    Sets: TEST_AIM_ID
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set — call "A finetuning workload exists" first
    ${namespace}=    Get Project Namespace
    # Reuse an existing AIMService for this model if available
    ${existing}=    Find Existing Fine-Tuned AIM Service    ${namespace}    ${TEST_FINETUNING_RESOURCE_NAME}
    IF    $existing != $None
        ${service_id}=    Get From Dictionary    ${existing}    id
        VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST
        Log    Reusing existing AIMService ${service_id} for fine-tuned model    INFO
        RETURN
    END
    # Cluster models and fine-tuned project-scoped models share the same deploy endpoint
    # — the API auto-detects the model type from the resource name.
    ${deploy_data}=    Create Dictionary    replicas=${1}
    ${response}=    Deploy AIM    ${TEST_FINETUNING_RESOURCE_NAME}    ${deploy_data}    ${namespace}    expected_status=202
    ${json}=    Set Variable    ${response.json()}
    ${service_id}=    Get From Dictionary    ${json}    id
    VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST
    Log    Deployed fine-tuned model ${TEST_FINETUNING_RESOURCE_NAME} as AIMService ${service_id}    INFO

Fine-tuned model is deployed with runtime profile overrides
    [Documentation]    Deploys the finetuned model with runtime profile override fields in
    ...    the API request. Undeploys any existing service first so the CR reflects this
    ...    deploy. When a Ready namespace AIMProfile exists, those fields are not written
    ...    to the AIMService CR — the profile is pinned by name instead.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME
    ...    Sets: TEST_AIM_ID
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set — call "A finetuning workload exists" first
    ${namespace}=    Get Project Namespace
    ${existing}=    Find Existing Fine-Tuned AIM Service    ${namespace}    ${TEST_FINETUNING_RESOURCE_NAME}
    IF    $existing != $None
        ${service_id}=    Get From Dictionary    ${existing}    id
        Undeploy AIM    ${service_id}    ${namespace}    expected_status=any
    END
    ${engine_args}=    Create Dictionary    max-model-len=${8192}
    ${engine_env_entry}=    Create Dictionary    name=VLLM_LOGGING_LEVEL    value=DEBUG
    ${engine_env}=    Create List    ${engine_env_entry}
    ${container_env_entry}=    Create Dictionary    name=FOO    value=bar
    ${container_env}=    Create List    ${container_env_entry}
    ${deploy_data}=    Create Dictionary
    ...    replicas=${1}
    ...    precision=fp8
    ...    gpuModel=MI300X
    ...    gpuCount=${2}
    ...    engineArgs=${engine_args}
    ...    engineEnv=${engine_env}
    ...    containerEnv=${container_env}
    ${response}=    Deploy AIM    ${TEST_FINETUNING_RESOURCE_NAME}    ${deploy_data}    ${namespace}    expected_status=202
    VAR    ${json}    ${response.json()}
    ${service_id}=    Get From Dictionary    ${json}    id
    VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST
    Log    Deployed fine-tuned model ${TEST_FINETUNING_RESOURCE_NAME} with runtime profile overrides as AIMService ${service_id}    INFO

Find Existing Fine-Tuned AIM Service
    [Documentation]    Finds an existing AIMService for a fine-tuned model in a namespace.
    ...    Returns the service dict if found, ${None} otherwise.
    [Arguments]    ${namespace}    ${model_resource_name}
    ${services_response}=    List AIM Services    ${namespace}    expected_status=200
    ${services_data}=    Set Variable    ${services_response.json()}
    ${services_list}=    Set Variable    ${services_data['data']}
    FOR    ${service}    IN    @{services_list}
        ${model}=    Get From Dictionary    ${service['spec']}    model
        ${model_name}=    Get From Dictionary    ${model}    name
        IF    "${model_name}" == "${model_resource_name}"
            RETURN    ${service}
        END
    END
    RETURN    ${None}

Deployed AIMService should reference the fine-tuned model
    [Documentation]    Verifies the AIMService spec.model.name matches the finetuned model resource name.
    ...    Requires: TEST_AIM_ID, TEST_FINETUNING_RESOURCE_NAME
    Should Not Be Equal    ${TEST_AIM_ID}    ${None}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIM Service    ${TEST_AIM_ID}    ${namespace}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${spec}=    Get From Dictionary    ${json}    spec
    ${model}=    Get From Dictionary    ${spec}    model
    ${model_name}=    Get From Dictionary    ${model}    name
    Should Be Equal    ${model_name}    ${TEST_FINETUNING_RESOURCE_NAME}
    ...    msg=AIMService model name '${model_name}' does not match finetuned model '${TEST_FINETUNING_RESOURCE_NAME}'
    Log    AIMService correctly references fine-tuned model: ${model_name}    INFO

Deployed fine-tuned model should have an inference endpoint
    [Documentation]    Verifies the deployed fine-tuned AIMService has an internal inference endpoint.
    ...    Requires: TEST_AIM_ID
    Should Not Be Equal    ${TEST_AIM_ID}    ${None}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIM Service    ${TEST_AIM_ID}    ${namespace}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    endpoints    msg=AIMService should have endpoints field
    ${endpoints}=    Get From Dictionary    ${json}    endpoints
    Dictionary Should Contain Key    ${endpoints}    internal    msg=AIMService should have an internal inference endpoint
    ${internal_url}=    Get From Dictionary    ${endpoints}    internal
    Should Not Be Empty    ${internal_url}    msg=Internal inference endpoint should not be empty
    Log    Fine-tuned model inference endpoint: ${internal_url}    INFO

Deployed fine-tuned model should be accessible for inference
    [Documentation]    Verifies the fine-tuned AIMService appears in the inference deployments list
    ...    filtered by capability=chat, confirming it is accessible from the playground for chat.
    ...    Requires: TEST_AIM_ID
    Should Not Be Equal    ${TEST_AIM_ID}    ${None}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    ${response}=    List AIM Services    ${namespace}    expected_status=200    capability=chat
    ${json}=    Set Variable    ${response.json()}
    ${services}=    Get From Dictionary    ${json}    data
    FOR    ${service}    IN    @{services}
        ${service_id}=    Get From Dictionary    ${service}    id
        IF    "${service_id}" == "${TEST_AIM_ID}"
            Log    Fine-tuned model AIMService ${TEST_AIM_ID} is accessible for inference    INFO
            RETURN
        END
    END
    Fail    Fine-tuned model AIMService ${TEST_AIM_ID} not found in chat-capable inference deployments list

Fine-tuned model deployment configurations should include hardware details
    [Documentation]    Verifies each deployment configuration for the fine-tuned model exposes
    ...    the hardware details users need to choose a profile: model reference and precision.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME (set by "a finetuning workload exists")
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set
    ${namespace}=    Get Project Namespace
    # status.aimId is populated asynchronously by the engine — poll until it appears.
    ${aim_id}=    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Resolve Fine-Tuned Model aimId    ${TEST_FINETUNING_RESOURCE_NAME}    ${namespace}
    ${response}=    List Fine-Tuned AIM Profiles
    ...    ${namespace}
    ...    aim_id=${aim_id}
    ...    expected_status=200
    ${configurations}=    Get From Dictionary    ${response.json()}    data
    Should Not Be Empty    ${configurations}
    ...    msg=No deployment configurations found for model ${TEST_FINETUNING_RESOURCE_NAME}
    FOR    ${config}    IN    @{configurations}
        ${spec}=    Get From Dictionary    ${config}    spec
        Dictionary Should Contain Key    ${spec}    aimId
        ...    msg=Deployment configuration missing aim reference
        Dictionary Should Contain Key    ${spec}    precision
        ...    msg=Deployment configuration missing precision
        Dictionary Should Contain Key    ${config}    status
        ...    msg=Deployment configuration missing hardware profile metadata
    END
    ${config_count}=    Get Length    ${configurations}
    Log    All ${config_count} deployment configurations expose hardware details    INFO

User deletes the fine-tuned model
    [Documentation]    Sends a non-forced delete request for the current finetuned model.
    ...    Stores the response so subsequent Then steps can inspect the outcome.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set
    ${namespace}=    Get Project Namespace
    ${response}=    Delete model    ${TEST_FINETUNING_RESOURCE_NAME}    ${namespace}    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The request should be rejected because the deployment is active
    [Documentation]    Verifies the previous delete request was rejected with a conflict response,
    ...    indicating an active deployment is preventing deletion.
    ...    Requires: TEST_RESPONSE (set by "user deletes the fine-tuned model")
    Should Not Be Equal    ${TEST_RESPONSE}    ${None}    msg=No prior delete response captured
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    409
    ...    msg=Expected 409 Conflict (active deployment), got ${TEST_RESPONSE.status_code}

User force-deletes the fine-tuned model
    [Documentation]    Sends a force-delete request for the current finetuned model.
    ...    Resets the suite-level finetuning cache so any subsequent test re-creates
    ...    the workload through the idempotent "a finetuning workload exists" precondition.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set
    ${namespace}=    Get Project Namespace
    Delete model    ${TEST_FINETUNING_RESOURCE_NAME}    ${namespace}    expected_status=204    force=${True}
    Log    Force-deleted model ${TEST_FINETUNING_RESOURCE_NAME}    INFO
    VAR    ${_CACHED_FINETUNING_WORKLOAD_ID}      ${None}    scope=SUITE
    VAR    ${_CACHED_FINETUNING_RESOURCE_NAME}    ${None}    scope=SUITE

The fine-tuned model should be removed
    [Documentation]    Verifies the finetuned model no longer exists in the namespace.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set
    ${namespace}=    Get Project Namespace
    Get model    ${TEST_FINETUNING_RESOURCE_NAME}    namespace=${namespace}    expected_status=404

The fine-tuned model deployment should be removed
    [Documentation]    Verifies the deployment of the finetuned model no longer exists.
    ...    Requires: TEST_AIM_ID
    Should Not Be Equal    ${TEST_AIM_ID}    ${None}    msg=No deployment ID set
    ${namespace}=    Get Project Namespace
    Get AIM Service    ${TEST_AIM_ID}    ${namespace}    expected_status=404

Setup Finetuning Suite
    [Documentation]    Initialize tracking for finetuning resource cleanup.
    ...    Models, datasets, and workloads are namespace-scoped and cascade-deleted
    ...    when the project is deleted. Model tracking is initialized for the
    ...    non-finetuning model tests (e.g. dummy AIMModel CR tests).
    Initialize Project Tracking
    Initialize Model Tracking
    Initialize Dataset Tracking

Teardown Finetuning Suite
    [Documentation]    Clean up by deleting the project. Project deletion cascades namespace
    ...    deletion which removes all namespace-scoped resources (models, datasets, workloads).
    Clean Up All Created Projects

An AIMModel CR exists in the namespace
    [Documentation]    Creates an AIMModel CR directly via kubectl for deletion testing.
    ...    Sets TEST_MODEL_NAME to the created CR name and registers it for teardown cleanup.
    [Tags]    kubectl
    ${namespace}=           Get Project Namespace
    ${random_suffix}=       Generate Random String              8                   [LOWER][NUMBERS]
    VAR    ${model_name}    test-model-${random_suffix}
    VAR    ${TEST_MODEL_NAME}    ${model_name}    scope=TEST
    Apply AIMModel CR With Source    ${model_name}    ${namespace}
    Append To List          ${CREATED_MODEL_IDS}                ${model_name}
    Log                     Created AIMModel CR ${model_name} in namespace ${namespace}     INFO

A completed fine-tuned model exists in the namespace
    [Documentation]    Creates an AIMModel CR via kubectl, sets a known aimId on the spec, and
    ...    patches its status to Ready, so the service accepts it as a valid base model for a new
    ...    finetuning run. Sets TEST_MODEL_NAME, TEST_MODEL_AIM_ID, and TEST_FINETUNING_WORKLOAD_ID
    ...    for later assertion. The known aimId lets tests distinguish "CR was resolved" from
    ...    "treated as HF model ID". The airm.silogen.ai/workload-id label is required for the UI
    ...    Fine-tune row action to be visible (item.id is derived from this label).
    [Tags]    kubectl
    An AIMModel CR exists in the namespace
    ${namespace}=    Get Project Namespace
    ${workload_id}=    Evaluate    str(uuid.uuid4())    modules=uuid
    ${result}=    Run Process
    ...    kubectl    patch    aimmodels    ${TEST_MODEL_NAME}
    ...    -n    ${namespace}
    ...    --type\=merge
    ...    -p    {"metadata":{"labels":{"airm.silogen.ai/workload-id":"${workload_id}","aiwb.apps.eai.amd.com/model-name":"${TEST_MODEL_NAME}"}},"spec":{"aimId":"test/base-model"}}
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to patch AIMModel ${TEST_MODEL_NAME} spec aimId and labels: ${result.stderr}
    VAR    ${TEST_FINETUNING_WORKLOAD_ID}    ${workload_id}    scope=TEST
    ${result}=    Run Process
    ...    kubectl    patch    aimmodels    ${TEST_MODEL_NAME}
    ...    -n    ${namespace}
    ...    --subresource\=status
    ...    --type\=merge
    ...    -p    {"status":{"status":"Ready"}}
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to patch AIMModel ${TEST_MODEL_NAME} status to Ready: ${result.stderr}
    VAR    ${TEST_MODEL_AIM_ID}    test/base-model    scope=TEST

Delete AIMModel CR request is sent
    [Documentation]    Sends a DELETE request using the AIMModel CR name (TEST_MODEL_NAME).
    ${namespace}=           Get Project Namespace
    ${response}=            Delete model            ${TEST_MODEL_NAME}      namespace=${namespace}
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The AIMModel CR should not exist
    [Documentation]    Verifies the AIMModel CR no longer exists in the namespace.
    ${namespace}=           Get Project Namespace
    AIMModel CR Should Be Absent    ${TEST_MODEL_NAME}    ${namespace}
    Log                     Confirmed AIMModel CR ${TEST_MODEL_NAME} was deleted    INFO

A finetune request from an existing model is sent
    [Documentation]    Sends a finetune request using the resource name of an existing AIMModel CR.
    ...    Tests the resource-name resolution path: bare string without slashes → AIMModel k8s lookup.
    ...    Requires TEST_MODEL_NAME (from "An AIMModel CR exists in the namespace")
    ...    and TEST_DATASET_ID (from "Finetune dataset exists").
    Should Not Be Empty    ${TEST_MODEL_NAME}    msg=AIMModel resource name not set — call "An AIMModel CR exists in the namespace" first
    Should Not Be Empty    ${TEST_DATASET_ID}    msg=Dataset ID not set — call "Finetune dataset exists" first
    ${namespace}=    Get Project Namespace
    ${random_suffix}=    Generate Random String    8    [LETTERS][NUMBERS]
    VAR    ${model_name}    finetuned-from-model-${random_suffix}
    ${finetune_data}=    Create Dictionary
    ...    name=${model_name}
    ...    datasetId=${TEST_DATASET_ID}
    ...    batchSize=2
    ...    learningRate=1.41421
    ...    epochs=1
    ${response}=    Finetune model    ${TEST_MODEL_NAME}    ${finetune_data}
    ...    namespace=${namespace}    expected_status=202
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST
    ${workload_id}=    Get From Dictionary    ${response.json()}    workloadId
    Track Workload For Cleanup    ${workload_id}

The workload should use the AIMModel as base model
    [Documentation]    Verifies that the finetuning response's baseModel equals the AIMModel CR's
    ...    aimId (TEST_MODEL_AIM_ID), not the bare resource name. This distinguishes "CR was looked
    ...    up by resource name and its aimId used" from "resource name silently treated as HF ID".
    Should Not Be Empty    ${TEST_MODEL_AIM_ID}
    ...    msg=TEST_MODEL_AIM_ID not set — call "A completed fine-tuned model exists in the namespace" first
    ${base_model}=    Get From Dictionary    ${TEST_RESPONSE.json()}    baseModel
    Should Be Equal    ${base_model}    ${TEST_MODEL_AIM_ID}
    ...    msg=baseModel should be the AIMModel's aimId (${TEST_MODEL_AIM_ID}), not the resource name

Finetunable models list is requested
    [Documentation]    Requests the list of finetunable models and stores the response.
    ${response}=    Get finetunable models    expected_status=200
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The finetuning job is cancelled
    [Documentation]    Cancels the in-progress finetuning workload identified by
    ...                TEST_FINETUNING_WORKLOAD_ID via the fine-tuning capability API.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}
    ...    msg=No finetuning workload ID set — call "A finetuning workload exists" first
    ${namespace}=    Get Project Namespace
    ${response}=    Cancel finetuning job    ${TEST_FINETUNING_WORKLOAD_ID}    namespace=${namespace}
    ...    expected_status=204
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST
    Log    Cancelled finetuning job ${TEST_FINETUNING_WORKLOAD_ID}    INFO
    # Drop the suite-level cache so subsequent tests don't reuse the cancelled workload.
    VAR    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${None}    scope=SUITE
    VAR    ${_CACHED_FINETUNED_MODEL_ID}    ${None}    scope=SUITE
    VAR    ${_CACHED_FINETUNING_RESOURCE_NAME}    ${None}    scope=SUITE

The workload status should become "${target_status}"
    [Documentation]    Polls the AIWB workloads API until the finetuning workload
    ...                identified by TEST_FINETUNING_WORKLOAD_ID reaches the target status.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}
    ...    msg=No finetuning workload ID set — call "A finetuning workload exists" first
    ${namespace}=    Get Project Namespace
    Wait For Resource Status    Get AIWB workload    ${TEST_FINETUNING_WORKLOAD_ID}    ${target_status}
    ...    timeout=5 min    interval=10 sec    namespace=${namespace}
    Log    Finetuning workload ${TEST_FINETUNING_WORKLOAD_ID} reached status ${target_status}    INFO

Each finetunable model should include GPU hardware compatibility details
    [Documentation]    Verifies every finetunable model includes meaningful GPU hardware
    ...    compatibility information: model name, a positive required GPU count, and at least
    ...    one compatible accelerator (both as IDs and human-readable names).
    ...    Skips gracefully when no models are compatible with the current cluster hardware.
    VAR    ${models}    ${TEST_RESPONSE.json()['data']}
    IF    len($models) == 0
        Skip    No finetunable models are compatible with the current cluster hardware configuration
    END
    FOR    ${model}    IN    @{models}
        Dictionary Should Contain Key    ${model}    canonicalName
        Should Not Be Empty    ${model}[canonicalName]
        ...    msg=Recipe is missing canonicalName

        ${gpu_count}=    Get From Dictionary    ${model}    gpuCount
        Should Not Be Equal    ${gpu_count}    ${None}
        ...    msg=Recipe ${model}[canonicalName] is missing required GPU count
        Should Be True    ${gpu_count} > 0
        ...    msg=Recipe ${model}[canonicalName] reports a non-positive GPU count: ${gpu_count}

        ${accelerators}=    Get From Dictionary    ${model}    compatibleAccelerators
        Should Not Be Empty    ${accelerators}
        ...    msg=Recipe ${model}[canonicalName] has no compatible accelerator IDs

        ${accelerator_names}=    Get From Dictionary    ${model}    compatibleAcceleratorNames
        Should Not Be Empty    ${accelerator_names}
        ...    msg=Recipe ${model}[canonicalName] has no compatible accelerator names
    END
