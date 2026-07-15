# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level custom-model preview, onboard, list, and detail testing keywords.
...                 Provides BDD-friendly keywords for exercising
...                 POST /v1/projects/{project}/models/preview,
...                 POST /v1/projects/{project}/models/onboard,
...                 GET /v1/projects/{project}/models, and
...                 GET /v1/projects/{project}/models/{model_name}.
Resource            api/custom_models.resource
Resource            api/models.resource
Resource            resources/airm_projects.resource
Resource            aiwb_secrets.resource
Resource            aiwb_common.resource
Resource            aiwb_aims.resource
Resource            api/cluster.resource
Library             Collections
Library             String
Library             AIMModelHelper


*** Variables ***
# A tiny public repo (weights are kilobytes). Used as the default public repo
# across the whole suite because onboard now kicks off a real
# HuggingFace-to-storage weight import on every call: a multi-GB repo would make
# smoke runs slow and consume significant storage even for tests that only check
# metadata/list/detail behaviour. The import still runs end-to-end in seconds.
${CUSTOM_MODELS_PUBLIC_REPO}         hf-internal-testing/tiny-random-LlamaForCausalLM
${CUSTOM_MODELS_GATED_REPO}          meta-llama/Llama-3.2-1B
# Private repo whose metadata Hub gates behind auth: requests without valid access
# get 401 (which the API surfaces as 403). A gated repo like the one above exposes
# metadata publicly, so it cannot exercise the invalid-token credential path.
${CUSTOM_MODELS_PRIVATE_REPO}        hf-internal-testing/private-model-for-testing
${CUSTOM_MODELS_MISSING_REPO}        aiwb-e2e-nonexistent-org-xyz/no-such-model-zzzzzz
${CUSTOM_MODELS_ONBOARD_IMAGE}       docker.io/amd/tinyllama:1.0.0


*** Keywords ***
A custom model preview is requested for "${source}"
    ${namespace}=    Get Project Namespace
    ${response}=    Preview Custom Model Source    ${namespace}    ${source}
    Set Test Variable    ${TEST_RESPONSE}    ${response}
    IF    ${response.status_code} == 200
        VAR    ${TEST_PREVIEW_JSON}    ${response.json()}    scope=TEST
    END

A custom model preview is requested for "${source}" with secret "${secret_name}"
    ${namespace}=    Get Project Namespace
    ${response}=    Preview Custom Model Source    ${namespace}    ${source}    hf_token_secret_name=${secret_name}
    Set Test Variable    ${TEST_RESPONSE}    ${response}
    IF    ${response.status_code} == 200
        VAR    ${TEST_PREVIEW_JSON}    ${response.json()}    scope=TEST
    END

The previewed custom model is onboarded with image "${image}"
    ${namespace}=    Get Project Namespace
    ${preview_json}=    Get Variable Value    ${TEST_PREVIEW_JSON}    ${None}
    IF    $preview_json is None
        VAR    ${preview_json}    ${TEST_RESPONSE.json()}
    END
    ${response}=    Onboard Custom Model From Preview    ${namespace}    ${preview_json}    ${image}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The previewed custom model is onboarded with image "${image}" and secret "${secret_name}"
    ${namespace}=    Get Project Namespace
    ${preview_json}=    Get Variable Value    ${TEST_PREVIEW_JSON}    ${None}
    IF    $preview_json is None
        VAR    ${preview_json}    ${TEST_RESPONSE.json()}
    END
    ${response}=    Onboard Custom Model From Preview
    ...    ${namespace}
    ...    ${preview_json}
    ...    ${image}
    ...    hf_token_secret_name=${secret_name}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The previewed custom model is onboarded with image "${image}" and runtime profile overrides
    [Documentation]    Onboard the previewed source with the given image and a
    ...    runtime profile overrides block, supplied as ``key=value`` kwargs
    ...    after the call. The dict is forwarded verbatim as the request's
    ...    ``customProfile`` field and lands on
    ...    ``AIMModel.spec.profiles.overrides``.
    [Arguments]    &{custom_profile}
    ${namespace}=    Get Project Namespace
    ${preview_json}=    Get Variable Value    ${TEST_PREVIEW_JSON}    ${None}
    IF    $preview_json is None
        VAR    ${preview_json}    ${TEST_RESPONSE.json()}
    END
    ${response}=    Onboard Custom Model From Preview
    ...    ${namespace}
    ...    ${preview_json}
    ...    ${image}
    ...    custom_profile=${custom_profile}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The previewed custom model is onboarded with image "${image}" overriding display name to "${display_name}"
    [Documentation]    Onboard the previewed source with the given image but replace the
    ...    preview-seeded display name with a user-supplied value, mirroring the wizard's
    ...    information step where users can change the name before submitting.
    ${namespace}=    Get Project Namespace
    ${preview_json}=    Get Variable Value    ${TEST_PREVIEW_JSON}    ${None}
    IF    $preview_json is None
        VAR    ${preview_json}    ${TEST_RESPONSE.json()}
    END
    &{overridden_preview}=    Copy Dictionary    ${preview_json}
    Set To Dictionary    ${overridden_preview}    displayName=${display_name}
    ${response}=    Onboard Custom Model From Preview    ${namespace}    ${overridden_preview}    ${image}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The previewed custom model is onboarded with image "${image}" and a conflicting profile image "${profile_image}"
    [Documentation]    Onboard with a deliberately disagreeing ``image`` and
    ...    ``customProfile.image``. The API must reject the payload at the
    ...    schema boundary so two image refs never land on the emitted profile.
    ${namespace}=    Get Project Namespace
    ${preview_json}=    Get Variable Value    ${TEST_PREVIEW_JSON}    ${None}
    IF    $preview_json is None
        VAR    ${preview_json}    ${TEST_RESPONSE.json()}
    END
    &{conflicting_profile}=    Create Dictionary    image=${profile_image}
    ${response}=    Onboard Custom Model From Preview
    ...    ${namespace}
    ...    ${preview_json}
    ...    ${image}
    ...    custom_profile=${conflicting_profile}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Custom model preview response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

Custom model preview response should explain the credential failure
    [Documentation]    Asserts the 403 response carries a non-empty, human-readable detail
    ...    message so the UI can prompt the user to verify their credentials rather than
    ...    showing a generic error.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    403
    VAR    ${json}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${json}    detail
    ${detail}=    Get From Dictionary    ${json}    detail
    Should Not Be Empty    ${detail}
    ...    msg=403 response must include a non-empty detail message explaining the credential failure

Custom model onboard response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

Copy request is sent for custom model "${model_name}"
    [Documentation]    Sends a copy request for a custom model resource name in
    ...    the current project namespace.
    ${namespace}=    Get Project Namespace
    ${response}=    Copy Custom Model    ${namespace}    ${model_name}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The onboarded custom model is copied for source "${source}"
    [Documentation]    Finds the onboarded model resource by canonical repo id and
    ...    sends a copy request for that model.
    ${namespace}=    Get Project Namespace
    ${list_response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${list_response.json()}    data
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${source}"
            ${name}=    Get From Dictionary    ${model}[metadata]    name
            ${response}=    Copy Custom Model    ${namespace}    ${name}
            Set Test Variable    ${TEST_RESPONSE}    ${response}
            RETURN
        END
    END
    Fail    No onboarded model with canonical-repo-id '${source}' found; cannot copy

Custom model copy response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

Record listed custom model count for source "${expected_repo_id}"
    [Documentation]    Counts list entries matching the canonical repo id and stores
    ...    the value for later comparison within the test.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${models}=    Get From Dictionary    ${json}    data
    VAR    ${count}    ${0}
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${expected_repo_id}"
            ${count}=    Evaluate    ${count} + 1
        END
    END
    VAR    ${TEST_CUSTOM_MODEL_MATCH_COUNT}    ${count}    scope=TEST

Listed custom model count for source "${expected_repo_id}" should increase
    [Documentation]    Verifies the list now contains more entries for the same
    ...    canonical repo id than the previously recorded count.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${models}=    Get From Dictionary    ${json}    data
    VAR    ${count}    ${0}
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${expected_repo_id}"
            ${count}=    Evaluate    ${count} + 1
        END
    END
    Should Be True    ${count} > ${TEST_CUSTOM_MODEL_MATCH_COUNT}
    ...    msg=Expected custom model count for '${expected_repo_id}' to increase (before=${TEST_CUSTOM_MODEL_MATCH_COUNT}, after=${count})

Custom model preview response should describe model "${expected_repo_id}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    Should Be Equal    ${json}[repoId]    ${expected_repo_id}
    Dictionary Should Contain Key    ${json}    revision
    Dictionary Should Contain Key    ${json}    sha
    Should Not Be Empty    ${json}[sha]    msg=Preview response must include a pinnable SHA
    Dictionary Should Contain Key    ${json}    weightFiles
    Dictionary Should Contain Key    ${json}    gated
    Dictionary Should Contain Key    ${json}    hfTokenRecommended
    ${weight_files}=    Get From Dictionary    ${json}    weightFiles
    Should Not Be Empty    ${weight_files}    msg=Preview response should include candidate files
    @{allowed_roles}=    Create List    primary    shard    config
    FOR    ${wf}    IN    @{weight_files}
        Dictionary Should Contain Key    ${wf}    path
        Dictionary Should Contain Key    ${wf}    role
        Dictionary Should Contain Key    ${wf}    sizeBytes
        Should Not Be Empty    ${wf}[path]
        List Should Contain Value    ${allowed_roles}    ${wf}[role]
    END
    VAR    ${selectable_count}    ${0}
    FOR    ${wf}    IN    @{weight_files}
        IF    "${wf}[role]" == "primary" or "${wf}[role]" == "shard"
            ${selectable_count}=    Evaluate    ${selectable_count} + 1
            Should Be True    ${wf}[sizeBytes] > 0
            ...    msg=Selectable weight file ${wf}[path] must have a positive sizeBytes
        END
    END
    Should Be True    ${selectable_count} > 0
    ...    msg=Preview response should include at least one selectable weight file

Custom model preview response revision should be "${expected_revision}"
    VAR    ${json}    ${TEST_RESPONSE.json()}
    Should Be Equal    ${json}[revision]    ${expected_revision}

A Hugging Face token secret "${name}" exists for custom model preview
    A secret "${name}" with use case "HuggingFace" is created via AIWB
    # The preview/onboard API resolves hfTokenSecretName by the secret's Kubernetes
    # resource name (read_namespaced_secret), not its AIWB display name. AIWB generates
    # a distinct k8s name (wb-secret-*) from the displayName, so pass the k8s name here.
    Set Test Variable    ${CUSTOM_MODELS_HF_SECRET_NAME}    ${TEST_AIWB_SECRET_K8S_NAME}

Custom model preview secret cleanup is performed
    Clean Up All Created AIWB Secrets

The project custom model list is retrieved
    ${namespace}=    Get Project Namespace
    ${response}=    List Custom Models    ${namespace}    expected_status=200
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The runtime profile options for the project are retrieved
    ${namespace}=    Get Project Namespace
    ${response}=    Get Runtime Profile Options    ${namespace}    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The discovered cluster base image family is recorded
    [Documentation]    Reads the aim-image catalog and records the non-automatic family
    ...    that cluster discovery selected for this environment.
    ${response}=    List aim image families    expected_status=200
    ${catalog}=    Get From Dictionary    ${response.json()}    data
    VAR    ${family_id}    ${EMPTY}
    FOR    ${family}    IN    @{catalog}
        ${candidate}=    Get From Dictionary    ${family}    familyId
        IF    "${candidate}" != "automatic"
            VAR    ${family_id}    ${candidate}
            BREAK
        END
    END
    Should Not Be Empty    ${family_id}
    ...    msg=No discovered base image family found in /cluster/aim-images response
    VAR    ${TEST_DISCOVERED_BASE_FAMILY_ID}    ${family_id}    scope=TEST

Runtime profile options response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

Runtime profile options response should expose the runtime matrix fields
    [Documentation]    The onboard wizard presets precision/accelerator/count from these
    ...    lists, so every field must be present and list-shaped even when the base model
    ...    has not emitted profiles yet (empty lists, never missing keys).
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    FOR    ${field}    IN    acceleratorModels    precisions    acceleratorCounts    optimizationClasses
        Dictionary Should Contain Key    ${json}    ${field}
        ...    msg=Runtime profile options response is missing '${field}'
        ${value}=    Get From Dictionary    ${json}    ${field}
        Should Be True    isinstance($value, list)
        ...    msg=Runtime profile options field '${field}' must be a list
    END

No custom model has been imported into the project
    [Documentation]    Asserts the project has never gone through the custom-model import flow.
    ...                Used as a regression precondition: a fine-tuned model that becomes
    ...                deployable in such a project proves the base needed for profile
    ...                generation is provisioned at fine-tune launch, not as a side effect
    ...                of a custom import.
    ${namespace}=    Get Project Namespace
    ${response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    Should Be Empty    ${models}
    ...    msg=Project already has imported custom models — regression precondition not met

The custom model list should be empty
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    ${models}=    Get From Dictionary    ${TEST_RESPONSE.json()}    data
    Should Be Empty    ${models}    msg=Expected an empty data array but got ${models}

Custom model list should contain a model from "${expected_repo_id}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${models}=    Get From Dictionary    ${json}    data
    Should Not Be Empty    ${models}    msg=No custom models returned in list
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${expected_repo_id}"
            RETURN
        END
    END
    Fail    No custom model with canonical-repo-id '${expected_repo_id}' found in list response

Listed custom model from "${expected_repo_id}" should include display name and tags
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${models}=    Get From Dictionary    ${json}    data
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${expected_repo_id}"
            ${display_name}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/model-display-name    default=${EMPTY}
            Should Not Be Empty    ${display_name}
            ...    msg=Custom model '${expected_repo_id}' must have a non-empty model-display-name annotation
            ${tags_raw}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/source-tags    default=${EMPTY}
            Should Not Be Equal    ${tags_raw}    ${EMPTY}
            ...    msg=Custom model '${expected_repo_id}' must have a source-tags annotation
            RETURN
        END
    END
    Fail    No custom model with canonical-repo-id '${expected_repo_id}' found in list response

Listed custom model from "${source}" should show display name "${expected_name}"
    [Documentation]    Asserts the display-name annotation on the listed model matches
    ...    the user-provided name supplied at onboard time rather than the preview default.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${models}=    Get From Dictionary    ${json}    data
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${source}"
            ${display_name}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/model-display-name    default=${EMPTY}
            Should Be Equal    ${display_name}    ${expected_name}
            ...    msg=Expected display name '${expected_name}', got '${display_name}' for model '${source}'
            RETURN
        END
    END
    Fail    No custom model with canonical-repo-id '${source}' found in list response

Custom model preview response should signal no authentication is required
    [Documentation]    Asserts the preview response for a public model carries
    ...    ``hfTokenRecommended: false`` so the UI does not prompt for a Hugging Face
    ...    token when importing a model that does not need one.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${json}    hfTokenRecommended
    ${flag}=    Get From Dictionary    ${json}    hfTokenRecommended
    Should Be Equal    ${flag}    ${False}
    ...    msg=Public model preview should report hfTokenRecommended=false; got '${flag}'

Failed weight import error should be present in the model detail
    [Documentation]    After a weight import failure the composed phase must include a
    ...    non-empty ``artifactLastError`` string so the UI can display the failure
    ...    reason rather than just showing a generic "Failed" state to the user.
    ${namespace}=    Get Project Namespace
    ${response}=    Get Custom Model    ${namespace}    ${TEST_CUSTOM_MODEL_NAME}    expected_status=200
    VAR    ${json}    ${response.json()}
    ${phase}=    Get From Dictionary    ${json}    phase
    ${last_error}=    Get From Dictionary    ${phase}    artifactLastError    default=${EMPTY}
    Should Not Be Empty    ${last_error}
    ...    msg=Failed weight import must populate artifactLastError so the UI can explain the failure

Custom AIMModel for source "${expected_repo_id}" should exist in the namespace
    [Documentation]    Finds the custom-onboarded AIMModel CR by its canonical-repo-id annotation
    ...    and stores it in ${CUSTOM_MODEL_AIM_CR} for subsequent spec assertions.
    ...    Uses the custom-models list endpoint (GET /projects/{ns}/models) which only
    ...    returns custom-imported models, not fine-tuned ones.
    ${namespace}=    Get Project Namespace
    ${response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    Should Not Be Empty    ${models}    msg=No custom AIMModel CRs found in namespace ${namespace}
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${expected_repo_id}"
            Set Test Variable    ${CUSTOM_MODEL_AIM_CR}    ${model}
            RETURN
        END
    END
    Fail    No custom AIMModel CR with canonical-repo-id '${expected_repo_id}' found in namespace ${namespace}

Exactly one custom AIMModel for source "${expected_repo_id}" should exist in the namespace
    [Documentation]    Asserts the namespace contains exactly one custom-onboarded AIMModel CR
    ...    for the given canonical repo id — the idempotency guarantee for repeated onboard calls.
    ...    Uses the canonical-repo-id annotation, which is the stable identity for custom imports.
    ${namespace}=    Get Project Namespace
    ${response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    ${matches}=    Create List
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${expected_repo_id}"
            Append To List    ${matches}    ${model}
        END
    END
    ${count}=    Get Length    ${matches}
    Should Be Equal As Integers    ${count}    1
    ...    msg=Expected exactly one AIMModel for source '${expected_repo_id}', found ${count}

Custom AIMModel for source "${expected_repo_id}" should wire HF token secret "${expected_secret_name}"
    [Documentation]    Asserts the AIMModel CR wires the HF token secret into the
    ...    first model source's env as an HF_TOKEN secretKeyRef. This is the v1alpha2
    ...    behavioral guarantee that gated/private models get their token plumbed by
    ...    aim-engine. Token wiring lives at spec.profiles.overrides.modelSources[0].env,
    ...    not the legacy top-level spec.env which is empty for custom onboarded models.
    Custom AIMModel for source "${expected_repo_id}" should exist in the namespace
    ${spec}=    Get From Dictionary    ${CUSTOM_MODEL_AIM_CR}    spec
    ${profiles}=    Get From Dictionary    ${spec}    profiles    default=&{EMPTY}
    Should Not Be Empty    ${profiles}    msg=AIMModel has no spec.profiles; HF_TOKEN wiring not present
    ${overrides}=    Get From Dictionary    ${profiles}    overrides    default=&{EMPTY}
    Should Not Be Empty    ${overrides}    msg=AIMModel has no spec.profiles.overrides; HF_TOKEN wiring not present
    ${sources}=    Get From Dictionary    ${overrides}    modelSources    default=${EMPTY}
    Should Not Be Empty    ${sources}    msg=AIMModel has no spec.profiles.overrides.modelSources; HF_TOKEN wiring not present
    ${first_source}=    Get From List    ${sources}    0
    ${env}=    Get From Dictionary    ${first_source}    env    default=${EMPTY}
    Should Not Be Empty    ${env}    msg=First model source has no env entries; HF_TOKEN not wired
    VAR    ${hf_token_entry}    ${None}
    FOR    ${entry}    IN    @{env}
        ${name}=    Get From Dictionary    ${entry}    name    default=${EMPTY}
        IF    "${name}" == "HF_TOKEN"
            VAR    ${hf_token_entry}    ${entry}
            BREAK
        END
    END
    Should Not Be Equal    ${hf_token_entry}    ${None}
    ...    msg=No HF_TOKEN entry in spec.profiles.overrides.modelSources[0].env
    ${value_from}=    Get From Dictionary    ${hf_token_entry}    valueFrom
    ${secret_ref}=    Get From Dictionary    ${value_from}    secretKeyRef
    Should Be Equal    ${secret_ref}[name]    ${expected_secret_name}
    Should Be Equal    ${secret_ref}[key]    token

Custom AIMModel for source "${expected_repo_id}" should use image "${expected_image}"
    [Documentation]    Asserts the AIMModel CR's container image matches the expected value.
    ...    v1alpha2 CRs store the image at spec.profiles.overrides.image, not the
    ...    legacy top-level spec.image which is always empty for custom onboarded models.
    Custom AIMModel for source "${expected_repo_id}" should exist in the namespace
    ${spec}=    Get From Dictionary    ${CUSTOM_MODEL_AIM_CR}    spec
    ${profiles}=    Get From Dictionary    ${spec}    profiles    default=&{EMPTY}
    Should Not Be Empty    ${profiles}    msg=AIMModel has no spec.profiles; image override not present
    ${overrides}=    Get From Dictionary    ${profiles}    overrides    default=&{EMPTY}
    Should Not Be Empty    ${overrides}    msg=AIMModel has no spec.profiles.overrides; image override not present
    ${image}=    Get From Dictionary    ${overrides}    image
    Should Be Equal    ${image}    ${expected_image}

Custom AIMModel for source "${expected_repo_id}" should derive from discovered base family
    [Documentation]    Asserts ``spec.profiles.derivedFrom.selector.modelRef.name`` matches
    ...    the family id discovered from ``/cluster/aim-images``.
    Should Not Be Empty    ${TEST_DISCOVERED_BASE_FAMILY_ID}
    ...    msg=No discovered base family recorded; call "The discovered cluster base image family is recorded" first
    Custom AIMModel for source "${expected_repo_id}" should exist in the namespace
    ${spec}=    Get From Dictionary    ${CUSTOM_MODEL_AIM_CR}    spec
    ${profiles}=    Get From Dictionary    ${spec}    profiles    default=&{EMPTY}
    ${derived_from}=    Get From Dictionary    ${profiles}    derivedFrom    default=&{EMPTY}
    ${selector}=    Get From Dictionary    ${derived_from}    selector    default=&{EMPTY}
    ${model_ref}=    Get From Dictionary    ${selector}    modelRef    default=&{EMPTY}
    ${model_name}=    Get From Dictionary    ${model_ref}    name    default=${EMPTY}
    Should Be Equal    ${model_name}    ${TEST_DISCOVERED_BASE_FAMILY_ID}
    ...    msg=Custom model should derive from discovered base family '${TEST_DISCOVERED_BASE_FAMILY_ID}', got '${model_name}'

Custom AIMModel for source "${expected_repo_id}" should carry profile override "${field}" with value "${expected_value}"
    [Documentation]    Asserts that at least one custom AIMModel CR for the source
    ...    has the given field in ``spec.profiles.overrides``. Searches all matching
    ...    models because a namespace may hold both an original and copies; only the
    ...    onboarded original carries the customProfile overrides.
    ${namespace}=    Get Project Namespace
    ${response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" != "${expected_repo_id}"    CONTINUE
        ${spec}=    Get From Dictionary    ${model}    spec
        ${profiles}=    Get From Dictionary    ${spec}    profiles    default=&{EMPTY}
        IF    not ${profiles}    CONTINUE
        ${overrides}=    Get From Dictionary    ${profiles}    overrides    default=&{EMPTY}
        IF    not ${overrides}    CONTINUE
        ${has_field}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${overrides}    ${field}
        IF    not ${has_field}    CONTINUE
        Should Be Equal As Strings    ${overrides}[${field}]    ${expected_value}
        ...    msg=Profile override '${field}' has unexpected value '${overrides}[${field}]' (expected '${expected_value}')
        Set Test Variable    ${CUSTOM_MODEL_AIM_CR}    ${model}
        RETURN
    END
    Fail    No custom AIMModel with canonical-repo-id '${expected_repo_id}' has profile override '${field}' == '${expected_value}' in namespace ${namespace}

The onboarded custom model detail is retrieved for "${source}"
    [Documentation]    Locate the onboarded model by source repo id in the list,
    ...    then fetch its detail by name via GET /projects/{project}/models/{model_name}.
    ${namespace}=    Get Project Namespace
    ${list_response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${list_response.json()}    data
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        IF    "${canonical}" == "${source}"
            ${name}=    Get From Dictionary    ${model}[metadata]    name
            ${response}=    Get Custom Model    ${namespace}    ${name}    expected_status=200
            Set Test Variable    ${TEST_RESPONSE}    ${response}
            RETURN
        END
    END
    Fail    No onboarded model with canonical-repo-id '${source}' found; cannot fetch detail

Requesting a non-existent custom model returns not-found
    ${namespace}=    Get Project Namespace
    ${response}=    Get Custom Model    ${namespace}    no-such-model-zzz    expected_status=404
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The custom model detail is requested for model "${model_name}"
    ${namespace}=    Get Project Namespace
    ${response}=    Get Custom Model    ${namespace}    ${model_name}    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Custom model detail response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

Custom model detail should match the onboarded source "${expected_repo_id}"
    [Documentation]    Verify the detail response describes the expected model:
    ...    correct metadata name, spec, and composed lifecycle phase present,
    ...    with the canonical-repo-id annotation matching the expected source.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${json}    metadata
    Dictionary Should Contain Key    ${json}    spec
    Dictionary Should Contain Key    ${json}    phase
    ${annotations}=    Get From Dictionary    ${json}[metadata]    annotations    default=&{EMPTY}
    ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
    Should Be Equal    ${canonical}    ${expected_repo_id}
    ...    msg=Detail response canonical-repo-id annotation does not match expected repo id

Custom model detail should include onboarding status fields
    [Documentation]    Verify that the composed lifecycle phase is present and structurally
    ...    correct: state, templateReady, artifactPhase, and artifactLastError
    ...    must all be present so the UI can render the onboarding state.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${phase}=    Get From Dictionary    ${json}    phase
    Dictionary Should Contain Key    ${phase}    state
    Dictionary Should Contain Key    ${phase}    templateReady
    Dictionary Should Contain Key    ${phase}    artifactPhase
    Dictionary Should Contain Key    ${phase}    artifactLastError
    ${valid_states}=    Create List    Pending    Importing    Ready    Failed
    List Should Contain Value    ${valid_states}    ${phase}[state]
    ...    msg=Onboard phase state '${phase}[state]' is not a recognised value

Listed custom models include onboarding status fields
    [Documentation]    Verify every item in the list response carries the composed lifecycle
    ...    phase: state, templateReady, artifactPhase, and artifactLastError
    ...    must all be present so the UI can render per-model onboarding state without
    ...    issuing a separate detail request.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${models}=    Get From Dictionary    ${json}    data
    Should Not Be Empty    ${models}    msg=No custom models returned in list
    ${valid_states}=    Create List    Pending    Importing    Ready    Failed
    FOR    ${model}    IN    @{models}
        ${phase}=    Get From Dictionary    ${model}    phase
        Dictionary Should Contain Key    ${phase}    state
        Dictionary Should Contain Key    ${phase}    templateReady
        Dictionary Should Contain Key    ${phase}    artifactPhase
        Dictionary Should Contain Key    ${phase}    artifactLastError
        List Should Contain Value    ${valid_states}    ${phase}[state]
        ...    msg=Onboard phase state '${phase}[state]' is not a recognised value
    END

A custom model is onboarded in the project
    [Documentation]    Previews and onboards the public test repo (a tiny repo, so the
    ...    weight import onboard triggers runs in seconds), then resolves the AIMModel
    ...    CR name into ${TEST_CUSTOM_MODEL_NAME} for subsequent PATCH and DELETE steps.
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    And custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should exist in the namespace
    ${metadata}=    Get From Dictionary    ${CUSTOM_MODEL_AIM_CR}    metadata
    ${model_name}=    Get From Dictionary    ${metadata}    name
    Set Test Variable    ${TEST_CUSTOM_MODEL_NAME}    ${model_name}
    ${namespace}=    Get Project Namespace
    Track Custom Model For Cleanup    ${namespace}    ${model_name}

The weight import for source "${repo}" should complete within "${timeout}"
    [Documentation]    Polls the model detail endpoint until the composed onboarding
    ...    status reports the weight import finished (artifactPhase == Ready). This is
    ...    the API-level observable that the HuggingFace weights were imported into the
    ...    model's storage prefix, not merely that the sourceUri was recorded.
    Wait Until Keyword Succeeds    ${timeout}    5 sec
    ...    Custom model weight import for "${repo}" should be Ready

Custom model weight import for "${repo}" should be Ready
    The onboarded custom model detail is retrieved for "${repo}"
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${phase}=    Get From Dictionary    ${json}    phase
    ${artifact_phase}=    Get From Dictionary    ${phase}    artifactPhase    default=${EMPTY}
    ${last_error}=    Get From Dictionary    ${phase}    artifactLastError    default=${EMPTY}
    Should Be Equal    ${artifact_phase}    Ready
    ...    msg=Weight import not complete yet (artifactPhase='${artifact_phase}', lastError='${last_error}')

The user updates the model display name to "${display_name}"
    ${namespace}=    Get Project Namespace
    &{body}=    Create Dictionary    displayName=${display_name}
    ${response}=    Patch Onboarded Model
    ...    ${namespace}
    ...    ${TEST_CUSTOM_MODEL_NAME}
    ...    ${body}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The user updates the model tags to "${tags_csv}"
    ${namespace}=    Get Project Namespace
    ${tags}=    Split String    ${tags_csv}    ,
    ${body}=    Create Dictionary    tags=${tags}
    ${response}=    Patch Onboarded Model
    ...    ${namespace}
    ...    ${TEST_CUSTOM_MODEL_NAME}
    ...    ${body}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The user updates the model display name to "${display_name}" and description to "${description}"
    [Documentation]    PATCH the onboarded model with both displayName and description
    ...    in a single request, mirroring the edit wizard saving the information step.
    ${namespace}=    Get Project Namespace
    &{body}=    Create Dictionary    displayName=${display_name}    description=${description}
    ${response}=    Patch Onboarded Model
    ...    ${namespace}
    ...    ${TEST_CUSTOM_MODEL_NAME}
    ...    ${body}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The user updates the model description to "${description}"
    ${namespace}=    Get Project Namespace
    &{body}=    Create Dictionary    description=${description}
    ${response}=    Patch Onboarded Model
    ...    ${namespace}
    ...    ${TEST_CUSTOM_MODEL_NAME}
    ...    ${body}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The user clears the model description
    [Documentation]    PATCH with ``description: ""`` — the empty string signals a
    ...    deliberate clear rather than an omitted field (which would leave the value
    ...    unchanged).
    ${namespace}=    Get Project Namespace
    &{body}=    Create Dictionary    description=${EMPTY}
    ${response}=    Patch Onboarded Model
    ...    ${namespace}
    ...    ${TEST_CUSTOM_MODEL_NAME}
    ...    ${body}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The user edits the model runtime profile with conflicting image references
    [Documentation]    PATCH the onboarded model with a top-level image and a
    ...    customProfile.image that disagree. The request must be rejected at the
    ...    schema boundary (before any AIMProfile lookup), so two image refs never
    ...    reach the emitted profile.
    ${namespace}=    Get Project Namespace
    &{custom_profile}=    Create Dictionary    image=docker.io/other/image:v9
    &{body}=    Create Dictionary
    ...    image=${CUSTOM_MODELS_ONBOARD_IMAGE}
    ...    customProfile=${custom_profile}
    ${response}=    Patch Onboarded Model
    ...    ${namespace}
    ...    ${TEST_CUSTOM_MODEL_NAME}
    ...    ${body}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

The runtime profile edit response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

The user sets two engine arguments and two environment variables on the model
    [Documentation]    Edit the runtime profile so both the engine-arguments and the
    ...    environment-variable maps carry two key/value pairs, establishing the
    ...    multi-key starting point for the later removal check.
    VAR    ${TEST_KEPT_ARG_KEY}    max-model-len    scope=TEST
    VAR    ${TEST_REMOVED_ARG_KEY}    attention-backend    scope=TEST
    VAR    ${TEST_KEPT_ENV_KEY}    VLLM_ROCM_USE_AITER    scope=TEST
    VAR    ${TEST_REMOVED_ENV_KEY}    VLLM_USE_TRITON_FLASH_ATTN    scope=TEST
    &{engine_args}=    Create Dictionary    ${TEST_KEPT_ARG_KEY}=8192    ${TEST_REMOVED_ARG_KEY}=TRITON_ATTN
    @{engine_env}=    Create List
    ...    ${{ {'name': $TEST_KEPT_ENV_KEY, 'value': '1'} }}
    ...    ${{ {'name': $TEST_REMOVED_ENV_KEY, 'value': '1'} }}
    The user edits the model runtime profile maps    ${engine_args}    ${engine_env}

The user removes one engine argument and one environment variable
    [Documentation]    Re-edit the runtime profile keeping only one pair in each map,
    ...    dropping the other; the dropped keys are simply absent from the new maps.
    &{engine_args}=    Create Dictionary    ${TEST_KEPT_ARG_KEY}=8192
    @{engine_env}=    Create List    ${{ {'name': $TEST_KEPT_ENV_KEY, 'value': '1'} }}
    The user edits the model runtime profile maps    ${engine_args}    ${engine_env}

The user edits the model runtime profile maps
    [Documentation]    PATCH the onboarded model with the given engineArgs map and
    ...    engineEnv name/value entries, mirroring the edit wizard's customProfile body.
    [Arguments]    ${engine_args}    ${engine_env}
    ${namespace}=    Get Project Namespace
    &{custom_profile}=    Create Dictionary    engineArgs=${engine_args}    engineEnv=${engine_env}
    &{body}=    Create Dictionary    customProfile=${custom_profile}
    ${response}=    Patch Onboarded Model    ${namespace}    ${TEST_CUSTOM_MODEL_NAME}    ${body}
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    ...    msg=Runtime profile edit failed: ${TEST_RESPONSE.status_code} ${TEST_RESPONSE.text}

The model runtime profile should carry both engine arguments and both environment variables
    ${overrides}=    Get onboarded model overrides
    ${args}=    Get From Dictionary    ${overrides}    engineArgs    default=&{EMPTY}
    Dictionary Should Contain Key    ${args}    ${TEST_KEPT_ARG_KEY}
    Dictionary Should Contain Key    ${args}    ${TEST_REMOVED_ARG_KEY}
    ${env}=    Get From Dictionary    ${overrides}    engineEnv    default=&{EMPTY}
    Dictionary Should Contain Key    ${env}    ${TEST_KEPT_ENV_KEY}
    Dictionary Should Contain Key    ${env}    ${TEST_REMOVED_ENV_KEY}

The model runtime profile should retain only the kept engine argument and environment variable
    [Documentation]    The dropped keys must be gone from the live AIMModel overrides;
    ...    the kept keys must remain. Polled because the edit writes the CR and the
    ...    derived AIMProfile under one lock before the read sees the result.
    Wait Until Keyword Succeeds    30 sec    5 sec
    ...    Onboarded model overrides should drop the removed runtime keys

Onboarded model overrides should drop the removed runtime keys
    ${overrides}=    Get onboarded model overrides
    ${args}=    Get From Dictionary    ${overrides}    engineArgs    default=&{EMPTY}
    Dictionary Should Contain Key    ${args}    ${TEST_KEPT_ARG_KEY}
    Dictionary Should Not Contain Key    ${args}    ${TEST_REMOVED_ARG_KEY}
    ...    msg=Removed engine argument '${TEST_REMOVED_ARG_KEY}' still present after edit
    ${env}=    Get From Dictionary    ${overrides}    engineEnv    default=&{EMPTY}
    Dictionary Should Contain Key    ${env}    ${TEST_KEPT_ENV_KEY}
    Dictionary Should Not Contain Key    ${env}    ${TEST_REMOVED_ENV_KEY}
    ...    msg=Removed environment variable '${TEST_REMOVED_ENV_KEY}' still present after edit

Get onboarded model overrides
    [Documentation]    Resolve the onboarded AIMModel CR fresh from the cluster and
    ...    return its ``spec.profiles.overrides`` block (camelCase keys).
    Custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should exist in the namespace
    ${spec}=    Get From Dictionary    ${CUSTOM_MODEL_AIM_CR}    spec
    ${profiles}=    Get From Dictionary    ${spec}    profiles    default=&{EMPTY}
    ${overrides}=    Get From Dictionary    ${profiles}    overrides    default=&{EMPTY}
    RETURN    ${overrides}

A custom model is onboarded with a non-default runtime profile
    [Documentation]    Preview and onboard the public test repo with a non-default
    ...    ``customProfile`` (precision plus one engine argument and one engine env var)
    ...    layered on the onboard image, then resolve the AIMModel name for later steps.
    ...    The overrides land on ``AIMModel.spec.profiles.overrides``; aim-engine bakes
    ...    them into the emitted AIMProfile. The chosen values are remembered in
    ...    ``TEST_PROFILE_*`` so the round-trip can assert them on the live pod.
    ...    Sets: TEST_CUSTOM_MODEL_NAME, TEST_PROFILE_*.
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    VAR    ${TEST_PROFILE_PRECISION}    fp16    scope=TEST
    VAR    ${TEST_PROFILE_ENGINE_ARG_KEY}    max-model-len    scope=TEST
    VAR    ${TEST_PROFILE_ENGINE_ARG_VALUE}    8192    scope=TEST
    VAR    ${TEST_PROFILE_ENGINE_ENV_KEY}    VLLM_LOGGING_LEVEL    scope=TEST
    VAR    ${TEST_PROFILE_ENGINE_ENV_VALUE}    DEBUG    scope=TEST
    &{engine_args}=    Create Dictionary    ${TEST_PROFILE_ENGINE_ARG_KEY}=${TEST_PROFILE_ENGINE_ARG_VALUE}
    @{engine_env}=    Create List    ${{ {'name': $TEST_PROFILE_ENGINE_ENV_KEY, 'value': $TEST_PROFILE_ENGINE_ENV_VALUE} }}
    &{custom_profile}=    Create Dictionary
    ...    precision=${TEST_PROFILE_PRECISION}
    ...    engineArgs=${engine_args}
    ...    engineEnv=${engine_env}
    ${namespace}=    Get Project Namespace
    ${preview_json}=    Get Variable Value    ${TEST_PREVIEW_JSON}    ${None}
    IF    $preview_json is None
        VAR    ${preview_json}    ${TEST_RESPONSE.json()}
    END
    ${response}=    Onboard Custom Model From Preview
    ...    ${namespace}
    ...    ${preview_json}
    ...    ${CUSTOM_MODELS_ONBOARD_IMAGE}
    ...    custom_profile=${custom_profile}
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    204
    ...    msg=Onboard with runtime profile failed: ${TEST_RESPONSE.status_code} ${TEST_RESPONSE.text}
    Custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should exist in the namespace
    ${metadata}=    Get From Dictionary    ${CUSTOM_MODEL_AIM_CR}    metadata
    ${model_name}=    Get From Dictionary    ${metadata}    name
    Set Test Variable    ${TEST_CUSTOM_MODEL_NAME}    ${model_name}
    ${namespace}=    Get Project Namespace
    Track Custom Model For Cleanup    ${namespace}    ${model_name}

The user revises the model's engine settings
    [Documentation]    Edit the runtime profile after onboard, changing the engine
    ...    argument value and the engine env value, so the round-trip proves the
    ...    *edited* values — not just the onboard values — reach the running pod.
    ...    Requires: TEST_CUSTOM_MODEL_NAME, TEST_PROFILE_* (from onboard).
    VAR    ${TEST_PROFILE_ENGINE_ARG_VALUE}    4096    scope=TEST
    VAR    ${TEST_PROFILE_ENGINE_ENV_VALUE}    INFO    scope=TEST
    &{engine_args}=    Create Dictionary    ${TEST_PROFILE_ENGINE_ARG_KEY}=${TEST_PROFILE_ENGINE_ARG_VALUE}
    @{engine_env}=    Create List    ${{ {'name': $TEST_PROFILE_ENGINE_ENV_KEY, 'value': $TEST_PROFILE_ENGINE_ENV_VALUE} }}
    The user edits the model runtime profile maps    ${engine_args}    ${engine_env}

The model runtime profile should carry the revised engine settings
    [Documentation]    The edited engine argument and env values are visible on the live
    ...    AIMModel overrides. Polled because the edit writes the CR and the derived
    ...    AIMProfile under one lock before the read sees the result.
    Wait Until Keyword Succeeds    30 sec    5 sec
    ...    Onboarded model overrides should carry the revised engine settings

Onboarded model overrides should carry the revised engine settings
    ${overrides}=    Get onboarded model overrides
    ${args}=    Get From Dictionary    ${overrides}    engineArgs    default=&{EMPTY}
    Should Be Equal As Strings    ${args}[${TEST_PROFILE_ENGINE_ARG_KEY}]    ${TEST_PROFILE_ENGINE_ARG_VALUE}
    ...    msg=Edited engine argument not persisted on the model overrides
    ${env}=    Get From Dictionary    ${overrides}    engineEnv    default=&{EMPTY}
    Should Be Equal As Strings    ${env}[${TEST_PROFILE_ENGINE_ENV_KEY}]    ${TEST_PROFILE_ENGINE_ENV_VALUE}
    ...    msg=Edited engine env var not persisted on the model overrides

The running inference pod should reflect the model's runtime profile
    [Documentation]    Assert the live inference pod actually runs the onboarded and edited
    ...    runtime profile: the onboard image, the accelerator product and count the derived
    ...    AIMProfile resolved to, and the edited engine argument and env var. The accelerator
    ...    expectations are read from the derived AIMProfile rather than hardcoded, so the
    ...    assertion holds on whatever hardware aim-engine selected for the model.
    ...    Requires: TEST_AIM_ID, TEST_CUSTOM_MODEL_NAME, TEST_PROFILE_*.
    ${namespace}=    Get Project Namespace
    ${profile_spec}=    Get AIMProfile Spec For Model    ${TEST_CUSTOM_MODEL_NAME}    ${namespace}
    ${accelerator_count}=    Get From Dictionary    ${profile_spec}    acceleratorCount
    ${accelerator_product}=    Get From Dictionary    ${profile_spec}    acceleratorModel
    The running inference pod should use image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    The running inference pod should request ${accelerator_count} accelerators
    The running inference pod should run on "${accelerator_product}" accelerators
    The running inference pod should expose env "${TEST_PROFILE_ENGINE_ENV_KEY}" set to "${TEST_PROFILE_ENGINE_ENV_VALUE}"
    The running inference pod should run with engine argument "${TEST_PROFILE_ENGINE_ARG_VALUE}"

The model should show display name "${display_name}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    Should Be Equal    ${json}[displayName]    ${display_name}

The model should show tags "${tags_csv}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${expected_tags}=    Split String    ${tags_csv}    ,
    Should Be Equal    ${json}[tags]    ${expected_tags}

The model should show description "${description}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    Should Be Equal    ${json}[description]    ${description}

Model description should be empty
    [Documentation]    Asserts the PATCH response carries an empty description,
    ...    confirming the empty-string clear semantic worked.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    VAR    ${json}    ${TEST_RESPONSE.json()}
    ${description}=    Get From Dictionary    ${json}    description    default=${EMPTY}
    Should Be Empty    ${description}
    ...    msg=PATCH with empty description must clear the field; got '${description}'

The model patch response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

A copy of the onboarded custom model is created in the project
    [Documentation]    Calls the copy API for the onboarded model then walks the
    ...    namespace model list to resolve the new copy's CR name into
    ...    ${TEST_COPY_MODEL_NAME}. The copy endpoint is synchronous, so the copy
    ...    is immediately visible in the list after a 204 response.
    ${namespace}=    Get Project Namespace
    ${copy_response}=    Copy Custom Model    ${namespace}    ${TEST_CUSTOM_MODEL_NAME}
    ${list_response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${list_response.json()}    data
    FOR    ${model}    IN    @{models}
        ${name}=    Get From Dictionary    ${model}[metadata]    name
        IF    "${name}" != "${TEST_CUSTOM_MODEL_NAME}"
            VAR    ${TEST_COPY_MODEL_NAME}    ${name}    scope=TEST
        END
    END
    Should Not Be Empty    ${TEST_COPY_MODEL_NAME}
    ...    msg=Copy model CR not found in list after copy (original=${TEST_CUSTOM_MODEL_NAME}, copy_status=${copy_response.status_code})
    Track Custom Model For Cleanup    ${namespace}    ${TEST_COPY_MODEL_NAME}

The user attempts to rename the copy to "${display_name}"
    [Documentation]    PATCH the copied model's display name. Used to trigger a
    ...    conflict when the target name is already held by the original.
    ${namespace}=    Get Project Namespace
    &{body}=    Create Dictionary    displayName=${display_name}
    ${response}=    Patch Onboarded Model
    ...    ${namespace}
    ...    ${TEST_COPY_MODEL_NAME}
    ...    ${body}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

An AIMService referencing the onboarded model exists
    [Documentation]    Apply a minimal AIMService CR pointing at the onboarded model so
    ...    the delete guard has an active deployment to block on.
    ${namespace}=    Get Project Namespace
    VAR    ${service_name}    blocking-svc-${TEST_CUSTOM_MODEL_NAME}
    Apply AIMService Referencing Model    ${service_name}    ${TEST_CUSTOM_MODEL_NAME}    ${namespace}
    Set Test Variable    ${TEST_BLOCKING_AIM_SERVICE}    ${service_name}

Remove blocking AIMService if present
    [Documentation]    Teardown helper for the delete-conflict test: removes the AIMService CR
    ...    that pins the model behind the 409 delete guard. Without it the model cannot be
    ...    cleaned up and stays in the namespace, polluting every subsequent test. Tolerant of
    ...    a test that failed before the service was created.
    ${service}=    Get Variable Value    ${TEST_BLOCKING_AIM_SERVICE}    ${None}
    IF    $service is None
        RETURN
    END
    ${namespace}=    Get Project Namespace
    Delete AIMService CR    ${service}    ${namespace}

An AIMProfile for the onboarded model exists
    [Documentation]    Wait for aim-engine to derive an AIMProfile from the onboarded
    ...    AIMModel, so the cascade-cleanup assertion after delete is meaningful.
    ${namespace}=    Get Project Namespace
    Wait Until Keyword Succeeds    3 min    10 sec
    ...    AIMProfile For Model Should Exist    ${TEST_CUSTOM_MODEL_NAME}    ${namespace}

The user deletes the onboarded model
    ${namespace}=    Get Project Namespace
    ${response}=    Delete Custom Model    ${namespace}    ${TEST_CUSTOM_MODEL_NAME}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Track Custom Model For Cleanup
    [Documentation]    Records a custom model for explicit cleanup at suite teardown.
    ...    Uses lazy initialisation — the tracking list is created on first call.
    ...    The entry format is ``namespace:::name`` so both pieces travel together.
    [Arguments]    ${namespace}    ${model_name}
    ${list}=    Get Variable Value    ${CREATED_CUSTOM_MODELS}    ${None}
    IF    $list is None
        @{list}=    Create List
        Set Suite Variable    @{CREATED_CUSTOM_MODELS}    @{list}
    END
    Append To List    ${CREATED_CUSTOM_MODELS}    ${namespace}:::${model_name}

Clean Up All Created Custom Models
    [Documentation]    Deletes every custom model tracked during the suite.
    ...    Call this before ``Clean Up All Created Projects`` so models are removed
    ...    explicitly rather than relying solely on namespace cascade — the cascade
    ...    still acts as a final safety net.
    ...    Tolerant of already-deleted or never-created models.
    ${list}=    Get Variable Value    ${CREATED_CUSTOM_MODELS}    ${None}
    IF    $list is None
        Log    No custom models tracked for cleanup    DEBUG
        RETURN
    END
    ${count}=    Get Length    ${list}
    IF    ${count} == 0
        Log    No custom models tracked for cleanup    DEBUG
        RETURN
    END
    Log    Cleaning up ${count} custom model(s)    INFO
    FOR    ${entry}    IN    @{list}
        ${parts}=    Split String    ${entry}    :::
        ${namespace}=    Set Variable    ${parts}[0]
        ${model_name}=    Set Variable    ${parts}[1]
        TRY
            Delete Custom Model    ${namespace}    ${model_name}    expected_status=any
            Log    Requested delete of custom model ${model_name} from ${namespace}    DEBUG
        EXCEPT    AS    ${err}
            Log    Could not delete custom model ${model_name} (${namespace}): ${err}    WARN
        END
    END
    # AIMModel deletion is asynchronous: the API returns immediately but a finalizer
    # holds the CR in Terminating while object storage is cleaned. As a per-test
    # teardown this keyword must leave the namespace empty for the next test, so wait
    # for each CR to actually disappear rather than only requesting the delete.
    FOR    ${entry}    IN    @{list}
        ${parts}=    Split String    ${entry}    :::
        ${namespace}=    Set Variable    ${parts}[0]
        ${model_name}=    Set Variable    ${parts}[1]
        TRY
            Wait Until Keyword Succeeds    90 sec    5 sec
            ...    AIMModel CR Should Be Absent    ${model_name}    ${namespace}
        EXCEPT    AS    ${err}
            Log    Custom model ${model_name} (${namespace}) still present after delete: ${err}    WARN
        END
    END
    @{empty}=    Create List
    Set Suite Variable    ${CREATED_CUSTOM_MODELS}    ${empty}
    Log    Custom model cleanup complete    INFO

Reset Custom Models In Test Project
    [Documentation]    Per-test teardown that leaves the project namespace free of custom
    ...    models so the next test starts from a clean slate, keeping the suite order
    ...    independent. The tracking-based cleanup covers models a test created in a
    ...    secondary project; the namespace sweep covers models onboarded through the raw
    ...    preview→onboard flow, which the tracking list does not capture. Tolerant of a
    ...    test that never established a project.
    Clean Up All Created Custom Models
    TRY
        ${namespace}=    Get Project Namespace
    EXCEPT    AS    ${err}
        Log    No project namespace to sweep for custom models: ${err}    DEBUG
        RETURN
    END
    ${response}=    List Custom Models    ${namespace}    expected_status=any
    IF    ${response.status_code} != 200
        RETURN
    END
    ${models}=    Get From Dictionary    ${response.json()}    data
    @{names}=    Create List
    FOR    ${model}    IN    @{models}
        ${name}=    Get From Dictionary    ${model}[metadata]    name
        Delete Custom Model    ${namespace}    ${name}    expected_status=any
        Append To List    ${names}    ${name}
    END
    FOR    ${name}    IN    @{names}
        TRY
            Wait Until Keyword Succeeds    90 sec    5 sec
            ...    AIMModel CR Should Be Absent    ${name}    ${namespace}
        EXCEPT    AS    ${err}
            Log    Custom model ${name} (${namespace}) still present after delete: ${err}    WARN
        END
    END

The user attempts to delete custom model "${model_name}"
    ${namespace}=    Get Project Namespace
    ${response}=    Delete Custom Model    ${namespace}    ${model_name}
    Set Test Variable    ${TEST_RESPONSE}    ${response}

Custom model delete response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

The onboarded AIMModel should no longer exist in the namespace
    ${namespace}=    Get Project Namespace
    Wait Until Keyword Succeeds    60 sec    5 sec
    ...    AIMModel CR Should Be Absent    ${TEST_CUSTOM_MODEL_NAME}    ${namespace}

The onboarded model should no longer appear in the project model list
    [Documentation]    The list endpoint is the API-level observable that both the CR and
    ...    its S3 manifest mirror are gone; a deleted model must not be listed.
    ${namespace}=    Get Project Namespace
    ${response}=    List Custom Models    ${namespace}    expected_status=200
    ${models}=    Get From Dictionary    ${response.json()}    data
    FOR    ${model}    IN    @{models}
        ${name}=    Get From Dictionary    ${model}[metadata]    name
        Should Not Be Equal    ${name}    ${TEST_CUSTOM_MODEL_NAME}
        ...    msg=Deleted model ${TEST_CUSTOM_MODEL_NAME} still appears in the project model list
    END

The derived AIMProfile should no longer exist in the namespace
    ${namespace}=    Get Project Namespace
    Wait Until Keyword Succeeds    2 min    5 sec
    ...    AIMProfile For Model Should Be Absent    ${TEST_CUSTOM_MODEL_NAME}    ${namespace}

The delete conflict response should name the blocking AIMService
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    409
    ${detail}=    Get From Dictionary    ${TEST_RESPONSE.json()}    detail
    Should Contain    ${detail}    ${TEST_BLOCKING_AIM_SERVICE}
    ...    msg=409 conflict detail should name the blocking AIMService

The onboarded AIMModel should still exist in the namespace
    Custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should exist in the namespace

Custom model onboarding status should be "${target_status}"
    [Documentation]    Polls custom model detail until phase.state reaches the target.
    ...    Requires: TEST_CUSTOM_MODEL_NAME.
    Should Not Be Empty    ${TEST_CUSTOM_MODEL_NAME}
    ...    msg=No custom model name set — call "A custom model is onboarded in the project" first
    ${namespace}=    Get Project Namespace
    Wait Until Keyword Succeeds    10 min    10 sec
    ...    Custom model status should be    ${namespace}    ${TEST_CUSTOM_MODEL_NAME}    ${target_status}

Custom model status should be
    [Documentation]    Single-poll helper for onboarding status checks.
    [Arguments]    ${namespace}    ${model_name}    ${target_status}
    ${response}=    Get Custom Model    ${namespace}    ${model_name}    expected_status=200
    ${phase}=    Get From Dictionary    ${response.json()}    phase
    ${state}=    Get From Dictionary    ${phase}    state
    Should Be Equal    ${state}    ${target_status}
    ...    msg=Custom model onboarding state is ${state} (waiting for ${target_status})

Custom model is deployed as an AIM service
    [Documentation]    Deploys the onboarded custom model through the shared inference endpoint.
    ...    Sends only non-profile deploy fields (e.g. replicas). Runtime settings were
    ...    written to the namespace AIMProfile via model settings at onboard/edit time.
    ...    Requires: TEST_CUSTOM_MODEL_NAME
    ...    Sets: TEST_AIM_ID
    Should Not Be Empty    ${TEST_CUSTOM_MODEL_NAME}
    ...    msg=No custom model name set — call "A custom model is onboarded in the project" first
    ${namespace}=    Get Project Namespace
    ${existing}=    Find Existing Custom AIM Service    ${namespace}    ${TEST_CUSTOM_MODEL_NAME}
    IF    $existing != $None
        ${service_id}=    Get From Dictionary    ${existing}    id
        VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST
        RETURN
    END
    ${deploy_data}=    Create Dictionary    replicas=${1}
    ${response}=    Deploy AIM    ${TEST_CUSTOM_MODEL_NAME}    ${deploy_data}    ${namespace}    expected_status=202
    VAR    ${json}    ${response.json()}
    ${service_id}=    Get From Dictionary    ${json}    id
    VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST

Custom model is deployed as an AIM service with display name
    [Documentation]    Deploys the onboarded custom model with a user-entered display name.
    ...    Requires: TEST_CUSTOM_MODEL_NAME
    ...    Sets: TEST_AIM_ID, TEST_AIM_DISPLAY_NAME
    [Arguments]    ${display_name}
    Should Not Be Empty    ${TEST_CUSTOM_MODEL_NAME}
    ...    msg=No custom model name set — call "A custom model is onboarded in the project" first
    ${namespace}=    Get Project Namespace
    ${deploy_data}=    Create Dictionary    replicas=${1}    displayName=${display_name}
    ${response}=    Deploy AIM    ${TEST_CUSTOM_MODEL_NAME}    ${deploy_data}    ${namespace}    expected_status=202
    VAR    ${json}    ${response.json()}
    ${service_id}=    Get From Dictionary    ${json}    id
    VAR    ${TEST_AIM_ID}    ${service_id}    scope=TEST
    VAR    ${TEST_AIM_DISPLAY_NAME}    ${display_name}    scope=TEST

The onboarded model's weight import has failed
    [Documentation]    Drives the model into a failed weight-import state: it waits for the
    ...    real import to finish (so the background task cannot later overwrite the state),
    ...    then stamps the workbench-owned import-state as Failed — the same terminal state
    ...    a mid-import object-storage upload failure produces. The composed onboarding phase
    ...    must then report Failed even though aim-engine has emitted an AIMProfile from the
    ...    base image. Requires: TEST_CUSTOM_MODEL_NAME.
    [Tags]    kubectl
    Should Not Be Empty    ${TEST_CUSTOM_MODEL_NAME}
    ...    msg=No custom model name set — call "A custom model is onboarded in the project" first
    The weight import for source "${CUSTOM_MODELS_PUBLIC_REPO}" should complete within "3 min"
    ${namespace}=    Get Project Namespace
    ${import_state_arg}=    Set Variable    aiwb.apps.eai.amd.com/import-state=Failed
    ${import_error_arg}=    Set Variable    aiwb.apps.eai.amd.com/import-error=Simulated weight upload failure: object storage returned HTTP 500
    ${result}=    Run Process
    ...    kubectl    annotate    aimmodels    ${TEST_CUSTOM_MODEL_NAME}
    ...    -n    ${namespace}
    ...    --overwrite
    ...    ${import_state_arg}
    ...    ${import_error_arg}
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Failed to stamp import-state annotation on AIMModel ${TEST_CUSTOM_MODEL_NAME}: ${result.stderr}
    Wait Until Keyword Succeeds    30 sec    5 sec
    ...    Custom model status should be    ${namespace}    ${TEST_CUSTOM_MODEL_NAME}    Failed

The user attempts to deploy the custom model
    [Documentation]    Sends a deploy request for the onboarded custom model without asserting
    ...    success, so the rejection can be inspected. Requires: TEST_CUSTOM_MODEL_NAME.
    ...    Sets: TEST_RESPONSE.
    Should Not Be Empty    ${TEST_CUSTOM_MODEL_NAME}
    ...    msg=No custom model name set — call "A custom model is onboarded in the project" first
    ${namespace}=    Get Project Namespace
    ${deploy_data}=    Create Dictionary    replicas=${1}
    ${response}=    Deploy AIM    ${TEST_CUSTOM_MODEL_NAME}    ${deploy_data}    ${namespace}    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The user attempts to deploy custom model with name "${model_name}"
    [Documentation]    Sends a deploy request using an explicit model CR name, allowing
    ...    negative tests to supply names that do not correspond to existing CRs.
    ...    Sets: TEST_RESPONSE.
    ${namespace}=    Get Project Namespace
    ${deploy_data}=    Create Dictionary    replicas=${1}
    ${response}=    Deploy AIM    ${model_name}    ${deploy_data}    ${namespace}    expected_status=any
    VAR    ${TEST_RESPONSE}    ${response}    scope=TEST

The custom model deploy response status should be "${expected_status}"
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    ${expected_status}

The custom model deploy should be rejected
    [Documentation]    The deploy must be rejected with a client error that explains the weight
    ...    import failure, rather than creating an AIMService whose predictor would crashloop
    ...    on missing weights. Requires: TEST_RESPONSE.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    400
    ...    msg=Expected deploy of a failed-import model to be rejected with 400, got ${TEST_RESPONSE.status_code}
    ${detail}=    Get From Dictionary    ${TEST_RESPONSE.json()}    detail
    Should Contain    ${detail}    weight import
    ...    msg=Rejection detail should explain the weight import failure, got: ${detail}

Deployed AIMService should show the deploy display name
    [Documentation]    Verifies the deploy-time display name is persisted on the AIMService
    ...    display-name annotation. Requires: TEST_AIM_ID, TEST_AIM_DISPLAY_NAME.
    Should Not Be Empty    ${TEST_AIM_ID}    msg=No AIM service ID set
    Should Not Be Empty    ${TEST_AIM_DISPLAY_NAME}    msg=No deploy display name set
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIM Service    ${TEST_AIM_ID}    ${namespace}    expected_status=200
    VAR    ${json}    ${response.json()}
    ${metadata}=    Get From Dictionary    ${json}    metadata
    ${annotations}=    Get From Dictionary    ${metadata}    annotations    default=&{EMPTY}
    ${shown_name}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/display-name    default=${EMPTY}
    Should Be Equal    ${shown_name}    ${TEST_AIM_DISPLAY_NAME}
    ...    msg=AIMService display-name annotation is '${shown_name}' (expected '${TEST_AIM_DISPLAY_NAME}')

Find Existing Custom AIM Service
    [Documentation]    Returns an existing AIMService for the custom model, if present.
    [Arguments]    ${namespace}    ${model_name}
    ${services_response}=    List AIM Services    ${namespace}    expected_status=200
    ${services}=    Get From Dictionary    ${services_response.json()}    data
    FOR    ${service}    IN    @{services}
        ${resolved}=    Get From Dictionary    ${service}[spec]    model
        ${resolved_name}=    Get From Dictionary    ${resolved}    name
        IF    "${resolved_name}" == "${model_name}"
            RETURN    ${service}
        END
    END
    RETURN    ${None}

Deployed AIMService should reference the custom model
    [Documentation]    Verifies service spec.model.name points at TEST_CUSTOM_MODEL_NAME.
    Should Not Be Empty    ${TEST_AIM_ID}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIM Service    ${TEST_AIM_ID}    ${namespace}    expected_status=200
    VAR    ${json}    ${response.json()}
    ${spec}=    Get From Dictionary    ${json}    spec
    ${model}=    Get From Dictionary    ${spec}    model
    ${model_name}=    Get From Dictionary    ${model}    name
    Should Be Equal    ${model_name}    ${TEST_CUSTOM_MODEL_NAME}

Deployed custom model should be accessible for inference
    [Documentation]    Verifies the deployment appears in the chat-capable inference list.
    Should Not Be Empty    ${TEST_AIM_ID}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    ${response}=    List AIM Services    ${namespace}    expected_status=200    capability=chat
    ${services}=    Get From Dictionary    ${response.json()}    data
    FOR    ${service}    IN    @{services}
        ${service_id}=    Get From Dictionary    ${service}    id
        IF    "${service_id}" == "${TEST_AIM_ID}"
            RETURN
        END
    END
    Fail    Custom model AIMService ${TEST_AIM_ID} not found in chat-capable deployments

Chat completion against deployed custom model should succeed
    [Documentation]    Sends a real chat completion request to the deployment's external endpoint.
    ...    Uses an API key assigned to the AIM service for authenticated access.
    Should Not Be Empty    ${TEST_AIM_ID}    msg=No AIM service ID set
    An API key exists and is assigned to AIM
    ${namespace}=    Get Project Namespace
    ${response}=    Get AIM Service    ${TEST_AIM_ID}    ${namespace}    expected_status=200
    ${endpoints}=    Get From Dictionary    ${response.json()}    endpoints
    ${external_host}=    Get From Dictionary    ${endpoints}    external
    Should Not Be Empty    ${external_host}    msg=AIMService should expose an external endpoint
    ${models}=    List models from external endpoint    ${external_host}    ${TEST_AIM_ID}    ${TEST_API_KEY_VALUE}
    Should Not Be Empty    ${models}    msg=External endpoint should expose at least one model
    ${first_model}=    Get From List    ${models}    0
    ${model_id}=    Get From Dictionary    ${first_model}    id
    ${chat_response}=    Send chat completion request to external endpoint
    ...    ${external_host}
    ...    ${model_id}
    ...    ${TEST_API_KEY_VALUE}
    ...    expected_status=200
    ${choices}=    Get From Dictionary    ${chat_response.json()}    choices
    Should Not Be Empty    ${choices}
    ${message}=    Get From Dictionary    ${choices}[0]    message
    ${content}=    Get From Dictionary    ${message}    content
    Should Not Be Empty    ${content}

Custom model deployment is removed
    [Documentation]    Undeploys the custom model AIMService.
    Should Not Be Empty    ${TEST_AIM_ID}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    Undeploy AIM    ${TEST_AIM_ID}    ${namespace}    expected_status=204

Custom model deployment should be removed
    [Documentation]    Verifies the custom model AIMService is gone.
    Should Not Be Empty    ${TEST_AIM_ID}    msg=No AIM service ID set
    ${namespace}=    Get Project Namespace
    Wait Until Keyword Succeeds    2 min    10 sec
    ...    Get AIM Service    ${TEST_AIM_ID}    ${namespace}    expected_status=404

Remove custom model deployment if present
    [Documentation]    Idempotent teardown: undeploy the custom model AIMService when one was
    ...    created in this test. Tolerates a failure that happened before deploy (no
    ...    TEST_AIM_ID) and a service that is already gone, so teardown never masks the
    ...    test's own failure. The project-deletion suite teardown removes any remaining
    ...    AIMModel and derived AIMProfile via the namespace cascade.
    ${aim_id}=    Get Variable Value    ${TEST_AIM_ID}    ${None}
    IF    $aim_id is None
        RETURN
    END
    ${namespace}=    Get Project Namespace
    Undeploy AIM    ${aim_id}    ${namespace}    expected_status=any

A second ready project with user access exists
    [Documentation]    Creates a second project for namespace isolation checks, preserving
    ...    the first project's namespace in ${TEST_FIRST_PROJECT_NAMESPACE} before
    ...    A ready project with user access exists overwrites ${TEST_PROJECT}.
    ...    Uses a distinct project name so the second namespace is genuinely separate —
    ...    the default name resolves to the shared "testing" project (same namespace),
    ...    which would defeat the isolation check.
    VAR    ${TEST_FIRST_PROJECT_NAMESPACE}    ${TEST_PROJECT}[name]    scope=TEST
    ${second_project_name}=    Test Name    testing-isolation
    A ready project with user access exists    project_name=${second_project_name}

The custom model from the first project should not appear in the second project model list
    [Documentation]    Verifies ${TEST_RESPONSE} (the second project's list) does not
    ...    contain any model whose canonical-repo-id matches the model imported into the
    ...    first project — AIMModel CRs are namespace-scoped so one project cannot see
    ...    another's imports.
    Should Be Equal As Integers    ${TEST_RESPONSE.status_code}    200
    ${models}=    Get From Dictionary    ${TEST_RESPONSE.json()}    data
    FOR    ${model}    IN    @{models}
        ${annotations}=    Get From Dictionary    ${model}[metadata]    annotations    default=&{EMPTY}
        ${canonical}=    Get From Dictionary    ${annotations}    aiwb.apps.eai.amd.com/canonical-repo-id    default=${EMPTY}
        Should Not Be Equal    ${canonical}    ${CUSTOM_MODELS_PUBLIC_REPO}
        ...    msg=Custom model imported into ${TEST_FIRST_PROJECT_NAMESPACE} should not be visible in the second project
    END
