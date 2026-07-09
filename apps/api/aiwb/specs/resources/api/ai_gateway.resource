# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for the unified Envoy AI Gateway endpoint.
...                 Stateless HTTP wrappers for OpenAI-compatible /v1/models and
...                 /v1/chat/completions routes published by ai-gateway-discovery
...                 (EAI-5889 / EAI-6040). All inputs are explicit arguments —
...                 callers in the business-logic layer own TEST_* state and
...                 resolve the gateway URL.
...
...                 SSL verification follows the suite-wide ${VERIFY_SSL} convention
...                 (testing/CLAUDE.md). Sessions are created via Create AI Gateway
...                 session so verify= is honored on every request.
Resource            resources/api/external_aim.resource
Library             RequestsLibrary
Library             Collections


*** Keywords ***
Create AI Gateway session
    [Documentation]    Creates a RequestsLibrary session for the AI Gateway base URL
    ...    with ${VERIFY_SSL} honored. Reuses the AIM external session helper since
    ...    the gateway is the same kind of cluster-external HTTPS endpoint.
    [Arguments]    ${gateway_url}    ${session_name}=ai_gateway
    ${name}=    Create AIM external session    ${gateway_url}    session_name=${session_name}
    RETURN    ${name}

Get Models From AI Gateway
    [Documentation]    GET /v1/models on the unified AI Gateway endpoint.
    ...    The endpoint follows the OpenAI listing contract: {"data": [{"id": ...}, ...]}.
    ...    Returns the raw RequestsLibrary response so callers can inspect status and body.
    [Arguments]    ${gateway_url}    ${api_key}=${None}    ${expected_status}=any    ${timeout}=60

    ${session}=    Create AI Gateway session    ${gateway_url}
    ${headers}=    Create Dictionary
    IF    "${api_key}" != "${None}"
        Set To Dictionary    ${headers}    Authorization=Bearer ${api_key}
    END

    ${response}=    Get From AIM External Endpoint    ${session}    /v1/models
    ...    headers=${headers}    expected_status=${expected_status}    timeout=${timeout}
    RETURN    ${response}

Send Chat Completion To AI Gateway
    [Documentation]    POST /v1/chat/completions on the unified AI Gateway endpoint.
    ...    Sends a minimal OpenAI-compatible chat completion request and returns
    ...    the raw response. Callers handle status assertions and body parsing.
    ...    When ${backend} is set, the AIM is selected by its UUID so routing is
    ...    unambiguous even when the same model name is deployed in another project.
    ...    Without it, the gateway routes by model name.
    ...
    ...    Backend-targeted routing (post-EAI-7043) requires the client to set BOTH
    ...    routing headers explicitly — x-ai-eg-backend AND x-ai-eg-model — so the
    ...    AIM's 3-condition route (Host + x-ai-eg-backend + x-ai-eg-model) is matched
    ...    at routing time and wins by specificity over any model-name fallback. The
    ...    model must also stay in the body for the backend. Relying on the gateway's
    ...    Lua to derive x-ai-eg-model from the body is NOT enough for UUID routing:
    ...    the Lua-set header is not present when the 3-condition rule is evaluated, so
    ...    only the 2-condition model-name rule matches and the request can be
    ...    mis-routed to an older co-hosted backend of the same model.
    [Arguments]    ${gateway_url}    ${model_name}    ${api_key}=${None}
    ...    ${backend}=${None}    ${expected_status}=any    ${timeout}=120

    ${session}=    Create AI Gateway session    ${gateway_url}
    ${headers}=    Create Dictionary    Content-Type=application/json
    IF    "${api_key}" != "${None}"
        Set To Dictionary    ${headers}    Authorization=Bearer ${api_key}
    END
    IF    "${backend}" != "${None}"
        Set To Dictionary    ${headers}    x-ai-eg-backend=${backend}
        Set To Dictionary    ${headers}    x-ai-eg-model=${model_name}
    END

    ${messages}=    Evaluate    [{"role": "user", "content": "Hello"}]
    # max_tokens MUST be an integer. Create Dictionary stringifies "10", and the
    # AI Gateway ext-proc rejects a quoted number as malformed JSON (BadRequest),
    # unlike vLLM directly which coerces it.
    ${body}=    Create Dictionary
    ...    model=${model_name}
    ...    messages=${messages}
    ...    max_tokens=${10}

    ${response}=    Post To AIM External Endpoint    ${session}    /v1/chat/completions
    ...    json=${body}    headers=${headers}    expected_status=${expected_status}    timeout=${timeout}
    RETURN    ${response}
