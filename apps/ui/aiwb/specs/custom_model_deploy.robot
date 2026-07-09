# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Frontend E2E tests for deploying and undeploying a custom model.
...
...                 Covers the deploy drawer entry point from the Custom Models tab card,
...                 the full deploy → Deployed Models list → undeploy confirmation flow,
...                 and a GPU-free smoke check that verifies the drawer renders correctly
...                 for a Ready model without submitting.

Resource            resources/common/browser_setup.resource
Resource            resources/custom_model_deploy.resource
Resource            resources/chat.resource
Resource            resources/airm_projects.resource
Resource            resources/airm_secrets.resource

Suite Teardown      Run Keywords    Clean Up All Created Custom Models    AND    Clean Up All Created Projects
Test Setup          Open test browser
Test Teardown       Close test browser


*** Test Cases ***
Deploy drawer opens with deployment settings for a Ready custom model
    [Documentation]    A user who clicks the Deploy button on a Ready model card should
    ...                see the deploy drawer with a display name input and an autoscaling
    ...                toggle — confirming the drawer rendered correctly without submitting
    ...                an actual deployment. The button is disabled for non-Ready models
    ...                so the Ready precondition is what gates the interaction.
    [Tags]    ui    models    custom-models    deploy    smoke

    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a ready custom model exists in the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on the custom models tab
    When user opens the deploy drawer from the custom model card
    Then the deploy drawer should show deployment settings

A deployed custom model can be chatted with from the chat page
    [Documentation]    A user who has a Ready custom model deployed and running can navigate
    ...                to the chat page for that deployment, send a message, and receive a
    ...                streamed response — confirming the inference endpoint is reachable
    ...                from the UI and the model processes input end-to-end.
    [Tags]    ui    models    custom-models    deploy    chat    gpu
    [Teardown]    Clean up custom model deployment if present

    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is deployed and running in the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    When user is on the chat page for the custom model deployment
    And user types a message and sends it
    Then response should stream and render in the chat interface

Deploying a custom model from the card and undeploying it from the Deployed Models tab
    [Documentation]    A user who opens the deploy drawer for a Ready custom model,
    ...                supplies a display name, and submits should see a success toast
    ...                and find the new deployment on the Deployed Models tab. Undeploying
    ...                it from there should show a confirmation modal, then a success toast,
    ...                and the entry should disappear from the list.
    [Tags]    ui    models    custom-models    deploy    undeploy    gpu
    [Teardown]    Clean up custom model deployment if present

    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a ready custom model exists in the project
    And user is logged in
    And project "${TEST_PROJECT}[name]" is selected
    And user is on the custom models tab
    ${deploy_name}=    Test Name    ui-deploy
    When user opens the deploy drawer from the custom model card
    And user fills the deployment display name "${deploy_name}"
    And user submits the deployment form
    Then the model deployment success toast should be shown
    When user is on the deployed models page
    Then a deployed model with display name "${deploy_name}" should appear in the list
    When user opens the undeploy action for the deployment with display name "${deploy_name}"
    And user confirms the undeploy
    Then the undeploy success toast should be shown
    And the deployed model should no longer appear in the list with display name "${deploy_name}"
