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
Resource            catalog_workloads.resource
Resource            kubectl_verification.resource
Library             Collections
Library             Process


*** Variables ***
${TEST_AIM_ID}              ${None}
${TEST_DEPLOY_DATA}         ${None}
${DEPLOYED_WORKLOAD_ID}     ${None}
${response}                 ${None}


*** Keywords ***
An AIM exists in system
    [Documentation]    Ensures an AIM exists and sets TEST_AIM_ID by looking up the default test AIM by name
    Project With GPU Quota Exists

    # Look up AIM by name to get its ID
    ${aim_name}=            Set Variable            aim-meta-llama-llama-3-1-8b-instruct
    ${response}=            List AIMs               ${TEST_PROJECT_ID}   expected_status=200
    ${aims_data}=           Set Variable            ${response.json()}
    ${aims_list}=           Set Variable            ${aims_data['data']}

    # Find AIM with matching image_name
    ${aim_id}=              Set Variable            ${None}
    FOR    ${aim}    IN    @{aims_list}
        ${current_name}=        Set Variable            ${aim}[image_name]
        IF    "${current_name}" == "${aim_name}"
            ${aim_id}=              Set Variable            ${aim}[id]
            BREAK
        END
    END

    # Verify AIM was found
    Should Not Be Equal     ${aim_id}               ${None}                 msg=AIM with name '${aim_name}' not found in system. Available AIMs: ${aims_list}
    Set Test Variable       ${TEST_AIM_ID}          ${aim_id}

Valid AIM deploy data is prepared
    [Documentation]    Prepares valid deployment data for an AIM
    ${deploy_data}=         Create Dictionary
    ...                     replicas=1
    ...                     cache_model=${True}
    Set Test Variable       ${TEST_DEPLOY_DATA}     ${deploy_data}

Deploy AIM request is sent
    [Documentation]    Sends request to deploy an AIM
    Project exists in system
    ${response}=            Deploy AIM              ${TEST_AIM_ID}          ${TEST_DEPLOY_DATA}                             ${TEST_PROJECT_ID}   expected_status=any
    Set Test Variable       ${response}             ${response}

AIM is deployed
    [Documentation]    Deploys an AIM and verifies deployment
    ...    Accepts both 202 (new deployment) and 409 (already deployed)
    An AIM exists in system
    Project exists in system
    Valid AIM deploy data is prepared
    ${response}=            Deploy AIM              ${TEST_AIM_ID}          ${TEST_DEPLOY_DATA}                             ${TEST_PROJECT_ID}   expected_status=any
    Set Test Variable       ${response}             ${response}

    # Handle both new deployment (202) and already deployed (409)
    IF    ${response.status_code} == 202
        # Extract workload ID from new deployment response
        ${json}=                Set Variable            ${response.json()}
        ${workload_id}=         Get From Dictionary     ${json}                 id
        Set Test Variable       ${DEPLOYED_WORKLOAD_ID}                         ${workload_id}
    ELSE IF    ${response.status_code} == 409
        # AIM already deployed, get the existing workload
        Log    AIM already deployed, fetching existing workload    WARN
        ${aims_response}=       List AIMs               ${TEST_PROJECT_ID}   expected_status=200
        ${aims_data}=           Set Variable            ${aims_response.json()}
        ${aims_list}=           Set Variable            ${aims_data['data']}
        FOR    ${aim}    IN    @{aims_list}
            ${aim_id}=              Set Variable            ${aim}[id]
            IF    "${aim_id}" == "${TEST_AIM_ID}"
                ${workload}=            Set Variable            ${aim}[workload]
                Should Not Be Equal     ${workload}             ${None}                 msg=AIM is deployed but has no workload
                ${workload_id}=         Set Variable            ${workload}[id]
                Set Test Variable       ${DEPLOYED_WORKLOAD_ID}                         ${workload_id}
                BREAK
            END
        END
    ELSE
        Fail    Unexpected status code ${response.status_code} when deploying AIM
    END

AIM is deployed and running
    [Documentation]    Deploys an AIM and waits for it to reach Running status
    AIM is deployed
    Wait for AIM workload to be running

Undeploy AIM request is sent
    [Documentation]    Sends request to undeploy an AIM
    Project exists in system
    ${response}=            Undeploy AIM            ${TEST_AIM_ID}          ${TEST_PROJECT_ID}                           expected_status=any
    Set Test Variable       ${response}             ${response}

List AIMs request is sent
    [Documentation]    Sends request to list AIMs
    Project exists in system
    ${response}=            List AIMs               ${TEST_PROJECT_ID}   expected_status=any
    Set Test Variable       ${response}             ${response}

Get AIM request is sent
    [Documentation]    Sends request to get a specific AIM
    ${response}=            Get AIM                 ${TEST_AIM_ID}          expected_status=any
    Set Test Variable       ${response}             ${response}

Response should contain AIM list
    [Documentation]    Verifies response contains a list of AIMs
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain 'data' field
    ${aims_list}=           Set Variable            ${json['data']}
    Should Be True          isinstance($aims_list, list)                    msg=Expected 'data' field to be a list
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} >= 0

AIMs in list should have required fields
    [Documentation]    Verifies that AIMs in the list have all required fields
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain 'data' field
    ${aims_list}=           Set Variable            ${json['data']}
    Should Be True          isinstance($aims_list, list)                    msg=Expected 'data' field to be a list
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} > 0            msg=AIM list should not be empty

    # Verify first AIM has required fields
    ${first_aim}=           Get From List           ${aims_list}            0
    Dictionary Should Contain Key                   ${first_aim}            id                      msg=AIM should have id field
    Dictionary Should Contain Key                   ${first_aim}            image_name              msg=AIM should have image_name field
    Dictionary Should Contain Key                   ${first_aim}            image_tag               msg=AIM should have image_tag field
    Dictionary Should Contain Key                   ${first_aim}            workload                msg=AIM should have workload field

Response should contain at least ${expected} AIMs
    [Documentation]    Verifies response contains at least the expected number of AIMs
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 data                    msg=Response should contain 'data' field
    ${aims_list}=           Set Variable            ${json['data']}
    ${count}=               Get Length              ${aims_list}
    Should Be True          ${count} >= ${expected}                         msg=Expected at least ${expected} AIMs, got ${count}

AIM should have active workload deployment
    [Documentation]    Verifies that the AIM has an active workload in the response
    [Arguments]             ${aim_id}=${TEST_AIM_ID}
    Project exists in system
    ${response}=            List AIMs               ${TEST_PROJECT_ID}   expected_status=200
    ${aims_data}=           Set Variable            ${response.json()}
    ${aims_list}=           Set Variable            ${aims_data['data']}
    ${target_aim}=          Set Variable            ${None}
    FOR    ${aim}    IN    @{aims_list}
        ${current_id}=          Set Variable            ${aim}[id]
        IF    "${current_id}" == "${aim_id}"
            ${target_aim}=          Set Variable            ${aim}
            BREAK
        END
    END
    Should Not Be Equal     ${target_aim}           ${None}                 msg=AIM ${aim_id} not found in list
    Dictionary Should Contain Key                   ${target_aim}           workload                                        msg=AIM should have workload field
    ${workload}=            Get From Dictionary     ${target_aim}           workload
    Should Not Be Equal     ${workload}             ${None}                 msg=AIM should have active workload deployment

AIM should not have active workload deployment
    [Documentation]    Verifies that the AIM does not have an active workload
    [Arguments]             ${aim_id}=${TEST_AIM_ID}
    Project exists in system
    ${response}=            List AIMs               ${TEST_PROJECT_ID}   expected_status=200
    ${aims_data}=           Set Variable            ${response.json()}
    ${aims_list}=           Set Variable            ${aims_data['data']}
    ${target_aim}=          Set Variable            ${None}
    FOR    ${aim}    IN    @{aims_list}
        ${current_id}=          Set Variable            ${aim}[id]
        IF    "${current_id}" == "${aim_id}"
            ${target_aim}=          Set Variable            ${aim}
            BREAK
        END
    END
    Should Not Be Equal     ${target_aim}           ${None}                 msg=AIM ${aim_id} not found in list
    Dictionary Should Contain Key                   ${target_aim}           workload                                        msg=AIM should have workload field
    ${workload}=            Get From Dictionary     ${target_aim}           workload
    Should Be Equal         ${workload}             ${None}                 msg=AIM should not have active workload deployment

AIM workload should exist in database
    [Documentation]    Verifies the deployed AIM workload exists
    Variable Should Exist                           ${DEPLOYED_WORKLOAD_ID}                         msg=DEPLOYED_WORKLOAD_ID is not set
    ${response}=            Get menaged workload    ${DEPLOYED_WORKLOAD_ID}                         expected_status=200
    Should Not Be Empty     ${response.json()}

Wait for AIM workload to reach state
    [Documentation]    Waits for the AIM workload to reach the specified status
    ...    Polls the workload status every 5 seconds for up to 10 minutes
    [Arguments]             ${target_state}         ${timeout}=600          ${interval}=5
    Variable Should Exist                           ${DEPLOYED_WORKLOAD_ID}                         msg=DEPLOYED_WORKLOAD_ID is not set
    ${start_time}=          Evaluate                time.time()             modules=time
    ${end_time}=            Evaluate                ${start_time} + ${timeout}

    WHILE    True
        # Small delay before checking to prevent overwhelming the API
        Sleep                   ${interval}s

        # Force session recreation to avoid connection pool issues
        Set Suite Variable      ${API_SESSION}          ${None}
        Create api session

        ${response}=            Get menaged workload    ${DEPLOYED_WORKLOAD_ID}                         expected_status=200
        ${json}=                Set Variable            ${response.json()}
        ${status}=              Get From Dictionary     ${json}                 status

        # Check if workload reached target state
        IF    "${status}" == "${target_state}"
            RETURN
        END

        # Check if workload failed
        IF    "${status}" == "Failed" or "${status}" == "Terminated"
            Fail                    AIM workload ${DEPLOYED_WORKLOAD_ID} failed to start. Status: ${status}
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
    [Documentation]    Verifies the AIM workload is running, has external_host, and the endpoint is accessible
    Variable Should Exist                           ${DEPLOYED_WORKLOAD_ID}                         msg=DEPLOYED_WORKLOAD_ID is not set
    ${response}=            Get menaged workload    ${DEPLOYED_WORKLOAD_ID}                         expected_status=200
    ${json}=                Set Variable            ${response.json()}

    # Verify workload status is Running
    Dictionary Should Contain Key                   ${json}                 status                  msg=Workload should have status field
    ${status}=              Get From Dictionary     ${json}                 status
    Should Be Equal         ${status}               Running                 msg=Workload must be in Running state before testing external endpoint. Current status: ${status}

    # Verify external_host exists
    Dictionary Should Contain Key                   ${json}                 output                  msg=Workload should have output field
    ${output}=              Get From Dictionary     ${json}                 output
    Should Not Be Equal     ${output}               ${None}                 msg=Workload output should not be None
    Dictionary Should Contain Key                   ${output}               external_host           msg=Output should contain external_host
    ${external_host}=       Get From Dictionary     ${output}               external_host
    Should Not Be Empty     ${external_host}        msg=external_host should not be empty

    # Test the external endpoint and verify models are available
    ${models}=              List models from external endpoint              ${external_host}        ${DEPLOYED_WORKLOAD_ID}
    Should Be True          isinstance($models, list)                       msg=Models data should be a list
    ${model_count}=         Get Length              ${models}
    Should Be True          ${model_count} > 0      msg=Endpoint should return at least one model
    Set Test Variable       ${models}               ${models}

External endpoint should return available models
    [Documentation]    Verifies that the external endpoint returns available models
    Variable Should Exist                           ${models}               msg=Models list not found. Run 'AIM workload should be accessible externally' first
    Should Be True          isinstance($models, list)                       msg=Models should be a list
    ${model_count}=         Get Length              ${models}
    Should Be True          ${model_count} > 0      msg=Should have at least one model available

Response should contain workload ID
    [Documentation]    Verifies response contains workload ID
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 id
    ${workload_id}=         Get From Dictionary     ${json}                 id
    Set Test Variable       ${DEPLOYED_WORKLOAD_ID}                         ${workload_id}

Deployed workload should be removed
    [Documentation]    Verifies the deployed workload is removed from database and reaches Deleted status
    Variable Should Exist                           ${DEPLOYED_WORKLOAD_ID}                         msg=DEPLOYED_WORKLOAD_ID is not set

    # Wait for workload to reach Deleted state or be removed (up to 60 seconds)
    Wait for AIM workload to reach state            Deleted                 timeout=60

    # Verify final state - workload should either be not found (404) or have Deleted status
    ${response}=            Get menaged workload    ${DEPLOYED_WORKLOAD_ID}                         expected_status=any
    IF    ${response.status_code} == 404
        RETURN
    ELSE IF    ${response.status_code} == 200
        ${json}=                Set Variable            ${response.json()}
        ${status}=              Get From Dictionary     ${json}                 status
        Should Be Equal         ${status}               Deleted                 msg=Workload should have Deleted status
    ELSE
        Fail                    Unexpected status code: ${response.status_code}
    END

Response should contain AIM details
    [Documentation]    Verifies response contains AIM details
    ${json}=                Set Variable            ${response.json()}
    Dictionary Should Contain Key                   ${json}                 id
    Dictionary Should Contain Key                   ${json}                 image_name
    Dictionary Should Contain Key                   ${json}                 image_tag

Cleanup AIM After Test
    [Documentation]    Teardown keyword to cleanup all deployed AIMs tracked in DEPLOYED_AIMS_LIST
    ...
    ...    Note: This keyword performs best-effort undeployment but does NOT verify
    ...    that workloads are fully cleaned up. Instead, we rely on project deletion
    ...    CASCADE behavior which automatically deletes all associated workloads.
    ...
    ...    Why: Workloads can get stuck in Pending state (database/Kubernetes out of sync),
    ...    causing verification to fail. The dedicated workload_lifecycle.robot test suite
    ...    specifically tests proper workload lifecycle and state transitions.
    TRY
        ${project_exists}=      Run Keyword And Return Status                   Variable Should Exist   ${TEST_PROJECT_ID}
        IF    ${project_exists}
            ${aims_count}=          Get Length              ${DEPLOYED_AIMS_LIST}
            IF    ${aims_count} > 0
                # Undeploy all tracked AIMs (best effort, don't fail on errors)
                FOR    ${aim_id}    IN    @{DEPLOYED_AIMS_LIST}
                    TRY
                        ${response}=            Undeploy AIM            ${aim_id}               ${TEST_PROJECT_ID}                           expected_status=any
                        Log                     Undeploy request sent for AIM ${aim_id}         DEBUG
                    EXCEPT
                        Log                     Failed to undeploy AIM ${aim_id} (may already be undeployed)                                  DEBUG
                    END
                END

                Log                     AIM undeploy requests completed. Project deletion will cascade cleanup any remaining workloads.       INFO

                # Clear the list
                @{DEPLOYED_AIMS_LIST}=  Create List
                Set Suite Variable      @{DEPLOYED_AIMS_LIST}
            END
        END
    EXCEPT
        # Ignore any cleanup errors
        Log                     Cleanup completed with warnings (expected)                      DEBUG
    END

Logs are requested from AIM workload
    [Documentation]    Requests logs from the deployed AIM workload
    Variable Should Exist                           ${DEPLOYED_WORKLOAD_ID}                         msg=DEPLOYED_WORKLOAD_ID is not set
    ${response}=            Get workload logs       ${DEPLOYED_WORKLOAD_ID}                         limit=50                expected_status=any
    Set Test Variable       ${response}             ${response}

Response should contain log entries
    [Documentation]    Verifies that the response contains valid log entries with proper structure
    ${json}=                Set Variable            ${response.json()}

    # Verify response structure
    Dictionary Should Contain Key                   ${json}                 logs                    msg=Response should contain logs field
    Dictionary Should Contain Key                   ${json}                 pagination              msg=Response should contain pagination field

    # Verify logs is a list
    ${logs}=                Get From Dictionary     ${json}                 logs
    Should Be True          isinstance($logs, list)                         msg=Logs should be a list

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
    [Documentation]    Requests detailed information about the deployed workload with resource metrics
    Variable Should Exist                           ${DEPLOYED_WORKLOAD_ID}                         msg=DEPLOYED_WORKLOAD_ID is not set
    ${params}=              Create Dictionary       with_resources=true
    ${response}=            Get menaged workload    ${DEPLOYED_WORKLOAD_ID}                         expected_status=200     params=${params}
    Set Test Variable       ${response}             ${response}

AIM workload detail endpoint should be complete
    [Documentation]    Verifies that workload detail endpoint contains all required fields including status, output, and resource metrics
    ${json}=                Set Variable            ${response.json()}

    # Core workload fields
    Dictionary Should Contain Key                   ${json}                 id                      msg=Workload should have id
    Dictionary Should Contain Key                   ${json}                 status                  msg=Workload should have status
    Dictionary Should Contain Key                   ${json}                 display_name            msg=Workload should have display_name
    Dictionary Should Contain Key                   ${json}                 name                    msg=Workload should have name

    # Verify workload type is INFERENCE for AIM workloads
    Dictionary Should Contain Key                   ${json}                 type                    msg=Workload should have type
    ${type}=                Get From Dictionary     ${json}                 type
    Should Be Equal         ${type}                 INFERENCE               msg=AIM workload type should be INFERENCE


    # Output field
    Dictionary Should Contain Key                   ${json}                 output                  msg=Workload should have output

    # Project information
    Dictionary Should Contain Key                   ${json}                 project                 msg=Workload should have project info

    # Resource metrics validation - should be populated when with_resources=true
    Dictionary Should Contain Key                   ${json}                 allocated_resources     msg=Workload should have allocated_resources field
    ${allocated_resources}=                         Get From Dictionary     ${json}                 allocated_resources
    Should Not Be Equal         ${allocated_resources}  ${None}                 msg=Workload should have allocated_resources populated when requested with with_resources=true

    # Verify resource structure
    Should Be True          isinstance($allocated_resources, dict)          msg=allocated_resources should be a dictionary

    # GPU count should be present (can be null)
    Dictionary Should Contain Key                   ${allocated_resources}  gpu_count               msg=allocated_resources should have gpu_count field

    # VRAM should be present (can be null)
    Dictionary Should Contain Key                   ${allocated_resources}  vram                    msg=allocated_resources should have vram field

    ${gpu_count}=           Get From Dictionary     ${allocated_resources}  gpu_count
    IF    $gpu_count is not None
        Should Be True          ${gpu_count} >= 0       msg=GPU count should be non-negative
    END

    # AIM-specific fields
    Dictionary Should Contain Key                   ${json}                 aim_id                  msg=AIM workload should have aim_id

AIM list endpoint should include workload details
    [Documentation]    Verifies that AIM list endpoint includes complete workload information for deployed AIMs
    ...    Checks AIM fields (id, image_name, image_tag, labels), workload presence,
    ...    workload details (id, status, type, aim_id), and allocated resources
    Variable Should Exist                           ${TEST_AIM_ID}          msg=TEST_AIM_ID is not set
    Project exists in system
    ${response}=            List AIMs               ${TEST_PROJECT_ID}   expected_status=200
    ${aims_data}=           Set Variable            ${response.json()}
    ${aims_list}=           Set Variable            ${aims_data['data']}

    # Find the deployed AIM
    ${target_aim}=          Set Variable            ${None}
    FOR    ${aim}    IN    @{aims_list}
        ${current_id}=          Set Variable            ${aim}[id]
        IF    "${current_id}" == "${TEST_AIM_ID}"
            ${target_aim}=          Set Variable            ${aim}
            BREAK
        END
    END

    Should Not Be Equal     ${target_aim}           ${None}                 msg=AIM ${TEST_AIM_ID} not found in list

    # Verify AIM has core fields
    Dictionary Should Contain Key                   ${target_aim}           id                      msg=AIM should have id field
    Dictionary Should Contain Key                   ${target_aim}           image_name              msg=AIM should have image_name field
    Dictionary Should Contain Key                   ${target_aim}           image_tag               msg=AIM should have image_tag field
    Dictionary Should Contain Key                   ${target_aim}           labels                  msg=AIM should have labels field

    # Verify workload is present and has details
    Dictionary Should Contain Key                   ${target_aim}           workload                msg=AIM should have workload field
    ${workload}=            Get From Dictionary     ${target_aim}           workload
    Should Not Be Equal     ${workload}             ${None}                 msg=AIM should have active workload

    # Verify workload has essential fields including aim_id (AIMWorkloadResponse)
    Dictionary Should Contain Key                   ${workload}             id                      msg=Workload should have id
    Dictionary Should Contain Key                   ${workload}             status                  msg=Workload should have status
    Dictionary Should Contain Key                   ${workload}             type                    msg=Workload should have type
    Dictionary Should Contain Key                   ${workload}             aim_id                  msg=Workload should have aim_id

    # Verify workload type is INFERENCE
    ${type}=                Get From Dictionary     ${workload}             type
    Should Be Equal         ${type}                 INFERENCE               msg=AIM workload type should be INFERENCE in list

    # Verify workload has allocated_resources
    Dictionary Should Contain Key                   ${workload}             allocated_resources     msg=Workload in list should have allocated_resources field

AIM deployment should exist in kubernetes
    [Documentation]    Verifies AIM workload has deployment in Kubernetes
    ...    Uses existing kubectl keyword to check deployment exists
    ${workload}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=200
    ${data}=    Set variable    ${workload.json()}
    ${name}=    Get from dictionary    ${data}    name
    ${project}=    Get from dictionary    ${data}    project
    ${namespace}=    Get from dictionary    ${project}    name

    # AIM workloads create deployment with -predictor suffix
    Deployment should exist in namespace    ${name}-predictor    ${namespace}

AIM deployment should not exist in kubernetes
    [Documentation]    Verifies AIM deployment removed from Kubernetes
    ...    Polls for deployment deletion with timeout
    ${workload}=    Get menaged workload    ${DEPLOYED_WORKLOAD_ID}    expected_status=any

    IF    ${workload.status_code} == 404
        Log    Workload already deleted from database    DEBUG
        RETURN
    END

    ${data}=    Set variable    ${workload.json()}
    ${name}=    Get from dictionary    ${data}    name
    ${project}=    Get from dictionary    ${data}    project
    ${namespace}=    Get from dictionary    ${project}    name

    # Poll for deployment to be removed
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Verify AIM deployment gone    ${name}-predictor    ${namespace}

Verify AIM deployment gone
    [Documentation]    Helper to verify deployment doesn't exist (used with polling)
    [Arguments]    ${deployment}    ${namespace}
    ${result}=    Run process    kubectl    get    deployment    ${deployment}
    ...    -n    ${namespace}
    ...    stderr=STDOUT
    Should not be equal as integers    ${result.rc}    0
    ...    msg=Deployment ${deployment} still exists in namespace ${namespace}
