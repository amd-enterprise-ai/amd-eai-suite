# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       E2E coverage for the unified Envoy AI Gateway (EAI-5889 / EAI-6040).
...                 Verifies the single OpenAI-compatible endpoint that serves all
...                 deployed AIMs: model discovery on /v1/models, inference happy
...                 path with API-key auth, auth enforcement, undeploy cleanup,
...                 error mapping for unknown models, and (EAI-7128) correct
...                 per-backend routing when two AIMs share a model name. After
...                 EAI-6787 the AI Gateway becomes the only external entry point
...                 for AIM inference (the per-AIM /workbench/{uuid} route is
...                 removed), so this suite is the canonical coverage for that
...                 contract.
...
...                 Suite design mirrors api_keys.robot: a single project is
...                 created once in Suite Setup, the AIM is deployed lazily by
...                 the idempotent precondition keywords and reused across
...                 tests, and the destructive undeploy scenario runs last so
...                 it doesn't tear down state needed by earlier tests.
Resource            resources/aiwb_ai_gateway.resource
Resource            resources/aims/api_keys.resource
Resource            resources/aiwb_aims.resource
Resource            resources/airm_projects.resource

Suite Setup         Initialize AIMS API key test environment
Suite Teardown      Clean Up All Tracked Resources


*** Test Cases ***
Deployed AIM appears in the unified model listing
    [Documentation]    Verify that an AIM deployed in the user's project shows up in the
    ...    OpenAI-compatible /v1/models response served by the AI Gateway.
    [Tags]    ai-gateway    inference    api-keys    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    When the unified /v1/models endpoint is queried with a valid API key
    Then the deployed AIM is listed among the available models

Inference works through the AI Gateway with a valid API key
    [Documentation]    Verify that a chat completion request routed through the AI
    ...    Gateway with a valid API key reaches the deployed AIM and returns an
    ...    OpenAI-shaped response.
    [Tags]    ai-gateway    inference    api-keys    positive    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    When a chat completion request is sent to the AI Gateway for that model
    Then the model returns a successful response

Inference is rejected for an API key authorized for a different model
    [Documentation]    Verify that per-model authorization is enforced even when the API key
    ...    holds valid credentials for another model on the same gateway hostname. Regression
    ...    test for EAI-6805: old cluster-auth matched HTTPRoutes by hostname only, so a key
    ...    authorized for model-A could reach model-B because the wrong route was selected.
    [Tags]    ai-gateway    inference    api-keys    negative    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    And a valid API key authorized for this model exists
    And another model is available on the gateway
    When a chat completion request is sent to the AI Gateway for the other model with the authorized key
    Then the request is rejected with an authentication error

Inference is rejected without an API key
    [Documentation]    Verify that the AI Gateway enforces authentication: a chat
    ...    completion request with no Authorization header is rejected before
    ...    reaching the backend.
    [Tags]    ai-gateway    inference    api-keys    negative    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    When a chat completion request is sent to the AI Gateway without an API key
    Then the request is rejected with an authentication error

Inference is rejected with an invalid API key
    [Documentation]    Verify that the AI Gateway rejects requests carrying an
    ...    unrecognised Bearer token, distinct from the no-header case.
    [Tags]    ai-gateway    inference    api-keys    negative    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    When a chat completion request is sent to the AI Gateway with an invalid API key
    Then the request is rejected with an authentication error

Chat completion request for an unknown model is rejected
    [Documentation]    Verify that the AI Gateway maps an unknown model name to a
    ...    client error (4xx) rather than surfacing a 5xx server failure.
    [Tags]    ai-gateway    inference    api-keys    negative    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    When a chat completion request is sent for a model name that does not exist
    Then the request fails with a client error

Inference routes to the correct backend when two AIMs share a model name
    [Documentation]    Regression test for EAI-7128 (Bug B): when two AIMs serve the same
    ...    model name (deployed in two projects), a request that targets a backend by UUID
    ...    must reach that exact backend, not the co-hosted one. Without precise routing,
    ...    Envoy merges the per-AIM AIGatewayRoutes and an equal-specificity model-name rule
    ...    can win by creation timestamp, mis-routing to the wrong deployment. This is fixed
    ...    by making the UUID route (Host + x-ai-eg-backend + x-ai-eg-model) more specific so
    ...    it wins; the client sets both routing headers (see Send Chat Completion To AI
    ...    Gateway).
    ...
    ...    No response field identifies the backend (both echo the same served model name),
    ...    so routing is verified via per-backend generated-token counters (vLLM
    ...    generation_tokens_total, exposed as the raw cumulative `total_tokens` metric scoped
    ...    by workload_id = backend UUID). Both directions are checked: a request targeting B
    ...    must increment only B's counter, and a request targeting A only A's — guarding
    ...    against routing collapsing onto a single backend.
    [Tags]    ai-gateway    inference    routing    metrics    gpu

    # gpu_count=1 (not 2 like the single-project tests above): this scenario holds
    # two projects with a live AIM each at the same time, so a 1-GPU footprint per
    # project keeps total demand within shared-cluster quota headroom. The smallest
    # deployable AIM is a 1-GPU model, so one GPU is sufficient to deploy it.
    Given a ready project with user access exists
    And project quota is set to    gpu_count=1    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    And the same AIM model is deployed in a second project
    When a chat completion is sent through the AI Gateway targeting backend B
    Then only backend B served the request
    When a chat completion is sent through the AI Gateway targeting backend A
    Then only backend A served the request

# Destructive — runs last so it doesn't tear down state shared with earlier tests.
Undeploying an AIM keeps workbench endpoints available and removes its route
    [Documentation]    Two post-undeploy guarantees in one flow.
    ...    After an AIM is undeployed, the AIWB inference list, workloads, and
    ...    workload-metrics endpoints must remain available (no HTTP 500).
    ...    The AIM's AI Gateway route must also be removed — verified via kubectl on the
    ...    route's unique backend UUID rather than the /v1/models listing, because model
    ...    names are shared across projects on a multi-tenant cluster and would not
    ...    disappear when only this project's AIM is removed.
    [Tags]    ai-gateway    undeploy    cleanup    regression    kubectl    gpu

    Given a ready project with user access exists
    And project quota is set to    gpu_count=2    cpu_milli_cores=8000    memory_bytes=68719476736
    And the AI Gateway endpoint is available
    And the smallest deployable AIM is selected
    And a HuggingFace token is available for AIM deployment
    And an AIM model is running with api key
    When AIM is undeployed
    Then AIWB workbench endpoints should remain accessible for 6 seconds after undeploy
    And the AIM's AI Gateway route is removed
