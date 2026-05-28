# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for AIM scaling and autoscaling operations.
...                 Verifies that AIM services can be scaled manually and automatically
...                 through the scaling policy API endpoint.
...
...                 Suite Efficiency Design:
...                 This suite uses Suite Setup/Teardown so the project is created once and
...                 deleted once at the end, avoiding costly per-test project cleanup. Each
...                 test still declares its preconditions via Given steps for readability and
...                 standalone execution - these are idempotent and reuse existing resources.
...
...                 Test ordering is intentional:
...                 1. API-level smoke tests (update policy, k8s verification) run first
...                 2. Scaling behavior tests verify actual replica changes
...                 3. Load-based autoscaling verifies HPA-driven scale-up under load
...                 4. Redeploy persistence test runs last (undeploys and redeploys)
Resource            resources/aiwb_aims.resource
Resource            resources/airm_keywords.resource
Resource            resources/airm_projects.resource
Suite Teardown      Clean Up All Tracked Resources


*** Test Cases ***
Update AIM scaling policy via API
    [Documentation]    Verify that AIM scaling policy can be updated via API endpoint
    ...    Tests that the API accepts valid scaling configuration
    ...    and updates the AIMService spec accordingly.
    [Tags]    aims    scaling    smoke    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And AIM is deployed
    And Valid AIM scaling policy data is prepared    min_replicas=1    max_replicas=3
    When Update AIM scaling policy request is sent
    Then response status should be 200
    And AIM service should have scaling policy    expected_min=1    expected_max=3

Update scaling policy to higher replica count
    [Documentation]    Verify that AIM scaling policy accepts increased replica range.
    ...    Tests updating minReplicas and maxReplicas to higher values via API.
    [Tags]    aims    scaling    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And AIM is deployed
    And Valid AIM scaling policy data is prepared    min_replicas=2    max_replicas=3
    When Update AIM scaling policy request is sent
    Then response status should be 200
    And AIM service should have scaling policy    expected_min=2    expected_max=3

Update scaling policy to lower replica count
    [Documentation]    Verify that AIM scaling policy accepts decreased replica range.
    ...    Tests reducing minReplicas and maxReplicas via API.
    ...    First sets a higher range as a precondition, then reduces it as the action under test.
    [Tags]    aims    scaling    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And AIM is deployed
    And Valid AIM scaling policy data is prepared    min_replicas=2    max_replicas=3
    And Update AIM scaling policy request is sent
    And response status should be 200
    And AIM service should have scaling policy    expected_min=2    expected_max=3
    And Valid AIM scaling policy data is prepared    min_replicas=1    max_replicas=2
    When Update AIM scaling policy request is sent
    Then response status should be 200
    And AIM service should have scaling policy    expected_min=1    expected_max=2

Update autoscaling configuration via API
    [Documentation]    Verify that autoscaling configuration is stored correctly via API.
    ...    Tests that the API accepts and persists a full autoscaling policy
    ...    with minReplicas, maxReplicas, and autoScaling config.
    [Tags]    aims    scaling    autoscaling    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And AIM is deployed
    And Valid AIM scaling policy data is prepared    min_replicas=1    max_replicas=2
    When Update AIM scaling policy request is sent
    Then response status should be 200
    And AIM service should have scaling policy    expected_min=1    expected_max=2
    And AIM service should have autoscaling config

Scaling policy reflected in Kubernetes AIMService CR
    [Documentation]    Verify that the scaling policy is reflected in the Kubernetes
    ...    AIMService Custom Resource after PATCH. Uses kubectl to verify spec fields.
    [Tags]    aims    scaling    smoke    gpu    kubectl

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And AIM is deployed
    And Valid AIM scaling policy data is prepared    min_replicas=1    max_replicas=3
    When Update AIM scaling policy request is sent
    Then response status should be 200
    And AIMService CR should have scaling policy in kubernetes    expected_min=1    expected_max=3

Increasing minimum replicas scales up running pods
    [Documentation]    Verify that increasing minReplicas causes actual pod scale-up.
    ...    Deploys AIM with 1 replica, then patches minReplicas=2 and waits for
    ...    the controller to report 2 desired replicas and 2 running pods.
    [Tags]    aims    scaling    autoscaling    gpu

    Given a ready project with user access exists
    # Each AIM replica requests ~4 CPU + 32GiB memory; guarantee resources for 2
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    And Valid AIM scaling policy data is prepared    min_replicas=2    max_replicas=3
    When Update AIM scaling policy request is sent
    Then response status should be 200
    And AIM should have at least 2 desired replicas
    And AIM should have at least 2 running pods

Load-based autoscaling scales replicas up
    [Documentation]    Verify that sustained inference load triggers HPA to scale up replicas.
    ...    Deploys AIM with autoscaling (min=1, max=3, target=1 running request),
    ...    then sends concurrent inference requests to exceed the threshold.
    [Tags]    aims    scaling    autoscaling    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=3    cpu_milli_cores=12000    memory_bytes=103079215104
    And AIM is deployed and running
    And An API key exists and is assigned to AIM
    And AIM autoscaling policy is configured    min_replicas=1    max_replicas=3    target_requests=1
    When concurrent inference load is applied    concurrent_requests=10    duration_seconds=300
    Then AIM should have at least 2 desired replicas
    And AIM should have at least 2 running pods
    [Teardown]    Stop inference load

Redeploy resets scaling policy to defaults
    [Documentation]    Verify that scaling policy resets when AIM is redeployed.
    ...    Tests that undeploying and redeploying an AIM does not retain the
    ...    previous scaling configuration - each deployment starts fresh.
    [Tags]    aims    scaling    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=1
    And AIM is deployed
    And Valid AIM scaling policy data is prepared    min_replicas=2    max_replicas=5
    And Update AIM scaling policy request is sent
    And response status should be 200
    And AIM service should have scaling policy    expected_min=2    expected_max=5
    And Undeploy AIM request is sent
    And response status should be 204
    And Deployed workload should be removed
    When AIM is deployed
    Then AIM service should not retain previous scaling policy    min_replicas=2    max_replicas=5
