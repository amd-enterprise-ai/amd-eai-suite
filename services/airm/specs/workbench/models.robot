# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API models endpoints.
...                 Verifies model listing, modification and deletion operations.
...
...                 IMPORTANT: Models are created through finetuning workflows (see finetuning.robot),
...                 not through direct POST /v1/models endpoint (which was removed from the API).
...
...                 Available endpoints:
...                 - GET /v1/models - List models with optional filters
...                 - GET /v1/models/finetunable - List finetunable model names
...                 - GET /v1/models/{id} - Get specific model details
...                 - PUT /v1/models/{id} - Update model properties
...                 - DELETE /v1/models/{id} - Delete a model
...                 - POST /v1/models/delete - Batch delete models
...                 - POST /v1/models/{id}/finetune - Finetune a model (creates new model)
...                 - POST /v1/models/{id}/deploy - Deploy model for inference
...
...                 Note: All test data is automatically cleaned up by tearing down
...                 the test database after the test suite execution.
Resource            ../resources/catalog_keywords.resource
Resource            ../resources/airm_projects.resource
Resource            ../resources/catalog_models.resource
Resource            ../resources/test_data.resource
Resource            ../resources/api/common.resource
Test Setup          Initialize Model Tracking
Test Teardown       Clean Up All Created Models


*** Test Cases ***
List models with filters
    [Documentation]    Verify that models can be listed with optional filters
    ...    Tests GET /v1/models endpoint with query parameters
    ...
    ...    NOTE: Currently skipped - requires model creation which is only possible
    ...    through finetuning workflow. The endpoint functionality is verified
    ...    through API integration tests. Creating models via finetuning is too
    ...    time-consuming and GPU-intensive for regular E2E test runs.
    ...
    ...    To enable this test:
    ...    1. Create multiple models via finetuning (see finetuning.robot)
    ...    2. Modify the "multiple models exist in system" keyword to use finetuned models
    ...    3. Or create test fixtures/mocks that provide model IDs without finetuning
    [Tags]                  models                  list                    filtering                   skip
    Given Project exists in system
    And multiple models exist in system
    ...                     base_model_count=2
    ...                     adapter_count=2
    When list models request is sent with type "BaseModel" and status "pending"
    Then response status should be 200
    And response should contain only base models
    And all models should have status "pending"

Modify existing model
    [Documentation]    Verify that an existing model can be modified
    ...    Tests PUT /v1/models/{id} endpoint
    ...
    ...    NOTE: Currently skipped - requires model creation which is only possible
    ...    through finetuning workflow. The finetuning process is complex and
    ...    time-consuming, making this test impractical for regular test runs.
    ...    The endpoint functionality is verified through API integration tests.
    ...
    ...    To enable this test:
    ...    1. Create a model via finetuning workflow (see finetuning.robot)
    ...    2. Modify the "model exists in system" keyword to use the finetuned model
    ...    3. Or create test fixture/mock that provides a model ID without finetuning
    ...
    ...    Steps:
    ...    1. Create test model (via finetuning or test fixture)
    ...    2. Modify model properties
    ...    3. Verify changes were applied
    [Tags]                  models                  modify                  skip
    Given Project exists in system
    And model exists in system
    and model with name "${TEST_UPDATED_NAME}" does not exist in system
    When modify model request is sent with name "${TEST_UPDATED_NAME}" and type "BaseModel"
    Then response status should be 200
    And model name in database should be "${TEST_UPDATED_NAME}"

Delete non-existent model
    [Documentation]    Verify proper error when deleting non-existent model
    ...    Tests DELETE /v1/models/{id} with invalid ID
    ...
    ...    Steps:
    ...    1. Attempt to delete model with invalid ID
    ...    2. Verify 404 error response
    [Tags]                  models                  delete                  negative
    Given Project exists in system
    And a model does not exist
    When delete model request is sent
    Then response status should be 404

Delete existing model
    [Documentation]    Verify that an existing model can be deleted
    ...    Tests DELETE /v1/models/{id} with valid model
    ...
    ...    NOTE: Currently skipped - requires model setup via finetuning workflow.
    ...    The finetuning process is complex and time-consuming, making this test
    ...    impractical for regular test runs. The endpoint functionality is verified
    ...    through the "Delete non-existent model" test which confirms the endpoint
    ...    exists and handles errors correctly.
    ...
    ...    To test this endpoint fully:
    ...    1. Create a model via finetuning workflow (see finetuning.robot)
    ...    2. Delete the model
    ...    3. Verify model no longer exists in database
    [Tags]                  models                  delete                  skip
    Given Project exists in system
    And model exists in system
    When delete model request is sent
    Then response status should be 204
    And the model should not exist in database

# Note: Model creation tests are in finetuning.robot since models are created
# through POST /v1/models/{id}/finetune endpoint, not through direct creation.
# The POST /v1/models endpoint was removed from the API.
