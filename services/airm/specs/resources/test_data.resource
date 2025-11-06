# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test data management layer.
...                 Handles creation and management of test data used across test cases.
...                 Provides consistent data generation that matches API schemas.
...                 This is a support layer used by the business-logic layer to
...                 prepare test data.
Library             String
Library             Collections
Library             Process
Resource            api/common.resource    # Need this for Catalog endpoint and Auth token
Resource            api/charts.resource    # Need this for Get chart verification
Resource            ./catalog_models.resource
Resource            ./catalog_projects.resource


*** Variables ***
${TEST_DATA}                    ${None}
${TEST_MODEL_NAME}              ${None}
${TEST_MODEL_ID}                ${None}
${TEST_UPDATED_NAME}            updated-model-name
${TEST_CHART_NAME}              ${None}
${TEST_JOB_CHART_ID}            ${None}
${TEST_SERVICE_CHART_ID}        ${None}
${TEST_DATASET_NAME}            ${None}
${TEST_DATASET_ID}              ${None}
${TEST_DATASET_DESCRIPTION}     ${None}
${TEST_DATASET_TYPE}            ${None}
${TEST_DATASET_FILE}            ${CURDIR}/../test_data/datasets/sample.jsonl
${TEST_DATASET_DATA}            ${None}
${TEST_UPDATED_DS_NAME}         ${None}
${TEST_UPDATED_DS_DESC}         ${None}
${TEST_DATASET_PATH}            ${None}
${MODEL_WEIGHTS_PATH}           ${None}
${TEST_CHAT_DATA}               ${None}


*** Keywords ***
Setup job test chart
    [Documentation]    Uploads the job test chart using the chart_uploader script and captures the ID.
    ${CHART_UPLOADER}=      Set Variable            ${CURDIR}/../../api/chart_uploader.py
    ${access_token}=        Authorization token
    ${catalog_endpoint}=    Catalog endpoint  # Gets base URL like http://localhost:8001/v1
    ${job_chart_dir}=       Normalize Path          ${CURDIR}/../test_data/job-chart
    ${cmd}=                 Set Variable            python ${CHART_UPLOADER} --api-url=${catalog_endpoint} --token=${access_token} --workload-dir=${job_chart_dir} --force

    ${result}=              Run Process             ${cmd}                  shell=True              stdout=PIPE             stderr=PIPE

    # Log stderr for debugging in case of failure
    Log                     Job chart uploader stderr: ${result.stderr}     level=DEBUG

    # Check return code first
    Should Be Equal As Integers                     ${result.rc}            0                       msg=Chart uploader script failed for job chart. RC: ${result.rc}\nStderr: ${result.stderr}

    # Retrieve job chart ID by chart name from database using polling
    Find chart ID by name                           test-sleep-job          TEST_JOB_CHART_ID
    Should Not Be Equal     ${TEST_JOB_CHART_ID}    ${None}                 msg=Could not find job chart with name 'test-sleep-job'

Setup service test chart
    [Documentation]    Uploads the service test chart using the chart_uploader script and captures the ID.
    ${CHART_UPLOADER}=      Set Variable            ${CURDIR}/../../api/chart_uploader.py
    ${access_token}=        Authorization token
    ${catalog_endpoint}=    Catalog endpoint
    ${service_chart_dir}=                           Normalize Path          ${CURDIR}/../test_data/service-chart
    ${cmd}=                 Set Variable            python ${CHART_UPLOADER} --api-url=${catalog_endpoint} --token=${access_token} --workload-dir=${service_chart_dir} --force

    ${result}=              Run Process             ${cmd}                  shell=True              stdout=PIPE             stderr=PIPE

    # Log stderr for debugging in case of failure
    Log                     Service chart uploader stderr: ${result.stderr}                         level=DEBUG

    # Check return code first
    Should Be Equal As Integers                     ${result.rc}            0                       msg=Chart uploader script failed for service chart. RC: ${result.rc}\nStderr: ${result.stderr}

    # Retrieve service chart ID by chart name from database using polling
    Find chart ID by name                           test-health-service     TEST_SERVICE_CHART_ID
    Should Not Be Equal     ${TEST_SERVICE_CHART_ID}                        ${None}                 msg=Could not find service chart with name 'test-health-service'

Valid adapter data is prepared
    [Documentation]    Prepares a valid set of test data for adapter creation (POST /models/{id}/adapters).
    ...    Ensures a base model exists first (creating if needed).
    ${base_model_exists}=                           Run Keyword And Return Status                   Variable Should Exist                           ${TEST_MODEL_ID}
    IF    not ${base_model_exists} or "${TEST_MODEL_ID}" == "${None}" or "${TEST_MODEL_ID}" == ""
        Valid base model data is prepared
        Create model request is sent
        ${model_id}=            Get from dictionary     ${response.json()}      id
        Set test variable       ${TEST_BASE_MODEL_ID}                           ${model_id}
    END

    ${random_suffix}=       Generate random string                          8                       [LETTERS][NUMBERS]
    ${adapter_name}=        Set variable            test-adapter-${random_suffix}
    ${adapter_data}=        Create dictionary
    ...                     name=${adapter_name}
    ...                     description=Test merged model description
    ...                     model_weights_path=default-bucket/models/${CURRENT_PROJECT_SLUG}/adapters/${adapter_name}
    ...                     type=MergedModel
    ...                     base_model_id=${TEST_BASE_MODEL_ID}
    ...                     canonical_name=test/merged-model
    Set test variable       ${TEST_DATA}            ${adapter_data}
    Set test variable       ${TEST_MODEL_NAME}      ${adapter_name}

Valid dataset data is prepared
    [Documentation]    Prepares a valid set of test data for dataset creation (POST /datasets).
    ...    Creates data matching DatasetCreate schema.
    # Ensure we have a project to work with
    Project exists in system

    ${random_suffix}=       Generate random string                          8                       [LETTERS][NUMBERS]
    ${dataset_name}=        Set variable            test dataset ${random_suffix}
    ${dataset_desc}=        Set variable            Description for ${dataset_name}
    ${dataset_type}=        Set variable            Fine-tuning  # Using exact enum value from DatasetType
    ${dataset_data}=        Create dictionary
    ...                     name=${dataset_name}
    ...                     description=${dataset_desc}
    ...                     path=default-bucket/datasets/${CURRENT_PROJECT_SLUG}/${dataset_name}
    ...                     type=${dataset_type}
    Set test variable       ${TEST_DATASET_DATA}    ${dataset_data}
    Set test variable       ${TEST_DATASET_NAME}    ${dataset_name}
    # The API transforms the name by converting hyphens to spaces and capitalizing words
    # Using the same logic as the backend: word.capitalize() for each word
    ${name_with_spaces}=    Replace String          ${dataset_name}         -                       ${SPACE}
    ${derived_name}=        Evaluate                " ".join(word.capitalize() for word in "${name_with_spaces}".split())
    Set test variable       ${TEST_DATASET_DERIVED_NAME}                    ${derived_name}
    Set test variable       ${TEST_DATASET_DESCRIPTION}                     ${dataset_desc}
    Set test variable       ${TEST_DATASET_TYPE}    ${dataset_type}
    Set test variable       ${TEST_DATASET_ID}      ${None}
    Set Test Variable       ${TEST_DATASET_PATH}    default-bucket/datasets/${CURRENT_PROJECT_SLUG}/${dataset_name}

    Log                     Prepared dataset test data with name: ${dataset_name}
    Log                     Expected derived name in response: ${derived_name}

Prepare updated dataset data
    [Documentation]    Generates a unique description for dataset modification tests.
    ...    Note: Dataset names are immutable after creation, so we only update the description.
    ${random_suffix}=       Generate Random String                          8                       [LETTERS][NUMBERS]
    ${updated_desc}=        Set Variable            Updated description ${random_suffix} for existing dataset.

    VAR    ${TEST_UPDATED_DS_DESC}    ${updated_desc}    scope=test
    Log                     Prepared updated dataset test data with description: ${updated_desc}

Valid dataset upload data is prepared
    [Documentation]    Prepares valid test data for dataset upload tests
    ${random_suffix}=       Generate random string                          8                       [LETTERS][NUMBERS]
    ${dataset_name}=        Set variable            test-dataset-upload-${random_suffix}
    ${dataset_desc}=        Set variable            Upload test dataset description
    ${dataset_type}=        Set variable            Fine-tuning

    # Set paths for test data - use the correct sample.jsonl in datasets directory
    ${dataset_file}=        Set variable            ${CURDIR}/../test_data/datasets/sample.jsonl

    # Verify file exists
    File should exist       ${dataset_file}         msg=Test dataset file not found: ${dataset_file}

    # Set test variables for use by other keywords
    Set test variable       ${TEST_DATASET_NAME}    ${dataset_name}
    # The API transforms the name by converting hyphens to spaces and capitalizing words
    ${name_with_spaces}=    Replace String          ${dataset_name}         -                       ${SPACE}
    ${derived_name}=        Evaluate                " ".join(word.capitalize() for word in "${name_with_spaces}".split())
    Set test variable       ${TEST_DATASET_DERIVED_NAME}                    ${derived_name}
    Set test variable       ${TEST_DATASET_DESCRIPTION}                     ${dataset_desc}
    Set test variable       ${TEST_DATASET_TYPE}    ${dataset_type}
    Set test variable       ${TEST_DATASET_FILE}    ${dataset_file}

    Log                     Prepared dataset upload test data with name: ${dataset_name}
    Log                     Expected derived name in response: ${derived_name}

Valid chat data is prepared
    [Documentation]    Prepares valid test data for chat tests
    ${messages}=            Create list
    ...                     {"role": "user", "content": "Hello?"}
    ${chat_data}=           Create dictionary
    ...                     model= /workload/${MODEL_WEIGHTS_PATH}
    ...                     stream=${False}
    ...                     messages=${messages}
    ...                     temperature=0.5
    Set test variable       ${TEST_CHAT_DATA}       ${chat_data}
