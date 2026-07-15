# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


import asyncio
import base64
import json
from typing import Any
from uuid import uuid4

import httpx
from kubernetes_asyncio.client import ApiException
from loguru import logger

from api_common.exceptions import (
    ConflictException,
    ExternalServiceError,
    ForbiddenException,
    NotFoundException,
    PreconditionNotMetException,
    ValidationException,
)

from ..aims import gateway as aims_gateway
from ..aims.constants import AIM_API_GROUP, AIM_API_VERSION
from ..aims.constants import AIM_MODEL_LABEL as AIM_MODEL_LABEL_KEY
from ..aims.crds import (
    AIMArtifactResource,
    AIMModelProfilesDerivedFrom,
    AIMModelProfilesSpec,
    AIMModelResource,
    AIMModelSource,
    AIMProfileResource,
    ProfileOverrides,
    ProfileSelector,
    ProfileSelectorModelRef,
)
from ..aims.utils import env_entries_to_map
from ..cluster.service import get_cluster_base_image_ref
from ..cluster.utils import parse_container_image_repository_and_tag
from ..config import SUBMITTER_ANNOTATION
from ..datasets.utils import slugify
from ..dispatch.crds import K8sMetadata
from ..dispatch.kube_client import KubernetesClient
from ..dispatch.utils import sanitize_label_value
from ..minio.client import MinioClient
from ..minio.config import MINIO_BUCKET, MINIO_URL
from ..models.utils import (
    delete_from_s3,
    get_custom_model_manifest_path,
    get_custom_model_root_path,
    get_custom_model_weights_path,
)
from ..workloads.constants import (
    CANONICAL_NAME_LABEL,
    DISPLAY_NAME_ANNOTATION,
    MODEL_NAME_LABEL,
    MODEL_SOURCE_TYPE_LABEL,
)
from ..workloads.enums import ModelSourceType
from .constants import (
    AIM_BASE_MODEL_NAME,
    AIM_BASE_MODEL_SCOPE,
    AIM_PROFILE_POLL_INTERVAL_SECONDS,
    AIM_PROFILE_WAIT_TIMEOUT_SECONDS,
    CANONICAL_REPO_ID_ANNOTATION,
    COMPONENT_ID_ANNOTATION,
    DEFAULT_AIM_DEPLOYMENT_IMAGE_REF,
    HF_MAX_RESPONSE_BYTES,
    HF_REQUEST_TIMEOUT,
    IMPORT_ERROR_ANNOTATION,
    IMPORT_STATE_ANNOTATION,
    MINIO_CREDENTIALS_ACCESS_KEY_KEY,
    MINIO_CREDENTIALS_SECRET_KEY_KEY,
    MINIO_CREDENTIALS_SECRET_NAME,
    MODEL_DISPLAY_NAME_ANNOTATION,
    REVISION_ANNOTATION,
    SOURCE_DESCRIPTION_ANNOTATION,
    SOURCE_SHA_ANNOTATION,
    SOURCE_TAGS_ANNOTATION,
    SOURCE_URI_ANNOTATION,
)
from .gateway import (
    find_aim_profile_for_model,
    list_aim_profiles,
    list_base_role_profiles,
    patch_aim_profile,
    wait_for_aim_profile,
)
from .manifest import (
    ManifestDocument,
    manifest_write_lock,
    read_manifest_from_s3,
    upsert_manifest_documents,
    write_manifest_to_s3,
)
from .schemas import (
    CustomModelOnboardStatus,
    CustomModelPatchRequest,
    CustomModelPatchResponse,
    CustomModelResponse,
    OnboardRequest,
    PreviewRequest,
    PreviewResponse,
    RuntimeProfileOptions,
)
from .utils import (
    build_copy_onboard_request,
    build_description,
    build_display_metadata_patch,
    build_display_name,
    classify_siblings,
    display_metadata_response_from_model,
    extract_onboard_repo_id,
    extract_overrides_image,
    get_layout_hint,
    hub_request_args,
    next_copy_display_name,
    normalize_hf_source,
    raise_for_hub_status,
    resolve_custom_model_display_name,
    resolve_onboard_phase,
    validate_hf_repo_id,
)
from .weights_import import cancel_import, schedule_import

# The AIMProfile CRD kind name carried on the wire. The Pydantic resource
# model strips ``kind`` and ``apiVersion`` during validation, so the manifest
# emitter has to re-add them — without these the document is not reapplyable
# with ``kubectl apply -f manifest.yaml``.
_AIM_PROFILE_KIND = "AIMProfile"
_AIM_MODEL_KIND = "AIMModel"
# All AIM CRDs share one group/version; kubectl apply routes each manifest
# document to its own CRD.
_AIM_API_VERSION_FULL = f"{AIM_API_GROUP}/{AIM_API_VERSION}"

# Trim a slugified display name so the AIMModel CR name stays well within the
# K8s DNS-subdomain 253-char limit even after appending the 8-char id suffix.
_RESOURCE_NAME_SLUG_MAX_LENGTH = 200


def _manifest_contains_aim_model(
    documents: list[ManifestDocument],
    namespace: str,
    aim_model_name: str,
) -> bool:
    """Return True iff ``documents`` carries an AIMModel scaffold matching
    the namespace and name being onboarded.

    The S3 key is already namespace-scoped, but a manifest carrying an
    AIMModel doc with a different ``metadata.namespace`` or
    ``metadata.name`` is a corruption signal — checking both fields
    catches a manifest that was hand-edited or partially written by an
    older version, where the overall blob exists but the AIMModel half
    is missing or wrong.
    """
    for doc in documents:
        if doc.get("kind") != _AIM_MODEL_KIND:
            continue
        metadata = doc.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("name") != aim_model_name:
            continue
        doc_namespace = metadata.get("namespace")
        if doc_namespace is None or doc_namespace == namespace:
            return True
    return False


async def _get_hf_token(kube_client: KubernetesClient, namespace: str, secret_name: str) -> str:
    try:
        secret = await kube_client.core_v1.read_namespaced_secret(name=secret_name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            raise NotFoundException(f"Secret '{secret_name}' not found in namespace '{namespace}'") from e
        logger.error(f"Failed to read secret '{secret_name}' in namespace '{namespace}': {e}")
        raise ExternalServiceError(f"Failed to read secret '{secret_name}': {e.reason}") from e

    data = secret.data or {}
    if "token" not in data:
        raise ValidationException(
            message=f"Secret '{secret_name}' does not contain a 'token' key. "
            "Ensure the secret was created with a 'token' key holding the HF access token."
        )

    try:
        token = base64.b64decode(data["token"], validate=True).decode("utf-8").strip()
    except Exception as e:
        raise ValidationException(
            message=f"Secret '{secret_name}' has an invalid 'token' value: {type(e).__name__}"
        ) from e
    if not token:
        raise ValidationException(
            message=f"Secret '{secret_name}' contains an empty 'token' value. "
            "The 'token' key must hold a non-empty Hugging Face access token."
        )
    return token


async def _get_hub_response(repo_id: str, url: str, params: dict, headers: dict) -> tuple[int, bytes]:
    try:
        async with httpx.AsyncClient(timeout=HF_REQUEST_TIMEOUT) as client:
            async with client.stream("GET", url, params=params, headers=headers) as response:
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > HF_MAX_RESPONSE_BYTES:
                        raise ExternalServiceError(
                            f"Hugging Face Hub response for '{repo_id}' exceeded {HF_MAX_RESPONSE_BYTES} bytes."
                        )
                    chunks.append(chunk)
                return response.status_code, b"".join(chunks)
    except httpx.TimeoutException as e:
        raise ExternalServiceError(f"Timed out contacting Hugging Face Hub for '{repo_id}'") from e
    except httpx.RequestError as e:
        raise ExternalServiceError(
            f"Network error contacting Hugging Face Hub for '{repo_id}': {type(e).__name__}"
        ) from e


async def _fetch_hub_model(repo_id: str, revision: str | None, token: str | None) -> dict:
    logger.debug(f"Fetching Hub metadata for {repo_id}@{revision or '<default-branch>'}")
    url, params, headers = hub_request_args(repo_id, revision, token)
    status_code, body = await _get_hub_response(repo_id, url, params, headers)
    raise_for_hub_status(status_code, repo_id, revision, token, body)
    try:
        payload = json.loads(body)
    except ValueError as e:
        raise ExternalServiceError(f"Hugging Face Hub returned an unparseable response for '{repo_id}'.") from e
    if not isinstance(payload, dict):
        raise ExternalServiceError(f"Hugging Face Hub returned an invalid response shape for '{repo_id}'.")
    siblings = payload.get("siblings")
    if siblings is not None and not isinstance(siblings, list):
        raise ExternalServiceError(f"Hugging Face Hub returned an invalid 'siblings' field for '{repo_id}'.")
    return payload


def _build_aim_base_model_manifest(*, namespace: str, image_ref: str, model_name: str = AIM_BASE_MODEL_NAME) -> dict:
    """Compose the namespace-scoped base-image AIMModel that emits derivable profiles."""
    metadata = K8sMetadata(name=model_name, namespace=namespace)
    return {
        "apiVersion": _AIM_API_VERSION_FULL,
        "kind": _AIM_MODEL_KIND,
        "metadata": metadata.model_dump(by_alias=True, exclude_none=True),
        "spec": {"image": image_ref},
    }


def _base_model_name_from_image_ref(image_ref: str) -> str:
    """Resolve the namespace base-model name from a selected base image ref.

    Use the repository tail directly as ``derivedFrom.modelRef.name``.
    Invalid or empty refs fall back to the legacy default (``aim-base``).
    """
    try:
        repository, _ = parse_container_image_repository_and_tag(image_ref)
    except ValueError:
        return AIM_BASE_MODEL_NAME
    model_name = repository.rsplit("/", 1)[-1].strip()
    if not model_name:
        return AIM_BASE_MODEL_NAME
    return model_name


async def ensure_namespace_aim_base_model(
    kube_client: KubernetesClient,
    namespace: str,
    image_ref: str | None = None,
    model_name: str | None = None,
) -> str:
    """Idempotently provision the base-image AIMModel BYOM ``derivedFrom`` needs.

    When ``image_ref`` is not supplied, the base image is resolved from the
    cluster's detected accelerators rather than a static default.
    """
    if AIM_BASE_MODEL_SCOPE != "Namespace":
        return AIM_BASE_MODEL_NAME

    if image_ref is None:
        image_ref = await get_cluster_base_image_ref(kube_client)
    if model_name is None:
        model_name = _base_model_name_from_image_ref(image_ref)

    existing = await aims_gateway.get_aim_model(kube_client, namespace, model_name)
    if existing is not None:
        current_image_ref = (existing.spec.image or "").strip()
        if current_image_ref != image_ref:
            await aims_gateway.patch_aim_model(
                kube_client,
                namespace,
                model_name,
                {"spec": {"image": image_ref}},
            )
            logger.info(
                f"Re-pointed base-image AIMModel {model_name} in namespace {namespace} "
                f"from {current_image_ref!r} to {image_ref!r}"
            )
        return model_name

    manifest = _build_aim_base_model_manifest(namespace=namespace, image_ref=image_ref, model_name=model_name)
    try:
        await aims_gateway.create_aim_model(kube_client, namespace, manifest)
        logger.info(f"Provisioned base-image AIMModel {model_name} in namespace {namespace}")
    except ConflictException:
        logger.debug(f"Base-image AIMModel {model_name} already exists in namespace {namespace} after create race")
    return model_name


# Keys in spec.profiles.overrides that the onboard/edit flow owns and stamps
# itself — model identity, runtime image, and BYO weights. Any same-named key
# in a client-supplied customProfile is dropped before these authoritative
# values are written, so the opaque pass-through cannot spoof the model
# identity or repoint the weights. Both snake_case and camelCase spellings are
# stripped because customProfile is opaque and may arrive in either casing.
_OVERRIDES_RESERVED_KEYS = (
    "aim_id",
    "aimId",
    "model_id",
    "modelId",
    "image",
    "model_sources",
    "modelSources",
)


def _normalize_engine_env(custom_profile: dict[str, Any] | None) -> dict[str, Any] | None:
    """If ``engineEnv`` is a list of ``{name, value}`` entries, rewrite it as a string map."""
    if not custom_profile or not isinstance(custom_profile.get("engineEnv"), list):
        return custom_profile
    normalized = dict(custom_profile)
    normalized["engineEnv"] = env_entries_to_map(normalized["engineEnv"])
    return normalized


def build_overrides_payload(
    *,
    custom_profile: dict[str, Any] | None,
    repo_id: str,
    image: str,
    model_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compose a ``spec.profiles.overrides`` payload from opaque customProfile fields plus the authoritative identity, image, and weights.

    Client ``customProfile`` keys pass through verbatim (aim-engine validates
    shape at admission); the reserved identity/image/weights keys are always
    stamped by the server in their camelCase CRD spelling so the result is
    applyable both through ``ProfileOverrides.model_validate`` (onboard) and as
    a raw JSON merge-patch body (edit). ``null`` values inside ``customProfile``
    are preserved so a merge-patch edit can delete (reset) an overridden field.
    """
    custom_profile = _normalize_engine_env(custom_profile)
    payload: dict[str, Any] = dict(custom_profile) if custom_profile else {}
    for reserved_key in _OVERRIDES_RESERVED_KEYS:
        payload.pop(reserved_key, None)
    payload.update(
        {
            "aimId": repo_id,
            "modelId": repo_id,
            "image": image,
            "modelSources": model_sources,
        }
    )
    return payload


def _runtime_override_fields(custom_profile: dict[str, Any] | None) -> dict[str, Any]:
    """Return only the opaque runtime knobs from a customProfile, dropping the server-owned identity/image/weights keys.

    The live AIMProfile derives identity, image, and weights from the AIMModel,
    so an edit must merge only the runtime tuning fields (engine, engineArgs,
    precision, etc.) onto ``AIMProfile.spec`` — never the reserved keys, which
    would clobber aim-engine-derived values. ``null`` values are preserved so a
    merge-patch can reset a field.
    """
    if not custom_profile:
        return {}
    normalized = _normalize_engine_env(custom_profile) or {}
    return {key: value for key, value in normalized.items() if key not in _OVERRIDES_RESERVED_KEYS}


# Runtime knobs persisted as maps under ``spec.profiles.overrides``. A JSON
# merge-patch deletes a map key only when the patch sets it to ``null``, so an
# edit that drops one key of several must carry an explicit ``null`` tombstone
# for it (see _tombstone_removed_map_keys).
_MERGE_PATCH_MAP_FIELDS = ("engineArgs", "engineEnv")


def _existing_overrides_map(model: AIMModelResource) -> dict[str, Any]:
    """Return the live ``spec.profiles.overrides`` as a camelCase dict, or ``{}``."""
    profiles = model.spec.profiles
    if profiles is None or profiles.overrides is None:
        return {}
    return profiles.overrides.model_dump(by_alias=True, exclude_none=True)


def _tombstone_removed_map_keys(
    custom_profile: dict[str, Any] | None,
    existing_overrides: dict[str, Any],
) -> dict[str, Any] | None:
    """Add explicit ``null`` entries for runtime-map keys the edit dropped.

    RFC 7396 merge-patch removes a map key only when the patch sets it to
    ``null``; a key merely absent from the patch is left intact. So removing one
    of several ``engineArgs``/``engineEnv`` pairs in the edit form must send the
    surviving keys *plus* a ``null`` tombstone for each dropped key, or the
    deletion silently fails to persist. A whole-field reset (incoming ``null``)
    and a never-set field need no tombstones.
    """
    if not custom_profile:
        return custom_profile
    normalized = _normalize_engine_env(custom_profile) or {}
    result = dict(normalized)
    for field in _MERGE_PATCH_MAP_FIELDS:
        new_value = result.get(field)
        existing_value = existing_overrides.get(field)
        if not isinstance(new_value, dict) or not isinstance(existing_value, dict):
            continue
        removed_keys = existing_value.keys() - new_value.keys()
        if removed_keys:
            result[field] = {**new_value, **dict.fromkeys(removed_keys, None)}
    return result


def _build_custom_aim_model_manifest(
    *,
    namespace: str,
    resource_name: str,
    source: OnboardRequest,
    source_uri: str,
    submitter: str,
    component_id: str,
    base_model_name: str = AIM_BASE_MODEL_NAME,
) -> dict:
    """Build a profiles-only v1alpha2 AIMModel manifest with image-family base derivation and stamped repo/image/weights/customProfile overrides."""
    display_label_value = sanitize_label_value(source.display_name)
    canonical_label_value = sanitize_label_value(source.repo_id)

    labels: dict[str, str] = {
        MODEL_NAME_LABEL: display_label_value,
        CANONICAL_NAME_LABEL: canonical_label_value,
        MODEL_SOURCE_TYPE_LABEL: ModelSourceType.CUSTOM,
    }

    annotations: dict[str, str] = {
        SUBMITTER_ANNOTATION: submitter,
        DISPLAY_NAME_ANNOTATION: source.display_name,
        MODEL_DISPLAY_NAME_ANNOTATION: source.display_name,
        CANONICAL_REPO_ID_ANNOTATION: source.repo_id,
        COMPONENT_ID_ANNOTATION: component_id,
        SOURCE_URI_ANNOTATION: source_uri,
        REVISION_ANNOTATION: source.revision,
        SOURCE_SHA_ANNOTATION: source.sha,
        SOURCE_DESCRIPTION_ANNOTATION: source.description,
        SOURCE_TAGS_ANNOTATION: json.dumps(source.tags),
    }

    weights_source = AIMModelSource(model_id=source.repo_id, source_uri=source_uri)
    # S3 credentials are always required so aim-engine's check-size job can
    # connect to MinIO when reconciling the AIMArtifact for this S3-backed source.
    weights_source.env = [
        {
            "name": "AWS_ACCESS_KEY_ID",
            "valueFrom": {
                "secretKeyRef": {"name": MINIO_CREDENTIALS_SECRET_NAME, "key": MINIO_CREDENTIALS_ACCESS_KEY_KEY}
            },
        },
        {
            "name": "AWS_SECRET_ACCESS_KEY",
            "valueFrom": {
                "secretKeyRef": {"name": MINIO_CREDENTIALS_SECRET_NAME, "key": MINIO_CREDENTIALS_SECRET_KEY_KEY}
            },
        },
        {
            "name": "AWS_ENDPOINT_URL",
            "value": MINIO_URL,
        },
    ]
    if source.hf_token_secret_name:
        weights_source.env.append(
            {
                "name": "HF_TOKEN",
                "valueFrom": {"secretKeyRef": {"name": source.hf_token_secret_name, "key": "token"}},
            }
        )
    overrides_payload = build_overrides_payload(
        custom_profile=source.custom_profile,
        repo_id=source.repo_id,
        image=source.image,
        model_sources=[weights_source.model_dump(by_alias=True, exclude_none=True)],
    )

    profiles = AIMModelProfilesSpec(
        derived_from=AIMModelProfilesDerivedFrom(
            selector=ProfileSelector(
                role="base",
                model_ref=ProfileSelectorModelRef(name=base_model_name, scope=AIM_BASE_MODEL_SCOPE),
            ),
        ),
        version_policy="all",
        overrides=ProfileOverrides.model_validate(overrides_payload),
    )

    metadata = K8sMetadata(
        name=resource_name,
        namespace=namespace,
        labels=labels,
        annotations=annotations,
    )

    return {
        "apiVersion": _AIM_API_VERSION_FULL,
        "kind": _AIM_MODEL_KIND,
        "metadata": metadata.model_dump(by_alias=True, exclude_none=True),
        "spec": {"profiles": profiles.model_dump(by_alias=True, exclude_none=True)},
    }


async def _sync_manifest_to_s3(minio_client: MinioClient, object_key: str, aim_model_manifest: dict) -> None:
    """Upsert the AIMModel doc into the namespace S3 manifest under lock, preserving any existing AIMProfile document."""
    async with manifest_write_lock(MINIO_BUCKET, object_key):
        await _upsert_manifest_to_s3_unlocked(minio_client, object_key, aim_model_manifest)


async def _upsert_manifest_to_s3_unlocked(minio_client: MinioClient, object_key: str, aim_model_manifest: dict) -> None:
    """Read → upsert a single AIMModel doc → write, without acquiring the lock.

    Thin wrapper over :func:`_upsert_manifest_documents_to_s3_unlocked` for the
    common single-document case (onboard sync, metadata-only edit).
    """
    await _upsert_manifest_documents_to_s3_unlocked(minio_client, object_key, [aim_model_manifest])


async def _upsert_manifest_documents_to_s3_unlocked(
    minio_client: MinioClient, object_key: str, documents: list[dict]
) -> None:
    """Read → upsert one or more documents → write the manifest object *without* acquiring the lock.

    Callers that must include a cluster mutation inside the same critical
    section (so the durable mirror cannot invert relative to the
    authoritative CR) hold ``manifest_write_lock`` themselves and invoke
    this directly — ``manifest_write_lock`` is a non-reentrant
    ``asyncio.Lock``, so re-entering via :func:`_sync_manifest_to_s3`
    would deadlock.

    Documents are matched on ``(kind, name)`` by
    :func:`upsert_manifest_documents`, so passing both the AIMModel and its
    AIMProfile in one call refreshes both in a single read-modify-write —
    used by the runtime-profile edit path, which mutates both CRs under one
    lock.
    """
    existing = await read_manifest_from_s3(minio_client, MINIO_BUCKET, object_key)
    merged = upsert_manifest_documents(existing=existing, new_documents=documents)
    await write_manifest_to_s3(minio_client, MINIO_BUCKET, object_key, merged)


def _custom_model_weights_uri(namespace: str, resource_name: str) -> str:
    """Compose the s3:// URI inference loads weights from for a BYOM AIMModel."""
    return f"s3://{MINIO_BUCKET}/{get_custom_model_weights_path(namespace, resource_name)}"


async def _verify_request_matches_hub(request: OnboardRequest, token: str | None) -> None:
    """Re-fetch Hub and reject onboard when repo_id, revision, or sha no longer match preview."""
    hub_data = await _fetch_hub_model(request.repo_id, request.revision, token)
    hub_sha = hub_data.get("sha")
    if not hub_sha:
        raise ExternalServiceError(f"Hugging Face Hub did not return a SHA for '{request.repo_id}'.")
    if hub_sha != request.sha:
        raise ValidationException(
            message=(
                f"Submitted sha '{request.sha}' does not match the current Hub sha "
                f"'{hub_sha}' for '{request.repo_id}' at revision '{request.revision}'. "
                "Re-preview the model to refresh the pin."
            )
        )


def _read_import_signal(
    cr: AIMModelResource,
    artifact: AIMArtifactResource | None,
) -> tuple[str | None, str | None]:
    """Return (phase, last_error) for the weight import.

    Prefers the workbench-owned import annotations on the CR; falls back to the
    AIMArtifact for models onboarded before annotation-based import existed.
    """
    annotations = cr.metadata.annotations or {}
    import_state = annotations.get(IMPORT_STATE_ANNOTATION)
    if import_state:
        return import_state, annotations.get(IMPORT_ERROR_ANNOTATION) or None

    if artifact is not None:
        return artifact.status.phase or None, artifact.status.last_error or None

    return None, None


def _compose_onboard_status(
    cr: AIMModelResource,
    profile: AIMProfileResource | None,
    artifact: AIMArtifactResource | None,
) -> CustomModelOnboardStatus:
    """Derive the composed onboard status from the contributing signals.

    ``profile_ready`` signals that the model has at least one deployable
    AIMProfile emitted by aim-engine.  For spec.profiles derivation models
    (the current onboard contract) aim-engine does not stamp the legacy
    ``deployment-image-ref`` annotation — profile existence alongside
    AIMModel Ready is the correct readiness signal.

    The weight-import signal (Importing/Ready/Failed) is read from
    the workbench-owned import annotations on the CR. When present it takes
    precedence over any AIMArtifact, which the onboard flow no longer uses to
    drive weight import; the AIMArtifact read remains a fallback for models
    that predate the annotation-based import.
    """
    aim_model_status = str(cr.status.status) if (cr.status and cr.status.status) else ""

    # For derived profiles (spec.profiles) aim-engine never stamps the legacy
    # deployment-image-ref annotation — profile existence is sufficient.
    profile_ready = profile is not None

    artifact_phase, artifact_last_error = _read_import_signal(cr, artifact)

    return CustomModelOnboardStatus(
        state=resolve_onboard_phase(aim_model_status, profile_ready, artifact_phase),
        status=aim_model_status,
        template_ready=profile_ready,
        artifact_phase=artifact_phase,
        artifact_last_error=artifact_last_error,
    )


def _to_custom_model_response(
    cr: AIMModelResource,
    profile: AIMProfileResource | None = None,
    artifact: AIMArtifactResource | None = None,
) -> CustomModelResponse:
    """Convert an AIMModel CR into a CustomModelResponse with composed status.

    ``profile`` and ``artifact`` are optional; pass them when available to
    populate the full composed status. The list endpoint fetches both in bulk
    to avoid N+1 Kubernetes calls.
    """
    composed_status = _compose_onboard_status(cr, profile, artifact)

    return CustomModelResponse(
        metadata=cr.metadata,
        spec=cr.spec,
        status=cr.status,
        profile=profile,
        phase=composed_status,
    )


async def _create_new_custom_model_from_onboard_request(
    *,
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    submitter: str,
    request: OnboardRequest,
    name_suffix: str | None,
    source_uri: str | None = None,
    base_model_name: str = AIM_BASE_MODEL_NAME,
) -> str:
    """Create a new custom AIMModel from an onboarding payload and sync manifest."""
    slug = slugify(request.display_name)[:_RESOURCE_NAME_SLUG_MAX_LENGTH] or "custom-model"
    name_parts = [slug]
    if name_suffix:
        name_parts.append(name_suffix)
    name_parts.append(uuid4().hex[:8])
    resource_name = "-".join(name_parts)

    manifest = _build_custom_aim_model_manifest(
        namespace=namespace,
        resource_name=resource_name,
        source=request,
        source_uri=source_uri or _custom_model_weights_uri(namespace, resource_name),
        submitter=submitter,
        component_id=str(uuid4()),
        base_model_name=base_model_name,
    )

    await aims_gateway.create_aim_model(kube_client, namespace, manifest)
    object_key = get_custom_model_manifest_path(namespace, resource_name)
    try:
        await _sync_manifest_to_s3(minio_client, object_key, manifest)
    except Exception as s3_error:
        # S3 is a hard precondition for finalize_aim_profile_for_onboarded_model, so
        # a CR without its manifest would cause finalization to fail. Roll back the
        # CR so the caller can retry cleanly from a known-good state.
        logger.warning(
            f"Created AIMModel {resource_name} in {namespace} but S3 manifest sync failed; "
            f"rolling back CR so the operation is safe to retry. Error: {s3_error}"
        )
        try:
            await aims_gateway.delete_aim_model(kube_client, namespace, resource_name)
        except Exception as rollback_error:
            logger.warning(
                f"Failed to roll back AIMModel {resource_name} after S3 sync failure; "
                f"the CR exists without an S3 manifest and will need manual cleanup. "
                f"Error: {rollback_error}"
            )
        raise

    return resource_name


async def list_custom_models(
    kube_client: KubernetesClient,
    namespace: str,
) -> list[CustomModelResponse]:
    """Return all custom AIMModel CRs in the namespace with composed status.

    Custom models are identified by the ``MODEL_SOURCE_TYPE_LABEL=custom``
    label, which is stamped unconditionally during onboarding and used as a
    server-side label selector so the API server filters results before they
    reach the service layer.

    Profiles and artifacts are bulk-fetched (two namespace-wide list calls)
    so the per-model status composition is O(1) lookups with no N+1 API calls.
    """
    custom_crs, profiles, artifacts = await asyncio.gather(
        aims_gateway.list_aim_models(
            kube_client, namespace, label_selector=f"{MODEL_SOURCE_TYPE_LABEL}={ModelSourceType.CUSTOM}"
        ),
        list_aim_profiles(kube_client, namespace),
        aims_gateway.list_aim_artifacts(kube_client, namespace),
    )

    # Index by model CR name for O(1) lookup inside the comprehension.
    profiles_by_model: dict[str, AIMProfileResource] = {
        p.metadata.labels.get(AIM_MODEL_LABEL_KEY, ""): p
        for p in profiles
        if p.metadata.labels.get(AIM_MODEL_LABEL_KEY)
    }

    artifacts_by_model: dict[str, AIMArtifactResource] = {
        a.metadata.labels.get(AIM_MODEL_LABEL_KEY, ""): a
        for a in artifacts
        if a.metadata.labels.get(AIM_MODEL_LABEL_KEY)
    }

    return [
        _to_custom_model_response(
            cr,
            profile=profiles_by_model.get(cr.metadata.name),
            artifact=artifacts_by_model.get(cr.metadata.name),
        )
        for cr in custom_crs
    ]


async def get_custom_model(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str,
) -> CustomModelResponse:
    """Return the full detail for a single onboarded custom model.

    Fetches the AIMModel CR by name, verifies it is a custom model, then
    concurrently fetches its AIMProfile and AIMArtifact to compose the full
    onboarding status in a single response.

    Raises:
        NotFoundException: when no AIMModel with ``model_name`` exists in
            ``namespace``, or the CR exists but is not a custom model
            (missing REVISION_ANNOTATION).
    """
    cr = await aims_gateway.get_aim_model(kube_client, namespace, model_name)
    if cr is None or (cr.metadata.annotations or {}).get(REVISION_ANNOTATION) is None:
        raise NotFoundException(f"Custom model '{model_name}' not found in project '{namespace}'.")

    profile_list, artifact_list = await asyncio.gather(
        list_aim_profiles(kube_client, namespace, model_name=model_name),
        aims_gateway.list_aim_artifacts(kube_client, namespace, model_name=model_name),
    )
    profile = profile_list[0] if profile_list else None
    artifact = artifact_list[0] if artifact_list else None

    return _to_custom_model_response(cr, profile=profile, artifact=artifact)


async def get_base_runtime_profile_options(
    kube_client: KubernetesClient,
    namespace: str,
) -> RuntimeProfileOptions:
    """Return the runtime options a custom model will support in this namespace.

    Derived from the base-image model's base-role AIMProfiles: a BYOM model
    inherits exactly that runtime matrix, so onboarding should offer (and
    preset) these accelerator/precision/count/optimization values rather than a
    free-form precision the AIMModel CRD silently prunes. Returns empty lists
    when the base model has not emitted profiles yet, so the client can fall
    back to static defaults.
    """
    profiles = await list_base_role_profiles(kube_client, namespace)

    accelerator_models: set[str] = set()
    precisions: set[str] = set()
    accelerator_counts: set[int] = set()
    optimization_classes: set[str] = set()
    for profile in profiles:
        spec = profile.spec
        if spec.accelerator_model:
            accelerator_models.add(spec.accelerator_model)
        if spec.precision:
            precisions.add(spec.precision)
        if spec.accelerator_count is not None and spec.accelerator_count > 0:
            accelerator_counts.add(spec.accelerator_count)
        if spec.type:
            optimization_classes.add(spec.type)

    return RuntimeProfileOptions(
        accelerator_models=sorted(accelerator_models),
        precisions=sorted(precisions),
        accelerator_counts=sorted(accelerator_counts),
        optimization_classes=sorted(optimization_classes),
    )


async def copy_custom_model(
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    source_model_name: str,
    submitter: str,
) -> None:
    """Copy an onboarded custom model into a new model in the same project."""
    source = await aims_gateway.get_aim_model(kube_client, namespace, source_model_name)
    source_labels = (source.metadata.labels if source is not None else None) or {}
    is_custom_model = source_labels.get(MODEL_SOURCE_TYPE_LABEL) == ModelSourceType.CUSTOM
    source_annotations = (source.metadata.annotations if source is not None else None) or {}
    has_onboard_stamps = (
        source_annotations.get(REVISION_ANNOTATION) is not None
        and source_annotations.get(SOURCE_SHA_ANNOTATION) is not None
    )
    if source is None or not is_custom_model or not has_onboard_stamps:
        raise NotFoundException(f"Custom model '{source_model_name}' not found in project '{namespace}'.")

    custom_crs = await aims_gateway.list_aim_models(
        kube_client,
        namespace,
        label_selector=f"{MODEL_SOURCE_TYPE_LABEL}={ModelSourceType.CUSTOM}",
    )
    source_display_name = resolve_custom_model_display_name(source)
    existing_display_names = {resolve_custom_model_display_name(cr) for cr in custom_crs}
    copy_display_name = next_copy_display_name(source_display_name, existing_display_names)
    copy_request = build_copy_onboard_request(source, copy_display_name)
    source_uri = (source.metadata.annotations or {}).get(SOURCE_URI_ANNOTATION)
    await _create_new_custom_model_from_onboard_request(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=namespace,
        submitter=submitter,
        request=copy_request,
        name_suffix=None,
        source_uri=source_uri,
    )


async def onboard_custom_model_source(
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    submitter: str,
    request: OnboardRequest,
) -> None:
    """Upsert the AIMModel CR + S3 manifest for a previewed HF source.

    Conflict key is the sanitized display name within the namespace, scoped by
    the HF repo (modelSources[0].modelId). Idempotent on (display_name, repo_id);
    a same-name request pointing at a different HF repo raises ConflictException
    so the FE prompts for a new name. The S3 sourceUri is derived from the
    AIMModel CR's `metadata.name`, so it isn't part of the conflict key (it
    would be unique per import by construction).

    Ordering: the AIMModel CR is the source of truth; the S3 manifest is a DR
    mirror. We write k8s first, then S3. On the **create** path, an S3 failure
    rolls back the CR so the next call retries from a clean slate. On the
    **patch** path the CR is preserved as the authority; the next call re-syncs
    the mirror.

    Once the CR and manifest are in place, a detached background task imports the
    HuggingFace weights into the model's S3 prefix; the call returns without
    waiting for it. A re-onboard supersedes any in-flight import for the model.
    """
    validate_hf_repo_id(request.repo_id)

    # Resolve the HF token once: it authorizes both the Hub re-verify below and
    # the detached weight import scheduled at the end of each branch.
    token = (
        await _get_hf_token(kube_client, namespace, request.hf_token_secret_name)
        if request.hf_token_secret_name
        else None
    )

    await _verify_request_matches_hub(request, token)
    await _verify_minio_credentials_secret(kube_client, namespace)
    base_model_name = await ensure_namespace_aim_base_model(
        kube_client,
        namespace,
    )
    display_label_value = sanitize_label_value(request.display_name)

    selector = f"{MODEL_NAME_LABEL}={display_label_value},{MODEL_SOURCE_TYPE_LABEL}={ModelSourceType.CUSTOM}"
    existing = await aims_gateway.find_aim_model_by_label(kube_client, namespace, selector)

    if existing is not None:
        existing_repo_id = extract_onboard_repo_id(existing)
        if existing_repo_id != request.repo_id:
            raise ConflictException(
                f"A custom model named '{request.display_name}' already exists in namespace '{namespace}' with a different source."
            )

        resource_name = existing.metadata.name
        existing_annotations = existing.metadata.annotations or {}
        component_id = existing_annotations.get(COMPONENT_ID_ANNOTATION) or str(uuid4())
        manifest = _build_custom_aim_model_manifest(
            namespace=namespace,
            resource_name=resource_name,
            source=request,
            source_uri=_custom_model_weights_uri(namespace, resource_name),
            submitter=submitter,
            component_id=component_id,
            base_model_name=base_model_name,
        )
        patch_body = {
            "metadata": {
                "labels": manifest["metadata"].get("labels", {}),
                "annotations": manifest["metadata"].get("annotations", {}),
            },
            "spec": manifest["spec"],
        }
        await aims_gateway.patch_aim_model(kube_client, namespace, resource_name, patch_body)
        object_key = get_custom_model_manifest_path(namespace, resource_name)
        try:
            await _sync_manifest_to_s3(minio_client, object_key, manifest)
        except Exception as s3_error:
            logger.warning(
                f"Patched AIMModel {resource_name} in {namespace} but S3 mirror sync failed; "
                f"the CR is authoritative and a retry may re-sync the manifest. Error: {s3_error}"
            )
            raise
        schedule_import(
            kube_client=kube_client,
            minio_client=minio_client,
            namespace=namespace,
            resource_name=resource_name,
            repo_id=request.repo_id,
            revision=request.revision,
            token=token,
        )
        logger.info(f"Patched existing custom AIMModel {resource_name} in namespace {namespace}")
        return

    resource_name = await _create_new_custom_model_from_onboard_request(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=namespace,
        submitter=submitter,
        request=request,
        name_suffix="import",
        base_model_name=base_model_name,
    )

    schedule_import(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=namespace,
        resource_name=resource_name,
        repo_id=request.repo_id,
        revision=request.revision,
        token=token,
    )
    logger.info(f"Created custom AIMModel {resource_name} in namespace {namespace}")


async def delete_onboarded_model(
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    name: str,
) -> None:
    """Delete an onboarded custom model: the AIMModel CR and its S3 object tree.

    Safety guard: if any AIMService in the namespace references this AIMModel,
    the deletion is refused with a ConflictException naming the blocking
    services so the caller can tear those deployments down first.

    Responsibility boundary: AIWB owns only the AIMModel CR and the
    namespace-scoped S3 tree (manifest + weights). The derived AIMProfileSet /
    AIMProfile are owner-referenced by the AIMModel and garbage-collected by
    aim-engine via Kubernetes owner references — AIWB never deletes them.
    Profile caches and artifacts are tied to AIMService lifecycle and
    aim-engine's reuse semantics, so they are not touched here either.

    Ordering: cancel any in-flight weight import first (so no upload races the
    cleanup), then delete the CR (the live intent), then the S3 tree. An S3
    failure after a successful CR delete is logged as a recoverable warning and
    does not fail the request — the live record is already gone and the orphaned
    objects can be reclaimed out-of-band. The importer also re-checks the CR
    before each upload, so even a late-landing cancellation cannot keep writing
    objects under a prefix the delete already swept.

    Raises:
        NotFoundException: when no AIMModel named ``name`` exists in
            ``namespace``, or the CR exists but is not a custom onboarded model.
        ConflictException: when one or more AIMServices still reference the model.
        ExternalServiceError: when a Kubernetes API call fails for any reason
            other than a 404 (surfaced as 502 to match the OpenAPI contract).
    """
    try:
        cr = await aims_gateway.get_aim_model(kube_client, namespace, name)
    except ApiException as e:
        logger.error(f"Failed to read AIMModel {name} in namespace {namespace}: {e}")
        raise ExternalServiceError(f"Failed to read AIMModel '{name}': {e.reason}") from e
    if cr is None or (cr.metadata.annotations or {}).get(REVISION_ANNOTATION) is None:
        raise NotFoundException(f"Custom model '{name}' not found in project '{namespace}'.")

    try:
        blocking = await aims_gateway.list_aim_services_for_model(kube_client, namespace, name)
    except ApiException as e:
        logger.error(f"Failed to list AIMServices referencing {name} in namespace {namespace}: {e}")
        raise ExternalServiceError(f"Failed to check active deployments for '{name}': {e.reason}") from e
    if blocking:
        blocking_names = ", ".join(sorted(service.metadata.name for service in blocking))
        raise ConflictException(
            f"Custom model '{name}' cannot be deleted while {len(blocking)} AIMService(s) "
            f"reference it: {blocking_names}. Delete those deployments first."
        )

    # Stop any in-flight import before removing the CR so the importer cannot
    # repopulate the S3 tree we are about to sweep.
    await cancel_import(namespace, name)

    try:
        await aims_gateway.delete_aim_model(kube_client, namespace, name)
    except ApiException as e:
        logger.error(f"Failed to delete AIMModel {name} in namespace {namespace}: {e}")
        raise ExternalServiceError(f"Failed to delete AIMModel '{name}': {e.reason}") from e

    root_prefix = get_custom_model_root_path(namespace, name)
    try:
        await delete_from_s3(root_prefix, minio_client, name)
    except Exception as s3_error:
        logger.warning(
            f"Deleted AIMModel {name} in {namespace} but S3 cleanup at '{root_prefix}' failed; "
            f"the live record is gone and the orphaned objects can be reclaimed out-of-band. "
            f"Error: {s3_error}"
        )
        return

    logger.info(f"Deleted custom AIMModel {name} and S3 tree '{root_prefix}' in namespace {namespace}")


async def preview_model_source(
    kube_client: KubernetesClient,
    namespace: str,
    request: PreviewRequest,
) -> PreviewResponse:
    repo_id, source_revision = normalize_hf_source(request.source)

    token: str | None = None
    if request.hf_token_secret_name:
        token = await _get_hf_token(kube_client, namespace, request.hf_token_secret_name)

    hub_data = await _fetch_hub_model(repo_id, source_revision, token)

    if hub_data.get("gated") and not token:
        raise ForbiddenException(
            f"Model '{repo_id}' is a gated repository. "
            "Provide a Hugging Face token via 'hfTokenSecretName' to access it."
        )

    siblings: list[dict] = hub_data.get("siblings") or []
    all_weight_files = classify_siblings(siblings)
    weight_files = [wf for wf in all_weight_files if wf.role != "config"]
    config_files = [wf for wf in all_weight_files if wf.role == "config"]

    gated_value = hub_data.get("gated", False)
    gated = bool(gated_value)
    hf_token_recommended = gated or bool(hub_data.get("private", False))

    sha = hub_data.get("sha")
    if not sha:
        logger.error(
            "Hub returned 200 without a SHA for {} (revision={}). Response keys: {}",
            repo_id,
            source_revision,
            sorted(hub_data.keys()),
        )
        raise ExternalServiceError(f"Hugging Face Hub did not return a SHA for '{repo_id}'.")

    resolved_revision = source_revision or sha
    display_name = build_display_name(hub_data, repo_id)
    description = build_description(hub_data)
    canonical_repo_id = hub_data.get("id") or repo_id

    return PreviewResponse(
        repo_id=canonical_repo_id,
        revision=resolved_revision,
        sha=sha,
        display_name=display_name,
        description=description,
        tags=hub_data.get("tags") or [],
        pipeline_tag=hub_data.get("pipeline_tag"),
        gated=gated,
        hf_token_recommended=hf_token_recommended,
        weight_files=weight_files + config_files,
        layout_hint=get_layout_hint(weight_files),
    )


async def _verify_minio_credentials_secret(kube_client: KubernetesClient, namespace: str) -> None:
    """Raise ValidationException (400) when the MinIO credentials secret is absent.

    aim-engine's check-size job requires this secret to authenticate to MinIO
    when caching weights for a custom model. Failing here at onboard time gives
    the caller a clear, actionable error rather than a silent pod startup failure
    later that is hard to trace back to a missing secret.
    """
    try:
        await kube_client.core_v1.read_namespaced_secret(name=MINIO_CREDENTIALS_SECRET_NAME, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            raise ValidationException(
                f"Secret '{MINIO_CREDENTIALS_SECRET_NAME}' not found in namespace '{namespace}'. "
                "This secret must be provisioned before custom models can be onboarded. "
                "Contact your platform administrator to ensure MinIO credentials are configured for this namespace."
            ) from e
        logger.error(f"Failed to read MinIO credentials secret in namespace '{namespace}': {e}")
        raise ExternalServiceError(
            f"Failed to verify MinIO credentials secret in namespace '{namespace}': {e.reason}"
        ) from e


def _profile_resource_to_manifest_document(profile: AIMProfileResource) -> ManifestDocument:
    """Render an AIMProfile as a re-applicable manifest doc, stripping server-owned status and metadata fields."""

    document = profile.model_dump(
        by_alias=True,
        exclude_none=True,
        exclude={
            "status": True,
            "metadata": {"uid", "creation_timestamp", "owner_references"},
        },
    )
    return {
        "apiVersion": _AIM_API_VERSION_FULL,
        "kind": _AIM_PROFILE_KIND,
        **document,
    }


def _model_resource_to_manifest_document(model: AIMModelResource) -> ManifestDocument:
    """Render a live AIMModel CR as a clean, reapplyable manifest document.

    Mirrors :func:`_profile_resource_to_manifest_document` but emits the
    AIMModel kind/apiVersion. Used by the display-metadata patch path to
    refresh the AIMModel document in the durable S3 manifest after a CR
    mutation; the same server-stamped fields (``status``, ``metadata.uid`` /
    ``creationTimestamp`` / ``ownerReferences``) are stripped so the record
    stays reapplyable into a freshly-installed cluster.

    A v1alpha2 custom AIMModel is profiles-shaped, but ``AIMModelSpec`` defaults
    the legacy ``image``/``modelSources``/``env`` fields to ``""``/``[]``/``[]``
    (not ``None``), so ``exclude_none`` alone would emit them alongside
    ``profiles`` and trip the CEL ``image XOR profiles`` rule on re-apply. Drop
    the empty legacy fields when the profiles shape is present so the durable
    record stays applyable — mirroring how the onboard builder emits a
    profiles-only spec.
    """
    document = model.model_dump(
        by_alias=True,
        exclude_none=True,
        exclude={
            "status": True,
            "metadata": {"uid", "creation_timestamp", "owner_references"},
        },
    )
    spec = document.get("spec")
    if isinstance(spec, dict) and spec.get("profiles"):
        for legacy_field in ("image", "modelSources", "env"):
            if not spec.get(legacy_field):
                spec.pop(legacy_field, None)
    return {
        "apiVersion": _AIM_API_VERSION_FULL,
        "kind": _AIM_MODEL_KIND,
        **document,
    }


async def _assert_display_name_available_for_patch(
    kube_client: KubernetesClient,
    namespace: str,
    display_name: str,
    resource_name: str,
) -> None:
    display_label_value = sanitize_label_value(display_name)
    selector = f"{MODEL_NAME_LABEL}={display_label_value},{MODEL_SOURCE_TYPE_LABEL}={ModelSourceType.CUSTOM}"
    try:
        existing = await aims_gateway.find_aim_model_by_label(kube_client, namespace, selector)
    except ApiException as e:
        logger.error(f"Failed to look up AIMModels in namespace {namespace} for display-name check: {e}")
        raise ExternalServiceError(f"Failed to verify display-name availability: {e.reason}") from e
    if existing is not None and existing.metadata.name != resource_name:
        raise ConflictException(f"A custom model named '{display_name}' already exists in namespace '{namespace}'.")


def _resolve_profile_image(request: CustomModelPatchRequest, model: AIMModelResource) -> str:
    """Resolve the deployment image for a runtime-profile edit.

    Prefer the explicit top-level ``image``, then ``customProfile.image`` (the
    request validator has already confirmed the two agree), then the image
    already recorded on the model's overrides. Guarantees a non-empty ref so the
    AIMProfile ``deployment-image-ref`` patch is well-formed.
    """
    if request.image:
        return request.image
    if request.custom_profile and request.custom_profile.get("image"):
        return request.custom_profile["image"]
    existing = extract_overrides_image(model)
    if existing:
        return existing
    raise ValidationException(
        message=(
            "Cannot edit the runtime profile without a container image: none was supplied "
            "and the model has no existing image override."
        )
    )


def _existing_model_source_dicts_for_profile_patch(model: AIMModelResource) -> list[dict[str, Any]]:
    """Return weights ``modelSources`` as camelCase dicts for a runtime-profile PATCH.

    BYO weights and identity must be carried verbatim from the live CR. If the
    AIMModel is not v1alpha2 profiles-shaped (no ``spec.profiles``) or overrides
    lack sources, returning an empty list would merge-patch empty ``modelSources``
    and corrupt the model — fail fast instead.
    """
    profiles = model.spec.profiles
    if profiles is None:
        raise ValidationException(
            message=(
                "Cannot edit the runtime profile: this AIMModel has no `spec.profiles` block "
                "(expected v1alpha2 profile derivation). Runtime edits are only supported for "
                "custom models onboarded through the current flow."
            )
        )
    overrides = profiles.overrides
    if not overrides.model_sources:
        raise ValidationException(
            message=(
                "Cannot edit the runtime profile: `spec.profiles.overrides.modelSources` "
                "is missing or empty, so weights cannot be preserved. Repair or re-onboard "
                "the model before editing its runtime settings."
            )
        )
    return [source.model_dump(by_alias=True, exclude_none=True) for source in overrides.model_sources]


async def patch_onboarded_model(
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    name: str,
    request: CustomModelPatchRequest,
) -> CustomModelPatchResponse:
    """Apply a partial update to a custom-onboarded model: display metadata and/or runtime profile.

    Display fields (display name, description, tags) patch the AIMModel
    annotations and labels. Runtime-profile fields (image, customProfile)
    rewrite ``spec.profiles.overrides`` and repatch the live AIMProfile
    (``deployment-image-ref`` annotation plus the runtime spec knobs) so the
    change takes effect without waiting for a controller reconcile. When both
    groups are present the AIMModel mutation is a single merge-patch and the S3
    mirror is refreshed in one read-modify-write, all under the manifest write
    lock, so the durable mirror never inverts relative to the authoritative CRs.

    Raises:
        ValidationException: empty request (no recognised field supplied); or a
            runtime-profile edit on an AIMModel without v1alpha2
            ``spec.profiles.overrides.modelSources`` (weights cannot be preserved).
        NotFoundException: model missing, or not a custom-onboarded model.
        ConflictException: requested display name already taken, or a runtime-
            profile edit was requested before aim-engine emitted the AIMProfile.
    """
    updates = request.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise ValidationException(
            message="At least one of displayName, description, tags, image, or customProfile must be provided."
        )

    metadata_updates = {key: value for key, value in updates.items() if key in ("display_name", "description", "tags")}
    profile_edit = "image" in updates or "custom_profile" in updates

    try:
        model = await aims_gateway.get_aim_model(kube_client, namespace, name)
    except ApiException as e:
        logger.error(f"Failed to read AIMModel {name} in namespace {namespace}: {e}")
        raise ExternalServiceError(f"Failed to read AIMModel '{name}': {e.reason}") from e
    if model is None:
        raise NotFoundException(f"Custom onboarded model '{name}' not found in namespace '{namespace}'")
    if (model.metadata.labels or {}).get(MODEL_SOURCE_TYPE_LABEL) != ModelSourceType.CUSTOM:
        raise NotFoundException(f"Custom onboarded model '{name}' not found in namespace '{namespace}'")

    if "display_name" in metadata_updates:
        await _assert_display_name_available_for_patch(kube_client, namespace, metadata_updates["display_name"], name)

    # Compose the AIMModel merge-patch: display metadata and/or the rewritten
    # profile overrides, in one body so both halves land atomically on the CR.
    patch_body: dict[str, Any] = {}
    if metadata_updates:
        patch_body.update(build_display_metadata_patch(metadata_updates))

    effective_image = ""
    profile_spec_patch: dict[str, Any] = {}
    if profile_edit:
        effective_image = _resolve_profile_image(request, model)
        # Tombstone keys the edit dropped so merge-patch actually deletes them
        # from the live engineArgs/engineEnv maps instead of silently keeping them.
        custom_profile = _tombstone_removed_map_keys(request.custom_profile, _existing_overrides_map(model))
        overrides_payload = build_overrides_payload(
            custom_profile=custom_profile,
            repo_id=extract_onboard_repo_id(model),
            image=effective_image,
            model_sources=_existing_model_source_dicts_for_profile_patch(model),
        )
        patch_body.setdefault("spec", {})["profiles"] = {"overrides": overrides_payload}
        profile_spec_patch = _runtime_override_fields(custom_profile)

    object_key = get_custom_model_manifest_path(namespace, name)

    async with manifest_write_lock(MINIO_BUCKET, object_key):
        # Resolve the live AIMProfile before mutating anything so a runtime-profile
        # edit on a not-yet-ready model fails (409) without a partial write.
        profile: AIMProfileResource | None = None
        if profile_edit:
            try:
                profile = await find_aim_profile_for_model(kube_client, namespace, name)
            except ApiException as e:
                logger.error(f"Failed to look up AIMProfile for {name} in namespace {namespace}: {e}")
                raise ExternalServiceError(f"Failed to look up AIMProfile for '{name}': {e.reason}") from e
            if profile is None:
                raise ConflictException(
                    f"Runtime profile for custom model '{name}' in project '{namespace}' is not ready yet; "
                    "wait for the model to finish importing before editing its runtime profile."
                )

        patched = await aims_gateway.patch_aim_model(kube_client, namespace, name, patch_body)
        documents = [_model_resource_to_manifest_document(patched)]

        if profile is not None:
            patched_profile = await patch_aim_profile(
                kube_client=kube_client,
                namespace=namespace,
                profile_name=profile.metadata.name,
                image_ref=effective_image,
                custom_profile_spec=profile_spec_patch or None,
            )
            documents.append(_profile_resource_to_manifest_document(patched_profile))

        try:
            await _upsert_manifest_documents_to_s3_unlocked(minio_client, object_key, documents)
        except Exception as s3_error:
            logger.warning(
                f"Patched custom AIMModel {name} in {namespace} but S3 mirror sync failed; "
                f"the CRs are authoritative and a subsequent patch will re-sync. Error: {s3_error}"
            )

    logger.info(
        f"Updated custom AIMModel {name} in namespace {namespace} "
        f"(metadata={bool(metadata_updates)}, profile={profile_edit})"
    )
    return display_metadata_response_from_model(patched)


async def finalize_aim_profile_for_onboarded_model(
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    aim_model_name: str,
    image_ref: str = DEFAULT_AIM_DEPLOYMENT_IMAGE_REF,
    custom_profile: dict[str, Any] | None = None,
    bucket: str = MINIO_BUCKET,
    timeout_seconds: float = AIM_PROFILE_WAIT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = AIM_PROFILE_POLL_INTERVAL_SECONDS,
) -> AIMProfileResource:
    """Wait for aim-engine AIMProfile, patch deployment-image-ref and customProfile, mirror AIMModel+AIMProfile to S3. Precondition failures leave cluster untouched."""
    profile = await wait_for_aim_profile(
        kube_client=kube_client,
        namespace=namespace,
        model_name=aim_model_name,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    if profile is None:
        raise PreconditionNotMetException(
            message=(
                f"aim-engine did not emit an AIMProfile for AIMModel "
                f"'{aim_model_name}' in namespace '{namespace}' within "
                f"{timeout_seconds:g}s; cannot complete onboard."
            )
        )

    manifest_key = get_custom_model_manifest_path(namespace, aim_model_name)
    # Hold the lock across read, patch, and write so concurrent re-onboards cannot drop the AIMProfile or publish a stale AIMModel.
    async with manifest_write_lock(bucket, manifest_key):
        existing_documents = await read_manifest_from_s3(minio_client, bucket, manifest_key)
        # Abort before patching when the S3 scaffold is missing or lacks the AIMModel doc, so we never append an orphaned AIMProfile.
        if not existing_documents:
            raise PreconditionNotMetException(
                message=(
                    f"Onboarded-model manifest at '{manifest_key}' is missing or "
                    "empty; the AIMModel document must be written before the "
                    "AIMProfile document can be appended."
                )
            )
        if not _manifest_contains_aim_model(existing_documents, namespace, aim_model_name):
            raise PreconditionNotMetException(
                message=(
                    f"Onboarded-model manifest at '{manifest_key}' does not contain "
                    f"an AIMModel document for '{aim_model_name}' in namespace "
                    f"'{namespace}'; refusing to write an AIMProfile document that "
                    "would be orphaned from its AIMModel scaffold."
                )
            )

        patched_profile = await patch_aim_profile(
            kube_client=kube_client,
            namespace=namespace,
            profile_name=profile.metadata.name,
            image_ref=image_ref,
            custom_profile_spec=custom_profile,
        )

        merged = upsert_manifest_documents(
            existing=existing_documents,
            new_documents=[_profile_resource_to_manifest_document(patched_profile)],
        )
        await write_manifest_to_s3(minio_client, bucket, manifest_key, merged)

    logger.info(
        "Onboarded-model manifest updated at {}/{} with AIMProfile {}",
        bucket,
        manifest_key,
        patched_profile.metadata.name,
    )
    return patched_profile
