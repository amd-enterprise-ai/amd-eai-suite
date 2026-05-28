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
Resource            aiwb_common.resource
Library             OperatingSystem
Library             Process


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

    ${random_suffix}=       Generate Random String                          8                       [LETTERS][NUMBERS]
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

A finetune request is sent
    [Documentation]    Sends a finetune request using a HuggingFace model name.
    ...                Uses namespace-based endpoint: /namespaces/{namespace}/models/{model_id}/finetune
    ...
    ...                Schema fields (from FinetuneCreate, wire names):
    ...                - name: Name of the finetuning job and resulting model
    ...                - datasetId: UUID of the dataset
    ...                - epochs: Number of epochs (default: 1)
    ...                - learningRate: Learning rate (default: 1.41421)
    ...                - batchSize: Batch size (default: 2)
    ...                - hfTokenSecretName: Optional HF token secret name
    Should Not Be Empty     ${TEST_DATASET_ID}      msg=Dataset ID is required for finetuning.
    ${namespace}=           Get Project Namespace

    ${random_suffix}=       Generate random string                          8                       [LETTERS][NUMBERS]
    ${model_name}=          Set Variable            finetuned-model-${random_suffix}
    # Use HuggingFace model name directly as model_id in the endpoint
    ${base_model_name}=     Set Variable            TinyLlama/TinyLlama-1.1B-Chat-v1.0

    # Generate finetune data matching FinetuneCreate schema (minimal defaults for fast execution)
    ${finetune_data}=       Create Dictionary
    ...                     name=${model_name}
    ...                     datasetId=${TEST_DATASET_ID}
    ...                     batchSize=2
    ...                     learningRate=1.41421
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

    Track Model For Cleanup    ${model_id}

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
    @{empty_list}=          Create List
    Set Suite Variable      ${CREATED_MODEL_IDS}    ${empty_list}
    Log                     Model cleanup complete. CREATED_MODEL_IDS reset to: ${CREATED_MODEL_IDS}                        INFO

A finetuning workload exists
    [Documentation]    Idempotent: ensures a finetuning workload exists.
    ...    Sets TEST_FINETUNING_WORKLOAD_ID, TEST_MANAGED_MODEL_ID, and TEST_FINETUNING_RESOURCE_NAME
    ...    as test variables. Uses suite-level cache to avoid re-querying the API across tests,
    ...    but always sets test-level variables so each test has explicit preconditions.
    # Check suite cache first — avoids redundant API queries across tests
    ${cached_workload_id}=    Get Variable Value    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${None}
    ${cached_model_id}=       Get Variable Value    ${_CACHED_FINETUNED_MODEL_ID}        ${None}
    ${cached_resource_name}=  Get Variable Value    ${_CACHED_FINETUNING_RESOURCE_NAME}  ${None}
    IF    $cached_workload_id != $None and $cached_model_id != $None and $cached_resource_name != $None
        VAR    ${TEST_FINETUNING_WORKLOAD_ID}    ${cached_workload_id}    scope=TEST
        VAR    ${TEST_MANAGED_MODEL_ID}    ${cached_model_id}    scope=TEST
        VAR    ${TEST_FINETUNING_RESOURCE_NAME}    ${cached_resource_name}    scope=TEST
        Log    Reusing cached finetuning workload: ${cached_workload_id}, model: ${cached_model_id}, resource: ${cached_resource_name}    DEBUG
        RETURN
    END
    # Check if a FINE_TUNING workload already exists in namespace
    ${workload_id}=    Find finetuning workload in namespace
    IF    $workload_id != $None
        VAR    ${TEST_FINETUNING_WORKLOAD_ID}    ${workload_id}    scope=TEST
        VAR    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${workload_id}    scope=SUITE
        # Resolve model ID and resource name from the namespace model list
        ${model_id}=    Get finetuned model ID from workload    ${workload_id}
        Should Not Be Equal    ${model_id}    ${None}    msg=Found finetuning workload but no matching model in namespace
        VAR    ${TEST_MANAGED_MODEL_ID}    ${model_id}    scope=TEST
        VAR    ${_CACHED_FINETUNED_MODEL_ID}    ${model_id}    scope=SUITE
        # TEST_FINETUNING_RESOURCE_NAME is set as side-effect by Get finetuned model ID from workload
        VAR    ${_CACHED_FINETUNING_RESOURCE_NAME}    ${TEST_FINETUNING_RESOURCE_NAME}    scope=SUITE
        RETURN
    END
    # No workload found — trigger finetune
    Finetune dataset exists
    A finetune request is sent
    # A finetune request is sent sets TEST_MANAGED_MODEL_ID as test variable
    # Find the workload created by the finetune
    ${workload_id}=    Find finetuning workload in namespace
    Should Not Be Equal    ${workload_id}    ${None}    msg=No FINE_TUNING workload found after finetune request
    VAR    ${TEST_FINETUNING_WORKLOAD_ID}    ${workload_id}    scope=TEST
    # Resolve resource name from the newly created workload
    Get finetuned model ID from workload    ${workload_id}
    # TEST_FINETUNING_RESOURCE_NAME is set as side-effect above
    # Cache all IDs for subsequent tests
    VAR    ${_CACHED_FINETUNING_WORKLOAD_ID}    ${workload_id}    scope=SUITE
    VAR    ${_CACHED_FINETUNED_MODEL_ID}    ${TEST_MANAGED_MODEL_ID}    scope=SUITE
    VAR    ${_CACHED_FINETUNING_RESOURCE_NAME}    ${TEST_FINETUNING_RESOURCE_NAME}    scope=SUITE

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

Get finetuned model ID from workload
    [Documentation]    Returns the AIMModel ID for a finetuning workload.
    ...    Also sets TEST_FINETUNING_RESOURCE_NAME to the actual K8s job name.
    ...    Finds the model in the namespace model list by matching on workloadId.
    [Arguments]    ${workload_id}
    ${namespace}=    Get Project Namespace
    ${models_response}=    Get models    namespace=${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${models_response.json()}    data
    FOR    ${model}    IN    @{models}
        ${wid}=    Evaluate    $model.get('workloadId')
        IF    "${wid}" == "${workload_id}"
            ${model_id}=    Get From Dictionary    ${model}    id
            ${resource_name}=    Get From Dictionary    ${model}    resourceName
            VAR    ${TEST_FINETUNING_RESOURCE_NAME}    ${resource_name}    scope=TEST
            RETURN    ${model_id}
        END
    END
    Fail    Could not find model with workloadId=${workload_id} in the namespace model list

The finetuned model should appear in the namespace model list
    [Documentation]    Verifies the finetuned model appears in the K8s-based namespace model list.
    ...    The list combines in-progress finetuning jobs and completed AIMModel CRs.
    ...    Searches by workload_id and checks that the expected response fields are present.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}    msg=No finetuning workload ID set
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${models}=    Get From Dictionary    ${json}    data
    FOR    ${model}    IN    @{models}
        ${wid}=    Evaluate    $model.get('workloadId')
        IF    "${wid}" == "${TEST_FINETUNING_WORKLOAD_ID}"
            Dictionary Should Contain Key    ${model}    name
            Dictionary Should Contain Key    ${model}    status
            Dictionary Should Contain Key    ${model}    resourceName
            Log    Found model in list: name=${model['name']} status=${model['status']}    INFO
            RETURN
        END
    END
    Fail    Finetuning model with workload_id=${TEST_FINETUNING_WORKLOAD_ID} not found in model list

Finetuned model should have expected fields
    [Documentation]    Verifies the finetuned model can be retrieved by resource name and has expected K8s-sourced fields.
    ...    Fetches the model by TEST_FINETUNING_RESOURCE_NAME and checks: name, resource_name, status.
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}    msg=No finetuning resource name set
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    ${TEST_FINETUNING_RESOURCE_NAME}    expected_status=200    namespace=${namespace}
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    name
    Dictionary Should Contain Key    ${json}    resourceName
    Dictionary Should Contain Key    ${json}    status

Finetuning workload should reach status "${target_status}"
    [Documentation]    Polls the namespace model list until the finetuning model reaches the target status.
    ...    Uses the K8s-based model list (GET /namespaces/{ns}/models), searching by workloadId.
    ...    Fails fast (Fatal Error) if the model enters Failed state before reaching the target.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}    msg=No finetuning workload ID set
    IF    "${target_status}" == "Complete"
        VAR    ${timeout}    15 min
    ELSE
        VAR    ${timeout}    5 min
    END
    Wait Until Keyword Succeeds    ${timeout}    10 sec
    ...    Finetuning model status should be    ${target_status}

Finetuning model status should be
    [Documentation]    Asserts the finetuning model has the expected status.
    ...    Calls Fatal Error on Failed state to bypass Wait Until Keyword Succeeds retry.
    [Arguments]    ${target_status}
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    FOR    ${model}    IN    @{models}
        ${wid}=    Evaluate    $model.get('workloadId')
        IF    "${wid}" == "${TEST_FINETUNING_WORKLOAD_ID}"
            ${status}=    Get From Dictionary    ${model}    status
            IF    "${status}" == "Failed" and "${target_status}" != "Failed"
                Fatal Error    Finetuning model entered Failed state (expected ${target_status})
            END
            Should Be Equal    ${status}    ${target_status}
            ...    msg=Finetuning model status: ${status} (waiting for ${target_status})
            Log    Finetuning model reached status: ${status}    INFO
            RETURN
        END
    END
    Fail    Finetuning model with workload_id=${TEST_FINETUNING_WORKLOAD_ID} not found in model list

Finetuned model onboarding status should be "${target_status}"
    [Documentation]    Polls the namespace model list until the finetuned model reaches the expected status.
    ...    In the K8s-first model, "ready" maps to Complete status in the model list.
    ...    Searches by TEST_FINETUNING_WORKLOAD_ID so it works for both in-progress jobs and completed AIMModel CRs.
    Should Not Be Equal    ${TEST_FINETUNING_WORKLOAD_ID}    ${None}    msg=No finetuning workload ID set
    # Map legacy "ready" status to K8s-based "Complete"
    VAR    ${k8s_status}    ${target_status}
    IF    "${target_status}" == "ready"
        VAR    ${k8s_status}    Complete
    END
    Wait Until Keyword Succeeds    10 min    10 sec
    ...    Finetuned model k8s status should be    ${k8s_status}    ${target_status}

Finetuned model k8s status should be
    [Documentation]    Asserts the finetuned model has the expected K8s status.
    ...    Calls Fatal Error on Failed state to bypass Wait Until Keyword Succeeds retry.
    [Arguments]    ${k8s_status}    ${original_target}
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    FOR    ${model}    IN    @{models}
        ${wid}=    Evaluate    $model.get('workloadId')
        IF    "${wid}" == "${TEST_FINETUNING_WORKLOAD_ID}"
            ${status}=    Get From Dictionary    ${model}    status
            IF    "${status}" == "Failed" and "${k8s_status}" != "Failed"
                Fatal Error    Finetuned model ${TEST_FINETUNING_WORKLOAD_ID} entered Failed status (expected ${original_target})
            END
            Should Be Equal    ${status}    ${k8s_status}
            ...    msg=Finetuned model status: ${status} (waiting for ${k8s_status})
            Log    Finetuned model reached target status: ${status}    INFO
            RETURN
        END
    END
    Fail    Finetuned model with workload_id=${TEST_FINETUNING_WORKLOAD_ID} not found in model list

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
    ${yaml}=    Catenate    SEPARATOR=\n
    ...    apiVersion: aim.eai.amd.com/v1alpha1
    ...    kind: AIMModel
    ...    metadata:
    ...    \ \ name: ${name}
    ...    \ \ labels:
    ...    \ \ \ \ aiwb.apps.eai.amd.com/model-name: "${name}"
    ...    spec:
    ...    \ \ image: "fake-registry/dummy:latest"
    ${tmpfile}=    Set Variable    /tmp/aimmodel-${name}.yaml
    Create File    ${tmpfile}    ${yaml}
    ${result}=    Run Process    kubectl    apply    -f    ${tmpfile}    -n    ${namespace}
    Remove File    ${tmpfile}
    Should Be Equal As Integers    ${result.rc}    0    msg=Failed to create AIMModel CR: ${result.stderr}
    VAR    ${TEST_DUMMY_AIMMODEL_NAME}    ${name}    scope=TEST
    VAR    ${_CACHED_DUMMY_AIMMODEL_NAME}    ${name}    scope=SUITE
    Log    Created dummy AIMModel CR '${name}' in namespace ${namespace}    INFO

The dummy AIMModel should appear in the namespace model list
    [Documentation]    Verifies the dummy AIMModel CR appears in the K8s-based namespace model list
    ...    with expected fields: name, status (Complete), resource_name.
    Should Not Be Equal    ${TEST_DUMMY_AIMMODEL_NAME}    ${None}    msg=No dummy AIMModel name set
    ${namespace}=    Get Project Namespace
    ${response}=    Get models    namespace=${namespace}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${models}=    Get From Dictionary    ${json}    data
    FOR    ${model}    IN    @{models}
        ${rn}=    Get From Dictionary    ${model}    resourceName
        IF    "${rn}" == "${TEST_DUMMY_AIMMODEL_NAME}"
            Dictionary Should Contain Key    ${model}    name
            Dictionary Should Contain Key    ${model}    status
            Dictionary Should Contain Key    ${model}    resourceName
            Should Be Equal    ${model['status']}    Complete
            Log    Found dummy model in list: name=${model['name']} status=${model['status']}    INFO
            RETURN
        END
    END
    Fail    Dummy AIMModel with resourceName=${TEST_DUMMY_AIMMODEL_NAME} not found in model list

The dummy AIMModel should be retrievable by resource name
    [Documentation]    Verifies the dummy AIMModel CR can be retrieved via GET /models/{resource_name}.
    ...    Checks expected fields: name, resource_name, status (Complete), canonical_name.
    Should Not Be Equal    ${TEST_DUMMY_AIMMODEL_NAME}    ${None}    msg=No dummy AIMModel name set
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    ${TEST_DUMMY_AIMMODEL_NAME}    expected_status=200    namespace=${namespace}
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    name
    Dictionary Should Contain Key    ${json}    resourceName
    Dictionary Should Contain Key    ${json}    status
    Should Be Equal    ${json['resourceName']}    ${TEST_DUMMY_AIMMODEL_NAME}
    Should Be Equal    ${json['status']}    Complete
    Log    Retrieved dummy model: name=${json['name']} status=${json['status']} canonicalName=${json.get('canonicalName', 'N/A')}    INFO

Getting a non-existent model should return 404
    [Documentation]    Verifies that requesting a model by a non-existent resource name returns 404.
    ${namespace}=    Get Project Namespace
    ${response}=    Get model    nonexistent-model-xyz    expected_status=404    namespace=${namespace}

Fine-tuned AIM service templates are available
    [Documentation]    Verifies that AIMServiceTemplates exist for the ready finetuned model.
    ...    Templates are provisioned by AIM Engine after model onboarding completes.
    ...    Requires: TEST_FINETUNING_RESOURCE_NAME
    Should Not Be Equal    ${TEST_FINETUNING_RESOURCE_NAME}    ${None}
    ...    msg=No finetuning resource name set — call "A finetuning workload exists" first
    ${namespace}=    Get Project Namespace
    ${response}=    List Fine-Tuned AIM Service Templates
    ...    ${TEST_FINETUNING_RESOURCE_NAME}
    ...    ${namespace}
    ...    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${templates}=    Get From Dictionary    ${json}    data
    ${count}=    Get Length    ${templates}
    Should Be True    ${count} > 0
    ...    msg=No AIMServiceTemplates found for fine-tuned model ${TEST_FINETUNING_RESOURCE_NAME}
    Log    Found ${count} AIMServiceTemplates for fine-tuned model ${TEST_FINETUNING_RESOURCE_NAME}    INFO

Fine-tuned model is deployed as an AIM service
    [Documentation]    Deploys the finetuned model via POST /aims/services.
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
    # Deploy via POST /aims/services (same endpoint as cluster models, auto-detects model type)
    ${deploy_data}=    Create Dictionary    replicas=${1}
    ${response}=    Deploy AIM    ${TEST_FINETUNING_RESOURCE_NAME}    ${deploy_data}    ${namespace}    expected_status=202
    ${json}=    Set Variable    ${response.json()}
    ${service_id}=    Get From Dictionary    ${json}    id
    VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST
    Log    Deployed fine-tuned model ${TEST_FINETUNING_RESOURCE_NAME} as AIMService ${service_id}    INFO

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
    [Documentation]    Verifies the fine-tuned AIMService appears in the chattable services list,
    ...    confirming it is accessible from the playground for chat.
    ...    Requires: TEST_AIM_ID
    Should Not Be Equal    ${TEST_AIM_ID}    ${None}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    ${response}=    List Chattable AIM Services    ${namespace}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${services}=    Get From Dictionary    ${json}    data
    FOR    ${service}    IN    @{services}
        ${service_id}=    Get From Dictionary    ${service}    id
        IF    "${service_id}" == "${TEST_AIM_ID}"
            Log    Fine-tuned model AIMService ${TEST_AIM_ID} is accessible for inference    INFO
            RETURN
        END
    END
    Fail    Fine-tuned model AIMService ${TEST_AIM_ID} not found in chattable services list

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

An AIMModel CR exists in the namespace
    [Documentation]    Creates an AIMModel CR directly via kubectl for deletion testing.
    ...    Sets TEST_MODEL_NAME to the created CR name and registers it for teardown cleanup.
    [Tags]    kubectl
    ${namespace}=           Get Project Namespace
    ${random_suffix}=       Generate Random String              8                   [LETTERS][NUMBERS]
    VAR    ${model_name}    test-model-${random_suffix}
    VAR    ${TEST_MODEL_NAME}    ${model_name}    scope=TEST
    ${yaml}=    Catenate    SEPARATOR=\n
    ...    apiVersion: aim.eai.amd.com/v1alpha1
    ...    kind: AIMModel
    ...    metadata:
    ...    ${SPACE}${SPACE}name: ${model_name}
    ...    ${SPACE}${SPACE}namespace: ${namespace}
    ...    spec:
    ...    ${SPACE}${SPACE}modelSources:
    ...    ${SPACE}${SPACE}- sourceUri: s3://test-bucket/${namespace}/models/${model_name}/
    VAR    ${tmpfile}    /tmp/aimmodel-${model_name}.yaml
    Create File             ${tmpfile}                          ${yaml}
    ${result}=              Run Process                         kubectl     apply   -f  ${tmpfile}  -n  ${namespace}
    Remove File             ${tmpfile}
    Should Be Equal As Integers     ${result.rc}                0
    ...    msg=Failed to create AIMModel CR: ${result.stderr}
    Append To List          ${CREATED_MODEL_IDS}                ${model_name}
    Log                     Created AIMModel CR ${model_name} in namespace ${namespace}     INFO

Delete AIMModel CR request is sent
    [Documentation]    Sends a DELETE request using the AIMModel CR name (TEST_MODEL_NAME).
    ${namespace}=           Get Project Namespace
    ${response}=            Delete model            ${TEST_MODEL_NAME}      namespace=${namespace}
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The AIMModel CR should not exist
    [Documentation]    Verifies via kubectl that the AIMModel CR no longer exists in the namespace.
    ${namespace}=           Get Project Namespace
    ${result}=              Run Process     kubectl     get     aimmodels   ${TEST_MODEL_NAME}  -n  ${namespace}
    Should Not Be Equal As Integers     ${result.rc}        0
    ...    msg=AIMModel CR ${TEST_MODEL_NAME} still exists in namespace ${namespace}
    Log                     Confirmed AIMModel CR ${TEST_MODEL_NAME} was deleted    INFO

Finetunable models list is requested
    [Documentation]    Requests the list of finetunable models and stores the response.
    ${response}=    Get finetunable models    expected_status=200
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

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
