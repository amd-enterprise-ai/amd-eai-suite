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
Suite Teardown      Clean Up All Tracked Resources


*** Test Cases ***
List available AIMs
    [Documentation]    Verify that users can see a list of available AIMs with proper structure
    [Tags]                  aims                    list                    smoke                   skip-in-ci

    Given a ready project with user access exists
    When List AIMs request is sent
    Then response status should be 200
    And Response should contain AIM list
    And Response should contain at least 1 AIMs
    And AIMs in list should have required fields

List available AIMs with Ready status filter
    [Documentation]    Verify that listing AIMs with statusFilter returns only models in Ready status.
    [Tags]                  aims                    list                    catalog                 smoke                   skip-in-ci

    Given a ready project with user access exists
    When List AIMs request is sent with status filter    Ready
    Then response status should be 200
    And Response should contain AIM list
    And AIMs in list should all have status    Ready

Get specific AIM by ID
    [Documentation]    Verify that a specific AIM can be retrieved by its ID
    [Tags]                  aims                    get                     skip-in-ci

    Given a ready project with user access exists
    And an AIM exists in system
    When Get AIM request is sent
    Then response status should be 200
    And Response should contain AIM details

AIM catalog returns models with image metadata
    [Documentation]    Verify that the AIM catalog returns models with complete image metadata
    ...    Tests that each AIM in the catalog has status, imageMetadata with model title,
    ...    canonicalName, tags, and variants fields.
    [Tags]                  aims                    catalog                 smoke                   skip-in-ci

    Given a ready project with user access exists
    When List AIMs request is sent
    Then response status should be 200
    And AIM catalog should contain models with image metadata

AIM catalog exposes hardware footprints for each AIM
    [Documentation]    Verifies that the AIM catalog surfaces each AIM's
    ...    accelerator footprints so the UI can render the AIM's runtime
    ...    options (CPU, or GPU with counts like 1x/2x/8x) without an
    ...    additional lookup. The footprint information may be unpublished
    ...    on clusters whose engine has not yet emitted it.
    [Tags]                  aims                    catalog                 smoke                   skip-in-ci

    Given a ready project with user access exists
    When List AIMs request is sent
    Then response status should be 200
    And Each AIM in the catalog should expose accelerator metadata

User filters the AIM catalog by accelerator type
    [Documentation]    Verifies that the user can filter the AIM catalog by
    ...    accelerator family and receive only AIMs that support that family.
    ...    If the cluster hosts no AIMs supporting the requested family, an
    ...    empty catalog is the correct outcome.
    [Tags]                  aims                    catalog                 smoke                   skip-in-ci

    Given a ready project with user access exists
    When List AIMs request is sent filtered by accelerator type    cpu
    Then response status should be 200
    And Every returned AIM should have accelerator type    cpu

User filters the AIM catalog by multiple accelerator types
    [Documentation]    Verifies that the user can filter the AIM catalog by
    ...    several accelerator families at once and receive every AIM that
    ...    supports at least one of them. An empty catalog is the correct
    ...    outcome when the cluster hosts no AIMs supporting any of the
    ...    requested families.
    [Tags]                  aims                    catalog                 smoke                   skip-in-ci

    Given a ready project with user access exists
    When List AIMs request is sent filtered by accelerator types    cpu    gpu
    Then response status should be 200
    And Every returned AIM should have one of the accelerator types    cpu    gpu

AIM catalog returns profiles for a model
    [Documentation]    Verify that the AIM profiles endpoint returns deployment configurations
    ...    Tests that profiles exist for a given AIM model and have proper CRD structure.
    [Tags]                  aims                    catalog                 smoke                   skip-in-ci

    Given a ready project with user access exists
    And an AIM exists in system
    When List AIM profiles request is sent
    Then response status should be 200
    And Response should contain AIM profiles

User can browse the inference base model catalog page by page
    [Documentation]    The cluster's inference base model catalog is served in
    ...                pages so the UI can paginate as the catalog grows with
    ...                custom AIM onboarding (see EAI-6620).
    [Tags]                  aims                    catalog                 pagination              skip-in-ci

    Given a ready project with user access exists
    When List AIMs request is sent
    Then the result is returned page by page

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

Deploy AIM with runtime profile overrides persists on AIMService CR
    [Documentation]    Deploy-time selector criteria and profile override fields from the
    ...    request are written to the AIMService CR manifest.
    [Tags]                  aims                    deploy                  gpu                    kubectl

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM exists in system
    When Deploy AIM request is sent with runtime profile overrides
    Then response status should be 202
    And AIMService CR should have runtime profile overrides in kubernetes

Deploy-time profile overrides reach the catalog AIM inference pod
    [Documentation]    The partitioned-cluster use case end-to-end: deploy a catalog AIM with
    ...    runtime profile overrides, let it reach Running, and confirm the live inference pod
    ...    runs with the requested accelerator product and count and the requested engine
    ...    argument and env var. Precision and selector criteria are asserted on the AIMService
    ...    CR (deploy-time selector); the pod assertions prove the overrides reached the
    ...    running model server, not just the manifest. Teardown removes the deployment so a
    ...    mid-test failure cannot leave an AIMService behind.
    [Tags]                  aims                    deploy                  profile                 gpu                    kubectl
    [Teardown]              Remove AIM deployment if present
    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And an AIM exists in system
    When Deploy AIM request is sent with runtime profile overrides
    Then response status should be 202
    And AIMService CR should have runtime profile overrides in kubernetes
    And Deployed AIM reaches Running state
    And the running inference pod should request 2 accelerators
    And the running inference pod should run on "MI300X" accelerators
    And the running inference pod should expose env "VLLM_LOGGING_LEVEL" set to "DEBUG"
    And the running inference pod should run with engine argument "8192"

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

Deployed AIM service profile is visible via resolved template
    [Documentation]    Verify that the deployed AIM service has a resolved template with accessible
    ...    profile metadata (GPU model, GPU count, metric, precision, type).
    ...    This validates the data chain the UI uses to display profile information
    ...    in the workload details page.
    [Tags]    aims    deploy    profile    gpu

    Given a ready project with user access exists
    And the project has GPU quota available
    And AIM is deployed and running
    Then AIM workload details should include profile information

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

Logs for a still-starting AIM workload return an empty state rather than an error
    [Documentation]    While an AIM is still starting (before any pods exist or logs are
    ...    produced), requesting workload logs should return 200 with a valid response
    ...    (often empty), rather than a not-found error. This avoids false negatives during
    ...    the startup window.
    [Tags]                  aims                    workload                logs                    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed
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

List inference deployments filtered to chat-capable models
    [Documentation]    Verify that listing inference deployments with the chat capability
    ...    filter returns only deployments whose model supports chat and whose serving
    ...    stack is fully ready. A running AIM with a chat-capable model should appear.
    [Tags]                  aims                    list                    inference                capability             gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    When Inference deployments are listed for chat
    Then response status should be 200
    And Chat-capable list should include the running AIM

User can browse inference deployments page by page
    [Documentation]    Inference deployments in a project are served in pages
    ...                rather than as one flat list.
    [Tags]                  aims                    list                    inference                pagination             skip-in-ci

    Given a ready project with user access exists
    When Inference deployments are listed for the project
    Then the result is returned page by page

Inference metric is available for a deployed AIM
    [Documentation]    Verify that an inference metric can be retrieved for a deployed AIM.
    ...    The metrics endpoint returns Prometheus-backed values scoped to the deployment.
    [Tags]                  aims                    inference                metrics                 gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    When A request metric is requested for the deployed AIM
    Then Inference metric response should contain a value

Inference replicas are available for a deployed AIM
    [Documentation]    Verify that per-replica pod data can be retrieved for a deployed AIM.
    ...    Each entry should expose the pod name and observable status.
    [Tags]                  aims                    inference                replicas                gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    When Inference replicas are requested for the deployed AIM
    Then response status should be 200
    And Response should contain per-replica pod data

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

Undeployed AIM appears in historical inference list
    [Documentation]    Verify that an AIM that has been undeployed is still
    ...    surfaced by the inference list endpoint when the Deleted status
    ...    filter is applied. This powers the historical-services panel on
    ...    the AIM detail page that survived the removal of the legacy
    ...    /aims/services/history route.
    [Tags]                  aims                    list                    inference               history                 gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And AIM is deployed and running
    And AIM is undeployed
    When Historical inference deployments are listed
    Then response status should be 200
    And Historical list should include the undeployed AIM

# Degraded status is not tested in E2E. The AIM engine controller sets Degraded when
# current_replicas < desired_replicas, but K8s ReplicaSet replaces deleted pods within
# seconds -- too fast to reliably observe via API polling. The PATCH endpoint only
# supports autoscaling policy changes (minReplicas/maxReplicas/autoScaling together),
# not direct replica count manipulation, so there is no API-level way to force a
# sustained replica mismatch without invasive cluster operations (e.g., node cordoning).
