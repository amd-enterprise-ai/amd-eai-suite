# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test templates for AIM catalog testing.
...                 These templates contain all test logic for end-to-end AIM testing.
...                 Python orchestration layer only controls which models to test and in what order.
...
...                 Each template implements a specific test scenario:
...                 - Deploy: Deploy AIM and verify workload creation
...                 - Running State: Verify deployment reaches Running status
...                 - Inference: Test inference via external endpoint
...                 - Metrics: Verify metrics are available
...                 - Undeploy: Remove deployment and verify cleanup

Resource            catalog_aims.resource
Resource            catalog_workloads.resource
Resource            api/aims.resource
Resource            api/models.resource
Resource            kubectl_verification.resource
Library             Collections
Library             RequestsLibrary
Library             OperatingSystem
Library             Process


*** Variables ***
# Track AIM state for catalog tests
${CATALOG_TEST_AIM_ID}              ${None}
${CATALOG_DEPLOY_DATA}              ${None}
${CATALOG_WORKLOAD_ID}              ${None}
@{DEPLOYED_AIMS_LIST}               @{EMPTY}


*** Keywords ***
Test Template: Deploy AIM Model
    [Documentation]    Test template for deploying an AIM model.
    ...                This template:
    ...                - Ensures project exists with user access (Given)
    ...                - Ensures HuggingFace token secret exists if needed (Given)
    ...                - Looks up the AIM by image_name
    ...                - Prepares deployment configuration
    ...                - Deploys the AIM (When)
    ...                - Verifies workload is created in database (Then)
    ...
    ...                Args:
    ...                - image_name: The AIM image name (e.g., aim-meta-llama-llama-3-1-8b-instruct)
    ...                - requires_hf_token: Boolean indicating if HuggingFace token is required
    [Arguments]    ${image_name}    ${requires_hf_token}

    Log    Deploying AIM: ${image_name} (HF token required: ${requires_hf_token})    INFO

    # GIVEN - Ensure prerequisites (each test is self-contained)
    A ready project "e2e-aim-catalog" with user access exists
    IF    ${requires_hf_token}
        HuggingFace token secret exists in namespace
    END

    # Look up AIM by image_name to get its ID
    ${aim_id}=    Find AIM by image name    ${image_name}

    # Prepare deployment configuration
    ${deploy_data}=    Create Dictionary
    ...    replicas=1
    ...    cache_model=${True}

    # Add HF token secret if required by this model
    IF    ${requires_hf_token}
        Set To Dictionary    ${deploy_data}    hf_token=${HF_TOKEN_SECRET_NAME}
        Log    Added HF token secret ${HF_TOKEN_SECRET_NAME} to deployment configuration    DEBUG
    END

    # Deploy the AIM
    ${response}=    Deploy AIM
    ...    ${aim_id}
    ...    ${deploy_data}
    ...    ${TEST_PROJECT_ID}
    ...    expected_status=any

    # Handle both new deployment (202) and already deployed (409)
    IF    ${response.status_code} == 202
        # New deployment - extract workload ID
        ${json}=    Set Variable    ${response.json()}
        ${workload_id}=    Get From Dictionary    ${json}    id

        # Track deployed AIM for cleanup
        Append To List    ${DEPLOYED_AIMS_LIST}    ${aim_id}

        Log    Created new workload ${workload_id} for AIM ${image_name}    INFO
    ELSE IF    ${response.status_code} == 409
        # Already deployed - get existing workload
        Log    AIM ${image_name} already deployed, using existing workload    WARN
        ${workload_id}=    Get existing workload ID for AIM    ${aim_id}

        # Track deployed AIM for cleanup
        Append To List    ${DEPLOYED_AIMS_LIST}    ${aim_id}

        Log    Using existing workload ${workload_id} for AIM ${image_name}    INFO
    ELSE
        Fail    Unexpected status code ${response.status_code} when deploying AIM ${image_name}
    END

    # Verify workload exists in database
    ${response}=    Get menaged workload    ${workload_id}    expected_status=200
    Should Not Be Empty    ${response.json()}    msg=Workload ${workload_id} should exist in database

    # Ensure API key exists for this test (creates if needed, reuses existing)
    Api key exists for user

    # Assign API key to this AIM for external endpoint access
    Set Test Variable    ${AIMS_MODEL_ID}    ${aim_id}
    Api key is assigned to AIMS model
    Log    Assigned API key to AIM ${image_name}    DEBUG

    Log    Successfully deployed AIM ${image_name} with workload ID ${workload_id}    INFO

Test Template: Verify AIM Running State
    [Documentation]    Test template for verifying AIM reaches Running state.
    ...                This template:
    ...                - Verifies AIM is deployed (Given - fails if not)
    ...                - Waits for the deployed AIM workload to reach Running status
    ...                - Verifies workload has proper status
    ...                - Fails fast if workload enters Failed or Terminated state
    ...
    ...                Args:
    ...                - image_name: The AIM image name for logging purposes
    [Arguments]    ${image_name}

    # GIVEN - Verify prerequisites from previous test
    AIM "${image_name}" is deployed

    Log    Waiting for AIM ${image_name} (workload ${DEPLOYED_WORKLOAD_ID}) to reach Running state    INFO

    # Wait for workload to reach Running state (uses common keyword with fast-fail on Failed/Terminated)
    Wait for AIM workload to reach state    Running    timeout=600    interval=10

    Log    AIM ${image_name} successfully reached Running state    INFO

Test Template: Run AIM Inference
    [Documentation]    Test template for running inference on a deployed AIM.
    ...                This template:
    ...                - Verifies AIM is Running (Given - fails if not)
    ...                - Gets external endpoint
    ...                - Lists available models from endpoint
    ...                - Runs a simple inference request
    ...                - Verifies response is valid
    ...
    ...                Args:
    ...                - image_name: The AIM image name
    [Arguments]    ${image_name}

    Log    Testing inference for AIM ${image_name}    INFO

    # GIVEN - Verify prerequisites from previous test
    AIM "${image_name}" is Running

    # Ensure API key exists for this test (self-contained)
    Api key exists for user

    # Assign API key to this AIM for external endpoint access
    Set Test Variable    ${AIMS_MODEL_ID}    ${TEST_AIM_ID}
    Api key is assigned to AIMS model
    Log    API key assigned for inference testing    DEBUG

    # Get workload details to get external endpoint
    ${response}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=200
    ${workload}=    Set Variable    ${response.json()}

    # Get external endpoint
    ${output}=    Get From Dictionary    ${workload}    output
    Should Not Be Equal    ${output}    ${None}    msg=Workload output should not be None
    Dictionary Should Contain Key    ${output}    external_host    msg=Output should contain external_host
    ${external_host}=    Get From Dictionary    ${output}    external_host
    Should Not Be Empty    ${external_host}    msg=external_host should not be empty

    Log    External endpoint: ${external_host}    DEBUG

    # List available models from endpoint (using API key)
    ${models}=    List models from external endpoint    ${external_host}    ${DEPLOYED_WORKLOAD_ID}    ${CURRENT_API_KEY_VALUE}
    Should Be True    isinstance($models, list)    msg=Models data should be a list
    ${model_count}=    Get Length    ${models}
    Should Be True    ${model_count} > 0    msg=Endpoint should return at least one model

    # Get the first available model name for inference
    ${model_data}=    Get From List    ${models}    0
    ${model_id}=    Get From Dictionary    ${model_data}    id

    Log    Running inference with model: ${model_id}    DEBUG

    # Run a simple inference request
    ${inference_response}=    Run simple inference    ${external_host}    ${model_id}    ${DEPLOYED_WORKLOAD_ID}

    # Verify inference response
    Should Not Be Empty    ${inference_response}    msg=Inference response should not be empty
    Log    Inference completed successfully for ${image_name}    INFO

Test Template: Verify AIM Metrics
    [Documentation]    Test template for verifying AIM metrics are available.
    ...                This template:
    ...                - Verifies AIM is Running (Given - fails if not)
    ...                - Verifies workload details include allocated resources
    ...                - Checks GPU count and VRAM metrics
    ...                - Ensures metrics are properly populated
    ...
    ...                Args:
    ...                - image_name: The AIM image name
    [Arguments]    ${image_name}

    Log    Verifying metrics for AIM ${image_name}    INFO

    # GIVEN - Verify prerequisites from previous test
    AIM "${image_name}" is Running

    # Get workload details with resource metrics
    ${params}=    Create Dictionary    with_resources=true
    ${response}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=200    params=${params}
    ${workload}=    Set Variable    ${response.json()}

    # Verify allocated_resources field exists
    Dictionary Should Contain Key    ${workload}    allocated_resources
    ...    msg=Workload should have allocated_resources field

    ${allocated_resources}=    Get From Dictionary    ${workload}    allocated_resources
    Should Not Be Equal    ${allocated_resources}    ${None}
    ...    msg=Workload should have allocated_resources populated when requested with with_resources=true

    # Verify resource structure
    Should Be True    isinstance($allocated_resources, dict)
    ...    msg=allocated_resources should be a dictionary

    # Verify GPU count is present
    Dictionary Should Contain Key    ${allocated_resources}    gpu_count
    ...    msg=allocated_resources should have gpu_count field

    # Verify VRAM is present
    Dictionary Should Contain Key    ${allocated_resources}    vram
    ...    msg=allocated_resources should have vram field

    ${gpu_count}=    Get From Dictionary    ${allocated_resources}    gpu_count
    IF    $gpu_count is not None
        Should Be True    ${gpu_count} >= 0    msg=GPU count should be non-negative
        Log    AIM ${image_name} has ${gpu_count} GPU(s) allocated    INFO
    END

    ${vram}=    Get From Dictionary    ${allocated_resources}    vram
    IF    $vram is not None
        Log    AIM ${image_name} has ${vram} VRAM allocated    INFO
    END

    Log    Metrics verification passed for ${image_name}    INFO

Test Template: Undeploy AIM Model
    [Documentation]    Test template for undeploying an AIM model.
    ...                This template:
    ...                - Verifies AIM is deployed (Given - fails if not)
    ...                - Sends undeploy request
    ...                - Waits for workload to be deleted
    ...                - Verifies cleanup from database
    ...                - Verifies cleanup from Kubernetes
    ...
    ...                Args:
    ...                - image_name: The AIM image name
    [Arguments]    ${image_name}

    Log    Undeploying AIM ${image_name}    INFO

    # GIVEN - Verify prerequisites from previous test
    AIM "${image_name}" is deployed

    # Get workload details for Kubernetes verification later
    ${workload_response}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=200
    ${workload_data}=    Set Variable    ${workload_response.json()}
    ${workload_name}=    Get From Dictionary    ${workload_data}    name
    ${project}=    Get From Dictionary    ${workload_data}    project
    ${namespace}=    Get From Dictionary    ${project}    name

    # Send undeploy request
    ${response}=    Undeploy AIM
    ...    ${TEST_AIM_ID}
    ...    ${TEST_PROJECT_ID}
    ...    expected_status=204

    Log    Undeploy request sent for AIM ${image_name}    DEBUG

    # Wait for workload to reach Deleted state or be removed (up to 60 seconds)
    Wait for catalog AIM workload to reach state    Deleted    timeout=60    interval=5    workload_id=${DEPLOYED_WORKLOAD_ID}

    # Verify workload is removed from database
    ${response}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=any
    IF    ${response.status_code} == 404
        Log    Workload ${DEPLOYED_WORKLOAD_ID} removed from database    DEBUG
    ELSE IF    ${response.status_code} == 200
        ${json}=    Set Variable    ${response.json()}
        ${status}=    Get From Dictionary    ${json}    status
        Should Be Equal    ${status}    Deleted
        ...    msg=Workload should have Deleted status
        Log    Workload ${DEPLOYED_WORKLOAD_ID} marked as Deleted in database    DEBUG
    ELSE
        Fail    Unexpected status code: ${response.status_code}
    END

    # Verify deployment removed from Kubernetes
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify AIM deployment gone    ${workload_name}-predictor    ${namespace}

    # Remove from tracking list
    ${list_contains}=    Run Keyword And Return Status
    ...    List Should Contain Value    ${DEPLOYED_AIMS_LIST}    ${TEST_AIM_ID}
    IF    ${list_contains}
        Remove Values From List    ${DEPLOYED_AIMS_LIST}    ${TEST_AIM_ID}
    END

    Log    Successfully undeployed AIM ${image_name}    INFO

# Helper keywords for catalog testing

AIM "${image_name}" is deployed
    [Documentation]    Verifies that an AIM has been deployed (workload exists).
    ...                Sets TEST_AIM_ID and DEPLOYED_WORKLOAD_ID variables.
    A ready project "e2e-aim-catalog" with user access exists

    ${aim_id}=    Find AIM by image name    ${image_name}
    ${workload_id}=    Get existing workload ID for AIM    ${aim_id}
    Should Not Be Equal    ${workload_id}    ${None}
    ...    msg=AIM ${image_name} is not deployed (no workload found)

    Set Test Variable    ${TEST_AIM_ID}    ${aim_id}
    Set Test Variable    ${DEPLOYED_WORKLOAD_ID}    ${workload_id}
    Log    AIM ${image_name} is deployed with workload ${workload_id}    DEBUG

AIM "${image_name}" is Running
    [Documentation]    Verifies that an AIM is in Running state.
    ...                Sets TEST_AIM_ID and DEPLOYED_WORKLOAD_ID variables.
    A ready project "e2e-aim-catalog" with user access exists

    ${aim_id}=    Find AIM by image name    ${image_name}
    ${workload_id}=    Get existing workload ID for AIM    ${aim_id}

    ${response}=    Get menaged workload    ${workload_id}    expected_status=200
    ${workload}=    Set Variable    ${response.json()}
    ${status}=    Get From Dictionary    ${workload}    status

    Should Be Equal    ${status}    Running
    ...    msg=AIM ${image_name} is not Running (status: ${status})

    Set Test Variable    ${TEST_AIM_ID}    ${aim_id}
    Set Test Variable    ${DEPLOYED_WORKLOAD_ID}    ${workload_id}
    Log    AIM ${image_name} is Running (workload ${workload_id})    DEBUG

Find AIM by image name
    [Documentation]    Finds an AIM by its image_name and returns the ID.
    ...                Fails if AIM is not found.
    ...                Assumes TEST_PROJECT_ID is already set.
    [Arguments]    ${image_name}

    # Project context should already be set by suite setup or test setup
    ${response}=    List AIMs    ${TEST_PROJECT_ID}    expected_status=200
    ${aims_data}=    Set Variable    ${response.json()}
    ${aims_list}=    Set Variable    ${aims_data['data']}

    # Search for AIM with matching image_name
    ${aim_id}=    Set Variable    ${None}
    FOR    ${aim}    IN    @{aims_list}
        ${current_name}=    Set Variable    ${aim}[image_name]
        IF    "${current_name}" == "${image_name}"
            ${aim_id}=    Set Variable    ${aim}[id]
            Log    Found AIM ${image_name} with ID ${aim_id}    DEBUG
            BREAK
        END
    END

    # Verify AIM was found
    Should Not Be Equal    ${aim_id}    ${None}
    ...    msg=AIM with image_name '${image_name}' not found in system. Available AIMs: ${aims_list}

    RETURN    ${aim_id}

Get existing workload ID for AIM
    [Documentation]    Gets the existing workload ID for a deployed AIM.
    ...                Assumes TEST_PROJECT_ID is already set.
    [Arguments]    ${aim_id}

    # Project context should already be set by suite setup
    ${response}=    List AIMs    ${TEST_PROJECT_ID}    expected_status=200
    ${aims_data}=    Set Variable    ${response.json()}
    ${aims_list}=    Set Variable    ${aims_data['data']}

    FOR    ${aim}    IN    @{aims_list}
        ${current_id}=    Set Variable    ${aim}[id]
        IF    "${current_id}" == "${aim_id}"
            ${workload}=    Set Variable    ${aim}[workload]
            Should Not Be Equal    ${workload}    ${None}
            ...    msg=AIM ${aim_id} is deployed but has no workload
            ${workload_id}=    Set Variable    ${workload}[id]
            RETURN    ${workload_id}
        END
    END

    Fail    AIM ${aim_id} not found in list

Wait for catalog AIM workload to reach state
    [Documentation]    Waits for the catalog test workload to reach the specified state.
    ...                Polls the workload status every interval seconds for up to timeout seconds.
    [Arguments]    ${target_state}    ${timeout}=1800    ${interval}=5    ${workload_id}=${None}

    Should Not Be Equal    ${workload_id}    ${None}    msg=workload_id must be provided
    ${start_time}=    Evaluate    time.time()    modules=time
    ${end_time}=    Evaluate    ${start_time} + ${timeout}

    WHILE    True
        # Small delay before checking to prevent overwhelming the API
        Sleep    ${interval}s

        # Force session recreation to avoid connection pool issues
        Set Suite Variable    ${API_SESSION}    ${None}
        Create api session

        ${response}=    Get menaged workload    ${workload_id}    expected_status=any

        # Handle 404 for Deleted state
        IF    ${response.status_code} == 404 and "${target_state}" == "Deleted"
            Log    Workload ${workload_id} has been removed (404)    DEBUG
            RETURN
        END

        IF    ${response.status_code} != 200
            ${current_time}=    Evaluate    time.time()    modules=time
            IF    ${current_time} >= ${end_time}
                Fail    Timeout waiting for workload. Last status code: ${response.status_code}
            END
            CONTINUE
        END

        ${json}=    Set Variable    ${response.json()}
        ${status}=    Get From Dictionary    ${json}    status

        # Check if workload reached target state
        IF    "${status}" == "${target_state}"
            Log    Workload ${workload_id} reached ${target_state} state    INFO
            RETURN
        END

        # Check if workload failed
        IF    "${status}" == "Failed" or "${status}" == "Terminated"
            Fail    AIM workload ${workload_id} failed to start. Status: ${status}
        END

        # Check timeout
        ${current_time}=    Evaluate    time.time()    modules=time
        IF    ${current_time} >= ${end_time}
            Fail    Timeout waiting for AIM workload to reach ${target_state} status. Last status: ${status}
        END

        Log    Workload ${workload_id} status: ${status} (waiting for ${target_state})    TRACE
    END

Run simple inference
    [Documentation]    Runs an inference request to test the model.
    ...                Automatically detects if model supports chat interface and uses appropriate endpoint.
    ...                Chat models: Tests /v1/chat/completions with instruction-following
    ...                Completion models: Tests /v1/completions with text continuation
    [Arguments]    ${external_host}    ${model_id}    ${workload_id}

    # Detect if model supports chat based on AIM metadata tags
    ${supports_chat}=    Model Supports Chat    ${TEST_AIM_ID}

    IF    ${supports_chat}
        Log    Model supports chat - testing /v1/chat/completions endpoint    INFO
        ${response}=    Run Chat Inference    ${external_host}    ${model_id}    ${workload_id}    ${CURRENT_API_KEY_VALUE}
        Log    Chat inference successful: ${response}    INFO
        RETURN    ${response}
    ELSE
        Log    Model does not support chat - testing /v1/completions endpoint    INFO
        ${response}=    Run Completion Inference    ${external_host}    ${model_id}    ${workload_id}    ${CURRENT_API_KEY_VALUE}
        Log    Completion inference successful: ${response}    INFO
        RETURN    ${response}
    END

HuggingFace token secret exists in namespace
    [Documentation]    Ensures HuggingFace token secret exists in the project namespace.
    ...                Creates the secret from HF_TOKEN environment variable if it doesn't exist.
    ...                This is a Given-style keyword following BDD pattern.
    ...
    ...                Args:
    ...                - secret_name: Name of the secret to create (default: huggingface-token)
    ...                - namespace: Kubernetes namespace (uses TEST_PROJECT_SLUG)
    [Arguments]    ${secret_name}=${HF_TOKEN_SECRET_NAME}    ${namespace}=${TEST_PROJECT_SLUG}

    # Check if secret already exists in namespace
    ${result}=    Run Process    kubectl    get    secret    ${secret_name}
    ...    -n    ${namespace}
    ...    stderr=STDOUT

    IF    ${result.rc} == 0
        Log    Secret ${secret_name} already exists in namespace ${namespace}    INFO
        RETURN
    END

    # Secret doesn't exist, create it from HF_TOKEN environment variable
    Log    Secret ${secret_name} not found in ${namespace}, creating from HF_TOKEN env var    INFO

    # Get HF_TOKEN from environment
    ${hf_token}=    Get Environment Variable    HF_TOKEN    default=${EMPTY}
    Should Not Be Empty    ${hf_token}
    ...    msg=HF_TOKEN environment variable is not set. Please set it with your HuggingFace token.

    # Create Kubernetes secret with the token
    ${result}=    Run Process    kubectl    create    secret    generic    ${secret_name}
    ...    --from-literal\=token\=${hf_token}
    ...    -n    ${namespace}
    ...    stderr=STDOUT

    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to create HuggingFace token secret: ${result.stdout}

    Log    Created HuggingFace token secret ${secret_name} in namespace ${namespace}    INFO
