# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API finetune endpoints.
...                 Verifies finetuning creation, workload lifecycle, and error handling.
...
...                 Suite Efficiency Design:
...                 This suite uses Suite Teardown so the project is created lazily and
...                 deleted once at the end. Each test declares its preconditions via Given
...                 steps for readability — these are idempotent and reuse existing resources.
...
...                 All GPU tests use idempotent preconditions — they reuse existing
...                 finetuning resources if available, avoiding duplicate job creation.
...
...                 Test ordering is intentional:
...                 1-3. CPU-only model API tests via dummy AIMModel CR (no GPU)
...                 4-5. Finetune model exists/list (GPU)
...                 6. Workload running test waits for workload to start (GPU)
...                 7. Workload complete test waits for finish (GPU)
...                 8. Model ready test verifies onboarding_status (GPU)
...                 9. Invalid data test is independent (no GPU)
...                 10-11. Fine-tuned model AIM deployment tests (GPU)
Resource    resources/aiwb_test_data.resource
Resource    resources/aiwb_models.resource
Resource    resources/aiwb_aims.resource
Resource    resources/aiwb_datasets.resource
Resource    resources/airm_keywords.resource
Resource    resources/api/common.resource
Resource    resources/airm_projects.resource
Resource    resources/airm_secrets.resource
Library             Collections
Suite Teardown      Teardown Finetuning Suite


*** Test Cases ***
Dummy AIMModel appears in model list
    [Documentation]    Verify that a dummy AIMModel CR (simulating a completed fine-tuned model)
    ...    appears in the namespace model list via the K8s-based endpoint.
    ...    No GPU required — the CR is created directly via kubectl.
    [Tags]    finetuning    models    list    cpu

    Given a ready project with user access exists
    And a dummy AIMModel CR exists in the namespace

    Then the dummy AIMModel should appear in the namespace model list

Dummy AIMModel is retrievable by resource name
    [Documentation]    Verify that a dummy AIMModel CR can be retrieved by resource name
    ...    via GET /models/{resource_name}. Tests the K8s-first single-model endpoint.
    [Tags]    finetuning    models    get    cpu

    Given a ready project with user access exists
    And a dummy AIMModel CR exists in the namespace

    Then the dummy AIMModel should be retrievable by resource name

Non-existent model returns 404
    [Documentation]    Verify that requesting a non-existent model by resource name returns 404.
    [Tags]    finetuning    models    error    cpu

    Given a ready project with user access exists

    Then getting a non-existent model should return 404

Finetuned model exists with expected fields
    [Documentation]    Verify that a finetuned model exists and has expected fields (id, name, onboardingStatus).
    ...    Uses idempotent precondition — reuses existing finetuning workload if available.
    [Tags]    finetuning    create    smoke    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists

    Then Finetuned model should have expected fields

Finetuning model appears in model list
    [Documentation]    Verify that a model undergoing finetuning appears in the namespace model list.
    ...    The list is K8s-based — it combines in-progress finetuning jobs and completed AIMModel CRs.
    ...    Checks that the response includes the expected fields: name, status, resource_name.
    [Tags]    finetuning    models    list    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists

    Then the finetuned model should appear in the namespace model list

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
    ...    batchSize=-1
    ...    learningRate=-0.001
    ...    epochs=0
    VAR    ${base_model_name}    meta-llama/Llama-3.2-1B-Instruct

    When finetune request is sent with data    ${base_model_name}    ${invalid_finetune_data}

    Then response status should be 422

Fine-tuned model can be deployed for inference
    [Documentation]    Verify a fine-tuned model can be deployed via POST /aims/services.
    ...    Deployment creates an AIMService CR referencing the namespace-scoped AIMModel
    ...    using the same deploy endpoint as cluster models — the API auto-detects the model type.
    [Tags]    finetuning    aims    deploy    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"
    And fine-tuned AIM service templates are available

    When fine-tuned model is deployed as an AIM service

    Then deployed AIMService should reference the fine-tuned model
    And deployed fine-tuned model should have an inference endpoint

Deployed fine-tuned model is accessible for inference
    [Documentation]    Verify a deployed fine-tuned model AIMService is accessible for inference.
    ...    Once the service reaches Running state, it appears in the chattable services list
    ...    and can be used for chat from the playground.
    [Tags]    finetuning    aims    inference    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"
    And fine-tuned model is deployed as an AIM service

    When deployed AIM reaches Running state

    Then deployed fine-tuned model should have an inference endpoint
    And deployed fine-tuned model should be accessible for inference
