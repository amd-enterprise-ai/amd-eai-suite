# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API finetune endpoints.
...                 Verifies finetuning creation, validation, and error handling operations.
Resource            resources/catalog_models.resource
Resource            resources/catalog_datasets.resource
Resource            resources/catalog_charts.resource
Resource            resources/catalog_keywords.resource
Resource            resources/test_data.resource
Resource            resources/api/common.resource
Resource            resources/api/finetuning.resource
Resource            resources/catalog_projects.resource
Library             Collections
Test Setup          Setup Finetuning Test Tracking
Test Teardown       Cleanup Finetuning Test Resources


*** Variables ***
${TEMPLATE_FILE}            ${CURDIR}/test_data/charts/finetuning_template.yaml
${VALUES_FILE}              ${CURDIR}/test_data/charts/values.yaml
${SCHEMA_FILE}              ${CURDIR}/test_data/charts/schema.json
${TINILLAMA_ID}             418da8ba-b839-42a9-8fe9-15878a6086fe
${FINETUNE_DATASET_ID}      50698587-8333-4fb6-ba89-c9f04633f3df


*** Keywords ***
Setup Finetuning Test Tracking
    [Documentation]    Initialize both model and dataset tracking for finetuning tests
    Initialize Model Tracking
    Initialize Dataset Tracking
    Initialize Chart Tracking

Cleanup Finetuning Test Resources
    [Documentation]    Clean up both models and datasets created during finetuning tests
    Clean Up All Created Models
    Clean Up All Created Datasets
    Clean Up All Created Charts


*** Test Cases ***
Finetune new base model
    [Documentation]    Verify that a finetune model request is sent successfully
    [Tags]                  finetuning              create                  smoke

    Given Project exists in system
    And Base model exists in system
    And Finetune dataset exists

    When a finetune request is sent

    When the merged model is retrieved
    Then Response should contain key "id"
    And Response should contain key "name"
    And Response should contain key "onboarding_status"

    When the workflow is retrieved
    Then Response should contain key "id"
    And Response should contain key "cluster"
    And Response should contain key "manifest"

Finetune existing base model
    [Documentation]    Verify that a finetune model request is sent successfully
    [Tags]                  finetuning              create                  smoke

    Given Project exists in system
    And Base model for finetuning exists in system
    And Finetune dataset exists

    When a finetune request is sent

    When the merged model is retrieved
    Then Response should contain key "id"
    And Response should contain key "name"
    And Response should contain key "onboarding_status"

    When the workflow is retrieved
    Then Response should contain key "id"
    And Response should contain key "cluster"
    And Response should contain key "manifest"

Finetune model with invalid data
    [Documentation]    Verify that a finetune model request with invalid data fails as expected
    [Tags]                  finetuning              error                   invalid-data

    Given Project exists in system
    And Base model exists in system

    # Modify the finetune data to include invalid fields
    ${invalid_finetune_data}=                       Create Dictionary
    ...                     batch_size=-1
    ...                     learning_rate=-0.001
    ...                     epochs=0

    Log                     Sending finetune request with invalid data: ${invalid_finetune_data}
    ${response}=            Send Finetune Request                           ${TEST_BASE_MODEL_ID}                           ${invalid_finetune_data}
    # Check that the response status is 422 Unprocessable Entity
    Then Status should be                           422                     ${response}
