# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Test scenarios for AIWB API AIMs endpoints.
...                 Verifies AIM deployment, listing, undeployment and management operations.
...
...                 Suite Efficiency Design:
...                 This suite uses Suite Setup/Teardown so the project is created once and
...                 deleted once at the end, avoiding costly per-test project cleanup and the
...                 ~8-10 minute namespace termination wait for GPU workloads. Each test still
...                 declares its preconditions via Given steps for readability and standalone
...                 execution - these are idempotent and reuse existing resources when present.
...
...                 The AIM precondition keywords ("AIM is deployed", "AIM is deployed and
...                 running") are idempotent: they check if an AIM service already exists in the
...                 namespace and reuse it, only deploying when needed. This means running the
...                 full suite deploys the AIM once and reuses it across tests.
...
...                 Test ordering is intentional:
...                 1. Non-GPU tests (list, get, catalog) run first with no AIM deployment needed
...                 2. Deploy test creates the initial AIM deployment
...                 3. Deployment verification tests (display name, version) run once AIM is running
...                 4. Operational tests (accessibility, listing, logs, details) reuse the running AIM
...                 5. Undeploy test runs last and cleans up the AIM
Resource            resources/aiwb_aims.resource
Resource            resources/airm_keywords.resource
Resource            resources/airm_projects.resource
Suite Setup         Initialize Project Tracking
Suite Teardown      Clean Up All Created Projects


*** Test Cases ***
List available AIMs
    [Documentation]    Verify that users can see a list of available AIMs with proper structure
    [Tags]                  aims                    list                    smoke

    Given a ready project with user access exists
    When List AIMs request is sent
    Then response status should be 200
    And Response should contain AIM list
    And Response should contain at least 1 AIMs
    And AIMs in list should have required fields

Get specific AIM by ID
    [Documentation]    Verify that a specific AIM can be retrieved by its ID
    [Tags]                  aims                    get

    Given a ready project with user access exists
    And an AIM exists in system
    When Get AIM request is sent
    Then response status should be 200
    And Response should contain AIM details

AIM catalog returns models with image metadata
    [Documentation]    Verify that the AIM catalog returns models with complete image metadata
    ...    Tests that each AIM in the catalog has status, imageMetadata with model title,
    ...    canonicalName, tags, and variants fields.
    [Tags]                  aims                    catalog                 smoke

    Given a ready project with user access exists
    When List AIMs request is sent
    Then response status should be 200
    And AIM catalog should contain models with image metadata

AIM catalog returns templates for a model
    [Documentation]    Verify that AIM templates endpoint returns deployment configurations
    ...    Tests that templates exist for a given AIM model and have proper CRD structure.
    [Tags]                  aims                    catalog                 smoke

    Given a ready project with user access exists
    And an AIM exists in system
    When List AIM templates request is sent
    Then response status should be 200
    And Response should contain AIM templates

Deploy AIM creates workload
    [Documentation]    Verify that deploying an AIM creates a workload and returns workload ID
    ...    Tests that the deployment request is accepted and a workload is created in the database.
    ...    This test intentionally runs before other GPU tests so no AIM is deployed yet.
    [Tags]                  aims                    deploy                  smoke                   gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM exists in system
    ${deploy_data}=         Valid AIM deploy data is prepared
    When Deploy AIM request is sent    ${deploy_data}
    Then response status should be 202
    And Response should contain workload ID
    And AIM workload should exist in database

Deployed AIM starts running
    [Documentation]    Verify that a deployed AIM workload reaches Running status
    [Tags]                  aims                    deploy                  status                  gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed
    Then Deployed AIM reaches Running state

Deployed AIM has correct display name
    [Documentation]    Verify that the deployed AIM has a display name from image metadata
    ...    The display name (title) is part of the AIM's imageMetadata and should be
    ...    consistent between the catalog and the deployed service.
    [Tags]                  aims                    deploy                  details                 gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And AIM is deployed and running
    Then AIM service should have display name

Deployed AIM service shows version info
    [Documentation]    Verify that the deployed AIM service has version information
    ...    Tests that the AIM has a versioned image reference and a resolved template.
    [Tags]                  aims                    deploy                  details                 gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2
    And AIM is deployed and running
    Then AIM service should have version info

Deployed AIM is accessible externally
    [Documentation]    Verify that a running AIM workload has external endpoint and is accessible
    ...    Tests that:
    ...    - Workload has external_host
    ...    - External endpoint responds with AIMS API key authentication
    ...    - Endpoint follows standard LLM API format (/v1/models)
    ...
    ...    NOTE: External AIM endpoints require an AIMS API key (not OIDC token).
    ...    The test creates an API key, assigns it to the AIM model, then uses it.
    [Tags]                  aims                    deploy                  external                gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    Then AIM workload should be accessible externally
    And External endpoint should return available models

List AIMs shows deployed AIM with correct fields
    [Documentation]    Verify that listing AIMs shows deployed AIM with complete information
    ...    Tests that deployed AIMs include AIM details, workload deployment info, and resource metrics in the list view
    [Tags]                  aims                    list                    deployment-status       gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    When List AIMs request is sent
    Then response status should be 200
    And Response should contain AIM list
    And AIM should have active workload deployment
    And AIM list endpoint should include workload details

View deployed AIM workload logs
    [Documentation]    Verify that users can view logs for a running AIM workload
    ...    Tests that logs have proper structure with timestamp, level, and message
    [Tags]                  aims                    workload                logs                    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    When logs are requested from AIM workload
    Then response status should be 200
    And Response should contain log entries

View deployed AIM workload details
    [Documentation]    Verify that users can view detailed information about a running AIM workload
    ...    Tests that workload details include status, output, allocated resources (GPU count, VRAM), and AIM-specific fields
    [Tags]                  aims                    workload                details                 gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    When workload details are requested
    Then response status should be 200
    And AIM workload detail endpoint should be complete

Undeploy deployed AIM
    [Documentation]    Verify that a deployed AIM can be undeployed
    ...    Tests that the AIM workload is removed from database AND Kubernetes.
    ...    This test runs last in the single-replica suite to avoid forcing redeployment for other tests.
    [Tags]                  aims                    undeploy                kubectl                 gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    And AIM deployment should exist in kubernetes
    When Undeploy AIM request is sent
    Then response status should be 204
    And Deployed workload should be removed
    And AIM deployment should not exist in kubernetes
    And AIM should not have active workload deployment

# Degraded status is not tested in E2E. The AIM engine controller sets Degraded when
# current_replicas < desired_replicas, but K8s ReplicaSet replaces deleted pods within
# seconds -- too fast to reliably observe via API polling. The PATCH endpoint only
# supports autoscaling policy changes (minReplicas/maxReplicas/autoScaling together),
# not direct replica count manipulation, so there is no API-level way to force a
# sustained replica mismatch without invasive cluster operations (e.g., node cordoning).
