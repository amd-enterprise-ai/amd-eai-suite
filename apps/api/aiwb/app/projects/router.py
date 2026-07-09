# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent

from fastapi import APIRouter, Body, Depends, Path, status

from api_common.auth.security import get_user_email, get_user_groups
from api_common.collections import PaginationMetadata, paginate_list
from api_common.schemas import ListResponse, QueryParam

from ..aims.crds import AIMProfileResource
from ..aims.service import get_aim_profile, list_aim_profiles
from ..common_responses import PROJECT_ACCESS_RESPONSES
from ..custom_models.schemas import (
    CustomModelPatchRequest,
    CustomModelPatchResponse,
    CustomModelResponse,
    OnboardRequest,
    PreviewRequest,
    PreviewResponse,
    RuntimeProfileOptions,
)
from ..custom_models.service import (
    copy_custom_model,
    delete_onboarded_model,
    get_base_runtime_profile_options,
    get_custom_model,
    list_custom_models,
    onboard_custom_model_source,
    patch_onboarded_model,
    preview_model_source,
)
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..inference.schemas import InferenceProfilesList, ListInferenceProfilesQuery
from ..minio import MinioClient, get_minio_client
from .security import ensure_access_to_project
from .service import get_accessible_namespaces

router = APIRouter(tags=["Projects"])


@router.get(
    "/projects",
    response_model=ListResponse[str],
    status_code=status.HTTP_200_OK,
    summary="List accessible projects",
    response_description="Project identifiers usable as the {project} path segment in other endpoints.",
    description=dedent("""
        Return the list of project identifiers that the caller has access to,
        derived from JWT group claims in combined mode, or just the default
        project in standalone mode.

        The returned strings are the same identifiers used wherever
        `{project}` appears in other paths (e.g.
        `/projects/{project}/inference`); they map 1:1 to the underlying
        workbench Kubernetes namespaces.
    """),
)
async def list_projects(
    user_groups: list[str] = Depends(get_user_groups),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[str]:
    namespaces = await get_accessible_namespaces(kube_client, user_groups)
    return ListResponse(data=[ns.name for ns in namespaces])


@router.get(
    "/projects/{project}/models/runtime-profile-options",
    response_model=RuntimeProfileOptions,
    status_code=status.HTTP_200_OK,
    summary="Get runtime profile options for custom model onboarding",
    description=dedent("""
        Return the runtime options a custom (BYOM) model will support in this
        project, derived from the namespace base-image model's base-role
        AIMProfiles.

        A custom model inherits its runtime matrix from the base model, so the
        onboard wizard offers and presets these accelerator/precision/count
        values instead of a free-form precision (which the AIMModel CRD prunes).
        Empty lists mean the base model has not emitted profiles yet; clients
        should fall back to static defaults.
    """),
    responses=PROJECT_ACCESS_RESPONSES,
)
async def get_runtime_profile_options_endpoint(
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> RuntimeProfileOptions:
    return await get_base_runtime_profile_options(kube_client=kube_client, namespace=project)


@router.get(
    "/projects/{project}/profiles",
    response_model=InferenceProfilesList,
    status_code=status.HTTP_200_OK,
    summary="List AIM profiles in a project",
    description=dedent("""
        List namespace-scoped AIMProfile resources in the project as a
        paginated envelope (default page size 10, max 100). Use `?page=`
        and `?pageSize=` to navigate.

        Pass `?aimId=<canonical-id>` to narrow the result set. The query
        parameter is repeatable to batch several models into one round-trip
        (`?aimId=…&aimId=…`). The `aimId` matches each profile's
        `spec.aimId`. Profiles owned by an AIMService (engine-created
        overlays from `spec.profileOverrides`) are excluded — those belong
        to a specific service deployment, not the authored catalog.

        Returns 200 + empty `data` when no profiles match; 404 is reserved
        for project-access failures.
    """),
    responses=PROJECT_ACCESS_RESPONSES,
)
async def list_project_profiles_endpoint(
    query: QueryParam[ListInferenceProfilesQuery],
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> InferenceProfilesList:
    profiles = await list_aim_profiles(
        kube_client=kube_client,
        namespace=project,
        aim_ids=query.aim_id,
    )
    paginated = paginate_list(profiles, page=query.page, page_size=query.page_size)
    return InferenceProfilesList(
        data=paginated.items,
        pagination=PaginationMetadata(
            page=paginated.page,
            page_size=paginated.page_size,
            total=paginated.total,
        ),
    )


@router.get(
    "/projects/{project}/profiles/{name}",
    response_model=AIMProfileResource,
    status_code=status.HTTP_200_OK,
    summary="Get a single AIM profile in a project",
    description=dedent("""
        Fetch a single namespace-scoped AIMProfile by resource name. Designed
        for targeted lookups where the caller already knows the profile name
        (e.g. the AIM detail page for a fine-tuned model joining
        `AIMService.status.resolvedProfile.name`) — avoids the aimId
        derivation hop required by the listing endpoint.
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "AIMProfile not found in the project."},
    },
)
async def get_project_profile_endpoint(
    name: str = Path(
        ...,
        description="AIMProfile resource name (metadata.name).",
        pattern=r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$",
    ),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> AIMProfileResource:
    return await get_aim_profile(kube_client, project, name)


@router.get(
    "/projects/{project}/models",
    response_model=ListResponse[CustomModelResponse],
    status_code=status.HTTP_200_OK,
    summary="List custom models in a project",
    description="List all models that were onboarded into the project via the preview endpoint.",
    responses={
        403: {"description": "User does not have access to the project"},
    },
)
async def list_custom_models_endpoint(
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[CustomModelResponse]:
    models = await list_custom_models(kube_client=kube_client, namespace=project)
    return ListResponse(data=models)


@router.get(
    "/projects/{project}/models/{model_name}",
    response_model=CustomModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a custom model",
    description=dedent("""
        Return the full representation of a single onboarded custom model,
        including its current onboarding state.

        The embedded `.status` is composed from three Kubernetes resources:

        * **AIMModel** — overall controller state (`status`).
        * **AIMProfile** — deploy-readiness: present and annotated with
          `aim.eai.amd.com/deployment-image-ref` → `templateReady = true`.
        * **AIMArtifact** — weight-import pipeline phase, progress (0–100),
          and last error.

        The derived `phase` summarises all three:
        `Pending` → `Importing` → `Ready` (or `Failed`).

        Re-fetch this endpoint to poll for state changes; there is no separate
        status endpoint.
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "No custom model with that name exists in the project"},
    },
)
async def get_custom_model_endpoint(
    model_name: str,
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> CustomModelResponse:
    return await get_custom_model(kube_client=kube_client, namespace=project, model_name=model_name)


@router.post(
    "/projects/{project}/models/{model_name}/copy",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Copy a custom model",
    description=dedent("""
        Copy an existing onboarded custom model into a new model resource in
        the same project. The source model is unchanged.

        The copied model carries the same source identity/runtime settings and
        receives a new display name derived from the source with a `-copy`
        suffix.
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "No custom model with that name exists in the project"},
    },
)
async def copy_custom_model_endpoint(
    model_name: str,
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
    minio_client: MinioClient = Depends(get_minio_client),
    submitter: str = Depends(get_user_email),
) -> None:
    await copy_custom_model(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=project,
        source_model_name=model_name,
        submitter=submitter,
    )


@router.post(
    "/projects/{project}/models/preview",
    response_model=PreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview a custom model source",
    description=dedent("""
        Resolve a Hugging Face source and return preview metadata along with
        the repo's file list. This call is read-only; use POST
        `/projects/{project}/models/onboard` to persist the model.

        The returned `weightFiles` contains both selectable weight blobs
        (role `primary` or `shard`) and associated config/tokenizer files
        (role `config`) included for context.

        Supported source formats:
        - Bare repo id (for example `meta-llama/Meta-Llama-3-8B-Instruct`)
        - Full Hugging Face URL
        - URL with `/tree/<revision>`, `/blob/<revision>/...`, or `/resolve/<revision>/...`
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        400: {"description": "Invalid source format, or the named secret does not contain a 'token' key"},
        403: {
            "description": (
                "Hub access denied. The detail message indicates the cause: "
                "(a) the supplied token is invalid or expired, "
                "(b) the model is gated and a token is required, or "
                "(c) the token lacks access to this gated model (accept license on huggingface.co)."
            )
        },
        404: {"description": "Model not found on Hub, or specified secret not found"},
        502: {
            "description": (
                "Upstream failure: network timeout or connection error contacting "
                "Hugging Face Hub, Hub 5xx response, Hub response that was oversized, "
                "unparseable, or missing a SHA, or a Kubernetes API failure while "
                "reading the token secret."
            )
        },
    },
)
async def preview_model_source_endpoint(
    body: PreviewRequest = Body(...),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> PreviewResponse:
    return await preview_model_source(
        kube_client=kube_client,
        namespace=project,
        request=body,
    )


@router.post(
    "/projects/{project}/models/onboard",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Onboard a custom model source",
    description=dedent("""
        Persist a previewed Hugging Face source into the project: an AIMModel CR
        is applied in the namespace and a DR manifest is written to S3. No
        database persistence is performed.

        Send the Hub-validated fields from preview (optionally edited by the
        user) together with the container `image` selected in the UI. The
        server re-fetches Hub and rejects the request if the supplied `sha`
        no longer matches what Hub resolves `(repoId, revision)` to — so a
        stale or forged preview payload fails before any CR or S3 mirror is
        written. The call is idempotent on `(displayName, modelId)` within
        the project, so re-submitting the same form is safe.

        When `customProfile` is supplied it is written verbatim to
        `AIMModel.spec.profiles.overrides`; aim-engine bakes those values into
        each emitted AIMProfile.spec (engine, engineArgs, engineEnv,
        containerEnv, metric, precision, accelerator settings, etc.). When
        omitted, aim-engine defaults are preserved.
    """),
    responses={
        400: {
            "description": (
                "Invalid repo id (not a well-formed Hugging Face repo), or the supplied "
                "`sha` does not match what Hub currently resolves `(repoId, revision)` "
                "to — re-preview the model and resubmit."
            )
        },
        403: {
            "description": (
                "Hub access denied while re-verifying the source. The detail message "
                "indicates the cause: (a) the supplied token is invalid or expired, "
                "(b) the model is gated and a token is required, or (c) the token "
                "lacks access to this gated model."
            )
        },
        404: {
            "description": (
                "The specified HF token secret was not found in the project, or the "
                "supplied `repoId` (or `revision`) was not found on Hugging Face Hub."
            )
        },
        409: {
            "description": (
                "A custom model with the same display name already exists in the project "
                "with a different source. Choose a different name to onboard a new source."
            )
        },
        502: {
            "description": (
                "Upstream failure: contacting Hugging Face Hub for re-verification "
                "(timeout, network error, 5xx, oversized or unparseable response), "
                "applying the AIMModel CR, or uploading the S3 manifest mirror."
            )
        },
    },
)
async def onboard_custom_model_source_endpoint(
    body: OnboardRequest = Body(...),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
    minio_client: MinioClient = Depends(get_minio_client),
    submitter: str = Depends(get_user_email),
) -> None:
    await onboard_custom_model_source(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=project,
        submitter=submitter,
        request=body,
    )


@router.patch(
    "/projects/{project}/models/{model_name}",
    response_model=CustomModelPatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a custom-onboarded model",
    description=dedent("""
        Update a custom-onboarded AIMModel after onboarding. Two groups of edits
        are supported and may be combined in one request:

        * **Display metadata** — `displayName`, `description`, `tags` (written to
          the AIMModel annotations).
        * **Runtime profile** — `image` and/or `customProfile`, which rewrite
          `spec.profiles.overrides` and repatch the live AIMProfile
          (`deployment-image-ref` plus the runtime spec) so the change applies
          without waiting for a controller reconcile.

        Only supplied fields are changed; unspecified fields are preserved. The
        runtime-profile overrides use JSON merge-patch semantics: send the
        complete desired profile — a present key is set, a key sent as `null` is
        reset to the aim-engine default. A runtime-profile edit requires the
        model to already have a derived AIMProfile (i.e. be past import). The
        multi-doc DR manifest in S3 is refreshed after a successful cluster patch
        (best effort: mirror write failures are logged and do not fail the request;
        cluster CRs remain authoritative). No database persistence is performed.

        Target the AIMModel CR by its resource name (for example
        `llama-3-8b-import-a1b2c3d4`).
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        400: {
            "description": (
                "Empty request body (none of displayName, description, tags, image, or customProfile "
                "supplied), or a runtime-profile edit with no resolvable container image."
            )
        },
        404: {"description": "Project not found, or custom-onboarded model not found in the project."},
        409: {
            "description": (
                "Another custom model in the project already uses the requested display name, or a "
                "runtime-profile edit was requested before the model's AIMProfile is ready."
            )
        },
        422: {"description": "Request body failed validation: empty display name, or conflicting image references."},
        502: {
            "description": (
                "Upstream failure from the Kubernetes API when reading the AIMModel, "
                "resolving the AIMProfile, or applying patches to the AIMModel or AIMProfile."
            )
        },
    },
)
async def patch_onboarded_model_endpoint(
    model_name: str = Path(..., description="AIMModel CR resource name"),
    body: CustomModelPatchRequest = Body(...),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
    minio_client: MinioClient = Depends(get_minio_client),
) -> CustomModelPatchResponse:
    return await patch_onboarded_model(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=project,
        name=model_name,
        request=body,
    )


@router.delete(
    "/projects/{project}/models/{model_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an onboarded custom model",
    description=dedent("""
        Permanently remove an onboarded custom model from the project: the
        AIMModel CR is deleted from the namespace and the workbench-owned S3
        tree (manifest mirror and weights) is removed. There is no soft-delete
        or retention — once deleted, both the live CR and the persisted manifest
        are gone.

        Deletion is guarded: if any AIMService in the project still references
        this model, the request is rejected with `409` and the response names
        the blocking services. Tear those deployments down first, then retry.

        The derived AIMProfile (and its AIMProfileSet) are not deleted here —
        they are owner-referenced by the AIMModel and cascade-cleaned by
        aim-engine via Kubernetes owner references. Profile caches and artifacts
        follow AIMService lifecycle and aim-engine's reuse semantics, so they
        are untouched by this endpoint.

        On success the live CR delete is authoritative; if the subsequent S3
        cleanup fails it is logged and retried out-of-band rather than failing
        the request.
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "No custom model with that name exists in the project"},
        409: {
            "description": (
                "One or more AIMServices in the project still reference this model. "
                "The response names the blocking services; delete them first."
            )
        },
        502: {"description": "Kubernetes API failure while reading or deleting the AIMModel CR."},
    },
)
async def delete_onboarded_model_endpoint(
    model_name: str = Path(..., description="AIMModel CR resource name"),
    project: str = Depends(ensure_access_to_project),
    kube_client: KubernetesClient = Depends(get_kube_client),
    minio_client: MinioClient = Depends(get_minio_client),
) -> None:
    await delete_onboarded_model(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=project,
        name=model_name,
    )
