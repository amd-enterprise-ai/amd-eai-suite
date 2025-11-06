# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Common test verification keywords.
...                 Provides generic response validation and assertion keywords
...                 used across different test scenarios. This is a utility layer
...                 that supports both API and business-logic layers.
Library             String
Resource            api/models.resource
Resource            api/health.resource
Resource            api/workloads.resource
Resource            api/datasets.resource
Resource            catalog_charts.resource
Resource            catalog_workloads.resource
Resource            catalog_datasets.resource
Resource            catalog_projects.resource


*** Keywords ***
Catalog service is running
    [Documentation]    Verifies that catalog service is running and healthy
    Verify catalog health


*** Keywords ***
Health check is performed
    [Documentation]    Perform a health check and store response
    ${response}=            Get health status
    Set Test Variable       ${response}             ${response}

Response status should be ${expected_status:[0-9]+}
    [Documentation]    Verify the response status code and log error details on failure
    TRY
        Status should be        ${expected_status}      ${response}
    EXCEPT    AS    ${error}
        ${body}=                Set Variable            ${response.text}
        ${error_msg}=           Set Variable            Response status was ${response.status_code} but expected ${expected_status}.\nResponse URL: ${response.url}\nResponse headers: ${response.headers}\nResponse body: ${body}
        Log                     ${error_msg}            ERROR
        Fail                    ${error_msg}
    END

Response should contain status "${expected_status}"
    [Documentation]    Verify the response contains expected status
    Dictionary should contain value                 ${response.json()}      ${expected_status}

Response should contain "${expected_value}"
    [Documentation]    Verifies response contains an expected value
    TRY
        Dictionary should contain value                 ${response.json()}      ${expected_value}
    EXCEPT    AS    ${error}
        ${response_json}=       Set Variable            ${response.json()}
        ${error_msg}=           Set Variable            Response does not contain expected value '${expected_value}'.\nActual response content: ${response_json}\nRequest URL: ${response.url}
        Log                     ${error_msg}            ERROR                   console=yes
        FAIL                    ${error_msg}
    END

Response should contain value "${expected_value}"
    [Documentation]    Verifies response contains an expected value (alias for consistency)
    Response should contain "${expected_value}"

Response should contain key "${expected_key}"
    [Documentation]    Verifies response contains an expected key
    TRY
        Dictionary should contain key                   ${response.json()}      ${expected_key}
    EXCEPT    AS    ${error}
        ${error_msg}=           Set Variable            Response is missing required key '${expected_key}'.\nResponse body: ${response.text}\nRequest URL: ${response.url}
        Log                     ${error_msg}            ERROR                   console=yes  # Keep console output for failures
        Fail                    ${error_msg}
    END

List response should contain key "${expected_key}"
    [Documentation]    Verifies all items in response contain the expected key
    ${json_list}=    ${response.json()}
    FOR    ${item}    IN    @{json_list}
        TRY
            Dictionary Should Contain Key                   ${item}                 ${expected_key}
        EXCEPT    AS    ${error}
            ${error_msg}=           Set Variable            Response item is missing required key '${expected_key}'.\nItem: ${item}\nFull Response: ${response.text}\nURL: ${response.url}
            Log                     ${error_msg}            level=ERROR             console=yes
            Fail                    ${error_msg}
        END
    END

Total count should be greater than ${expected}
    [Documentation]    Verifies total_count is greater than expected value
    ${total}=               Get length              ${response.json()}
    Should be true          ${total} >= ${expected}

Multiple charts exist
    [Documentation]    Creates multiple test charts for listing tests
    # Use the chart tracking system from catalog_charts.resource
    FOR    ${index}    IN RANGE    3
        ${random_suffix}=       Generate random string                          8                       [LETTERS][NUMBERS]
        ${chart_name}=          Set variable            test-chart-${random_suffix}
        ${response}=            Create chart request    ${chart_name}           ${TEMPLATE_FILE}        ${VALUES_FILE}          ${SCHEMA_FILE}

        # Accept 201 Created as success for chart creation
        IF    ${response.status_code} != 200 and ${response.status_code} != 201
            ${error_msg}=           Set Variable            Chart creation failed with status ${response.status_code}.\nResponse body: ${response.text}
            Log                     ${error_msg}            ERROR                   console=yes  # Keep console output for failures
            Fail                    ${error_msg}
        END

        # Log success - explicitly mention success with status 201
        Log                     Chart created successfully with status ${response.status_code}: ${chart_name}

        # Extract and store the chart ID using the proper tracking system
        ${json}=                Set Variable            ${response.json()}
        TRY
            # Try direct ID
            ${chart_id}=            Get from dictionary     ${json}                 id
            Append to list          ${CREATED_CHART_IDS}    ${chart_id}
            Log                     Added chart ${chart_id} to cleanup list: ${CREATED_CHART_IDS}           level=DEBUG
        EXCEPT    AS    ${error}
            TRY
                # Try charts array
                ${charts}=              Get from dictionary     ${json}                 charts
                ${chart}=               Get from list           ${charts}               0
                ${chart_id}=            Get from dictionary     ${chart}                id
                Append to list          ${CREATED_CHART_IDS}    ${chart_id}
                Log                     Added chart ${chart_id} to cleanup list: ${CREATED_CHART_IDS}           level=DEBUG
            EXCEPT    AS    ${nested_error}
                Log                     Chart creation response has unexpected format.\nResponse: ${response.text}                      ERROR                   console=yes  # Keep console output for failures
                Fail                    Chart creation response has unexpected format
            END
        END
    END

Response should contain only base models
    [Documentation]    Verifies all models in response are base models
    ${json}=                Set variable            ${response.json()}
    @{models}=              Set variable            ${json}
    FOR    ${model}    IN    @{models}
        Dictionary should contain item                  ${model}                type                    BaseModel
    END

All models should have pending status
    [Documentation]    Verifies all models have pending onboarding status
    ${json}=                Set variable            ${response.json()}
    @{models}=              Set variable            ${json}
    FOR    ${model}    IN    @{models}
        Dictionary should contain item                  ${model}                onboarding_status       pending
    END

Cleanup
    [Documentation]    Cleanup created items after test execution
    [Arguments]             ${workload_id}=${None}                          ${base_model_id}=${None}                        ${managed_model_id}=${None}
    Remove created items    ${workload_id}          ${base_model_id}        ${managed_model_id}

Remove created items
    [Documentation]    Remove created items from the system and verify deletion
    [Arguments]             ${workload_id}=${None}                          ${base_model_id}=${None}                        ${managed_model_id}=${None}
    Log To Console          message=Cleanup started for workload_id=${workload_id}, base_model_id=${base_model_id}, managed_model_id=${managed_model_id}

    IF    '${workload_id}' != '${None}'
        Delete menaged workload                         ${workload_id}          params=${QUERY_PARAMS}                          expected_status=204
    END

    IF    '${base_model_id}' != '${None}'
        Delete model            model_id=${base_model_id}                       expected_status=204     project_id=${CURRENT_PROJECT_ID}
        Get model               model_id=${base_model_id}                       expected_status=404     project_id=${CURRENT_PROJECT_ID}
    END

    IF    '${managed_model_id}' != '${None}'
        Delete model            model_id=${managed_model_id}                    expected_status=204     project_id=${CURRENT_PROJECT_ID}
        Get model               model_id=${managed_model_id}                    expected_status=404     project_id=${CURRENT_PROJECT_ID}
    END

Finetune test variables are prepaired
    [Documentation]    Prepares finetune data for the test
    Set Test Variable       ${MODEL_WEIGHTS_PATH}                           /workload/default-bucket/models/${CURRENT_PROJECT_SLUG}/TinyLlama/TinyLlama-1.1B-Chat-v1.0
    Set Test Variable       ${TEST_WORKLOAD_ID}     5243353d-1511-4813-9bd0-50459b08aa28
