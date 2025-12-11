# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Library     RequestsLibrary
Library     Collections
Resource    common.resource


*** Keywords ***
Finetune endpoint
    [Documentation]    Returns the full charts endpoint URL
    [Arguments]             ${model_id}
    ${finetune_endpoint}=                           Catalog endpoint        models/${model_id}/finetune
    RETURN                  ${finetune_endpoint}

Finetune model
    [Documentation]    Finetune a model using the provided model ID and data.
    [Arguments]             ${model_id}             ${finetune_data}        ${expected_status}=any                          ${params}=${None}
    Create api session

    TRY
        ${endpoint}=            Finetune endpoint       ${model_id}
        ${response}=            POST On Session         ${API_SESSION}          ${endpoint}             json=${finetune_data}                           params=${params}        expected_status=${expected_status}
        RETURN                  ${response}
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to create model: ${error}                ERROR                   console=yes
        FAIL                    Model creation failed: ${error}
    END
