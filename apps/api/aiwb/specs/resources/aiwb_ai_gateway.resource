# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Business-logic keywords for the unified Envoy AI Gateway
...                 (EAI-5889 / EAI-6040). Provides Given/When/Then steps for
...                 model discovery and OpenAI-compatible inference through the
...                 single gateway endpoint exposed by ai-gateway-discovery.
...
...                 Owns TEST_AI_GATEWAY_URL (resolved once per suite) and reuses
...                 TEST_AIM_ID / TEST_AIM_MODEL_ID / TEST_API_KEY_VALUE set by
...                 the shared AIM and API-key keywords. The served model name
...                 is currently sourced from the per-AIM external endpoint via
...                 `An AIM model is running with api key`; this becomes a TODO
...                 once EAI-6787 removes that route (see EAI-6834).
Resource            resources/aiwb_common.resource
Resource            resources/aiwb_aims.resource
Resource            resources/aims/api_keys.resource
Resource            resources/aim_catalog.resource
Resource            resources/api/ai_gateway.resource
Resource            resources/api/projects.resource
Resource            resources/deployment.resource
Resource            resources/airm_projects.resource
Library             Collections
Library             String
Library             Process
Library             DateTime


*** Variables ***
${AI_GATEWAY_URL}            ${EMPTY}
${AIWB_NAMESPACE}            aiwb
${HF_TOKEN_SECRET_NAME}      huggingface-token
${AIM_RESOURCE_OVERRIDE}     ${EMPTY}


*** Keywords ***
# Resource resolver

The AI Gateway endpoint
    [Documentation]    Resolves the unified AI Gateway base URL once per suite.
    ...    Order: ${AI_GATEWAY_URL} override → read AI_GATEWAY_URL from the aiwb-ui
    ...    deployment (the value aiwb itself uses) → fail with a clear message.
    ...    Caches the result in ${TEST_AI_GATEWAY_URL} (suite scope) so subsequent
    ...    calls return the same URL without re-querying the cluster.
    ${cached}=    Get Variable Value    ${TEST_AI_GATEWAY_URL}    ${EMPTY}
    IF    "${cached}" != ""
        RETURN    ${cached}
    END

    IF    "${AI_GATEWAY_URL}" != ""
        VAR    ${TEST_AI_GATEWAY_URL}    ${AI_GATEWAY_URL}    scope=SUITE
        Log    Using AI Gateway URL from variable: ${AI_GATEWAY_URL}    INFO
        RETURN    ${AI_GATEWAY_URL}
    END

    ${url}=    Get AI Gateway URL From AIWB
    IF    "${url}" == ""
        Fail    Could not resolve AI Gateway URL: set --variable AI_GATEWAY_URL:<url> or ensure the aiwb-ui deployment in namespace ${AIWB_NAMESPACE} has AI_GATEWAY_URL set
    END
    VAR    ${TEST_AI_GATEWAY_URL}    ${url}    scope=SUITE
    Log    Discovered AI Gateway URL from aiwb-ui deployment: ${url}    INFO
    RETURN    ${url}

Get AI Gateway URL From AIWB
    [Documentation]    Reads AI_GATEWAY_URL from the aiwb-ui deployment — the value
    ...    aiwb itself uses for the unified gateway endpoint, so the test exercises
    ...    exactly what the product is configured with. Read from the stable aiwb
    ...    namespace (${AIWB_NAMESPACE}) rather than the ai-gateway-discovery
    ...    controller, whose namespace varies across installs. Returns the full URL
    ...    (scheme included), or empty string if the deployment is not found or the
    ...    env var is unset.
    VAR    ${jsonpath}    jsonpath={.spec.template.spec.containers[?(@.name=="aiwb-ui")].env[?(@.name=="AI_GATEWAY_URL")].value}
    ${result}=    Run Process    kubectl    get    deployment    aiwb-ui
    ...    -n    ${AIWB_NAMESPACE}
    ...    -o    ${jsonpath}
    ...    timeout=10s
    IF    ${result.rc} != 0
        Log    Could not read AI_GATEWAY_URL from aiwb-ui deployment: ${result.stderr}    WARN
        RETURN    ${EMPTY}
    END
    RETURN    ${result.stdout.strip()}

# Given-step keywords

The AI Gateway endpoint is available
    [Documentation]    Resolves and caches the AI Gateway base URL.
    The AI Gateway endpoint

The smallest deployable AIM is selected
    [Documentation]    Pins TEST_AIM_NAME to the smallest non-gated Ready AIM on
    ...    this cluster so the subsequent `An AIM model is running...` precondition
    ...    deploys something usable. Without this step, the upstream selector
    ...    picks the first alphabetical Ready AIM, which on some clusters is an
    ...    8-GPU model (DeepSeek-R1) — far too expensive for a smoke test.
    # Honor an explicit override (e.g. --variable AIM_RESOURCE_OVERRIDE:...)
    # so a known-good model can be pinned on clusters where catalog profile
    # provisioning is incomplete.
    ${override}=    Get Variable Value    ${AIM_RESOURCE_OVERRIDE}    ${EMPTY}
    IF    "${override}" != ""
        VAR    ${TEST_AIM_NAME}    ${override}    scope=SUITE
        Log    Using pinned AIM override: ${override}    INFO
        RETURN
    END
    ${resource_name}=    Smallest deployable AIM resource name
    # SUITE scope so the upstream `An AIM exists in system` short-circuit
    # (which compares ${already_set} != ${None}) actually fires — the
    # short-circuit Get Variable Value otherwise resolves to None because
    # the suite-level ${TEST_AIM_NAME} default takes precedence in some
    # scope chains.
    VAR    ${TEST_AIM_NAME}    ${resource_name}    scope=SUITE

A HuggingFace token is available for AIM deployment
    [Documentation]    Opt-in: if $HF_TOKEN is present in the environment, creates the
    ...    HuggingFace secret in the project namespace and publishes its name via
    ...    ${TEST_HF_TOKEN_SECRET} so the shared `Valid AIM deploy data is prepared`
    ...    keyword includes hfToken in the deploy payload.
    ...    When $HF_TOKEN is absent (e.g. open-model clusters), the step is a no-op —
    ...    TEST_HF_TOKEN_SECRET is left unset and the AIM deploys without hfToken.
    ${hf_token}=    Get Environment Variable    HF_TOKEN    default=${EMPTY}
    IF    "${hf_token}" == ""
        Log    HF_TOKEN not set — skipping HuggingFace secret creation; open models work without it    INFO
        RETURN
    END
    HuggingFace token secret exists in namespace
    VAR    ${TEST_HF_TOKEN_SECRET}    ${HF_TOKEN_SECRET_NAME}    scope=TEST

# When-step keywords

The unified /v1/models endpoint is queried with a valid API key
    [Documentation]    Lists models from the AI Gateway using the active test API key.
    ...    Requires: TEST_API_KEY_VALUE
    ...    Sets: TEST_RESPONSE, TEST_GATEWAY_MODELS
    Variable Should Exist    ${TEST_API_KEY_VALUE}    msg=TEST_API_KEY_VALUE is not set
    ${gateway}=    The AI Gateway endpoint
    ${response}=    Get Models From AI Gateway    ${gateway}    api_key=${TEST_API_KEY_VALUE}
    ...    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST
    IF    ${response.status_code} == 200
        ${body}=    Set Variable    ${response.json()}
        ${models}=    Get From Dictionary    ${body}    data    default=${None}
        VAR    ${TEST_GATEWAY_MODELS}    ${models}    scope=TEST
    END

A chat completion request is sent to the AI Gateway for that model
    [Documentation]    Sends a chat completion through the AI Gateway with the test API key,
    ...    addressing the AIM precisely via its backend UUID (x-ai-eg-backend). This routes
    ...    to this project's AIM even when the same model name is deployed in another project,
    ...    so the happy path is deterministic on a multi-tenant cluster.
    ...    Requires: TEST_AIM_MODEL_ID (served model name), TEST_AIM_ID (backend UUID), TEST_API_KEY_VALUE
    ...    Sets: TEST_RESPONSE
    Variable Should Exist    ${TEST_AIM_MODEL_ID}    msg=TEST_AIM_MODEL_ID is not set
    Variable Should Exist    ${TEST_AIM_ID}    msg=TEST_AIM_ID is not set
    Variable Should Exist    ${TEST_API_KEY_VALUE}    msg=TEST_API_KEY_VALUE is not set
    ${gateway}=    The AI Gateway endpoint
    ${response}=    Send Chat Completion To AI Gateway    ${gateway}    ${TEST_AIM_MODEL_ID}
    ...    api_key=${TEST_API_KEY_VALUE}    backend=${TEST_AIM_ID}    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

A valid API key authorized for this model exists
    [Documentation]    Creates a fresh API key and adds it to the deployed AIM's
    ...    cluster-auth group, making it a valid credential for model-T. Stores the
    ...    value in TEST_OUTSIDER_API_KEY_VALUE without disturbing TEST_API_KEY or
    ...    TEST_API_KEY_VALUE. Used with "another model is available on the gateway"
    ...    to test cross-model authorization (EAI-6805 regression).
    Variable Should Exist    ${TEST_AIM_AUTH_GROUP_ID}
    ...    msg=TEST_AIM_AUTH_GROUP_ID not set — ensure "An AIM model is running with api key" ran first
    VAR    ${saved_key}    ${TEST_API_KEY}
    VAR    ${saved_key_value}    ${TEST_API_KEY_VALUE}
    Api key exists for user
    VAR    ${outsider_id}    ${TEST_API_KEY}[id]
    VAR    ${outsider_value}    ${TEST_API_KEY_VALUE}
    ${project}=    Get Project Namespace
    api_keys_api.Add api key to group    ${outsider_id}    ${TEST_AIM_AUTH_GROUP_ID}
    ...    project=${project}    expected_status=201
    VAR    ${TEST_OUTSIDER_API_KEY_VALUE}    ${outsider_value}    scope=TEST
    VAR    ${TEST_API_KEY}    ${saved_key}    scope=TEST
    VAR    ${TEST_API_KEY_VALUE}    ${saved_key_value}    scope=TEST

Another model is available on the gateway
    [Documentation]    Discovers a model on the AI Gateway that is NOT the test AIM and
    ...    stores it in TEST_OTHER_MODEL_ID. Fails clearly if no second model is deployed —
    ...    the EAI-6805 regression test requires at least two AIMs on the same hostname so
    ...    the buggy hostname-only route selection can pick the wrong one.
    Variable Should Exist    ${TEST_AIM_MODEL_ID}    msg=TEST_AIM_MODEL_ID is not set
    ${gateway}=    The AI Gateway endpoint
    ${response}=    Get Models From AI Gateway    ${gateway}    api_key=${TEST_API_KEY_VALUE}
    ...    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data    default=@{EMPTY}
    ${other_ids}=    Evaluate    [m['id'] for m in $models if m.get('id') != '${TEST_AIM_MODEL_ID}']
    IF    len($other_ids) == 0
        Fail
        ...    No other models found on the gateway — EAI-6805 regression test needs at least two AIMs deployed on the same hostname
    END
    VAR    ${TEST_OTHER_MODEL_ID}    ${other_ids[0]}    scope=TEST
    Log    Cross-model auth test will request: ${TEST_OTHER_MODEL_ID}    INFO

A chat completion request is sent to the AI Gateway for the other model with the authorized key
    [Documentation]    Sends a chat completion for TEST_OTHER_MODEL_ID using
    ...    TEST_OUTSIDER_API_KEY_VALUE, which is authorized for the test AIM but not
    ...    for the other model. Sets: TEST_RESPONSE
    Variable Should Exist    ${TEST_OTHER_MODEL_ID}
    ...    msg=TEST_OTHER_MODEL_ID not set — ensure "Another model is available on the gateway" ran
    Variable Should Exist    ${TEST_OUTSIDER_API_KEY_VALUE}
    ...    msg=TEST_OUTSIDER_API_KEY_VALUE not set — ensure "A valid API key authorized for this model exists" ran
    ${gateway}=    The AI Gateway endpoint
    ${response}=    Send Chat Completion To AI Gateway    ${gateway}    ${TEST_OTHER_MODEL_ID}
    ...    api_key=${TEST_OUTSIDER_API_KEY_VALUE}    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

A chat completion request is sent to the AI Gateway without an API key
    [Documentation]    Sends a chat completion through the AI Gateway with no Authorization header.
    ...    Requires: TEST_AIM_MODEL_ID
    ...    Sets: TEST_RESPONSE
    Variable Should Exist    ${TEST_AIM_MODEL_ID}    msg=TEST_AIM_MODEL_ID is not set
    ${gateway}=    The AI Gateway endpoint
    ${response}=    Send Chat Completion To AI Gateway    ${gateway}    ${TEST_AIM_MODEL_ID}
    ...    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

A chat completion request is sent to the AI Gateway with an invalid API key
    [Documentation]    Sends a chat completion through the AI Gateway with a bogus Bearer token.
    ...    Requires: TEST_AIM_MODEL_ID
    ...    Sets: TEST_RESPONSE
    Variable Should Exist    ${TEST_AIM_MODEL_ID}    msg=TEST_AIM_MODEL_ID is not set
    ${gateway}=    The AI Gateway endpoint
    ${response}=    Send Chat Completion To AI Gateway    ${gateway}    ${TEST_AIM_MODEL_ID}
    ...    api_key=invalid-api-key-12345    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

A chat completion request is sent for a model name that does not exist
    [Documentation]    Sends a chat completion for a model the gateway does not know about.
    ...    Requires: TEST_API_KEY_VALUE
    ...    Sets: TEST_RESPONSE
    Variable Should Exist    ${TEST_API_KEY_VALUE}    msg=TEST_API_KEY_VALUE is not set
    ${gateway}=    The AI Gateway endpoint
    ${response}=    Send Chat Completion To AI Gateway    ${gateway}
    ...    model_name=this-model-does-not-exist    api_key=${TEST_API_KEY_VALUE}
    ...    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

# Then-step keywords

The deployed AIM is listed among the available models
    [Documentation]    Verifies the gateway /v1/models response includes the served
    ...    model name for the currently deployed AIM.
    ...    Requires: TEST_RESPONSE (from the /v1/models query), TEST_AIM_MODEL_ID
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    ...    msg=/v1/models should return 200, got ${TEST_RESPONSE.status_code}
    Variable Should Exist    ${TEST_GATEWAY_MODELS}    msg=TEST_GATEWAY_MODELS not set — /v1/models did not return a parsable body
    Variable Should Exist    ${TEST_AIM_MODEL_ID}    msg=TEST_AIM_MODEL_ID is not set
    ${model_ids}=    Evaluate    [m.get('id') for m in $TEST_GATEWAY_MODELS]
    Should Contain    ${model_ids}    ${TEST_AIM_MODEL_ID}
    ...    msg=Deployed model ${TEST_AIM_MODEL_ID} not found in gateway /v1/models response: ${model_ids}

The model returns a successful response
    [Documentation]    Verifies the chat completion response is 200 with an OpenAI-shaped body
    ...    and that the response came from the correct backend. vLLM echoes its own
    ...    served-model-name, not the requested model — a mismatch means the gateway
    ...    routed to the wrong backend (catches cluster-auth misrouting bugs like EAI-6805).
    ...    Requires: TEST_RESPONSE, TEST_AIM_MODEL_ID
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    ...    msg=Expected 200, got ${TEST_RESPONSE.status_code}: ${TEST_RESPONSE.text}
    ${body}=    Set Variable    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${body}    choices    msg=Response should contain choices array
    ${choices}=    Get From Dictionary    ${body}    choices
    Should Not Be Empty    ${choices}    msg=Choices array should not be empty
    ${served_model}=    Get From Dictionary    ${body}    model    default=${None}
    Should Be Equal    ${served_model}    ${TEST_AIM_MODEL_ID}
    ...    msg=Gateway routed to wrong backend: requested ${TEST_AIM_MODEL_ID} but response model is ${served_model}

The request is rejected with an authentication error
    [Documentation]    Verifies the response is a 401 or 403. Body inspection is
    ...    intentionally minimal — Envoy may return a plain-text or empty body for
    ...    rejected auth, so the status code is the contract.
    ...    Requires: TEST_RESPONSE
    Should Be True    ${TEST_RESPONSE.status_code} in [401, 403]
    ...    msg=Expected 401 or 403, got ${TEST_RESPONSE.status_code}: ${TEST_RESPONSE.text}

The AIM's AI Gateway route is removed
    [Documentation]    Polls until ai-gateway-discovery has deleted the AIGatewayRoute for the
    ...    undeployed AIM. Verifies via kubectl that no route in the project namespace still
    ...    targets this AIM's backend UUID. This is collision-proof: unlike the /v1/models
    ...    listing (which reports model names shared across projects on a multi-tenant cluster),
    ...    the backend UUID is unique to this AIM, so its absence proves this specific route was
    ...    garbage-collected. Discovery reconciliation can take a handful of seconds after undeploy.
    ...    Requires: TEST_AIM_ID
    Variable Should Exist    ${TEST_AIM_ID}    msg=TEST_AIM_ID is not set
    ${namespace}=    Get Project Namespace
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    No AI Gateway route targets backend    ${TEST_AIM_ID}    ${namespace}

The request fails with a client error
    [Documentation]    Verifies the response is a 4xx (not 5xx). Used for unknown-model
    ...    routing where the gateway should reject the request without surfacing a
    ...    server-side failure.
    ...    Requires: TEST_RESPONSE
    Should Be True    400 <= ${TEST_RESPONSE.status_code} < 500
    ...    msg=Expected 4xx client error, got ${TEST_RESPONSE.status_code}: ${TEST_RESPONSE.text}

# Internal helpers

No AI Gateway route targets backend
    [Documentation]    Helper for polling: asserts no AIGatewayRoute in the namespace has an
    ...    x-ai-eg-backend match header equal to the given AIM UUID. ai-gateway-discovery stamps
    ...    this header (rule 1) with the AIM's workload-id, so its absence across all routes means
    ...    the AIM's route was deleted. Reads routes by their fully-qualified resource name so the
    ...    lookup does not depend on the short-name registration.
    [Arguments]    ${aim_uuid}    ${namespace}
    ${result}=    Run Process    kubectl    get    aigatewayroutes.aigateway.envoyproxy.io
    ...    -n    ${namespace}    -o    json    timeout=15s
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Could not list AIGatewayRoutes in ${namespace}: ${result.stderr}
    ${data}=    Evaluate    json.loads($result.stdout)    modules=json
    ${backends}=    Evaluate
    ...    [h.get('value') for item in $data.get('items', []) for rule in item.get('spec', {}).get('rules', []) for match in rule.get('matches', []) for h in match.get('headers', []) if h.get('name') == 'x-ai-eg-backend']
    Should Not Contain    ${backends}    ${aim_uuid}
    ...    msg=AIGatewayRoute still targets backend ${aim_uuid} in namespace ${namespace}

# ===========================================================================
# EAI-7128 — same-model routing regression (Bug B)
# ===========================================================================
# When two AIMs serve the same model name (in two projects), a request that
# targets a backend by UUID must reach that exact backend. Without precise
# routing, Envoy merges the per-AIM AIGatewayRoutes and an equal-specificity
# model-name fallback rule can win by creation timestamp, mis-routing to the
# wrong deployment. The fix makes the UUID route (Host + x-ai-eg-backend +
# x-ai-eg-model) more specific so it wins; clients set both routing headers.
# There is no per-backend identity in the response (both backends echo the
# same served model name), so routing is verified via per-backend generated-
# token counters: vLLM's generation_tokens_total, exposed by the aiwb API as
# the raw cumulative `total_tokens` metric scoped by workload_id (= the
# backend UUID), compared before/after as a delta.

# Given-step keywords

The same AIM model is deployed in a second project
    [Documentation]    Deploys the SAME catalog AIM (same served model name) into a fresh
    ...    second project so two backends share a model name on the gateway — the
    ...    precondition for the EAI-7128 mis-routing bug. AIM-A must already be running
    ...    (run "An AIM model is running with api key" first).
    ...
    ...    Records A-side coordinates for the metric comparison (TEST_AIM_A_ID /
    ...    TEST_AIM_A_NAMESPACE), creates project B as the same user, deploys the same
    ...    model there, and creates a B-authorized API key. AIM-A's shared state
    ...    (TEST_PROJECT, TEST_AIM_ID, TEST_AIM_MODEL_ID, TEST_API_KEY/_VALUE) is
    ...    restored on exit so the rest of the suite still sees A.
    ...    Sets: TEST_AIM_A_ID, TEST_AIM_A_NAMESPACE, TEST_AIM_B_ID,
    ...    TEST_AIM_B_NAMESPACE, TEST_AIM_B_API_KEY_VALUE.
    Variable Should Exist    ${TEST_AIM_ID}    msg=TEST_AIM_ID not set — run "An AIM model is running with api key" first
    Variable Should Exist    ${TEST_AIM_MODEL_ID}    msg=TEST_AIM_MODEL_ID is not set
    Variable Should Exist    ${TEST_AIM_NAME}    msg=TEST_AIM_NAME is not set

    # Record A-side coordinates (the model name and backend we expect to stay idle).
    ${a_namespace}=    Get Project Namespace
    VAR    ${TEST_AIM_A_ID}    ${TEST_AIM_ID}    scope=TEST
    VAR    ${TEST_AIM_A_NAMESPACE}    ${a_namespace}    scope=TEST

    # Save A-side state we are about to overwrite while standing up project B.
    VAR    ${saved_project}    ${TEST_PROJECT}
    VAR    ${saved_project_id}    ${TEST_PROJECT_ID}
    VAR    ${saved_aim_id}    ${TEST_AIM_ID}
    VAR    ${saved_model_id}    ${TEST_AIM_MODEL_ID}
    VAR    ${saved_api_key}    ${TEST_API_KEY}
    VAR    ${saved_api_key_value}    ${TEST_API_KEY_VALUE}

    # Stand up project B (same user) and give it GPU quota. gpu_count=1 matches the
    # caller's project-A quota: both projects hold a live 1-GPU AIM simultaneously,
    # so a 1-GPU footprint each keeps total demand within cluster quota headroom.
    A Fresh Project With User Access Exists
    Project quota is set to    gpu_count=1    cpu_milli_cores=8000    memory_bytes=68719476736

    # Deploy the SAME model into B (TEST_AIM_NAME is unchanged). This yields a new
    # backend UUID (TEST_AIM_ID = B) but the same served model name as A.
    An AIM model is running
    ${b_namespace}=    Get Project Namespace
    VAR    ${TEST_AIM_B_ID}    ${TEST_AIM_ID}    scope=TEST
    VAR    ${TEST_AIM_B_NAMESPACE}    ${b_namespace}    scope=TEST

    # Create an API key authorized for backend B (bound to B's cluster-auth group).
    User is authenticated
    Api key exists for user
    Api key is assigned to AIMS model
    Key assignment should succeed
    VAR    ${TEST_AIM_B_API_KEY_VALUE}    ${TEST_API_KEY_VALUE}    scope=TEST

    # Sanity: B serves the same model name as A (the whole premise of the bug).
    ${b_models}=    List models from external endpoint
    ...    ${TEST_AIM_EXTERNAL_HOST}    ${TEST_AIM_B_ID}    ${TEST_AIM_B_API_KEY_VALUE}
    ${b_first}=    Get From List    ${b_models}    0
    Should Be Equal    ${b_first}[id]    ${saved_model_id}
    ...    msg=Second project's AIM serves a different model (${b_first}[id]) than A (${saved_model_id}); EAI-7128 needs the SAME model name in both projects

    # Restore A-side context for the rest of the suite (TEST_PROJECT and
    # TEST_PROJECT_ID were both repointed at B by the fresh-project setup).
    VAR    ${TEST_PROJECT}    ${saved_project}    scope=TEST
    VAR    ${TEST_PROJECT_ID}    ${saved_project_id}    scope=TEST
    VAR    ${TEST_AIM_ID}    ${saved_aim_id}    scope=TEST
    VAR    ${TEST_AIM_MODEL_ID}    ${saved_model_id}    scope=TEST
    VAR    ${TEST_API_KEY}    ${saved_api_key}    scope=TEST
    VAR    ${TEST_API_KEY_VALUE}    ${saved_api_key_value}    scope=TEST
    Log    AIM-A backend=${TEST_AIM_A_ID} (ns ${TEST_AIM_A_NAMESPACE}); AIM-B backend=${TEST_AIM_B_ID} (ns ${TEST_AIM_B_NAMESPACE}); shared model=${saved_model_id}    INFO

# When-step keywords

A chat completion is sent through the AI Gateway targeting backend B
    [Documentation]    Baselines both backends' generated-token counters, then sends a few chat
    ...    completions to the gateway addressed to backend B by UUID (x-ai-eg-backend +
    ...    x-ai-eg-model, using B's API key). Status is logged, not asserted — a mis-route to a
    ...    same-named backend also returns 200; the per-backend token counter is the routing
    ...    signal (see the Then step).
    ...    Requires: TEST_AIM_MODEL_ID, TEST_AIM_*_ID/_NAMESPACE, TEST_AIM_B_API_KEY_VALUE
    ...    Sets: TEST_TOKENS_A_BEFORE, TEST_TOKENS_B_BEFORE
    Variable Should Exist    ${TEST_AIM_B_ID}    msg=TEST_AIM_B_ID not set — run "The same AIM model is deployed in a second project" first
    Variable Should Exist    ${TEST_AIM_B_API_KEY_VALUE}    msg=TEST_AIM_B_API_KEY_VALUE is not set
    Baseline both backend token counters
    Send gateway completions to backend    ${TEST_AIM_B_ID}    ${TEST_AIM_B_API_KEY_VALUE}

A chat completion is sent through the AI Gateway targeting backend A
    [Documentation]    Symmetric to the backend-B step: re-baselines both counters, then sends a
    ...    few chat completions addressed to backend A by UUID, using A's API key. Verifying
    ...    BOTH directions guards against routing that collapses onto a single backend (e.g. the
    ...    creation-timestamp race always resolving to the older route): if every request went
    ...    to A, the backend-B phase fails; if every request went to B, this phase fails.
    ...    Requires: TEST_AIM_MODEL_ID, TEST_AIM_*_ID/_NAMESPACE, TEST_API_KEY_VALUE (A's key)
    ...    Sets: TEST_TOKENS_A_BEFORE, TEST_TOKENS_B_BEFORE
    Variable Should Exist    ${TEST_AIM_A_ID}    msg=TEST_AIM_A_ID not set — run the earlier Given steps first
    Variable Should Exist    ${TEST_API_KEY_VALUE}    msg=TEST_API_KEY_VALUE (A's key) is not set
    Baseline both backend token counters
    Send gateway completions to backend    ${TEST_AIM_A_ID}    ${TEST_API_KEY_VALUE}

# Then-step keywords

Only backend B served the request
    [Documentation]    Verifies the backend-B request reached B's vLLM and NOT co-hosted A, via
    ...    per-backend generated-token counters (vLLM generation_tokens_total, exposed as the
    ...    raw cumulative `total_tokens` metric scoped by workload_id = backend UUID): B's
    ...    counter must rise above its pre-send baseline (it produced output → it served), while
    ...    A's must stay flat. A raw cumulative counter is used — not a windowed increase() — so
    ...    a short burst right after backend startup is not missed (increase() over a window that
    ...    only sees post-burst samples reads 0). Polls to absorb Prometheus scrape lag. Fails
    ...    if the request is mis-routed to the co-hosted backend.
    ...    Requires: TEST_TOKENS_*_BEFORE, TEST_AIM_*_ID/_NAMESPACE
    Variable Should Exist    ${TEST_TOKENS_B_BEFORE}    msg=TEST_TOKENS_B_BEFORE not set — run the When step first
    Wait Until Keyword Succeeds    3 min    15 sec    Backend serves while peer stays idle
    ...    ${TEST_AIM_B_ID}    ${TEST_AIM_B_NAMESPACE}    ${TEST_TOKENS_B_BEFORE}
    ...    ${TEST_AIM_A_ID}    ${TEST_AIM_A_NAMESPACE}    ${TEST_TOKENS_A_BEFORE}

Only backend A served the request
    [Documentation]    Mirror of "Only backend B served the request" for the backend-A phase: A's
    ...    token counter must rise while B's stays flat, proving a UUID-targeted request reaches
    ...    A and is not pulled to B.
    ...    Requires: TEST_TOKENS_*_BEFORE, TEST_AIM_*_ID/_NAMESPACE
    Variable Should Exist    ${TEST_TOKENS_A_BEFORE}    msg=TEST_TOKENS_A_BEFORE not set — run the When step first
    Wait Until Keyword Succeeds    3 min    15 sec    Backend serves while peer stays idle
    ...    ${TEST_AIM_A_ID}    ${TEST_AIM_A_NAMESPACE}    ${TEST_TOKENS_A_BEFORE}
    ...    ${TEST_AIM_B_ID}    ${TEST_AIM_B_NAMESPACE}    ${TEST_TOKENS_B_BEFORE}

# Internal helpers (EAI-7128)

Baseline both backend token counters
    [Documentation]    Snapshots A's and B's cumulative generated-token counters into
    ...    TEST_TOKENS_A_BEFORE / TEST_TOKENS_B_BEFORE so a Then step can assert a per-backend
    ...    delta. Re-run before each send phase to re-baseline against the current totals.
    ${a_before}=    Total generated tokens for backend    ${TEST_AIM_A_ID}    ${TEST_AIM_A_NAMESPACE}
    ${b_before}=    Total generated tokens for backend    ${TEST_AIM_B_ID}    ${TEST_AIM_B_NAMESPACE}
    VAR    ${TEST_TOKENS_A_BEFORE}    ${a_before}    scope=TEST
    VAR    ${TEST_TOKENS_B_BEFORE}    ${b_before}    scope=TEST

Send gateway completions to backend
    [Documentation]    Sends 3 chat completions to the gateway addressed to the given backend
    ...    UUID with the given API key. Status is logged, not asserted.
    [Arguments]    ${backend_id}    ${api_key}
    ${gateway}=    The AI Gateway endpoint
    FOR    ${i}    IN RANGE    3
        ${response}=    Send Chat Completion To AI Gateway    ${gateway}    ${TEST_AIM_MODEL_ID}
        ...    api_key=${api_key}    backend=${backend_id}    expected_status=any
        Log    Gateway completion #${i} targeting backend ${backend_id} → HTTP ${response.status_code}    INFO
    END

Backend serves while peer stays idle
    [Documentation]    Single poll iteration: the target backend's cumulative generated-token
    ...    counter must have risen above its pre-send baseline, and the peer backend's must be
    ...    unchanged.
    [Arguments]    ${target_id}    ${target_ns}    ${target_before}    ${peer_id}    ${peer_ns}    ${peer_before}
    ${target_after}=    Total generated tokens for backend    ${target_id}    ${target_ns}
    ${peer_after}=    Total generated tokens for backend    ${peer_id}    ${peer_ns}
    Log    Generated tokens — target ${target_id}: ${target_before} -> ${target_after}; peer ${peer_id}: ${peer_before} -> ${peer_after}    INFO
    Should Be True    ${target_after} > ${target_before}
    ...    msg=Intended backend ${target_id} generated no new tokens (${target_before} -> ${target_after}); request did not reach it
    Should Be Equal As Numbers    ${peer_after}    ${peer_before}
    ...    msg=Peer backend ${peer_id} generated tokens (${peer_before} -> ${peer_after}); request was mis-routed (EAI-7128)

Total generated tokens for backend
    [Documentation]    Returns a backend's cumulative generated-token count (vLLM
    ...    generation_tokens_total) via the aiwb API `total_tokens` metric. The endpoint
    ...    scopes the query by workload_id (= the backend UUID), isolating one backend even
    ...    when several share a model name. This is a raw cumulative scalar (not a windowed
    ...    increase), so before/after snapshots give a reliable per-backend delta. A missing
    ...    series resolves to 0. Returns a float.
    ...
    ...    The endpoint requires a start/end range even though total_tokens is an instantaneous
    ...    cumulative query that ignores it, so a nominal 1-hour window is passed.
    [Arguments]    ${service_id}    ${namespace}
    ${end}=    Get Current Date    time_zone=UTC    result_format=%Y-%m-%dT%H:%M:%SZ
    ${start}=    Get Current Date    time_zone=UTC    increment=-1 hour    result_format=%Y-%m-%dT%H:%M:%SZ
    &{params}=    Create Dictionary    start=${start}    end=${end}
    ${response}=    Get AIM Service Metric    ${service_id}    total_tokens    ${namespace}
    ...    expected_status=200    params=${params}
    ${data}=    Get From Dictionary    ${response.json()}    data
    RETURN    ${data}

AIWB workbench endpoints should remain accessible for 6 seconds after undeploy
    [Documentation]    Polls the three AIWB routes that share the Envoy gateway in a
    ...    tight loop for 6 seconds after AIM undeploy. Fails immediately on HTTP 500.
    ...    200 and 404 are acceptable — the AIM is gone so the inference list may be
    ...    empty, but Envoy must not reject the requests outright.
    ${namespace}=    Get Project Namespace
    ${deadline}=     Evaluate    time.time() + 6    modules=time

    WHILE    True    limit=NONE
        ${now}=    Evaluate    time.time()    modules=time
        IF    ${now} >= ${deadline}    BREAK

        ${r_inference}=    List AIM Services                   ${namespace}
        ${r_workloads}=    Get AIWB workloads                  ${namespace}
        ${r_metrics}=      Get AIWB Project Workloads Metrics  ${namespace}

        Should Contain    ${{[200, 404]}}    ${r_inference.status_code}
        ...    msg=GET .../inference returned HTTP ${r_inference.status_code} during post-undeploy window (expected 200 or 404)
        Should Contain    ${{[200, 404]}}    ${r_workloads.status_code}
        ...    msg=GET .../workloads returned HTTP ${r_workloads.status_code} during post-undeploy window (expected 200 or 404)
        Should Contain    ${{[200, 404]}}    ${r_metrics.status_code}
        ...    msg=GET .../workloads/metrics returned HTTP ${r_metrics.status_code} during post-undeploy window (expected 200 or 404)
    END
