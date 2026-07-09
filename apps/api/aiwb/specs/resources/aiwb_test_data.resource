# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       AIWB test data management layer.
...                 Handles creation and management of test data used across AIWB test cases.
...                 Provides consistent data generation that matches API schemas.
Library             String
Library             Collections
Library             OperatingSystem
Resource            resources/airm_projects.resource
Resource            aiwb_common.resource


*** Variables ***
${TEST_DATASET_ID}              ${None}
${TEST_DATASET_FILE}            ${EXECDIR}/test_data/datasets/sample.jsonl
${TEST_DATASET}                 ${None}
${TEST_UPDATED_DS_DESC}         ${None}


*** Keywords ***
Prepare updated dataset data
    [Documentation]    Generates a unique description for dataset modification tests.
    ...    Note: Dataset names are immutable after creation, so we only update the description.
    ${random_suffix}=       Generate Random String                          8                       [LETTERS][NUMBERS]
    ${updated_desc}=        Set Variable            Updated description ${random_suffix} for existing dataset.

    VAR    ${TEST_UPDATED_DS_DESC}    ${updated_desc}    scope=test
    Log                     Prepared updated dataset test data with description: ${updated_desc}

Valid dataset upload data is prepared
    [Documentation]    Prepares valid test data for dataset upload tests.
    ...    Sets TEST_DATASET dict with name, description, type keys.
    # K8s/DB resource names must be lowercase.
    ${random_suffix}=       Generate random string                          8                       [LOWER][NUMBERS]
    ${dataset_name}=        Set variable            test-dataset-upload-${random_suffix}
    ${dataset_desc}=        Set variable            Upload test dataset description
    ${dataset_type}=        Set variable            Fine-tuning

    ${dataset_file}=        Set variable            ${TEST_DATASET_FILE}

    # Verify file exists
    File should exist       ${dataset_file}         msg=Test dataset file not found: ${dataset_file}

    ${dataset_data}=        Create dictionary
    ...                     name=${dataset_name}
    ...                     description=${dataset_desc}
    ...                     type=${dataset_type}
    Set test variable       ${TEST_DATASET}         ${dataset_data}
    Set test variable       ${TEST_DATASET_FILE}    ${dataset_file}

    Log                     Prepared dataset upload test data with name: ${dataset_name}
