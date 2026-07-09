# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for Catalog API finetune endpoints.
...                 Verifies finetuning creation, workload lifecycle, and error handling.
...
...                 Suite Efficiency Design:
...                 All GPU tests share a project and finetuning workload via idempotent Given
...                 preconditions backed by a suite-level cache. The cache avoids re-creating
...                 the same 30+ minute GPU job for each test. Every test is independently
...                 executable — Given steps re-create missing resources if run in isolation.
...                 Tests that destroy cached resources (force-delete) reset the cache so
...                 subsequent tests re-create via the same idempotent precondition.
Resource    resources/aiwb_test_data.resource
Resource    resources/aiwb_models.resource
Resource    resources/aiwb_aims.resource
Resource    resources/aiwb_custom_models.resource
Resource    resources/aiwb_datasets.resource
Resource    resources/airm_keywords.resource
Resource    resources/api/common.resource
Resource    resources/airm_projects.resource
Resource    resources/airm_secrets.resource
Library             Collections
Suite Teardown      Teardown Finetuning Suite


*** Test Cases ***
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

Finetuned model exists with expected fields
    [Documentation]    Verify that a finetuned model exists and has expected fields (id, name, onboardingStatus).
    ...    Runs after workload completes so the AIMModel CR is guaranteed to exist.
    [Tags]    finetuning    create    smoke    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists

    Then Finetuned model should have expected fields

Finetuning model appears in model list
    [Documentation]    Verify that a completed finetuned model appears in the namespace model list.
    ...    The list is K8s-based — it shows completed AIMModel CRs with workload-id labels.
    ...    Runs after workload completes so the AIMModel CR is guaranteed to exist.
    [Tags]    finetuning    models    list    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists

    Then the finetuned model should appear in the namespace model list

User can browse fine-tuned models page by page
    [Documentation]    Fine-tuned models in a project are served in pages rather
    ...                than as one flat list.
    [Tags]    finetuning    models    list    pagination

    Given a ready project with user access exists
    When fine-tuned models are listed for the project
    Then the result is returned page by page

Finetuned model becomes ready
    [Documentation]    Verify that the finetuned model onboarding status becomes ready after workload completes
    [Tags]    finetuning    model    onboarding    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    Then Finetuned model onboarding status should be "ready"

Finetuned model can be used as base model for a new finetuning run
    [Documentation]    Verify that a completed fine-tuned model can be selected as the base for a
    ...    new finetuning run and that the request is accepted.
    [Tags]    finetuning    create    models    kubectl

    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a completed fine-tuned model exists in the namespace
    And finetune dataset exists

    When a finetune request from an existing model is sent

    Then response status should be 202
    And the workload should use the AIMModel as base model

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
    [Documentation]    Verify a fine-tuned model can be deployed via the inference
    ...    capability endpoint. Deployment creates an AIMService CR referencing the
    ...    namespace-scoped AIMModel using the same deploy endpoint as cluster models —
    ...    the API auto-detects the model type.
    [Tags]    finetuning    aims    deploy    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"
    And fine-tuned model deployment configurations are available

    When fine-tuned model is deployed as an AIM service

    Then deployed AIMService should reference the fine-tuned model

Fine-tuned model is deployable without a prior custom-model import
    [Documentation]    Regression guard: a fine-tuned model must be deployable in a project
    ...    that has never imported a custom model. Deployment requires generated profiles,
    ...    and those are derived from a base model the platform must provision at fine-tune
    ...    launch. Previously the base existed only as a side effect of the custom-import
    ...    flow, so fine-tuned models in fresh projects had no profiles and could not deploy.
    [Tags]    finetuning    models    deploy    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And no custom model has been imported into the project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"

    Then fine-tuned model deployment configurations are available

Fine-tuned model deploy pins namespace AIMProfile when profiles are available
    [Documentation]    When aim-engine has emitted a Ready namespace AIMProfile, fine-tuned
    ...    deploy pins ``spec.profile.name`` to that profile even if the deploy request
    ...    includes runtime selector/override fields.
    [Tags]    finetuning    aims    deploy    gpu    kubectl

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"
    And fine-tuned model deployment configurations are available

    When fine-tuned model is deployed with runtime profile overrides

    Then AIMService CR should pin namespace profile for model in kubernetes    ${TEST_FINETUNING_RESOURCE_NAME}

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

Cancel a running finetuning job
    [Documentation]    Verify a user can cancel an in-progress finetuning job and that
    ...    the underlying workload transitions to the Deleted state.
    [Tags]    finetuning    delete    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    When the finetuning job is cancelled
    Then the workload status should become "Deleted"

Fine-tuned model shows deployment configurations
    [Documentation]    Verify that a ready fine-tuned model has AIMProfiles with
    ...    hardware configuration details (model name, precision) so users can choose
    ...    the right deployment profile.
    [Tags]    finetuning    models    deploy    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"
    And fine-tuned model deployment configurations are available

    Then fine-tuned model deployment configurations should include hardware details

Deleting fine-tuned model with active deployment is blocked
    [Documentation]    Verify the API rejects deletion of a fine-tuned model while it has
    ...    active deployments. Non-destructive — model and deployment remain intact.
    [Tags]    finetuning    models    delete    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"
    And fine-tuned model is deployed as an AIM service

    When user deletes the fine-tuned model

    Then the request should be rejected because the deployment is active

Force-deleting fine-tuned model cascades deployment removal
    [Documentation]    Verify force-delete removes the model and cascades removal of its
    ...    deployments.
    ...
    ...    DESTRUCTIVE: This test removes the fine-tuned model. Must be the last GPU test.
    [Tags]    finetuning    models    delete    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And secret "minio-credentials-fetcher" is assigned to project
    And a finetuning workload exists
    And finetuned model onboarding status should be "ready"
    And fine-tuned model is deployed as an AIM service

    When user force-deletes the fine-tuned model

    Then the fine-tuned model should be removed
    And the fine-tuned model deployment should be removed
