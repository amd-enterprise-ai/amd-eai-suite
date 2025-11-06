# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API models endpoints.
...                 Verifies model creation, listing, modification and stats operations.
...                 These tests cover the core functionality of the models API including:
...                 - Creating base models and adapters
...                 - Listing and filtering models
...                 - Retrieving model statistics
...                 - Modifying existing models
...
...                 Note: All test data is automatically cleaned up by tearing down
...                 the test database after the test suite execution.
Resource            resources/catalog_keywords.resource
Resource            resources/catalog_models.resource
Resource            resources/test_data.resource
Resource            resources/api/common.resource
Test Setup          Initialize Model Tracking
Test Teardown       Clean Up All Created Models


*** Test Cases ***
Create base model
    [Documentation]    Verify that a new base model can be created
    [Tags]                  models                  create                  base-model              smoke
    Given Project exists in system
    and valid base model data is prepared
    When create model request is sent
    Then response status should be 201
    And response should contain "${TEST_MODEL_NAME}"
    And response should contain key "created_at"
    And model should exist in database with correct properties

Create adapter model
    [Documentation]    Verify that a new adapter model can be created
    ...    Prerequisites:
    ...    - Base model exists in the system
    ...
    ...    Steps:
    ...    1. Prepare adapter test data
    ...    2. Create adapter linked to base model
    ...    3. Verify adapter properties
    ...    4. Verify base model linkage
    [Tags]                  models                  create                  adapter

    Given Project exists in system
    And base model exists in system
    When valid adapter data is prepared
    And create model request is sent
    Then response status should be 201
    And response should contain "MergedModel"
    And response should contain "${TEST_MODEL_NAME}"
    And response should contain key "base_model"
    And model should exist in database with correct properties
    And adapter should be linked to correct base model

List models with filters
    [Documentation]    Verify that models can be listed with filters
    [Tags]                  models                  list                    filtering
    Given Project exists in system
    And multiple models exist in system
    ...                     base_model_count=2
    ...                     adapter_count=2
    When list models request is sent with type "BaseModel" and status "pending"
    Then response status should be 200
    And response should contain only base models
    And all models should have pending status

Modify existing model
    [Documentation]    Verify that an existing model can be modified
    ...
    ...    Steps:
    ...    1. Create test model
    ...    2. Modify model properties
    ...    3. Verify changes were applied
    [Tags]                  models                  modify
    Given Project exists in system
    And model exists in system
    and model with name "${TEST_UPDATED_NAME}" does not exist in system
    When modify model request is sent with name "${TEST_UPDATED_NAME}" and type "BaseModel"
    Then response status should be 200
    And model name in database should be "${TEST_UPDATED_NAME}"

Delete non-existent model
    [Documentation]    Verify proper error when deleting non-existent model
    ...    Steps:
    ...    1. Attempt to delete model with invalid ID
    ...    2. Verify error response
    [Tags]                  models                  delete                  negative
    Given Project exists in system
    And a model does not exist
    When delete model request is sent
    Then response status should be 404

Delete existing model
    [Documentation]    Verify that an existing model can be deleted
    ...    Steps:
    ...    1. Create a test model
    ...    2. Delete the model
    ...    3. Verify model no longer exists
    [Tags]                  models                  delete                  smoke
    Given Project exists in system
    And model exists in system
    When delete model request is sent
    Then response status should be 204
    And the model should not exist in database

# Note: All test data is cleaned up by tearing down the test database after the test suite execution
