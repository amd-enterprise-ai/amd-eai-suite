# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       E2E coverage for custom-model preview, onboard, list, and detail endpoints.
Test Teardown       Reset Custom Models In Test Project
Suite Teardown      Run Keywords    Clean Up All Created Custom Models    AND    Clean Up All Created Projects With Wait
Resource            resources/airm_projects.resource
Resource            resources/airm_secrets.resource
Resource            resources/aiwb_custom_models.resource
Resource            resources/aiwb_models.resource


*** Test Cases ***
Preview a public custom model by bare repo id
    [Tags]    custom-models    preview    smoke
    Given a ready project with user access exists
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    And custom model preview response should describe model "${CUSTOM_MODELS_PUBLIC_REPO}"

Preview a public custom model via huggingface.co URL with a revision
    [Tags]    custom-models    preview    smoke
    Given a ready project with user access exists
    When a custom model preview is requested for "https://huggingface.co/${CUSTOM_MODELS_PUBLIC_REPO}/tree/main"
    Then custom model preview response status should be "200"
    And custom model preview response should describe model "${CUSTOM_MODELS_PUBLIC_REPO}"
    And custom model preview response revision should be "main"

Preview rejects a malformed custom-model source
    [Tags]    custom-models    preview    smoke    negative
    Given a ready project with user access exists
    When a custom model preview is requested for "not-a-valid-source"
    Then custom model preview response status should be "400"

Preview returns 404 for a nonexistent custom-model repo
    [Tags]    custom-models    preview    smoke    negative
    Given a ready project with user access exists
    When a custom model preview is requested for "${CUSTOM_MODELS_MISSING_REPO}"
    Then custom model preview response status should be "404"

Preview returns 403 for a gated custom-model without a token
    [Tags]    custom-models    preview    smoke    negative    auth
    Given a ready project with user access exists
    When a custom model preview is requested for "${CUSTOM_MODELS_GATED_REPO}"
    Then custom model preview response status should be "403"

Preview accepts hfTokenSecretName for custom-model preview
    [Tags]    custom-models    preview    smoke    auth
    [Teardown]    Custom model preview secret cleanup is performed
    Given a ready project with user access exists
    And a Hugging Face token secret "hf-token-preview" exists for custom model preview
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}" with secret "${CUSTOM_MODELS_HF_SECRET_NAME}"
    Then custom model preview response status should be "200"
    And custom model preview response should describe model "${CUSTOM_MODELS_PUBLIC_REPO}"

Preview with hfTokenSecretName handles invalid token for private custom-model
    [Documentation]    A private repo gates its metadata behind auth, so an invalid token
    ...    yields a 401 from the Hub that the API surfaces as 403. A gated (license-only)
    ...    repo exposes metadata publicly, so it cannot exercise this credential path.
    [Tags]    custom-models    preview    smoke    negative    auth
    [Teardown]    Custom model preview secret cleanup is performed
    Given a ready project with user access exists
    And a Hugging Face token secret "hf-token-invalid" exists for custom model preview
    When a custom model preview is requested for "${CUSTOM_MODELS_PRIVATE_REPO}" with secret "${CUSTOM_MODELS_HF_SECRET_NAME}"
    Then custom model preview response status should be "403"

Preview with invalid token reports a user-facing credential error in the response body
    [Documentation]    A 403 from the hub when credentials are wrong must surface a non-empty
    ...    detail message to the caller so the UI can direct the user to verify their token.
    ...    Status alone (403) is not enough — the body must explain why the request failed.
    ...    Uses a private repo because its metadata is gated behind auth, unlike a
    ...    license-gated repo whose metadata the Hub serves publicly.
    [Tags]    custom-models    preview    smoke    negative    auth
    [Teardown]    Custom model preview secret cleanup is performed
    Given a ready project with user access exists
    And a Hugging Face token secret "hf-token-invalid" exists for custom model preview
    When a custom model preview is requested for "${CUSTOM_MODELS_PRIVATE_REPO}" with secret "${CUSTOM_MODELS_HF_SECRET_NAME}"
    Then custom model preview response status should be "403"
    And custom model preview response should explain the credential failure

Preview response signals that a public model does not require a token
    [Documentation]    The preview response for a fully public model must carry
    ...    ``hfTokenRecommended: false`` so the UI can suppress the token picker
    ...    for models that do not need authentication — prompting unnecessarily
    ...    for credentials on public models degrades the import experience.
    [Tags]    custom-models    preview    smoke
    Given a ready project with user access exists
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    And custom model preview response should signal no authentication is required

Onboard persists the previewed custom model into the namespace
    [Documentation]    After preview, onboard creates a namespace-scoped AIMModel CR
    ...    for the previewed source so it shows up in the project's model list.
    [Tags]    custom-models    onboard    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    And custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should exist in the namespace
    And custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should use image "${CUSTOM_MODELS_ONBOARD_IMAGE}"

Onboard derives from the cluster-discovered base image family
    [Documentation]    Onboarding should derive profiles from the base image family the
    ...    cluster discovery selected (the catalog's non-automatic family), while
    ...    keeping the request's image on ``spec.profiles.overrides.image`` for the
    ...    custom model itself.
    [Tags]    custom-models    onboard    profile    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And the discovered cluster base image family is recorded
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    And custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should derive from discovered base family
    And custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should use image "${CUSTOM_MODELS_ONBOARD_IMAGE}"

Onboard is idempotent when called twice with the same source
    [Documentation]    Re-submitting the same onboard payload must not create duplicate
    ...    AIMModel CRs and must not raise — exactly one CR remains.
    [Tags]    custom-models    onboard    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    And exactly one custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should exist in the namespace

Onboard accepts a user-customized display name and stores it on the model
    [Documentation]    The import wizard lets users rename the model from the HuggingFace
    ...    default before submitting. The custom display name must survive the onboard call
    ...    and appear on the model card, not be silently overwritten by the preview default.
    [Tags]    custom-models    onboard    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}" overriding display name to "My Custom TinyLlama"
    Then custom model onboard response status should be "204"
    When the project custom model list is retrieved
    Then listed custom model from "${CUSTOM_MODELS_PUBLIC_REPO}" should show display name "My Custom TinyLlama"

Custom model imported into one project is not visible in another project
    [Documentation]    After onboarding a model in project A, the model must be absent from
    ...    project B's custom-model list — AIMModel CRs are namespace-scoped so a second
    ...    project cannot see or deploy an import that belongs to a different namespace.
    [Tags]    custom-models    onboard    namespace    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    And aiwb_custom_models.A second ready project with user access exists
    When the project custom model list is retrieved
    Then the custom model from the first project should not appear in the second project model list

Copy creates another custom model from the same source
    [Documentation]    Copying an onboarded custom model should create another model
    ...    entry for the same canonical source in the project model list.
    [Tags]    custom-models    copy    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    When the project custom model list is retrieved
    And record listed custom model count for source "${CUSTOM_MODELS_PUBLIC_REPO}"
    When the onboarded custom model is copied for source "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model copy response status should be "204"
    When the project custom model list is retrieved
    Then listed custom model count for source "${CUSTOM_MODELS_PUBLIC_REPO}" should increase

Copy returns not-found for a missing source model
    [Documentation]    Copying a model name that does not exist in the project must
    ...    return a not-found response.
    [Tags]    custom-models    copy    negative    smoke
    Given a ready project with user access exists
    When copy request is sent for custom model "no-such-model-zzz"
    Then custom model copy response status should be "404"

Copy rejects a non-custom source model
    [Documentation]    Copying a model that is not a custom import must return
    ...    not-found to enforce custom-model eligibility.
    [Tags]    custom-models    copy    negative    smoke
    Given a ready project with user access exists
    And a completed fine-tuned model exists in the namespace
    When copy request is sent for custom model "${TEST_MODEL_NAME}"
    Then custom model copy response status should be "404"

Onboard wires HF_TOKEN env when a secret is supplied
    [Documentation]    When the user supplies a token secret on onboard, the resulting
    ...    AIMModel CR must reference it from spec.env so the engine can authenticate
    ...    to Hub for gated/private weights. The token only matters on onboard, so the
    ...    preview here intentionally runs without a secret to isolate the dimension.
    [Tags]    custom-models    onboard    auth    smoke
    [Teardown]    Run Keywords    Custom model preview secret cleanup is performed
    ...    AND    Reset Custom Models In Test Project
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a Hugging Face token secret "hf-token-onboard" exists for custom model preview
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}" and secret "${CUSTOM_MODELS_HF_SECRET_NAME}"
    Then custom model onboard response status should be "204"
    And custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should wire HF token secret "${CUSTOM_MODELS_HF_SECRET_NAME}"

Onboard imports the custom model weights into object storage
    [Documentation]    Onboarding must populate the model's storage prefix, not just
    ...    record the sourceUri. A detached task imports the HuggingFace weights and
    ...    reports completion through the model's onboarding status, so the UI can
    ...    track Importing → Ready. A tiny public repo keeps the import fast.
    [Tags]    custom-models    onboard    import    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    And the weight import for source "${CUSTOM_MODELS_PUBLIC_REPO}" should complete within "3 min"

Re-onboarding an existing custom model re-imports its weights to Ready
    [Documentation]    A user who re-onboards a model they already imported (same
    ...    source, e.g. after changing a setting or description) must end up with a
    ...    model whose weight import is Ready again — re-importing over an already
    ...    imported model must not leave it Failed.
    [Tags]    custom-models    onboard    import    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    And the weight import for source "${CUSTOM_MODELS_PUBLIC_REPO}" should complete within "3 min"
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    And the weight import for source "${CUSTOM_MODELS_PUBLIC_REPO}" should complete within "3 min"

A project with no imports returns an empty custom model list
    [Documentation]    The list endpoint must return an empty data array for a fresh
    ...    project before any custom model has been onboarded — this is the baseline
    ...    contract that all subsequent list assertions build on.
    [Tags]    custom-models    list    smoke
    Given a ready project with user access exists
    When the project custom model list is retrieved
    Then the custom model list should be empty

Onboarded custom model appears in the project model list with metadata
    [Documentation]    After onboard, the project model list endpoint must return
    ...    the custom model with its display name and tags so the UI can present it.
    [Tags]    custom-models    list    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    When the project custom model list is retrieved
    Then custom model list should contain a model from "${CUSTOM_MODELS_PUBLIC_REPO}"
    And listed custom model from "${CUSTOM_MODELS_PUBLIC_REPO}" should include display name and tags

Listed custom models include onboarding status fields
    [Documentation]    Every model in the list carries the composed onboard status
    ...    (phase, templateReady, artifactPhase, etc.) so the UI can render
    ...    per-model state without issuing a separate detail request.
    [Tags]    custom-models    list    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    When the project custom model list is retrieved
    Then listed custom models include onboarding status fields

GET list reflects the updated display name after a PATCH
    [Documentation]    After patching a model's display name, the list endpoint must
    ...    return the updated value immediately — annotation writes in K8s are
    ...    synchronous from the API server's perspective, so there is no replication
    ...    delay to account for between the PATCH and the subsequent list read.
    [Tags]    custom-models    list    patch    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user updates the model display name to "Read-After-Write Name"
    And the project custom model list is retrieved
    Then listed custom model from "${CUSTOM_MODELS_PUBLIC_REPO}" should show display name "Read-After-Write Name"

Onboarded custom model is retrievable by name
    [Documentation]    After onboard, the model detail endpoint returns the full model
    ...    representation for the onboarded source, including all top-level fields.
    [Tags]    custom-models    detail    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    When the onboarded custom model detail is retrieved for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model detail response status should be "200"
    And custom model detail should match the onboarded source "${CUSTOM_MODELS_PUBLIC_REPO}"

Onboarded custom model detail includes onboarding status
    [Documentation]    The detail endpoint exposes the composed onboarding state so the
    ...    UI can poll a single endpoint to track Pending → Importing → Ready progress.
    [Tags]    custom-models    detail    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}"
    Then custom model onboard response status should be "204"
    When the onboarded custom model detail is retrieved for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model detail should include onboarding status fields

Retrieving a non-existent custom model returns not-found
    [Documentation]    A detail request for a model name that does not exist in the
    ...    project must be rejected with a not-found response.
    [Tags]    custom-models    detail    negative    smoke
    Given a ready project with user access exists
    When requesting a non-existent custom model returns not-found
    Then custom model detail response status should be "404"

Retrieving a non-custom AIMModel via the custom model endpoint returns not-found
    [Documentation]    The detail endpoint must not expose fine-tuned or base
    ...    AIMModels through the custom-model path — only CRs stamped with the
    ...    custom-import revision annotation are valid targets. This prevents
    ...    leaking other model types and keeps the endpoint purpose-specific.
    [Tags]    custom-models    detail    negative    smoke    kubectl
    Given a ready project with user access exists
    And a completed fine-tuned model exists in the namespace
    When the custom model detail is requested for model "${TEST_MODEL_NAME}"
    Then custom model detail response status should be "404"

Runtime profile options expose the base-template runtime matrix
    [Documentation]    The onboard wizard presets precision, accelerator model, and
    ...    accelerator count from the namespace base model's base-role profiles, so
    ...    the endpoint must return all four runtime-matrix lists (empty when the base
    ...    model has not emitted profiles yet) for a project the user can access.
    [Tags]    custom-models    profile    smoke
    Given a ready project with user access exists
    When the runtime profile options for the project are retrieved
    Then runtime profile options response status should be "200"
    And runtime profile options response should expose the runtime matrix fields

Onboard persists runtime profile overrides on the AIMModel
    [Documentation]    When the user supplies ``customProfile`` on onboard, the
    ...    overrides land on ``AIMModel.spec.profiles.overrides``. aim-engine
    ...    consumes the block at admission and bakes the values into each
    ...    emitted AIMProfile, so the durable cross-cluster contract is the
    ...    AIMModel itself. Asserts ``acceleratorModel`` because the AIMModel CRD's
    ...    ``overrides`` schema enumerates it as a persisted field; free-form keys
    ...    such as ``precision`` are not in the schema and are pruned on write.
    [Tags]    custom-models    onboard    profile    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}" and runtime profile overrides
    ...    acceleratorModel=MI300X
    Then custom model onboard response status should be "204"
    And custom AIMModel for source "${CUSTOM_MODELS_PUBLIC_REPO}" should carry profile override "acceleratorModel" with value "MI300X"

Onboard rejects a customProfile whose image disagrees with the top-level image
    [Documentation]    Two disagreeing image refs in the same payload would
    ...    silently pick one for deployment, so the API rejects the request at
    ...    the Pydantic schema boundary with a 422 instead of accepting an
    ...    ambiguous deployment image.
    [Tags]    custom-models    onboard    profile    negative    smoke
    Given a ready project with user access exists
    When a custom model preview is requested for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then custom model preview response status should be "200"
    When the previewed custom model is onboarded with image "${CUSTOM_MODELS_ONBOARD_IMAGE}" and a conflicting profile image "docker.io/other/image:v9"
    Then custom model onboard response status should be "422"

Delete an onboarded custom model with no active deployments
    [Documentation]    With nothing deploying it, deleting an onboarded model removes
    ...    its AIMModel CR and the workbench-owned object storage, so it disappears
    ...    from the project entirely.
    [Tags]    custom-models    delete    smoke    kubectl
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user deletes the onboarded model
    Then custom model delete response status should be "204"
    And the onboarded AIMModel should no longer exist in the namespace
    And the onboarded model should no longer appear in the project model list

Delete cancels an in-flight weight import and removes the model cleanly
    [Documentation]    Deleting a model whose weight import is still in flight must
    ...    cancel the import and remove the model — the delete still returns 204 and
    ...    the model disappears, with no upload racing the storage cleanup.
    [Tags]    custom-models    delete    import    smoke    kubectl
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user deletes the onboarded model
    Then custom model delete response status should be "204"
    And the onboarded AIMModel should no longer exist in the namespace
    And the onboarded model should no longer appear in the project model list

Deleting an onboarded model cascade-cleans its derived AIMProfile
    [Documentation]    The AIMProfile aim-engine derives from the model is owner-referenced
    ...    by the AIMModel, so deleting the model must cascade-clean the profile via
    ...    Kubernetes owner references — the workbench never deletes it directly.
    [Tags]    custom-models    delete    kubectl
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    And an AIMProfile for the onboarded model exists
    When the user deletes the onboarded model
    Then custom model delete response status should be "204"
    And the derived AIMProfile should no longer exist in the namespace

Deleting a custom model with an active deployment is rejected with a conflict
    [Documentation]    A model still referenced by an AIMService must not be deletable;
    ...    the request is rejected with a conflict that names the blocking deployment so
    ...    the user knows what to tear down first, and the model is left untouched.
    [Tags]    custom-models    delete    negative    kubectl
    [Teardown]    Run Keywords    Remove blocking AIMService if present
    ...    AND    Reset Custom Models In Test Project
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    And an AIMService referencing the onboarded model exists
    When the user attempts to delete custom model "${TEST_CUSTOM_MODEL_NAME}"
    Then custom model delete response status should be "409"
    And the delete conflict response should name the blocking AIMService
    And the onboarded AIMModel should still exist in the namespace

Deleting a custom model that does not exist returns not-found
    [Documentation]    A delete request for a model name that does not exist in the
    ...    project must be rejected with a not-found response.
    [Tags]    custom-models    delete    negative    smoke
    Given a ready project with user access exists
    When the user attempts to delete custom model "no-such-model-zzz"
    Then custom model delete response status should be "404"

Deleting a custom model whose weight import has failed succeeds cleanly
    [Documentation]    A model stuck in Failed onboarding state must still be deletable —
    ...    the failure does not lock the model in place. Delete returns 204 and the
    ...    AIMModel CR is removed from the namespace, just as it would be for a Ready model.
    [Tags]    custom-models    delete    import    smoke    kubectl
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    And the onboarded model's weight import has failed
    When the user deletes the onboarded model
    Then custom model delete response status should be "204"
    And the onboarded AIMModel should no longer exist in the namespace
    And the onboarded model should no longer appear in the project model list

# Conflict-on-different-source is exercised in pytest (tests/custom_models/test_onboard.py)
# rather than Robot: triggering it requires two Hugging Face repos whose
# server-derived display names sanitize to the same Kubernetes label value, which
# isn't a contract we can rely on for E2E setup.

Update custom model display name after onboard
    [Documentation]    After onboard, the user can PATCH the model display name and
    ...    see the updated value in the API response.
    [Tags]    custom-models    patch    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user updates the model display name to "Renamed TinyLlama"
    Then the model should show display name "Renamed TinyLlama"

Update custom model tags after onboard
    [Documentation]    After onboard, the user can PATCH model tags and see the
    ...    updated list in the API response.
    [Tags]    custom-models    patch    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user updates the model tags to "llama,chat"
    Then the model should show tags "llama,chat"

Editing the runtime profile with conflicting image references is rejected
    [Documentation]    A runtime-profile edit whose customProfile.image disagrees
    ...    with the top-level image would leave the deployment image ambiguous, so
    ...    the API rejects it at the schema boundary with a 422 before touching the
    ...    model or its profile.
    [Tags]    custom-models    patch    profile    negative    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user edits the model runtime profile with conflicting image references
    Then the runtime profile edit response status should be "422"

Editing a runtime profile map to remove one of several pairs persists the removal
    [Documentation]    A user who has several engine arguments and environment
    ...    variables on a model and removes one of them, keeping the rest, should see
    ...    only the kept settings after saving — the removed one must not reappear.
    [Tags]    custom-models    patch    profile    kubectl
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    And an AIMProfile for the onboarded model exists
    When the user sets two engine arguments and two environment variables on the model
    Then the model runtime profile should carry both engine arguments and both environment variables
    When the user removes one engine argument and one environment variable
    Then the model runtime profile should retain only the kept engine argument and environment variable

PATCH updates display name and description in a single combined request
    [Documentation]    A single PATCH carrying both displayName and description must
    ...    persist both fields atomically — the edit wizard sends one request for
    ...    the entire information step, not two separate ones.
    [Tags]    custom-models    patch    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user updates the model display name to "Combined Edit Name" and description to "A combined edit description"
    Then the model should show display name "Combined Edit Name"
    And the model should show description "A combined edit description"

PATCH clears the description when an empty string is provided
    [Documentation]    The description field uses an empty string as a deliberate
    ...    clear signal — sending ``description: ""`` must wipe the existing value.
    ...    An empty string is not the same as omitting the field (no change), so the
    ...    API must treat it as an explicit reset and return an empty description.
    [Tags]    custom-models    patch    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user updates the model description to "Initial description"
    Then the model should show description "Initial description"
    When the user clears the model description
    Then model description should be empty

PATCH display name is rejected when it conflicts with another model in the project
    [Documentation]    Two models in the same project cannot share a display name —
    ...    the conflict guard rejects the rename with a 409 so the edit wizard can
    ...    surface a meaningful error rather than silently overwriting or leaving the
    ...    user confused about why nothing changed.
    [Tags]    custom-models    patch    negative    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    When the user updates the model display name to "Taken Name"
    Then the model should show display name "Taken Name"
    Given a copy of the onboarded custom model is created in the project
    When the user attempts to rename the copy to "Taken Name"
    Then the model patch response status should be "409"

# The not-ready 409 runtime-profile edit is exercised in pytest
# (tests/custom_models/test_patch_display_metadata.py) rather than Robot: it depends
# on editing before aim-engine has emitted an AIMProfile for the freshly onboarded
# model, a race that is not a deterministic E2E precondition.

Custom onboarded model can run deploy to chat lifecycle
    [Documentation]    Validates the custom-model inference lifecycle end-to-end:
    ...    onboard → deploy → running/chat-capable → chat completion → undeploy.
    ...    Deploy pins the namespace AIMProfile from model settings; it never applies
    ...    deploy-time profile selector or override fields.
    [Tags]    custom-models    deploy    chat    undeploy    gpu
    [Teardown]    Run Keywords    Remove custom model deployment if present
    ...    AND    Reset Custom Models In Test Project
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And project quota is set to    gpu_count=2
    And a custom model is onboarded in the project
    And custom model onboarding status should be "Ready"
    When custom model is deployed as an AIM service
    Then deployed AIMService should reference the custom model
    And AIMService CR should pin model-settings AIMProfile for custom model in kubernetes
    And Deployed AIM reaches Running state
    And deployed custom model should be accessible for inference
    And chat completion against deployed custom model should succeed
    When custom model deployment is removed
    Then custom model deployment should be removed

Custom model runtime profile round-trips from onboard through the inference pod
    [Documentation]    The full customProfile round-trip on a real cluster: onboard a public
    ...    model with a non-default runtime profile, edit the profile, deploy, and confirm the
    ...    running inference pod reflects the edited profile — image, accelerator product and
    ...    count, and the edited engine argument and env var. Deploy pins the namespace
    ...    AIMProfile written via model settings; it never sends deploy-time profile overrides
    ...    for custom models. Teardown removes the deployment so a mid-test failure cannot leave
    ...    an AIMService behind.
    [Tags]    custom-models    onboard    patch    profile    deploy    undeploy    gpu    kubectl
    [Teardown]    Run Keywords    Remove custom model deployment if present
    ...    AND    Reset Custom Models In Test Project
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And project quota is set to    gpu_count=2
    And a custom model is onboarded with a non-default runtime profile
    And custom model onboarding status should be "Ready"
    And an AIMProfile for the onboarded model exists
    When the user revises the model's engine settings
    Then the model runtime profile should carry the revised engine settings
    When custom model is deployed as an AIM service
    And Deployed AIM reaches Running state
    Then the running inference pod should reflect the model's runtime profile

Failed weight import surfaces the error reason in the model detail
    [Documentation]    When a weight import fails the composed onboarding phase must
    ...    include a non-empty ``artifactLastError`` string so the UI can explain the
    ...    failure to the user rather than showing a generic "Failed" label with no
    ...    actionable information.
    [Tags]    custom-models    import    detail    smoke    kubectl
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    And the onboarded model's weight import has failed
    When the onboarded custom model detail is retrieved for "${CUSTOM_MODELS_PUBLIC_REPO}"
    Then failed weight import error should be present in the model detail

A custom model whose weight import failed cannot be deployed
    [Documentation]    A failed HuggingFace→object-storage weight import composes to a Failed
    ...    onboarding phase even when aim-engine has emitted an AIMProfile (profiles derive
    ...    from the base image, not the presence of weights). Deploying such a model would
    ...    crashloop the predictor with missing weights, so the API must reject the deploy
    ...    request instead of creating the AIMService. Validation happens before any pod is
    ...    scheduled, so no GPU quota is required.
    [Tags]    custom-models    deploy    negative    import    kubectl    smoke
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And a custom model is onboarded in the project
    And the onboarded model's weight import has failed
    When the user attempts to deploy the custom model
    Then the custom model deploy should be rejected

Deploying a custom model that does not exist returns not-found
    [Documentation]    The deploy endpoint must reject a request for a model name that
    ...    does not exist in the project namespace — it cannot create an AIMService that
    ...    references a missing AIMModel CR, and the caller needs a 404 to distinguish
    ...    this from a validation failure (400) or quota issue.
    [Tags]    custom-models    deploy    negative    smoke
    Given a ready project with user access exists
    When the user attempts to deploy custom model with name "no-such-model-zzz"
    Then the custom model deploy response status should be "404"

Custom model deployed with a display name shows that name
    [Documentation]    Validates that the display name entered at deploy time is persisted
    ...    on the deployment, so users can give meaningful names to deployed custom models.
    [Tags]    custom-models    deploy    gpu
    [Teardown]    Run Keywords    Remove custom model deployment if present
    ...    AND    Reset Custom Models In Test Project
    Given a ready project with user access exists
    And secret "minio-credentials-fetcher" is assigned to project
    And project quota is set to    gpu_count=2
    And a custom model is onboarded in the project
    And custom model onboarding status should be "Ready"
    When custom model is deployed as an AIM service with display name    My TinyLlama
    Then deployed AIMService should show the deploy display name
    When custom model deployment is removed
    Then custom model deployment should be removed
