# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for model deletion endpoints.
...                 Verifies deletion of AIMModel CRs via the API and error handling.
...
...                 IMPORTANT: Models are created through finetuning workflows (see finetuning.robot),
...                 not through direct POST /v1/models endpoint (which was removed from the API).
...                 The delete endpoint uses the AIMModel CR name (not a DB UUID).
...                 Pre-created AIMModel CRs via kubectl are used for successful deletion tests.
Resource    resources/airm_keywords.resource
Resource    resources/airm_projects.resource
Resource    resources/aiwb_models.resource
Resource    resources/aiwb_test_data.resource
Resource    resources/api/common.resource
Test Teardown       Clean Up All Created Models


*** Test Cases ***
Finetunable models include GPU hardware compatibility information
    [Documentation]    Verify finetunable models are returned with GPU hardware details
    ...    so users can identify which models are compatible with their cluster's accelerators.
    [Tags]    models    finetunable    smoke

    Given Project exists in system
    When finetunable models list is requested
    Then each finetunable model should include GPU hardware compatibility details

Delete non-existent model
    [Documentation]    Verify proper error when deleting a model that does not exist.
    ...    Tests DELETE /v1/namespaces/{namespace}/models/{name} with a non-existent name.
    ...
    ...    Steps:
    ...    1. Attempt to delete a model with a name that has no matching AIMModel CR
    ...    2. Verify 404 error response
    [Tags]                  models                  delete                  negative
    Given Project exists in system
    And a model does not exist
    When delete model request is sent
    Then response status should be 404

Delete AIMModel CR via API
    [Documentation]    Verify a fine-tuned model is deleted when the API endpoint is called with its name.
    ...    Tests the full deletion path: API call → AIMModel CR removal from the cluster.
    ...
    ...    Steps:
    ...    1. Pre-create an AIMModel CR directly in the cluster
    ...    2. Call DELETE /v1/namespaces/{namespace}/models/{name}
    ...    3. Verify 204 No Content response
    ...    4. Verify the AIMModel CR no longer exists in the cluster
    [Tags]                  models                  delete                  kubectl
    Given Project exists in system
    And an AIMModel CR exists in the namespace
    When delete AIMModel CR request is sent
    Then response status should be 204
    And the AIMModel CR should not exist

# Note: Model creation tests are in finetuning.robot since models are created
# through POST /v1/models/{id}/finetune endpoint, not through direct creation.
# The POST /v1/models endpoint was removed from the API.
