# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API finetuning endpoints.
...                 Provides direct API operation wrappers for the /models/{model_id}/finetune endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource
Resource            resources/airm_projects.resource
Resource            workloads.resource


*** Keywords ***
Finetune endpoint
    [Documentation]    Returns the full finetune endpoint URL for a model in a namespace.
    ...                Pattern: /namespaces/{namespace}/models/{model_id}/finetune
    [Arguments]             ${model_id}             ${namespace}
    ${finetune_endpoint}=   Service API Endpoint    aiwb    endpoint=namespaces/${namespace}/models/${model_id}/finetune
    RETURN                  ${finetune_endpoint}

Finetune model
    [Documentation]    Finetune a model using the provided model ID and data.
    ...                Uses namespace-based endpoint pattern: /namespaces/{namespace}/models/{model_id}/finetune
    ...
    ...                Args:
    ...                model_id: Model ID or canonical name (e.g., UUID or "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    ...                finetune_data: Dictionary with finetuning parameters
    ...                expected_status: Expected HTTP status code (default: any)
    ...                namespace: Namespace for the request
    ...                display_name: Optional display name for the workload
    ...
    ...                Returns:
    ...                response: API response containing the finetuning workload details
    [Arguments]             ${model_id}             ${finetune_data}        ${namespace}            ${expected_status}=any
    ...                     ${display_name}=${None}
    Create api session    aiwb

    ${endpoint}=            Finetune endpoint       ${model_id}             ${namespace}

    # Build query parameters if display_name is provided
    ${params}=              Create Dictionary
    IF    $display_name is not None
        Set To Dictionary   ${params}               display_name=${display_name}
    END

    Log                     POST ${endpoint}        DEBUG
    Log                     Request body: ${finetune_data}                  DEBUG

    ${response}=            Safe Post Request       ${endpoint}             json=${finetune_data}
    ...                     params=${params}        expected_status=${expected_status}

    Log                     Response status: ${response.status_code}        DEBUG
    RETURN                  ${response}
