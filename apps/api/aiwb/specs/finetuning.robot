# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API finetune endpoints.
...                 Verifies finetuning creation, workload lifecycle, and error handling.
...
...                 Suite Efficiency Design:
...                 This suite uses Suite Setup/Teardown so the project is created once and
...                 deleted once at the end. Each test declares its preconditions via Given
...                 steps for readability — these are idempotent and reuse existing resources.
...
...                 All GPU tests use idempotent preconditions — they reuse existing
...                 finetuning resources if available, avoiding duplicate job creation.
...
...                 Test ordering is intentional:
...                 1. Finetune model exists with expected fields
...                 2. Workload running test waits for workload to start
...                 3. Workload complete test waits for finish
...                 4. Model ready test verifies onboarding_status
...                 5. Invalid data test is independent (no GPU)
Resource    resources/aiwb_test_data.resource
Resource    resources/aiwb_models.resource
Resource    resources/aiwb_datasets.resource
Resource    resources/airm_keywords.resource
Resource    resources/api/common.resource
Resource    resources/airm_projects.resource
Resource    resources/airm_secrets.resource
Library             Collections
Suite Setup         Setup Finetuning Suite
Suite Teardown      Teardown Finetuning Suite


*** Test Cases ***
Finetuned model exists with expected fields
    [Documentation]    Verify that a finetuned model exists and has expected fields (id, name, onboarding_status).
    ...    Uses idempotent precondition — reuses existing finetuning workload if available.
    [Tags]    finetuning    create    smoke    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists

    Then Finetuned model should have expected fields

Finetuning workload starts running
    [Documentation]    Verify that the finetuning workload reaches Running status
    [Tags]    finetuning    workload    status    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    Then Finetuning workload should reach status "Running"

Finetuning workload completes
    [Documentation]    Verify that the finetuning workload completes successfully
    [Tags]    finetuning    workload    complete    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    Then Finetuning workload should reach status "Complete"

Finetuned model becomes ready
    [Documentation]    Verify that the finetuned model onboarding status becomes ready after workload completes
    [Tags]    finetuning    model    onboarding    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    Then Finetuned model onboarding status should be "ready"

Finetune with invalid data fails
    [Documentation]    Verify that a finetune request with invalid data fails with 422
    [Tags]    finetuning    error    invalid-data

    Given a ready project with user access exists

    # Prepare invalid finetune parameters
    VAR    &{invalid_finetune_data}
    ...    batch_size=-1
    ...    learning_rate=-0.001
    ...    epochs=0
    VAR    ${base_model_name}    TinyLlama/TinyLlama-1.1B-Chat-v1.0

    When finetune request is sent with data    ${base_model_name}    ${invalid_finetune_data}

    Then response status should be 422
