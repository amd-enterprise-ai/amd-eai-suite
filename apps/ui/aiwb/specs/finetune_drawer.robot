# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for the fine-tuning drawer base model selector (EAI-5741)
...                 and the custom-model deploy drawer (EAI-6370).
...
...                 EAI-5741: Verifies that the fine-tuning drawer displays GPU-compatible recipes
...                 with hardware names and handles the empty state when no recipes are compatible
...                 with the cluster's GPU hardware.
...
...                 Verifies the custom-model deploy drawer for a ready model — drawer
...                 rendering, submit with default values, and AIMService existence and
...                 chat-accessibility after deployment.

Resource            resources/common/browser_setup.resource
Resource            resources/finetune.resource
Resource            resources/airm_projects.resource

Suite Teardown      Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***

Fine-tuning drawer lists compatible recipes with GPU hardware names
    [Documentation]    Verify the fine-tuning drawer shows available base models with their
    ...    GPU hardware names displayed as descriptions below each model name.
    ...
    ...    Requires: at least one GPU-compatible fine-tuning recipe in the catalog.
    [Tags]    ui    models    finetune    smoke

    Given a ready project with user access exists
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tuning drawer
    And user opens the base model selector
    Then compatible fine-tuning recipes should be listed with hardware names

Fine-tuning drawer shows each base model at most once
    [Documentation]    Verify that when a base model has recipes for multiple hardware types,
    ...    only the recipe matching the cluster's GPU appears — no model is listed twice.
    [Tags]    ui    models    finetune    smoke

    Given a ready project with user access exists
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tuning drawer
    And user opens the base model selector
    Then each base model should appear at most once in the recipe list

Fine-tuning drawer shows empty state when no recipes match cluster hardware
    [Documentation]    Verify the fine-tuning drawer tells the user no recipes are available
    ...    when the cluster's GPU hardware has no compatible fine-tuning recipes.
    ...
    ...    Auto-skips on GPU clusters where recipes will match. Runs on CPU-only clusters
    ...    where no fine-tuning recipes are compatible with the hardware.
    [Tags]    ui    models    finetune    cpu-only

    Given a cluster with no GPU hardware exists
    And a ready project with user access exists
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tuning drawer
    Then fine-tuning drawer should show no compatible recipes message

Fine-tuning drawer locks batch size until a recipe is selected
    [Documentation]    Verify that the batch size input is disabled before any recipe
    ...    is selected. The form gates the input on recipe selection so the
    ...    GPU-count-derived constraints (min, step) can be applied to a known recipe.
    ...    Auto-skips on CPU-only clusters where no recipes are listed.
    [Tags]    ui    models    finetune    validation

    Given a ready project with user access exists
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tuning drawer
    Then the batch size input should be locked until a recipe is chosen

Fine-tuning drawer constrains batch size to multiples of the recipe's GPU count
    [Documentation]    Verify that selecting a multi-GPU recipe locks the batch size
    ...    input to multiples of the recipe's GPU count, preventing the user from
    ...    submitting batch sizes that would silently crash the workload (EAI-5822).
    ...
    ...    Auto-skips when no GPU recipes are listed (CPU-only cluster) or when the
    ...    only listed recipes use a single GPU (no multiple-of constraint to verify).
    [Tags]    ui    models    finetune    validation    gpu

    Given a ready project with user access exists
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tuning drawer
    And user selects the first compatible recipe
    Then the batch size input should require multiples of the recipe's GPU count

Fine-tune action is available on completed fine-tuned model row
    [Documentation]    Verify that a completed fine-tuned model row shows a Fine-tune option
    ...    in its row action menu, and that clicking it opens the fine-tuning drawer
    ...    with the selected model locked as the base model.
    [Tags]    ui    models    finetune    kubectl

    Given a ready project with user access exists
    And a completed fine-tuned model exists for the test project
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tune action on the completed model row
    Then fine-tuning drawer should be open
    And the base model selector should be locked to the completed model

Re-fine-tuning a fine-tuned model does not ask for a HuggingFace token
    [Documentation]    Verify that opening the fine-tuning drawer from a completed fine-tuned
    ...    model hides the HuggingFace token section and lets the user submit the form
    ...    without a token.
    ...
    ...    A fine-tuned source keeps its weights in project storage, so re-fine-tuning it
    ...    needs no HuggingFace token. The drawer must reflect that source's actual token
    ...    requirement rather than forcing a token on an unknown source — which previously
    ...    crashed the page when submitted without one.
    [Tags]    ui    models    finetune    hf-token    kubectl

    Given a ready project with user access exists
    And a completed fine-tuned model exists for the test project
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tune action on the completed model row
    Then the HuggingFace token section should not be visible
    And the user can submit the fine-tuning form without a token

Fine-tune models table paginates when more models exist than fit one page
    [Documentation]    Verify the fine-tune models table renders the first page only and
    ...    surfaces pagination controls when the project contains more fine-tuned
    ...    models than fit on a single page; the user can step to subsequent pages.
    [Tags]    ui    models    pagination    kubectl

    Given a ready project with user access exists
    And more fine-tuned models exist in the namespace than fit a single page
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    Then the fine-tune models table shows the first page of fine-tuned models
    And pagination controls are visible on the fine-tune models table
    When user navigates to the next page of fine-tune models
    Then the fine-tune models table shows the next page of fine-tuned models

Fine-tuning drawer requires a HuggingFace token for a gated base model
    [Documentation]    Verify that selecting a gated base model reveals the HuggingFace
    ...    token section, and that submitting the form without selecting a token is blocked.
    ...
    ...    Gated models carry weights behind a HuggingFace access gate. The drawer must
    ...    surface the token selector so the fine-tuning job can pull the weights.
    ...    Auto-skips when no gated recipes are available on the cluster.
    [Tags]    ui    models    finetune    hf-token    smoke

    Given a ready project with user access exists
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tuning drawer
    And user selects a gated base model
    Then the HuggingFace token section should be visible
    And submitting the form without a token should be blocked

Fine-tuning drawer hides HuggingFace token section for a non-gated base model
    [Documentation]    Verify that selecting a non-gated base model keeps the HuggingFace
    ...    token section hidden.
    ...
    ...    Non-gated models have publicly available weights — no HF token is needed to
    ...    pull them. Showing the token section would confuse users and block submission.
    ...    Auto-skips when no non-gated recipes are available on the cluster.
    [Tags]    ui    models    finetune    hf-token

    Given a ready project with user access exists
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens fine-tuning drawer
    And user selects a non-gated base model
    Then the HuggingFace token section should not be visible

Custom model deploy drawer shows model details and deployment settings
    [Documentation]    Verify the custom-model deploy drawer renders the model header
    ...    (name and namespace) and the deployment-settings section including a display-name
    ...    input and an autoscaling toggle — without performing an actual GPU deployment.
    ...
    ...    This is a GPU-free smoke check for drawer rendering only.
    [Tags]    ui    models    finetune    deploy    kubectl    smoke

    Given a ready project with user access exists
    And a completed fine-tuned model exists for the test project
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens the deploy drawer for the custom model
    Then the deploy drawer should show the custom model's details
    And the deploy drawer should offer a deployment name and autoscaling

Deploy a custom model and verify it is ready to chat
    [Documentation]    Full lifecycle: open the custom-model deploy drawer from a ready
    ...    AIMModel row, submit with all default values, then verify via the AIWB API
    ...    that an AIMService CR was created in the project namespace and that the
    ...    service appears in the chat-capable inference list.
    ...
    ...    Requires GPU — the AIMService must reach a running state before the chat
    ...    endpoint becomes accessible.
    [Tags]    ui    models    finetune    deploy    kubectl    gpu

    Given a ready project with user access exists
    And a completed fine-tuned model exists for the test project
    And user is logged in
    And test project is selected
    And user is on fine-tune models page
    When user opens the deploy drawer for the custom model
    And user deploys the model with default settings
    Then a deployment for the custom model should exist in the project
    And the deployed model should be ready to chat
