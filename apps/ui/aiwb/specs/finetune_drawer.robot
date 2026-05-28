# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for the fine-tuning drawer base model selector (EAI-5741).
...
...                 Verifies that the fine-tuning drawer displays GPU-compatible recipes with
...                 hardware names and handles the empty state when no recipes are compatible
...                 with the cluster's GPU hardware.

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
    And user is on custom models page
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
    And user is on custom models page
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
    And user is on custom models page
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
    And user is on custom models page
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
    And user is on custom models page
    When user opens fine-tuning drawer
    And user selects the first compatible recipe
    Then the batch size input should require multiples of the recipe's GPU count
