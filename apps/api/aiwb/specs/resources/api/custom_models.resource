# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIWB API custom-model preview, onboard, list, and detail endpoints.
...                 Wraps POST /v1/projects/{project}/models/preview,
...                 POST /v1/projects/{project}/models/onboard,
...                 GET /v1/projects/{project}/models, and
...                 GET /v1/projects/{project}/models/{model_name}.
...                 Higher-level test logic should use aiwb_custom_models.resource instead.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource


*** Keywords ***
Custom Models List Endpoint
    [Documentation]    Return the full list endpoint URL for a project.
    ...    Pattern: /projects/{project}/models
    [Arguments]    ${project}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/models
    RETURN    ${endpoint}

List Custom Models
    [Documentation]    GET the list of custom models onboarded into a project.
    ...    Pattern: GET /projects/{project}/models
    [Arguments]    ${project}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Models List Endpoint    ${project}
    Log    GET ${endpoint}    DEBUG
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    Log    List custom models response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Custom Model Detail Endpoint
    [Documentation]    Return the detail endpoint URL for a single custom model.
    ...    Pattern: /projects/{project}/models/{model_name}
    [Arguments]    ${project}    ${model_name}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/models/${model_name}
    RETURN    ${endpoint}

Get Custom Model
    [Documentation]    GET the detail for a single custom model by name.
    ...    Pattern: GET /projects/{project}/models/{model_name}
    [Arguments]    ${project}    ${model_name}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Model Detail Endpoint    ${project}    ${model_name}
    Log    GET ${endpoint}    DEBUG
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    Log    Get custom model response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Delete Custom Model
    [Documentation]    DELETE an onboarded custom model by name.
    ...    Pattern: DELETE /projects/{project}/models/{model_name}
    [Arguments]    ${project}    ${model_name}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Model Detail Endpoint    ${project}    ${model_name}
    Log    DELETE ${endpoint}    DEBUG
    ${response}=    Safe Delete Request    ${endpoint}    expected_status=${expected_status}
    Log    Delete custom model response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Custom Models Runtime Profile Options Endpoint
    [Documentation]    Return the runtime-profile-options endpoint URL for a project.
    ...    Pattern: /projects/{project}/models/runtime-profile-options
    [Arguments]    ${project}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/models/runtime-profile-options
    RETURN    ${endpoint}

Get Runtime Profile Options
    [Documentation]    GET the base-template runtime options a custom model can use.
    ...    Pattern: GET /projects/{project}/models/runtime-profile-options
    [Arguments]    ${project}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Models Runtime Profile Options Endpoint    ${project}
    Log    GET ${endpoint}    DEBUG
    ${response}=    Safe Get Request    ${endpoint}    expected_status=${expected_status}
    Log    Runtime profile options response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Custom Model Copy Endpoint
    [Documentation]    Return the copy endpoint URL for a single custom model.
    ...    Pattern: /projects/{project}/models/{model_name}/copy
    [Arguments]    ${project}    ${model_name}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/models/${model_name}/copy
    RETURN    ${endpoint}

Copy Custom Model
    [Documentation]    POST a copy request for a custom model by resource name.
    ...    Pattern: POST /projects/{project}/models/{model_name}/copy
    [Arguments]    ${project}    ${model_name}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Model Copy Endpoint    ${project}    ${model_name}
    Log    POST ${endpoint}    DEBUG
    ${response}=    Safe Post Request    ${endpoint}    expected_status=${expected_status}
    Log    Copy custom model response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Custom Models Preview Endpoint
    [Documentation]    Return the full preview endpoint URL for a project.
    ...    Pattern: /projects/{project}/models/preview
    [Arguments]    ${project}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/models/preview
    RETURN    ${endpoint}

Custom Models Onboard Endpoint
    [Documentation]    Return the full onboard endpoint URL for a project.
    ...    Pattern: /projects/{project}/models/onboard
    [Arguments]    ${project}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/models/onboard
    RETURN    ${endpoint}

Preview Custom Model Source
    [Documentation]    POST a custom-model source preview request.
    [Arguments]    ${project}    ${source}    ${hf_token_secret_name}=${None}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Models Preview Endpoint    ${project}
    &{body}=    Create Dictionary    source=${source}
    IF    $hf_token_secret_name is not None
        Set To Dictionary    ${body}    hfTokenSecretName=${hf_token_secret_name}
    END
    Log    POST ${endpoint} body=${body}    DEBUG
    ${response}=    Safe Post Request    ${endpoint}
    ...    json=${body}
    ...    expected_status=${expected_status}
    Log    Preview response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Onboard Custom Model From Preview
    [Documentation]    POST an onboard request built from a preview response JSON body.
    ...    ``custom_profile`` is forwarded as the optional ``customProfile`` body
    ...    field (runtime profile overrides written to AIMModel.spec.profiles.overrides).
    [Arguments]    ${project}    ${preview_json}    ${image}    ${hf_token_secret_name}=${None}
    ...    ${custom_profile}=${None}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Models Onboard Endpoint    ${project}
    &{body}=    Create Dictionary
    ...    repoId=${preview_json}[repoId]
    ...    revision=${preview_json}[revision]
    ...    sha=${preview_json}[sha]
    ...    displayName=${preview_json}[displayName]
    ...    description=${preview_json}[description]
    ...    image=${image}
    IF    $hf_token_secret_name is not None
        Set To Dictionary    ${body}    hfTokenSecretName=${hf_token_secret_name}
    END
    IF    $custom_profile is not None
        Set To Dictionary    ${body}    customProfile=${custom_profile}
    END
    Log    POST ${endpoint} body=${body}    DEBUG
    ${response}=    Safe Post Request    ${endpoint}
    ...    json=${body}
    ...    expected_status=${expected_status}
    Log    Onboard response status: ${response.status_code}    DEBUG
    RETURN    ${response}

Custom Models Patch Endpoint
    [Documentation]    Return the PATCH URL for a project model.
    ...    Pattern: /projects/{project}/models/{name}
    [Arguments]    ${project}    ${model_name}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${project}/models/${model_name}
    RETURN    ${endpoint}

Patch Onboarded Model
    [Documentation]    PATCH an onboarded model. The body may carry display metadata
    ...    (displayName, description, tags) and/or runtime profile fields (image,
    ...    customProfile); only supplied fields are changed.
    [Arguments]    ${project}    ${model_name}    ${patch_body}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=    Custom Models Patch Endpoint    ${project}    ${model_name}
    Log    PATCH ${endpoint} body=${patch_body}    DEBUG
    ${response}=    Safe Patch Request    ${endpoint}
    ...    json=${patch_body}
    ...    expected_status=${expected_status}
    Log    Patch model response status: ${response.status_code}    DEBUG
    RETURN    ${response}
