# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API models endpoints.
...                 Verifies model deletion error handling.
...
...                 IMPORTANT: Models are created through finetuning workflows (see finetuning.robot),
...                 not through direct POST /v1/models endpoint (which was removed from the API).
...                 Tests requiring model existence (list, modify, delete existing) are not feasible
...                 as E2E tests because model creation requires a full finetuning workflow.
Resource    resources/airm_keywords.resource
Resource    resources/airm_projects.resource
Resource    resources/aiwb_models.resource
Resource    resources/aiwb_test_data.resource
Resource    resources/api/common.resource
Test Setup          Initialize Model Tracking
Test Teardown       Clean Up All Created Models


*** Test Cases ***
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

# Note: Model creation tests are in finetuning.robot since models are created
# through POST /v1/models/{id}/finetune endpoint, not through direct creation.
# The POST /v1/models endpoint was removed from the API.
