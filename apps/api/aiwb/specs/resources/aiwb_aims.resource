# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level AIM testing keywords.
...                 Provides business-logic level keywords for testing AIM operations.
...                 Uses the low-level API keywords from api/aims.resource to implement
...                 higher-level testing scenarios.
Resource            api/aims.resource
Resource            api/models.resource
Resource            api_keys.resource
Resource            aims/api_keys.resource
Resource    resources/airm_workloads.resource
Resource    resources/kubectl_verification.resource
Resource    resources/common/resource_resolver.resource
Resource    aiwb_common.resource
Library             Collections
Library             Process
Library             ../libraries/AutoscalingPayload.py


*** Variables ***
${TEST_AIM_NAME}            ${None}
${TEST_AIM}                  ${None}
${TEST_AIM_ID}              ${None}


*** Keywords ***
An AIM exists in system
    [Documentation]    Ensures an AIM exists and sets TEST_AIM_NAME by finding an AIM that is Ready
    ...    (compatible with cluster GPUs), doesn't require HF token, and uses version 0.8.5.
    ...    Short-circuits if TEST_AIM_NAME is already set (e.g., from Suite Setup).

    # Short-circuit if already selected
    ${already_set}=         Get Variable Value      ${TEST_AIM_NAME}    ${None}
    IF    $already_set != $None
        Log                     AIM already selected: ${TEST_AIM_NAME}    DEBUG
        RETURN
    END

    # List all available AIMs
    ${response}=            List AIMs               expected_status=200
    ${aims_data}=           Set Variable            ${response.json()}
    ${aims_list}=           Set Variable            ${aims_data['data']}

    # Verify at least one AIM exists
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} > 0            msg=No AIMs available in system

    # Find first AIM that is Ready, doesn't require HF token, and uses version 0.8.5
    ${found_aim}=           Set Variable            ${None}
    FOR    ${aim}    IN    @{aims_list}
        # Only consider AIMs with Ready status (compatible with cluster GPUs)
        ${aim_status}=          Evaluate                $aim.get('status_value', '')
        IF    "${aim_status}" != "Ready"
            CONTINUE
        END

        # Check if HF token is required
        ${requires_hf}=         Set Variable            ${False}
        TRY
            ${image_metadata}=      Get From Dictionary     ${aim['status']}        imageMetadata
            ${model}=               Get From Dictionary     ${image_metadata}       model
            ${requires_hf}=         Get From Dictionary     ${model}                hfTokenRequired                 default=${False}
        EXCEPT
            ${requires_hf}=         Set Variable            ${False}
        END

        # Check if version is 0.8.5 (resource name contains -0-8-5-)
        ${aim_name}=            Get From Dictionary     ${aim['metadata']}      name
        ${is_085}=              Evaluate                '-0-8-5-' in '''${aim_name}'''

        IF    not ${requires_hf} and ${is_085}
            ${found_aim}=           Set Variable            ${aim}
            BREAK
        END
    END

    # Fallback: if no v0.8.5 Ready AIM found, try any Ready AIM without HF token
    IF    ${found_aim} == ${None}
        Log    No Ready v0.8.5 AIM without HF token found, trying any Ready AIM    WARN
        FOR    ${aim}    IN    @{aims_list}
            ${aim_status}=          Evaluate                $aim.get('status_value', '')
            IF    "${aim_status}" != "Ready"
                CONTINUE
            END
            ${requires_hf}=         Set Variable            ${False}
            TRY
                ${image_metadata}=      Get From Dictionary     ${aim['status']}        imageMetadata
                ${model}=               Get From Dictionary     ${image_metadata}       model
                ${requires_hf}=         Get From Dictionary     ${model}                hfTokenRequired                 default=${False}
            EXCEPT
                ${requires_hf}=         Set Variable            ${False}
            END
            IF    not ${requires_hf}
                ${found_aim}=           Set Variable            ${aim}
                BREAK
            END
        END
    END

    # Final fallback: use first available AIM (may be unsupported on this cluster)
    IF    ${found_aim} == ${None}
        Log                     No Ready AIM found, using first available AIM    WARN
        ${found_aim}=           Get From List           ${aims_list}            0
    END

    ${aim_resource_name}=   Set Variable            ${found_aim['metadata']['name']}
    Log                     Using AIM: ${aim_resource_name}                 INFO
    Set Test Variable       ${TEST_AIM_NAME}                       ${aim_resource_name}
    Set Test Variable       ${TEST_AIM}             ${found_aim}

    # Extract display name (title) and canonical name from AIM image metadata
    ${display_name}=        Evaluate
    ...    $found_aim.get('status', {}).get('imageMetadata', {}).get('model', {}).get('title') or $aim_resource_name
    Set Test Variable       ${TEST_AIM_DISPLAY_NAME}                        ${display_name}
    Log                     AIM display name: ${display_name}               INFO

    ${canonical_name}=      Evaluate
    ...    $found_aim.get('status', {}).get('imageMetadata', {}).get('model', {}).get('canonicalName') or $aim_resource_name
    Set Test Variable       ${TEST_AIM_CANONICAL_NAME}                      ${canonical_name}
    Log                     AIM canonical name: ${canonical_name}           INFO

Valid AIM deploy data is prepared
    [Documentation]    Prepares and returns valid deployment data for an AIM
    ${deploy_data}=         Create Dictionary       replicas=1
    RETURN                  ${deploy_data}

Valid AIM deploy data with autoscaling is prepared
    [Documentation]    Prepares deployment data for an AIM with autoscaling enabled.
    ...                Creates KEDA-compatible autoscaling policy structure matching
    ...                AIMDeployPayload from apps/ui/aiwb/types/aims.ts.
    ...                Payload structure: top-level minReplicas/maxReplicas/autoScaling (camelCase).
    [Arguments]         ${min_replicas}=1    ${max_replicas}=3    ${metric}=running_requests    ${target_value}=10

    ${metric_query}=    Map Metric To Query    ${metric}

    # MUST match AutoscalingPolicyConfig from types/aims.ts
    ${auto_scaling}=    Create KEDA Policy Config
    ...                 metric_query=${metric_query}
    ...                 operation_over_time=max
    ...                 target_type=Value
    ...                 target_value=${target_value}

    # UI always sends replicas=1 even when autoscaling (see DeployAIMDrawer.tsx:244)
    # IMPORTANT: Convert to int to match API schema (Robot Framework defaults to strings)
    ${min_replicas_int}=    Convert To Integer    ${min_replicas}
    ${max_replicas_int}=    Convert To Integer    ${max_replicas}

    ${deploy_data}=     Create Dictionary
    ...                 replicas=${1}
    ...                 minReplicas=${min_replicas_int}
    ...                 maxReplicas=${max_replicas_int}
    ...                 autoScaling=${auto_scaling}

    RETURN              ${deploy_data}

AIM is deployed with autoscaling
    [Documentation]    Deploys an AIM with autoscaling enabled.
    ...                Idempotent: reuses existing service if present.
    ...                Sets: TEST_AIM_ID
    [Arguments]         ${min_replicas}=1    ${max_replicas}=3    ${metric}=running_requests    ${target_value}=10

    An AIM exists in system
    ${namespace}=       Get Project Namespace

    # Check for existing AIM service
    ${existing}=        Find Existing AIM Service    ${namespace}    ${TEST_AIM_NAME}
    IF    $existing != $None
        ${service_id}=      Get From Dictionary     ${existing}             id
        ${status_dict}=     Get From Dictionary     ${existing}             status
        ${status}=          Get From Dictionary     ${status_dict}          status

        # Check if existing service has matching autoscaling configuration
        ${spec}=            Get From Dictionary     ${existing}             spec        default=${None}
        ${config_matches}=  Set Variable            ${False}
        IF    ${spec} != ${None}
            ${existing_min}=        Get From Dictionary     ${spec}     minReplicas     default=1
            ${existing_max}=        Get From Dictionary     ${spec}     maxReplicas     default=1
            ${config_matches}=      Evaluate    ${existing_min} == ${min_replicas} and ${existing_max} == ${max_replicas}
        END

        ${is_terminal}=     Evaluate                "${status}" in ("Failed", "Degraded", "Deleted")
        IF    ${is_terminal} or not ${config_matches}
            Log    Existing AIM service ${service_id} (status: ${status}, config_matches: ${config_matches}) - redeploying    WARN
            Undeploy AIM        ${service_id}       ${namespace}            expected_status=any
            Sleep    5s
        ELSE
            Log    Reusing existing AIM service ${service_id} with matching config (min=${existing_min}, max=${existing_max})    INFO
            Set Test Variable   ${TEST_AIM_ID}      ${service_id}
            RETURN
        END
    END

    # Deploy with autoscaling
    ${deploy_data}=     Valid AIM deploy data with autoscaling is prepared
    ...                 min_replicas=${min_replicas}
    ...                 max_replicas=${max_replicas}
    ...                 metric=${metric}
    ...                 target_value=${target_value}

    ${response}=        Deploy AIM      ${TEST_AIM_NAME}    ${deploy_data}    ${namespace}    expected_status=202
    ${json}=            Set Variable    ${response.json()}
    ${service_id}=      Get From Dictionary     ${json}     id
    Set Test Variable   ${TEST_AIM_ID}          ${service_id}

    # Wait for backend to persist the configuration before UI tests verify it
    Sleep    10s

Deploy AIM request is sent
    [Documentation]    Sends request to deploy an AIM.
    ...    Requires: TEST_AIM_NAME
    ...    Sets: TEST_RESPONSE
    [Arguments]             ${deploy_data}=${None}
    IF    $deploy_data == $None
        ${deploy_data}=         Valid AIM deploy data is prepared
    END
    ${namespace}=           Get Project Namespace
    ${response}=            Deploy AIM              ${TEST_AIM_NAME}                       ${deploy_data}          ${namespace}                            expected_status=any
    Set Test Variable       ${TEST_RESPONSE}             ${response}

AIM is deployed
    [Documentation]    Ensures an AIM is deployed in the current project.
    ...    Idempotent: if an AIM service already exists for the selected model, reuses it.
    ...    If no service exists, deploys a new one.
    ...    This enables efficient sequential test execution while maintaining test independence.
    ...    Sets: TEST_AIM_ID
    An AIM exists in system
    ${namespace}=           Get Project Namespace

    # Check for existing AIM service
    ${existing}=            Find Existing AIM Service    ${namespace}    ${TEST_AIM_NAME}
    IF    $existing != $None
        ${service_id}=          Get From Dictionary     ${existing}             id
        ${status_dict}=         Get From Dictionary     ${existing}             status
        ${status}=              Get From Dictionary     ${status_dict}          status
        ${is_terminal}=         Evaluate                "${status}" in ("Failed", "Degraded", "Deleted")
        IF    ${is_terminal}
            # Service in bad state, undeploy and redeploy
            Log    Existing AIM service ${service_id} is ${status}, removing and redeploying    WARN
            Undeploy AIM            ${service_id}           ${namespace}            expected_status=any
            Sleep    5s
        ELSE
            # Service exists in usable state (Running, Pending, Starting, etc.)
            Log    Reusing existing AIM service ${service_id} (status: ${status})    INFO
            Set Test Variable       ${TEST_AIM_ID}                     ${service_id}
            RETURN
        END
    END

    # No usable service found, deploy fresh
    ${deploy_data}=         Valid AIM deploy data is prepared
    ${response}=            Deploy AIM              ${TEST_AIM_NAME}                       ${deploy_data}          ${namespace}                            expected_status=202
    ${json}=                Set Variable            ${response.json()}
    ${service_id}=          Get From Dictionary     ${json}                 id
    Set Test Variable       ${TEST_AIM_ID}                         ${service_id}

AIM is deployed and running
    [Documentation]    Ensures an AIM is deployed and running in the current project.
    ...    Idempotent: if an AIM service is already running, reuses it immediately.
    ...    If a service is starting up, waits for it to reach Running status.
    ...    If no service exists, deploys one and waits for Running status.
    ...    This makes tests efficient when run sequentially (AIM deployed once, reused
    ...    across tests) while each test remains self-sufficient when run in isolation.
    ...    Sets: TEST_AIM_ID
    An AIM exists in system
    ${namespace}=           Get Project Namespace

    # Check for existing AIM service
    ${existing}=            Find Existing AIM Service    ${namespace}    ${TEST_AIM_NAME}
    IF    $existing != $None
        ${service_id}=          Get From Dictionary     ${existing}             id
        ${status_dict}=         Get From Dictionary     ${existing}             status
        ${status}=              Get From Dictionary     ${status_dict}          status
        Set Test Variable       ${TEST_AIM_ID}                         ${service_id}
        IF    "${status}" == "Running"
            Log    AIM service ${service_id} already running, reusing    INFO
            RETURN
        END
        ${is_starting}=         Evaluate                "${status}" in ("Pending", "Starting")
        IF    ${is_starting}
            Log    AIM service ${service_id} is ${status}, waiting for Running    INFO
            Wait for AIM workload to be running
            RETURN
        END
        # Service in bad state (Failed, Degraded), undeploy and redeploy
        Log    Existing AIM service ${service_id} is ${status}, removing and redeploying    WARN
        Undeploy AIM            ${service_id}           ${namespace}            expected_status=any
        Sleep    5s
    END

    # No usable service, deploy fresh and wait
    AIM is deployed
    Wait for AIM workload to be running

Undeploy AIM request is sent
    [Documentation]    Sends request to undeploy an AIM.
    ...    Requires: TEST_AIM_ID
    ...    Sets: TEST_RESPONSE
    ${namespace}=           Get Project Namespace
    ${response}=            Undeploy AIM            ${TEST_AIM_ID}                      ${namespace}            expected_status=any
    Set Test Variable       ${TEST_RESPONSE}             ${response}

List AIMs request is sent
    [Documentation]    Sends request to list AIMs.
    ...    Sets: TEST_RESPONSE
    ${response}=            List AIMs               expected_status=any
    Set Test Variable       ${TEST_RESPONSE}             ${response}

Get AIM request is sent
    [Documentation]    Sends request to get a specific AIM.
    ...    Requires: TEST_AIM_NAME
    ...    Sets: TEST_RESPONSE
    ${response}=            Get AIM                 ${TEST_AIM_NAME}                       expected_status=any
    Set Test Variable       ${TEST_RESPONSE}             ${response}

Response should contain AIM list
    [Documentation]    Verifies response contains a list of AIMs
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain 'data' field
    ${aims_list}=           Set Variable            ${json['data']}
    Should Be True          isinstance($aims_list, list)                    msg=Expected 'data' field to be a list
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} >= 0

AIMs in list should have required fields
    [Documentation]    Verifies that AIMs in the list have all required fields
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain 'data' field
    ${aims_list}=           Set Variable            ${json['data']}
    Should Be True          isinstance($aims_list, list)                    msg=Expected 'data' field to be a list
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} > 0            msg=AIM list should not be empty

    # Verify first AIM has required fields (AIWB uses K8s CRD structure)
    ${first_aim}=           Get From List           ${aims_list}            0
    Dictionary Should Contain Key                   ${first_aim}            metadata                msg=AIM should have metadata field
    Dictionary Should Contain Key                   ${first_aim}            spec                    msg=AIM should have spec field
    Dictionary Should Contain Key                   ${first_aim}            status                  msg=AIM should have status field
    Dictionary Should Contain Key                   ${first_aim}            resource_name           msg=AIM should have resource_name field
    Dictionary Should Contain Key                   ${first_aim}            image_reference         msg=AIM should have image_reference field

Response should contain at least ${expected} AIMs
    [Documentation]    Verifies response contains at least the expected number of AIMs
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain 'data' field
    ${aims_list}=           Set Variable            ${json['data']}
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} >= ${expected}                         msg=Expected at least ${expected} AIMs, got ${count}

AIM should have active workload deployment
    [Documentation]    Verifies that the AIM has an active AIMService deployment
    [Arguments]             ${resource_name}=${TEST_AIM_NAME}
    ${namespace}=           Get Project Namespace
    ${response}=            List AIM Services       ${namespace}            expected_status=200
    ${services_data}=       Set Variable            ${response.json()}
    ${services_list}=       Set Variable            ${services_data['data']}

    # Find service for this AIM model
    ${found_service}=       Set Variable            ${None}
    FOR    ${service}    IN    @{services_list}
        ${model}=               Get From Dictionary     ${service['spec']}      model
        ${model_name}=          Get From Dictionary     ${model}                name
        IF    "${model_name}" == "${resource_name}"
            ${found_service}=       Set Variable            ${service}
            BREAK
        END
    END
    Should Not Be Equal     ${found_service}        ${None}                 msg=No active AIMService found for AIM ${resource_name}

AIM should not have active workload deployment
    [Documentation]    Verifies that the AIM does not have an active AIMService deployment
    [Arguments]             ${resource_name}=${TEST_AIM_NAME}
    ${namespace}=           Get Project Namespace
    ${response}=            List AIM Services       ${namespace}            expected_status=200
    ${services_data}=       Set Variable            ${response.json()}
    ${services_list}=       Set Variable            ${services_data['data']}

    # Check that no service exists for this AIM model
    ${found_service}=       Set Variable            ${None}
    FOR    ${service}    IN    @{services_list}
        ${model}=               Get From Dictionary     ${service['spec']}      model
        ${model_name}=          Get From Dictionary     ${model}                name
        IF    "${model_name}" == "${resource_name}"
            ${found_service}=       Set Variable            ${service}
            BREAK
        END
    END
    Should Be Equal         ${found_service}        ${None}                 msg=Found unexpected AIMService for AIM ${resource_name}

Find Existing AIM Service
    [Documentation]    Finds an existing AIM service for a given model in a namespace.
    ...    Returns the service dictionary if found, ${None} otherwise.
    [Arguments]             ${namespace}            ${model_resource_name}
    ${services_response}=   List AIM Services       ${namespace}            expected_status=200
    ${services_data}=       Set Variable            ${services_response.json()}
    ${services_list}=       Set Variable            ${services_data['data']}

    FOR    ${service}    IN    @{services_list}
        ${model}=               Get From Dictionary     ${service['spec']}      model
        ${model_name}=          Get From Dictionary     ${model}                name
        IF    "${model_name}" == "${model_resource_name}"
            RETURN                  ${service}
        END
    END
    RETURN                  ${None}

Get AIM Service By ID
    [Documentation]    Helper to get AIMService by ID using the current project namespace
    [Arguments]             ${service_id}           ${expected_status}=any    ${params}=${None}
    ${namespace}=           Get Project Namespace
    ${response}=            Get AIM Service         ${service_id}           ${namespace}            expected_status=${expected_status}
    RETURN                  ${response}

AIM workload should exist in database
    [Documentation]    Verifies the deployed AIM service exists
    Variable Should Exist                           ${TEST_AIM_ID}                         msg=TEST_AIM_ID is not set
    ${response}=            Get AIM Service By ID    ${TEST_AIM_ID}                         expected_status=200
    Should Not Be Empty     ${response.json()}

Wait for AIM workload to reach state
    [Documentation]    Waits for the AIM workload to reach the specified status
    ...    Polls the workload status every 5 seconds for up to 10 minutes
    [Arguments]             ${target_state}         ${timeout}=600          ${interval}=5
    Variable Should Exist                           ${TEST_AIM_ID}                         msg=TEST_AIM_ID is not set
    ${start_time}=          Evaluate                time.time()             modules=time
    ${end_time}=            Evaluate                ${start_time} + ${timeout}

    WHILE    True
        # Small delay before checking to prevent overwhelming the API
        Sleep                   ${interval}s

        # Force session recreation to avoid connection pool issues
        Set Suite Variable      ${API_SESSION}          ${None}
        Create api session    aiwb

        # For Deleted state, accept 404 as success (resource is gone)
        ${response}=            Get AIM Service By ID    ${TEST_AIM_ID}                         expected_status=any

        # If waiting for Deleted and got 404, the resource is gone - success!
        IF    $target_state == "Deleted" and ${response.status_code} == 404
            Log    AIM workload ${TEST_AIM_ID} successfully deleted (404)    INFO
            RETURN
        END

        # If got 404 but not waiting for Deleted, that's an error
        IF    ${response.status_code} == 404
            Fail    AIM workload ${TEST_AIM_ID} was deleted unexpectedly
        END

        ${json}=                Set Variable            ${response.json()}
        ${status_dict}=         Get From Dictionary     ${json}                 status
        ${status}=              Get From Dictionary     ${status_dict}          status
        Log    DEBUG: status_value='${status}', target='${target_state}', status_dict='${status_dict}'    level=INFO

        # Check if workload reached target state
        IF    $status == $target_state
            RETURN
        END

        # Check if workload failed
        IF    $status == "Failed" or $status == "Degraded"
            Fail                    AIM workload ${TEST_AIM_ID} failed to start. Status: ${status}
        END

        # Check timeout
        ${current_time}=        Evaluate                time.time()             modules=time
        IF    ${current_time} >= ${end_time}
            Fail                    Timeout waiting for AIM workload to reach ${target_state} status. Last status: ${status}
        END
    END

Wait for AIM workload to be running
    [Documentation]    Waits for the AIM workload to reach Running status (backward compatibility)
    Wait for AIM workload to reach state            Running

Deployed AIM reaches ${state} state
    [Documentation]    Waits for the deployed AIM workload to reach the specified state
    ...    Example: Deployed AIM reaches Running state
    Wait for AIM workload to reach state            ${state}

AIM workload should be accessible externally
    [Documentation]    Verifies the AIM workload is running, has external_host, and the endpoint is accessible.
    ...    External AIM endpoints require an AIMS API key (not OIDC token).
    ...    Creates an API key, assigns it to the AIM model, then uses it for authentication.
    Variable Should Exist                           ${TEST_AIM_ID}                         msg=TEST_AIM_ID is not set
    ${response}=            Get AIM Service By ID    ${TEST_AIM_ID}                         expected_status=200
    ${json}=                Set Variable            ${response.json()}

    # Verify workload status is Running
    Dictionary Should Contain Key                   ${json}                 status                  msg=Workload should have status field
    ${status_dict}=         Get From Dictionary     ${json}                 status
    ${status}=              Get From Dictionary     ${status_dict}          status
    Should Be Equal         ${status}               Running                 msg=Workload must be in Running state before testing external endpoint. Current status: ${status}

    # Verify external endpoint exists (AIWB uses endpoints.external)
    Dictionary Should Contain Key                   ${json}                 endpoints               msg=Workload should have endpoints field
    ${endpoints}=           Get From Dictionary     ${json}                 endpoints
    Should Not Be Equal     ${endpoints}            ${None}                 msg=Workload endpoints should not be None
    Dictionary Should Contain Key                   ${endpoints}            external                msg=Endpoints should contain external
    ${external_host}=       Get From Dictionary     ${endpoints}            external
    Should Not Be Empty     ${external_host}        msg=external endpoint should not be empty

    # External AIM endpoints require an AIMS API key for authentication
    # Initialize TEST_API_KEYS as a proper list (api_keys.resource tracks created keys for cleanup)
    @{api_keys_list}=    Create List
    Set Test Variable    ${TEST_API_KEYS}    ${api_keys_list}
    Api key exists for user
    Api key is assigned to AIMS model
    ${models}=              List models from external endpoint              ${external_host}        ${TEST_AIM_ID}    ${TEST_API_KEY_VALUE}
    Should Be True          isinstance($models, list)                       msg=Models data should be a list
    ${model_count}=         Get Length              ${models}
    Should Be True          ${model_count} > 0      msg=Endpoint should return at least one model
    RETURN                  ${models}

External endpoint should return available models
    [Documentation]    Verifies that the external endpoint returns available models.
    ...    Re-fetches the model list from the external endpoint to avoid shared state.
    ...    Uses the AIMS API key (TEST_API_KEY_VALUE) set by the preceding accessibility check.
    Variable Should Exist                           ${TEST_AIM_ID}          msg=TEST_AIM_ID is not set
    Variable Should Exist                           ${TEST_API_KEY_VALUE}   msg=TEST_API_KEY_VALUE is not set (call AIM workload should be accessible externally first)
    ${response}=            Get AIM Service By ID    ${TEST_AIM_ID}         expected_status=200
    ${json}=                Set Variable            ${response.json()}
    ${endpoints}=           Get From Dictionary     ${json}                 endpoints
    ${external_host}=       Get From Dictionary     ${endpoints}            external
    ${models}=              List models from external endpoint              ${external_host}        ${TEST_AIM_ID}    ${TEST_API_KEY_VALUE}
    Should Be True          isinstance($models, list)                       msg=Models should be a list
    ${model_count}=         Get Length              ${models}
    Should Be True          ${model_count} > 0      msg=Should have at least one model available

Response should contain workload ID
    [Documentation]    Verifies response contains workload ID and extracts TEST_AIM_ID.
    ...    Sets TEST_AIM_ID from the response so subsequent keywords can reference the workload.
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key                   ${json}                 id
    ${workload_id}=         Get From Dictionary     ${json}                 id
    Set Test Variable       ${TEST_AIM_ID}                         ${workload_id}
    RETURN                  ${workload_id}

Deployed workload should be removed
    [Documentation]    Verifies the deployed workload is removed from database and reaches Deleted status
    Variable Should Exist                           ${TEST_AIM_ID}                         msg=TEST_AIM_ID is not set

    # Wait for workload to reach Deleted state or be removed (up to 60 seconds)
    Wait for AIM workload to reach state            Deleted                 timeout=60

    # Verify final state - workload should either be not found (404) or have Deleted status
    ${response}=            Get AIM Service By ID    ${TEST_AIM_ID}                         expected_status=any
    IF    ${response.status_code} == 404
        RETURN
    ELSE IF    ${response.status_code} == 200
        ${json}=                Set Variable            ${response.json()}
        ${status_dict}=         Get From Dictionary     ${json}                 status
        ${status}=              Get From Dictionary     ${status_dict}          status
        Should Be Equal         ${status}               Deleted                 msg=Workload should have Deleted status
    ELSE
        Fail                    Unexpected status code: ${response.status_code}
    END

Response should contain AIM details
    [Documentation]    Verifies response contains AIM details (AIWB K8s CRD structure)
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key                   ${json}                 metadata
    Dictionary Should Contain Key                   ${json}                 spec
    Dictionary Should Contain Key                   ${json}                 status
    Dictionary Should Contain Key                   ${json}                 resource_name
    Dictionary Should Contain Key                   ${json}                 image_reference

Cleanup AIM After Test
    [Documentation]    Teardown keyword to cleanup deployed AIMServices
    ...
    ...    Note: This keyword performs best-effort undeployment. We rely on namespace/project
    ...    deletion CASCADE behavior which automatically deletes all associated AIMServices.
    TRY
        ${project_id_value}=    Get Variable Value      ${TEST_PROJECT_ID}                              ${None}
        ${service_id_value}=    Get Variable Value      ${TEST_AIM_ID}                      ${None}

        IF    $project_id_value is not None and $service_id_value is not None
            ${namespace}=           Get Project Namespace
            TRY
                ${response}=            Undeploy AIM            ${TEST_AIM_ID}                      ${namespace}            expected_status=any
                Log                     Undeploy request sent for AIMService ${TEST_AIM_ID}          DEBUG
            EXCEPT
                Log                     Failed to undeploy AIMService ${TEST_AIM_ID} (may already be deleted)                    DEBUG
            END
            Log                     AIM undeploy request completed. Namespace deletion will cascade cleanup.     INFO
        END
    EXCEPT
        # Ignore any cleanup errors
        Log                     Cleanup completed with warnings (expected)                      DEBUG
    END

Logs are requested from AIM workload
    [Documentation]    Requests logs from the deployed AIM workload via AIWB API
    Variable Should Exist                           ${TEST_AIM_ID}                         msg=TEST_AIM_ID is not set
    ${namespace}=           Get Project Namespace
    Create api session    aiwb
    ${endpoint}=            Service API Endpoint    aiwb    endpoint=namespaces/${namespace}/aims/services/${TEST_AIM_ID}/logs
    # Logs endpoint requires start/end timestamps - use last hour
    ${end_time}=            Get Current Date        result_format=%Y-%m-%dT%H:%M:%SZ
    ${start_time}=          Get Current Date        increment=-1 hour       result_format=%Y-%m-%dT%H:%M:%SZ
    ${params}=              Create Dictionary       start=${start_time}     end=${end_time}          limit=50    direction=forward
    ${response}=            Safe Get Request        ${endpoint}             params=${params}         expected_status=any
    Set Test Variable       ${TEST_RESPONSE}             ${response}

Response should contain log entries
    [Documentation]    Verifies that the response contains valid log entries with proper structure
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}

    # Verify response structure
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain data field
    Dictionary Should Contain Key                   ${json}                 pagination              msg=Response should contain pagination field

    # Verify data is a list
    ${logs}=                Get From Dictionary     ${json}                 data
    Should Be True          isinstance($logs, list)                         msg=Data should be a list

    # Verify pagination metadata
    ${pagination}=          Get From Dictionary     ${json}                 pagination
    Dictionary Should Contain Key                   ${pagination}           total_returned          msg=Pagination should have total_returned
    Dictionary Should Contain Key                   ${pagination}           has_more                msg=Pagination should have has_more

    # If there are logs, verify their structure
    ${logs_count}=          Get Length              ${logs}
    IF    ${logs_count} > 0
        ${first_log}=           Get From List           ${logs}                 0
        Dictionary Should Contain Key                   ${first_log}            timestamp               msg=Log entry should have timestamp
        Dictionary Should Contain Key                   ${first_log}            level                   msg=Log entry should have level
        Dictionary Should Contain Key                   ${first_log}            message                 msg=Log entry should have message
    END

Workload details are requested
    [Documentation]    Requests detailed information about the deployed AIM service
    Variable Should Exist                           ${TEST_AIM_ID}                         msg=TEST_AIM_ID is not set
    ${response}=            Get AIM Service By ID    ${TEST_AIM_ID}                         expected_status=200
    Set Test Variable       ${TEST_RESPONSE}             ${response}

AIM workload detail endpoint should be complete
    [Documentation]    Verifies that AIM service detail endpoint contains all required fields
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}

    # Core AIMService fields
    Dictionary Should Contain Key                   ${json}                 id                      msg=Service should have id
    Dictionary Should Contain Key                   ${json}                 resource_name           msg=Service should have resource_name
    Dictionary Should Contain Key                   ${json}                 status_value            msg=Service should have status_value

    # Metadata (contains name, namespace, labels, etc.)
    Dictionary Should Contain Key                   ${json}                 metadata                msg=Service should have metadata
    ${metadata}=            Get From Dictionary     ${json}                 metadata
    Dictionary Should Contain Key                   ${metadata}             name                    msg=Metadata should have name
    Dictionary Should Contain Key                   ${metadata}             namespace               msg=Metadata should have namespace

    # Endpoints
    Dictionary Should Contain Key                   ${json}                 endpoints               msg=Service should have endpoints

    # Spec (contains model, replicas, etc.)
    Dictionary Should Contain Key                   ${json}                 spec                    msg=Service should have spec

    # Status (contains detailed status info)
    Dictionary Should Contain Key                   ${json}                 status                  msg=Service should have status

AIM list endpoint should include workload details
    [Documentation]    Verifies that AIMService list includes complete deployment information
    ...    AIWB separates AIMs (models) from AIMServices (deployments), so we check the services endpoint
    Variable Should Exist                           ${TEST_AIM_NAME}                       msg=TEST_AIM_NAME is not set
    ${namespace}=           Get Project Namespace

    # Get the deployed AIMService
    ${response}=            Get AIM Service         ${TEST_AIM_ID}                      ${namespace}            expected_status=200
    ${service}=             Set Variable            ${response.json()}

    # Verify AIMService has core fields
    Dictionary Should Contain Key                   ${service}              id                      msg=AIMService should have id
    Dictionary Should Contain Key                   ${service}              metadata                msg=AIMService should have metadata
    Dictionary Should Contain Key                   ${service}              spec                    msg=AIMService should have spec
    Dictionary Should Contain Key                   ${service}              status                  msg=AIMService should have status

    # Verify spec contains model reference
    ${spec}=                Get From Dictionary     ${service}              spec
    Dictionary Should Contain Key                   ${spec}                 model                   msg=Spec should have model field
    ${model}=               Get From Dictionary     ${spec}                 model
    Dictionary Should Contain Key                   ${model}                name                    msg=Model should have name field

    # Verify status
    ${status}=              Get From Dictionary     ${service}              status
    Dictionary Should Contain Key                   ${status}               status                  msg=Status should have status field

AIM deployment should exist in kubernetes
    [Documentation]    Verifies AIM workload has deployment in Kubernetes
    ...    AIM deployments are named {aim-name}-{template-hash}-predictor
    ${workload}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=200
    ${data}=    Set variable    ${workload.json()}
    ${metadata}=    Get from dictionary    ${data}    metadata
    ${name}=    Get from dictionary    ${metadata}    name
    ${namespace}=    Get from dictionary    ${metadata}    namespace

    # AIM deployments include a template hash: {name}-{hash}-predictor
    ${result}=    Run Process    kubectl    get    deployments
    ...    -n    ${namespace}    --no-headers    -o    custom-columns\=NAME:.metadata.name
    ${matching}=    Evaluate    [d for d in '''${result.stdout}'''.strip().split('\\n') if d.startswith('${name}-') and d.endswith('-predictor')]
    ${count}=    Get Length    ${matching}
    Should Be True    ${count} > 0
    ...    msg=No deployment matching ${name}-*-predictor found in namespace ${namespace}

AIM deployment should not exist in kubernetes
    [Documentation]    Verifies AIM deployment removed from Kubernetes
    ...    Polls for deployment deletion with timeout
    ${workload}=    Get AIM Service By ID    ${TEST_AIM_ID}    expected_status=any

    IF    ${workload.status_code} == 404
        Log    Workload already deleted from database    DEBUG
        RETURN
    END

    ${data}=    Set variable    ${workload.json()}
    ${metadata}=    Get from dictionary    ${data}    metadata
    ${name}=    Get from dictionary    ${metadata}    name
    ${namespace}=    Get from dictionary    ${metadata}    namespace

    # Poll for deployment to be removed
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify AIM deployment gone    ${name}    ${namespace}

AIM catalog should contain models with image metadata
    [Documentation]    Verifies that the AIM catalog contains models with complete image metadata.
    ...    Checks resource_name, status, and imageMetadata fields including title, canonicalName, and tags.
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    ${aims_list}=           Set Variable            ${json['data']}
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} > 0            msg=AIM catalog should not be empty

    FOR    ${aim}    IN    @{aims_list}
        # Every AIM must have resource_name and status
        Dictionary Should Contain Key               ${aim}                  resource_name           msg=AIM should have resource_name
        Dictionary Should Contain Key               ${aim}                  status                  msg=AIM should have status
        Dictionary Should Contain Key               ${aim}                  status_value            msg=AIM should have status_value

        # Verify imageMetadata structure
        ${status}=              Get From Dictionary     ${aim}                  status
        Dictionary Should Contain Key               ${status}               imageMetadata           msg=AIM status should have imageMetadata
        ${image_metadata}=      Get From Dictionary     ${status}               imageMetadata
        Dictionary Should Contain Key               ${image_metadata}       model                   msg=imageMetadata should have model

        ${model}=               Get From Dictionary     ${image_metadata}       model
        Dictionary Should Contain Key               ${model}                title                   msg=model metadata should have title
        Dictionary Should Contain Key               ${model}                canonicalName           msg=model metadata should have canonicalName
        Dictionary Should Contain Key               ${model}                tags                    msg=model metadata should have tags
        Dictionary Should Contain Key               ${model}                variants                msg=model metadata should have variants
    END

List AIM templates request is sent
    [Documentation]    Sends request to list AIM templates for the selected model.
    ...    Requires: TEST_AIM_NAME
    ...    Sets: TEST_RESPONSE
    Variable Should Exist                           ${TEST_AIM_NAME}        msg=TEST_AIM_NAME is not set
    ${response}=            List AIM Templates      ${TEST_AIM_NAME}        expected_status=any
    Set Test Variable       ${TEST_RESPONSE}             ${response}

Response should contain AIM templates
    [Documentation]    Verifies that AIM templates exist for the selected model.
    ...    Templates provide deployment configurations with GPU requirements.
    ${json}=                Set Variable            ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should have data field
    ${templates}=           Set Variable            ${json['data']}
    Should Be True          isinstance($templates, list)                    msg=Templates should be a list
    ${count}=               Get Length              ${templates}
    Should Be True          ${count} > 0            msg=AIM ${TEST_AIM_NAME} should have at least one template

    # Verify each template has required CRD structure
    FOR    ${template}    IN    @{templates}
        Dictionary Should Contain Key               ${template}             metadata                msg=Template should have metadata
        Dictionary Should Contain Key               ${template}             spec                    msg=Template should have spec
        Dictionary Should Contain Key               ${template}             status                  msg=Template should have status

        ${metadata}=            Get From Dictionary     ${template}             metadata
        Dictionary Should Contain Key               ${metadata}             name                    msg=Template metadata should have name
    END

AIM service should have display name
    [Documentation]    Verifies that the deployed AIM service response includes the expected display name.
    ...    The display name comes from the AIM's imageMetadata.model.title field.
    ...    Requires: TEST_AIM_ID, TEST_AIM_DISPLAY_NAME
    Variable Should Exist                           ${TEST_AIM_ID}          msg=TEST_AIM_ID is not set
    Variable Should Exist                           ${TEST_AIM_DISPLAY_NAME}    msg=TEST_AIM_DISPLAY_NAME is not set

    # Verify the AIM model's title is available from the catalog
    ${response}=            Get AIM                 ${TEST_AIM_NAME}        expected_status=200
    ${aim_data}=            Set Variable            ${response.json()}
    ${status}=              Get From Dictionary     ${aim_data}             status
    ${image_metadata}=      Get From Dictionary     ${status}               imageMetadata
    ${model}=               Get From Dictionary     ${image_metadata}       model
    ${title}=               Get From Dictionary     ${model}                title
    Should Not Be Empty     ${title}                msg=AIM model title (display name) should not be empty
    Should Be Equal         ${title}                ${TEST_AIM_DISPLAY_NAME}
    ...    msg=AIM display name mismatch: expected '${TEST_AIM_DISPLAY_NAME}', got '${title}'

AIM service should have version info
    [Documentation]    Verifies that the deployed AIM service has version information.
    ...    Version info is present in the image_reference field and in the resolved template.
    ...    Requires: TEST_AIM_ID, TEST_AIM_NAME
    Variable Should Exist                           ${TEST_AIM_ID}          msg=TEST_AIM_ID is not set
    ${response}=            Get AIM Service By ID    ${TEST_AIM_ID}         expected_status=200
    ${json}=                Set Variable            ${response.json()}

    # Verify the AIM model's image_reference contains a version tag
    ${aim_response}=        Get AIM                 ${TEST_AIM_NAME}        expected_status=200
    ${aim_data}=            Set Variable            ${aim_response.json()}
    ${image_ref}=           Get From Dictionary     ${aim_data}             image_reference
    Should Not Be Empty     ${image_ref}            msg=AIM image_reference should not be empty
    # Image references follow format: registry/image:version
    Should Contain          ${image_ref}            :                       msg=image_reference should contain version tag separator ':'

    # Verify the AIM service has a resolved template reference
    ${status}=              Get From Dictionary     ${json}                 status
    ${resolved_template}=   Evaluate                $status.get('resolvedTemplate')
    IF    $resolved_template is not None
        Dictionary Should Contain Key               ${resolved_template}    name                    msg=resolvedTemplate should have name
        ${template_name}=       Get From Dictionary     ${resolved_template}    name
        Should Not Be Empty     ${template_name}        msg=resolvedTemplate name should not be empty
        Log    AIM service resolved template: ${template_name}    INFO
    END

Verify AIM deployment gone
    [Documentation]    Helper to verify no deployment matching AIM name prefix exists
    [Arguments]    ${aim_name}    ${namespace}
    ${result}=    Run process    kubectl    get    deployments
    ...    -n    ${namespace}    --no-headers    -o    custom-columns\=NAME:.metadata.name
    ...    stderr=STDOUT
    ${matching}=    Evaluate    [d for d in '''${result.stdout}'''.strip().split('\\n') if d.startswith('${aim_name}-') and d.endswith('-predictor')]
    ${count}=    Get Length    ${matching}
    Should Be True    ${count} == 0
    ...    msg=Deployment matching ${aim_name}-*-predictor still exists in namespace ${namespace}
