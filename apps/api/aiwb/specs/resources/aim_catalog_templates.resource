# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test templates for AIM catalog testing.
...                 These templates contain all test logic for end-to-end AIM testing.
...                 Python orchestration layer only controls which models to test and in what order.
...
...                 Each template implements a specific test scenario:
...                 - Deploy: Deploy AIM and verify AIM service creation
...                 - Running State: Verify deployment reaches Running status
...                 - Inference: Test inference via external endpoint
...                 - Metrics: Verify AIM service details and resources
...                 - Undeploy: Remove deployment and verify cleanup

Resource            aiwb_aims.resource
Resource            aims/api_keys.resource
Resource            api/aims.resource
Resource            api/models.resource
Library             Collections
Library             RequestsLibrary
Library             OperatingSystem
Library             Process
Library             TestPrefix


*** Variables ***
# Track AIM state for catalog tests
@{DEPLOYED_AIMS_LIST}               @{EMPTY}


*** Keywords ***
Test Template: Deploy AIM Model
    [Documentation]    Test template for deploying an AIM model.
    ...                This template:
    ...                - Ensures project exists with user access (Given)
    ...                - Ensures HuggingFace token secret exists if needed (Given)
    ...                - Looks up the AIM by image name (substring match on spec.image)
    ...                - Prepares deployment configuration
    ...                - Deploys the AIM (When)
    ...                - Verifies AIM service is created (Then)
    ...
    ...                Args:
    ...                - docker_image: Full docker image reference (e.g., ghcr.io/silogen/aim-foo:0.11.0)
    ...                - requires_hf_token: Boolean indicating if HuggingFace token is required
    [Arguments]    ${docker_image}    ${requires_hf_token}

    Log    Deploying AIM: ${docker_image} (HF token required: ${requires_hf_token})    INFO

    # GIVEN - Ensure prerequisites (each test is self-contained)
    ${catalog_project}=    Test Name    aim-catalog
    A ready project "${catalog_project}" with user access exists
    Project quota is set to    gpu_count=${MAX_GPU_COUNT}
    IF    ${requires_hf_token}
        HuggingFace token secret exists in namespace
    END

    # Look up AIM by docker image reference to get its resource_name
    ${aim_resource_name}=    Find AIM by image name    ${docker_image}
    ${namespace}=    Get Project Namespace

    # Prepare deployment configuration
    # allowUnoptimized lets models deploy even when recommended profile IDs aren't present
    # in the test cluster's runtime configs — needed for pre-release catalog validation.
    # imagePullSecrets passes the GHCR pull credentials copied to the namespace in suite
    # setup, so kserve predictor pods can pull private ghcr.io/silogen images.
    ${pull_secrets}=    Create List    regcred
    ${deploy_data}=    Create Dictionary
    ...    replicas=1
    ...    allowUnoptimized=${True}
    ...    imagePullSecrets=${pull_secrets}

    # Add HF token secret if required by this model
    IF    ${requires_hf_token}
        Set To Dictionary    ${deploy_data}    hfToken=${HF_TOKEN_SECRET_NAME}
        Log    Added HF token secret ${HF_TOKEN_SECRET_NAME} to deployment configuration    DEBUG
    END

    # Deploy the AIM (creates an AIMService)
    ${response}=    Deploy AIM
    ...    ${aim_resource_name}
    ...    ${deploy_data}
    ...    ${namespace}
    ...    expected_status=any

    # Handle both new deployment (202) and already deployed (409)
    IF    ${response.status_code} == 202
        # New deployment - extract AIM service ID
        ${json}=    Set Variable    ${response.json()}
        ${service_id}=    Get From Dictionary    ${json}    id

        # Track deployed AIM service for cleanup
        Append To List    ${DEPLOYED_AIMS_LIST}    ${service_id}

        Log    Created new AIM service ${service_id} for ${docker_image}    INFO
    ELSE IF    ${response.status_code} == 409
        # Already deployed - get existing service
        Log    AIM ${docker_image} already deployed, using existing service    WARN
        ${service_id}=    Get existing workload ID for AIM    ${aim_resource_name}

        # Track deployed AIM service for cleanup
        Append To List    ${DEPLOYED_AIMS_LIST}    ${service_id}

        Log    Using existing AIM service ${service_id} for ${docker_image}    INFO
    ELSE
        Fail    Unexpected status code ${response.status_code} when deploying AIM ${docker_image}
    END

    # Set variables for subsequent tests
    Set Test Variable    ${TEST_AIM_ID}    ${service_id}
    Set Test Variable    ${TEST_AIM_NAME}    ${aim_resource_name}

    # Verify AIM service exists
    ${response}=    Get AIM Service By ID    ${service_id}    expected_status=200
    Should Not Be Empty    ${response.json()}    msg=AIM service ${service_id} should exist

    # Ensure API key exists for this test (creates if needed, reuses existing)
    Api key exists for user

    # Assign API key to this AIM for external endpoint access
    Api key is assigned to AIMS model
    Log    Assigned API key to AIM ${docker_image}    DEBUG

    Log    Successfully deployed AIM ${docker_image} with service ID ${service_id}    INFO

Test Template: Verify AIM Running State
    [Documentation]    Test template for verifying AIM reaches Running state.
    ...                This template:
    ...                - Verifies AIM is deployed (Given - fails if not)
    ...                - Waits for the deployed AIM service to reach Running status
    ...                - Verifies service has proper status
    ...                - Fails fast if service enters Failed or Degraded state
    ...
    ...                Args:
    ...                - docker_image: Full docker image reference for logging purposes
    [Arguments]    ${docker_image}

    # GIVEN - Verify prerequisites from previous test
    AIM "${docker_image}" is deployed

    Log    Waiting for AIM ${docker_image} (service ${TEST_AIM_ID}) to reach Running state    INFO

    # Wait for AIM service to reach Running state (uses aiwb_aims keyword with fast-fail)
    Wait for AIM workload to reach state    Running    timeout=${AIM_DEPLOY_TIMEOUT}    interval=10

    Log    AIM ${docker_image} successfully reached Running state    INFO

Test Template: Run AIM Inference
    [Documentation]    Test template for running inference on a deployed AIM.
    ...                This template:
    ...                - Verifies AIM is Running (Given - fails if not)
    ...                - Gets external endpoint from AIM service
    ...                - Lists available models from endpoint
    ...                - Runs a simple inference request
    ...                - Verifies response is valid
    ...
    ...                Args:
    ...                - docker_image: Full docker image reference
    [Arguments]    ${docker_image}

    Log    Testing inference for AIM ${docker_image}    INFO

    # GIVEN - Verify prerequisites from previous test
    AIM "${docker_image}" is Running

    # Ensure API key exists for this test (self-contained)
    Api key exists for user

    # Assign API key to this AIM for external endpoint access
    Api key is assigned to AIMS model
    Log    API key assigned for inference testing    DEBUG

    # Get AIM service details to get inference endpoint
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${json}=    Set Variable    ${response.json()}

    # Prefer internal endpoint when running inside K8s (external is unreachable from in-cluster)
    Dictionary Should Contain Key    ${json}    endpoints    msg=AIM service should have endpoints field
    ${endpoints}=    Get From Dictionary    ${json}    endpoints
    Should Not Be Equal    ${endpoints}    ${None}    msg=AIM service endpoints should not be None
    ${in_cluster}=    Evaluate    __import__('os').path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token')
    ${has_internal}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${endpoints}    internal
    IF    ${in_cluster} and ${has_internal}
        ${inference_host}=    Get From Dictionary    ${endpoints}    internal
        Log    Running in-cluster, using internal endpoint: ${inference_host}    INFO
    ELSE
        Dictionary Should Contain Key    ${endpoints}    external    msg=Endpoints should contain external
        ${inference_host}=    Get From Dictionary    ${endpoints}    external
        Should Not Be Empty    ${inference_host}    msg=external endpoint should not be empty
        Log    Using external endpoint: ${inference_host}    DEBUG
    END

    # List available models from endpoint (using API key)
    ${models}=    List models from external endpoint    ${inference_host}    ${TEST_AIM_ID}    ${TEST_API_KEY_VALUE}
    Should Be True    isinstance($models, list)    msg=Models data should be a list
    ${model_count}=    Get Length    ${models}
    Should Be True    ${model_count} > 0    msg=Endpoint should return at least one model

    # Get the first available model name for inference
    ${model_data}=    Get From List    ${models}    0
    ${model_id}=    Get From Dictionary    ${model_data}    id

    Log    Running inference with model: ${model_id}    DEBUG

    # Run a simple inference request
    ${inference_response}=    Run simple inference    ${inference_host}    ${model_id}    ${TEST_AIM_ID}

    # Verify inference response
    Should Not Be Empty    ${inference_response}    msg=Inference response should not be empty
    Log    Inference completed successfully for ${docker_image}    INFO

Test Template: Verify AIM Metrics
    [Documentation]    Test template for verifying AIM service details are complete.
    ...                This template:
    ...                - Verifies AIM is Running (Given - fails if not)
    ...                - Verifies AIM service has complete metadata, spec, and status
    ...                - Checks endpoints are populated
    ...                - Verifies model spec information
    ...
    ...                Args:
    ...                - docker_image: Full docker image reference
    [Arguments]    ${docker_image}

    Log    Verifying details for AIM ${docker_image}    INFO

    # GIVEN - Verify prerequisites from previous test
    AIM "${docker_image}" is Running

    # Get AIM service details
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${json}=    Set Variable    ${response.json()}

    # Verify core AIM service fields exist
    Dictionary Should Contain Key    ${json}    id    msg=AIM service should have id
    Dictionary Should Contain Key    ${json}    metadata    msg=AIM service should have metadata
    Dictionary Should Contain Key    ${json}    spec    msg=AIM service should have spec
    Dictionary Should Contain Key    ${json}    status    msg=AIM service should have status
    Dictionary Should Contain Key    ${json}    endpoints    msg=AIM service should have endpoints

    # Verify metadata
    ${metadata}=    Get From Dictionary    ${json}    metadata
    Dictionary Should Contain Key    ${metadata}    name    msg=Metadata should have name
    Dictionary Should Contain Key    ${metadata}    namespace    msg=Metadata should have namespace

    # Verify spec contains model info
    ${spec}=    Get From Dictionary    ${json}    spec
    Dictionary Should Contain Key    ${spec}    model    msg=Spec should have model field
    ${model}=    Get From Dictionary    ${spec}    model
    Dictionary Should Contain Key    ${model}    name    msg=Model should have name field

    # Verify status is Running
    ${status_dict}=    Get From Dictionary    ${json}    status
    ${status}=    Get From Dictionary    ${status_dict}    status
    Should Be Equal    ${status}    Running    msg=AIM service should be Running

    # Verify endpoints are populated (should be when Running)
    ${endpoints}=    Get From Dictionary    ${json}    endpoints
    Should Not Be Equal    ${endpoints}    ${None}    msg=Endpoints should not be None when Running
    Dictionary Should Contain Key    ${endpoints}    external    msg=Endpoints should have external field
    ${external}=    Get From Dictionary    ${endpoints}    external
    Should Not Be Empty    ${external}    msg=External endpoint should not be empty when Running

    Log    Details verification passed for ${docker_image}    INFO

Test Template: Undeploy AIM Model
    [Documentation]    Test template for undeploying an AIM model.
    ...                This template:
    ...                - Verifies AIM is deployed (Given - fails if not)
    ...                - Sends undeploy request
    ...                - Waits for AIM service to be deleted
    ...                - Verifies cleanup from database
    ...                - Verifies cleanup from Kubernetes
    ...
    ...                Args:
    ...                - docker_image: Full docker image reference
    [Arguments]    ${docker_image}

    Log    Undeploying AIM ${docker_image}    INFO

    # GIVEN - Verify prerequisites from previous test
    AIM "${docker_image}" is deployed
    ${namespace}=    Get Project Namespace

    # Get AIM service details for Kubernetes verification later
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${service_data}=    Set Variable    ${response.json()}
    ${metadata}=    Get From Dictionary    ${service_data}    metadata
    ${service_name}=    Get From Dictionary    ${metadata}    name

    # Send undeploy request (uses service_id and namespace)
    ${response}=    Undeploy AIM
    ...    ${TEST_AIM_ID}
    ...    ${namespace}
    ...    expected_status=204

    Log    Undeploy request sent for AIM ${docker_image}    DEBUG

    # Wait for AIM service to reach Deleted state or be removed (up to 60 seconds)
    Wait for catalog AIM workload to reach state    Deleted    timeout=60    interval=5    workload_id=${TEST_AIM_ID}

    # Verify AIM service is removed from database
    ${response}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=any
    IF    ${response.status_code} == 404
        Log    AIM service ${TEST_AIM_ID} removed from database    DEBUG
    ELSE IF    ${response.status_code} == 200
        ${json}=    Set Variable    ${response.json()}
        ${status_dict}=    Get From Dictionary    ${json}    status
        ${status}=    Get From Dictionary    ${status_dict}    status
        Should Be Equal    ${status}    Deleted
        ...    msg=AIM service should have Deleted status
        Log    AIM service ${TEST_AIM_ID} marked as Deleted in database    DEBUG
    ELSE
        Fail    Unexpected status code: ${response.status_code}
    END

    # Verify deployment removed from Kubernetes
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify AIM deployment gone    ${service_name}    ${namespace}

    # Remove from tracking list
    ${list_contains}=    Run Keyword And Return Status
    ...    List Should Contain Value    ${DEPLOYED_AIMS_LIST}    ${TEST_AIM_ID}
    IF    ${list_contains}
        Remove Values From List    ${DEPLOYED_AIMS_LIST}    ${TEST_AIM_ID}
    END

    Log    Successfully undeployed AIM ${docker_image}    INFO

# Helper keywords for catalog testing

AIM "${image_name}" is deployed
    [Documentation]    Verifies that an AIM has been deployed (AIM service exists).
    ...                Accepts full docker image reference or short image name.
    ...                Sets TEST_AIM_NAME and TEST_AIM_ID variables.
    ${catalog_project}=    Test Name    aim-catalog
    A ready project "${catalog_project}" with user access exists

    ${aim_resource_name}=    Find AIM by image name    ${image_name}
    ${service_id}=    Get existing workload ID for AIM    ${aim_resource_name}
    Should Not Be Equal    ${service_id}    ${None}
    ...    msg=AIM ${image_name} is not deployed (no AIM service found)

    Set Test Variable    ${TEST_AIM_NAME}    ${aim_resource_name}
    Set Test Variable    ${TEST_AIM_ID}    ${service_id}
    Log    AIM ${image_name} is deployed with service ${service_id}    DEBUG

AIM "${image_name}" is Running
    [Documentation]    Verifies that an AIM is in Running state.
    ...                Accepts full docker image reference or short image name.
    ...                Sets TEST_AIM_NAME and TEST_AIM_ID variables.
    ${catalog_project}=    Test Name    aim-catalog
    A ready project "${catalog_project}" with user access exists

    ${aim_resource_name}=    Find AIM by image name    ${image_name}
    ${service_id}=    Get existing workload ID for AIM    ${aim_resource_name}

    ${response}=    Get AIM Service By ID    ${service_id}    expected_status=200
    ${json}=    Set Variable    ${response.json()}
    ${status_dict}=    Get From Dictionary    ${json}    status
    ${status}=    Get From Dictionary    ${status_dict}    status

    Should Be Equal    ${status}    Running
    ...    msg=AIM ${image_name} is not Running (status: ${status})

    Set Test Variable    ${TEST_AIM_NAME}    ${aim_resource_name}
    Set Test Variable    ${TEST_AIM_ID}    ${service_id}
    Log    AIM ${image_name} is Running (service ${service_id})    DEBUG

Find AIM by image name
    [Documentation]    Finds an AIM cluster model by image name substring match on spec.image.
    ...                Returns the AIM's metadata.name (Kubernetes resource name). Fails if not found.
    ...
    ...                Accepts either a full docker image reference
    ...                (e.g., ghcr.io/silogen/aim-foo:0.11.0) or a short image name
    ...                (e.g., aim-foo). Uses substring matching so both forms work.
    [Arguments]    ${image_name}

    ${response}=    List AIMs    expected_status=200
    ${aims_data}=    Set Variable    ${response.json()}
    ${aims_list}=    Set Variable    ${aims_data['data']}

    # Search for AIM whose spec.image contains the image_name (substring match).
    # spec.image is the full Docker image reference, e.g.
    # "ghcr.io/silogen/aim-openai-gpt-oss-20b:0.11.0", which always
    # contains the short image name "aim-openai-gpt-oss-20b".
    ${found_aim}=    Set Variable    ${None}
    FOR    ${aim}    IN    @{aims_list}
        ${current_ref}=    Set Variable    ${aim}[spec][image]
        IF    "${image_name}" in "${current_ref}"
            ${found_aim}=    Set Variable    ${aim}
            Log    Found AIM ${image_name} (image: ${current_ref}, resource: ${aim}[metadata][name])    DEBUG
            BREAK
        END
    END

    # Verify AIM was found
    Should Not Be Equal    ${found_aim}    ${None}
    ...    msg=AIM with image_name '${image_name}' not found in system. Available AIMs: ${aims_list}

    RETURN    ${found_aim}[metadata][name]

Get existing workload ID for AIM
    [Documentation]    Gets the existing AIM service ID for a deployed AIM.
    ...                Uses AIMServices API to find a service for the given model resource_name.
    [Arguments]    ${aim_resource_name}

    ${namespace}=    Get Project Namespace
    ${existing}=    Find Existing AIM Service    ${namespace}    ${aim_resource_name}
    IF    $existing == $None
        RETURN    ${None}
    END
    ${service_id}=    Get From Dictionary    ${existing}    id
    RETURN    ${service_id}

Wait for catalog AIM workload to reach state
    [Documentation]    Waits for the catalog test AIM service to reach the specified state.
    ...                Delegates to the shared polling keyword from catalog_aims.resource
    ...                after setting TEST_AIM_ID to the provided workload_id.
    [Arguments]    ${target_state}    ${timeout}=1800    ${interval}=5    ${workload_id}=${None}

    Should Not Be Equal    ${workload_id}    ${None}    msg=workload_id must be provided
    Set Test Variable    ${TEST_AIM_ID}    ${workload_id}
    Wait for AIM workload to reach state    ${target_state}    timeout=${timeout}    interval=${interval}

Run simple inference
    [Documentation]    Runs an inference request to test the model.
    ...                Automatically detects if model supports chat interface and uses appropriate endpoint.
    ...                Chat models: Tests /v1/chat/completions with instruction-following
    ...                Completion models: Tests /v1/completions with text continuation
    [Arguments]    ${external_host}    ${model_id}    ${workload_id}

    # Detect if model supports chat based on AIM metadata tags
    ${supports_chat}=    Model Supports Chat    ${TEST_AIM_NAME}

    IF    ${supports_chat}
        Log    Model supports chat - testing /v1/chat/completions endpoint    INFO
        ${response}=    Run Chat Inference    ${external_host}    ${model_id}    ${workload_id}    ${TEST_API_KEY_VALUE}
        Log    Chat inference successful: ${response}    INFO
        RETURN    ${response}
    ELSE
        Log    Model does not support chat - testing /v1/completions endpoint    INFO
        ${response}=    Run Completion Inference    ${external_host}    ${model_id}    ${workload_id}    ${TEST_API_KEY_VALUE}
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
    ...                - namespace: Kubernetes namespace (uses TEST_PROJECT[name])
    [Arguments]    ${secret_name}=${HF_TOKEN_SECRET_NAME}    ${namespace}=${None}
    IF    $namespace == $None
        ${namespace}=    Get Project Namespace
    END

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

Ensure GHCR pull secret exists in namespace
    [Documentation]    Ensures the GHCR image pull secret exists in the namespace.
    ...                Copies regcred from aim-system if missing. AIM inference server images are
    ...                private on ghcr.io/silogen and require credentials to pull.
    [Arguments]    ${namespace}    ${source_namespace}=aim-system    ${secret_name}=regcred

    Log    Checking GHCR pull secret "${secret_name}" in namespace ${namespace}    DEBUG

    ${result}=    Run Process    kubectl    get    secret    ${secret_name}
    ...    -n    ${namespace}
    ...    stdout=DEVNULL    stderr=PIPE
    IF    ${result.rc} == 0
        Log    GHCR pull secret "${secret_name}" already exists in namespace ${namespace}    DEBUG
        RETURN
    END

    Log    GHCR pull secret missing, copying from ${source_namespace} namespace    INFO

    ${get_result}=    Run Process    kubectl    get    secret    ${secret_name}
    ...    -n    ${source_namespace}
    ...    -o    json
    ...    stderr=PIPE

    Should Be Equal As Integers    ${get_result.rc}    0
    ...    msg=Failed to get ${secret_name} from ${source_namespace}. Error: ${get_result.stderr}

    # Strip cluster-specific metadata fields so the secret can be recreated in a new namespace.
    # Uses Evaluate + stdin to avoid shell quoting issues with multi-line JSON.
    ${clean_json}=    Evaluate
    ...    (lambda d: json.dumps({**d, 'metadata': {k: v for k, v in d['metadata'].items() if k not in ['namespace', 'resourceVersion', 'uid', 'creationTimestamp', 'ownerReferences', 'annotations']}}))(__import__('json').loads($get_result.stdout))
    ...    json
    ${copy_result}=    Run Process    kubectl    create    -n    ${namespace}    -f    -
    ...    stdin=${clean_json}
    ...    stderr=PIPE

    Should Be Equal As Integers    ${copy_result.rc}    0
    ...    msg=Failed to copy ${secret_name} to namespace ${namespace}. Error: ${copy_result.stderr}

    Log    GHCR pull secret "${secret_name}" copied to namespace ${namespace}    INFO

Setup AIM catalog testing
    [Documentation]    Suite setup for AIM catalog testing.
    ...                Cleans up the AIM catalog test project if it exists from a previous run,
    ...                then creates a fresh one. Only touches the test project — never other projects.

    Log    Starting AIM catalog testing suite    INFO
    Log    Test mode: ${TEST_MODE}    INFO

    ${catalog_project}=    Test Name    aim-catalog

    # Clean up stale test project from previous runs (only our project, never others).
    # Waits for deletion to complete so the next step creates a truly fresh project.
    TRY
        ${response}=    Get projects    expected_status=any
        IF    ${response.status_code} == 200
            VAR    ${projects}    ${response.json()}[data]
            FOR    ${project}    IN    @{projects}
                IF    "${project}[name]" == "${catalog_project}"
                    Log    Deleting stale test project: ${project}[name] (${project}[id])    INFO
                    Delete project    ${project}[id]    expected_status=any
                    Wait Until Project Deleted    ${project}[id]    timeout=5 min
                END
            END
        END
    EXCEPT    AS    ${cleanup_error}
        Log    Pre-test cleanup: ${cleanup_error}    WARN
    END

    # Initialize tracking lists (for cleanup)
    VAR    @{DEPLOYED_AIMS_LIST}    scope=SUITE
    VAR    @{CREATED_PROJECT_IDS}    scope=SUITE
    VAR    @{TEST_API_KEYS}    scope=SUITE

    # Create the project for testing
    A ready project "${catalog_project}" with user access exists

    # AIM inference server images are private on ghcr.io/silogen — copy the pull secret
    # from aim-system so the project namespace can pull them before public release
    ${namespace}=    Get Project Namespace
    Ensure GHCR pull secret exists in namespace    ${namespace}

    Log    AIM catalog testing suite initialized    INFO

Cleanup AIM catalog testing
    [Documentation]    Suite teardown for AIM catalog testing.
    ...                Performs best-effort cleanup of any remaining deployments.
    ...                Deletes all created projects (which cascades cleanup of AIM services).

    Log    Cleaning up AIM catalog testing suite    INFO

    TRY
        # Check if we have a project
        ${project_id}=    Get Variable Value    ${TEST_PROJECT_ID}    ${None}

        IF    $project_id is not None
            ${aims_count}=    Get Length    ${DEPLOYED_AIMS_LIST}
            Log    Found ${aims_count} deployed AIM services to clean up    DEBUG

            IF    ${aims_count} > 0
                ${namespace}=    Get Project Namespace
                FOR    ${service_id}    IN    @{DEPLOYED_AIMS_LIST}
                    TRY
                        ${response}=    Undeploy AIM
                        ...    ${service_id}
                        ...    ${namespace}
                        ...    expected_status=any
                        Log    Undeploy request sent for AIM service ${service_id}    DEBUG
                    EXCEPT
                        Log    Failed to undeploy AIM service ${service_id} (may already be undeployed)    DEBUG
                    END
                END

                Log    AIM undeploy requests completed    INFO

                VAR    @{DEPLOYED_AIMS_LIST}    scope=SUITE
            END
        END
    EXCEPT
        Log    AIM cleanup completed with warnings (expected)    DEBUG
    END

    # Clean up all created projects (this will cascade delete any remaining AIM services)
    TRY
        Clean Up All Created Projects With Wait
    EXCEPT    AS    ${cleanup_error}
        Log    Project cleanup completed with warnings: ${cleanup_error}    DEBUG
    END

    Log    AIM catalog testing suite cleanup complete    INFO
