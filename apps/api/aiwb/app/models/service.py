# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import os
from typing import Any
from uuid import UUID, uuid4

from kubernetes_asyncio.client import ApiException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import DeletionConflictException, NotFoundException, ValidationException

from ..aims import gateway as aims_gateway
from ..aims.crds import AIMModelResource, AIMModelSource
from ..charts.config import FINETUNING_CHART_NAME, MLFLOW_CHART_NAME
from ..charts.service import get_chart
from ..charts.utils import render_helm_template
from ..cluster.service import get_cluster_gpu_device_info
from ..custom_models.service import ensure_namespace_aim_base_model
from ..datasets.repository import select_dataset
from ..dispatch.kube_client import KubernetesClient
from ..dispatch.utils import parse_uuid, sanitize_label_value
from ..minio.client import MinioClient
from ..minio.config import MINIO_BUCKET, MINIO_URL
from ..overlays.repository import list_overlays
from ..secrets.service import get_secret_details
from ..workloads.constants import (
    DISPLAY_NAME_ANNOTATION,
    MODEL_ID_LABEL,
    MODEL_NAME_LABEL,
    MODEL_SOURCE_TYPE_LABEL,
    WORKLOAD_ID_LABEL,
    WORKLOAD_TYPE_LABEL,
)
from ..workloads.enums import ModelSourceType, WorkloadStatus, WorkloadType
from ..workloads.repository import create_workload, get_workloads, update_workload_status
from ..workloads.schemas import WorkloadResponse
from ..workloads.utils import apply_manifest
from .schemas import FinetunableModelResponse, FinetuneCreate, FinetuneJobResponse
from .utils import delete_from_s3, get_finetuned_model_weights_path


async def get_aim_model(
    kube_client: KubernetesClient,
    namespace: str,
    resource_name: str,
) -> AIMModelResource:
    aim_model = await aims_gateway.get_aim_model(kube_client, namespace, resource_name)
    if aim_model is not None:
        return aim_model

    # Fall back to label-based lookup (supports workload UUIDs as resource_name)
    workload_id_selector = f"{WORKLOAD_ID_LABEL}={resource_name}"
    aim_model = await aims_gateway.find_aim_model_by_label(kube_client, namespace, workload_id_selector)
    if aim_model is not None:
        return aim_model

    raise NotFoundException(f"Model {resource_name} not found")


async def get_finetunable_models(
    session: AsyncSession, kube_client: KubernetesClient, chart_name: str = FINETUNING_CHART_NAME
) -> list[FinetunableModelResponse]:
    """Get models that can be finetuned on the cluster's current AIM and GPU profile.

    A recipe is returned only when both:
    - its `aimManifest.aimId` matches an AIMClusterProfile present on the cluster
      (via `spec.aimId`), and
    - its `metadata.compatibleAccelerators` intersect the cluster's GPU device IDs
      (recipes without `compatibleAccelerators` are treated as compatible with all hardware).

    Both sides of the join use `modelId` (the base-weights / artifact identity) rather than
    `aimId` (the family identity that is shared across packagings like FP8 inference
    variants). A fine-tuning recipe targets a specific set of weights, so matching on the
    family would let incompatible packagings appear as finetunable. In current overlays
    `aimManifest.modelId == aimManifest.aimId`, so this read is behavior-neutral today; it
    expresses the intended join semantics for when the two diverge.
    """
    cluster_aim_ids = await _get_cluster_profile_aim_ids(kube_client)
    if not cluster_aim_ids:
        return []

    chart = await get_chart(session, chart_name=chart_name)
    overlays = await list_overlays(session, chart_id=chart.id, include_generic=True)
    cluster_gpu_info = await get_cluster_gpu_device_info(kube_client)
    cluster_gpu_ids = set(cluster_gpu_info)

    result = []
    for overlay in overlays:
        if overlay.canonical_name is None:
            continue
        overlay_data = overlay.overlay if isinstance(overlay.overlay, dict) else {}
        aim_manifest = overlay_data.get("aimManifest")
        aim_id = aim_manifest.get("aimId") if isinstance(aim_manifest, dict) else None
        if not aim_id or aim_id not in cluster_aim_ids:
            continue
        metadata = overlay_data.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        compatible_accelerators = metadata.get("compatibleAccelerators")
        if compatible_accelerators is not None and cluster_gpu_ids.isdisjoint(compatible_accelerators):
            continue
        # Resolve display names only for GPUs present in this cluster; deduplicate preserving order
        accelerator_names = (
            list(
                dict.fromkeys(
                    cluster_gpu_info[acc_id] for acc_id in compatible_accelerators if acc_id in cluster_gpu_ids
                )
            )
            if compatible_accelerators
            else []
        )
        hf_token_required = metadata.get("hfTokenRequired")
        result.append(
            FinetunableModelResponse(
                canonical_name=overlay.canonical_name,
                # finetuningGpus is an integer in well-formed overlays; Pydantic coerces numeric strings
                gpu_count=overlay_data.get("finetuningGpus"),
                compatible_accelerators=compatible_accelerators or [],
                compatible_accelerator_names=accelerator_names,
                hf_token_required=hf_token_required if isinstance(hf_token_required, bool) else None,
            )
        )

    return sorted(result, key=lambda m: m.canonical_name)


async def _get_cluster_profile_aim_ids(kube_client: KubernetesClient) -> set[str]:
    """Collect aimIds advertised by Ready AIMClusterProfile resources on the cluster.

    Only profiles with `status.status == "Ready"` contribute their aimIds —
    Pending, Progressing, Degraded, Failed, and NotAvailable profiles describe
    a profile the cluster cannot currently serve.
    """
    profiles = await aims_gateway.list_aim_cluster_profiles_by_aim_ids(kube_client)
    aim_ids: set[str] = set()
    for profile in profiles:
        if profile.status.status != "Ready":
            continue
        if profile.spec.aim_id:
            aim_ids.add(profile.spec.aim_id)
    return aim_ids


async def list_aim_models(
    kube_client: KubernetesClient,
    namespace: str,
    label_selector: str | None = None,
) -> list[AIMModelResource]:
    exclude_custom = f"{MODEL_SOURCE_TYPE_LABEL}!={ModelSourceType.CUSTOM}"
    combined_selector = f"{label_selector},{exclude_custom}" if label_selector else exclude_custom
    return await aims_gateway.list_aim_models(kube_client, namespace, label_selector=combined_selector)


async def _find_job_by_name(
    kube_client: KubernetesClient,
    namespace: str,
    name: str,
) -> Any | None:
    try:
        job = await kube_client.batch_v1.read_namespaced_job(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            return None
        raise

    labels = job.metadata.labels or {}
    if labels.get(WORKLOAD_TYPE_LABEL) != WorkloadType.FINE_TUNING:
        return None
    return job


async def _find_job_by_label(
    kube_client: KubernetesClient,
    namespace: str,
    label_selector: str,
) -> Any | None:
    fine_tuning_selector = f"{WORKLOAD_TYPE_LABEL}={WorkloadType.FINE_TUNING},{label_selector}"
    job_list = await kube_client.batch_v1.list_namespaced_job(
        namespace=namespace,
        label_selector=fine_tuning_selector,
    )
    if job_list and job_list.items:
        return job_list.items[0]
    return None


def _extract_s3_prefix(source_uri: str) -> str:
    # s3://bucket-name/path/to/weights/ → path/to/weights/
    without_scheme = source_uri.removeprefix("s3://")
    _, _, prefix = without_scheme.partition("/")
    return prefix


async def delete_model(
    kube_client: KubernetesClient,
    resource_name: str,
    namespace: str,
    minio_client: MinioClient,
    force: bool = False,
    session: AsyncSession | None = None,
) -> None:
    aim_model = await aims_gateway.get_aim_model(kube_client, namespace, resource_name)

    if aim_model is None:
        job = await _find_job_by_name(kube_client, namespace, resource_name)
        if job is None:
            # resource_name may be a workload UUID (from the dashboard) — look up by label
            job = await _find_job_by_label(kube_client, namespace, f"{WORKLOAD_ID_LABEL}={resource_name}")
        if job is None:
            raise NotFoundException(f"Model {resource_name} not found in namespace {namespace}")

        job_labels = job.metadata.labels or {}
        workload_id = job_labels.get(WORKLOAD_ID_LABEL)
        associated_model = (
            await aims_gateway.find_aim_model_by_label(kube_client, namespace, f"{WORKLOAD_ID_LABEL}={workload_id}")
            if workload_id
            else None
        )
        if associated_model:
            active_services = await aims_gateway.list_aim_services_for_model(
                kube_client, namespace, associated_model.metadata.name
            )
            if active_services:
                if not force:
                    raise DeletionConflictException(
                        f"Model {resource_name} has {len(active_services)} active deployment(s). Use force=true to delete anyway."
                    )
                for svc in active_services:
                    logger.warning(
                        f"Force-deleting AIMService {svc.metadata.name} — cluster-auth group cleanup skipped"
                    )
                    await aims_gateway.delete_aim_service(kube_client, namespace, UUID(svc.id))

        await kube_client.batch_v1.delete_namespaced_job(name=job.metadata.name, namespace=namespace)

        workload_uuid = parse_uuid(job_labels.get(WORKLOAD_ID_LABEL))
        if workload_uuid and session:
            await update_workload_status(session, workload_uuid, WorkloadStatus.DELETED, "system")

        if associated_model:
            await aims_gateway.delete_aim_model(kube_client, namespace, associated_model.metadata.name)
            for source in associated_model.spec.model_sources:
                if not source.source_uri:
                    continue
                prefix = _extract_s3_prefix(source.source_uri)
                if not prefix:
                    logger.warning(
                        f"Cannot determine S3 prefix from {source.source_uri} for model {resource_name}, skipping."
                    )
                    continue
                try:
                    await delete_from_s3(prefix, minio_client, resource_name)
                except NotFoundException:
                    logger.warning(
                        f"Model weights not found in S3 for model {resource_name} ({source.source_uri}), skipping."
                    )
        return

    active_services = await aims_gateway.list_aim_services_for_model(kube_client, namespace, resource_name)
    if active_services:
        if not force:
            raise DeletionConflictException(
                f"Model {resource_name} has {len(active_services)} active deployment(s). Use force=true to delete anyway."
            )
        for svc in active_services:
            logger.warning(f"Force-deleting AIMService {svc.metadata.name} — cluster-auth group cleanup skipped")
            await aims_gateway.delete_aim_service(kube_client, namespace, UUID(svc.id))

    await aims_gateway.delete_aim_model(kube_client, namespace, resource_name)

    aim_model_labels = aim_model.metadata.labels or {}
    workload_id = parse_uuid(aim_model_labels.get(WORKLOAD_ID_LABEL))
    if workload_id and session:
        await update_workload_status(session, workload_id, WorkloadStatus.DELETED, "system")

    for source in aim_model.spec.model_sources:
        if not source.source_uri:
            continue
        prefix = _extract_s3_prefix(source.source_uri)
        if not prefix:
            logger.warning(f"Cannot determine S3 prefix from {source.source_uri} for model {resource_name}, skipping.")
            continue
        try:
            await delete_from_s3(prefix, minio_client, resource_name)
        except NotFoundException:
            logger.warning(f"Model weights not found in S3 for model {resource_name} ({source.source_uri}), skipping.")


def _resolve_base_model_source(aim_model: AIMModelResource) -> AIMModelSource | None:
    """Return the AIMModelSource carrying the base model's weights, or None.

    The legacy flat ``spec.modelSources`` is populated for official and
    fine-tuning-published models. v1alpha2 imported / re-finetuned models instead
    carry their weights under ``spec.profiles.overrides.modelSources``. Prefer the
    flat field and fall back to the profiles override so a fine-tuned model can be
    used as the base for another round of fine-tuning.

    TODO(EAI 2.3): drop the legacy flat ``spec.modelSources`` branch once all
    models carry weights under ``spec.profiles.overrides.modelSources``.
    """
    if aim_model.spec.model_sources:
        return aim_model.spec.model_sources[0]
    if aim_model.spec.profiles and aim_model.spec.profiles.overrides.model_sources:
        return aim_model.spec.profiles.overrides.model_sources[0]
    return None


async def run_finetune_model_workload(
    session: AsyncSession,
    kube_client: KubernetesClient,
    model_id: UUID | str,
    finetuning_data: FinetuneCreate,
    submitter: str,
    namespace: str,
) -> FinetuneJobResponse:
    try:
        model_id = UUID(model_id) if isinstance(model_id, str) else model_id
    except ValueError:
        pass

    hf_token_secret_name = None
    if finetuning_data.hf_token_secret_name:
        hf_secret = await get_secret_details(
            namespace=namespace,
            secret_name=finetuning_data.hf_token_secret_name,
            kube_client=kube_client,
        )
        hf_token_secret_name = hf_secret.metadata.name

    is_finetuned_basemodel = isinstance(model_id, UUID)
    aim_model: AIMModelResource | None = None
    base_model_source: AIMModelSource | None = None

    # Resolve base model: AIMModel CR (UUID or resource name) or HuggingFace canonical name (str with /)
    base_model_uri: str
    if is_finetuned_basemodel:
        aim_model = await get_aim_model(kube_client, namespace, str(model_id))

        model_canonical_name = (
            aim_model.status.image_metadata.model.canonical_name or aim_model.status.aim_id or str(model_id)
        )
        # Weights live under the legacy flat field for official/fine-tuning models, but
        # imported/re-finetuned v1alpha2 models carry them under
        # spec.profiles.overrides.modelSources instead. Prefer the flat field and fall
        # back to the profiles override so a fine-tuned model can itself be re-finetuned.
        base_model_source = _resolve_base_model_source(aim_model)
        if base_model_source is None or not base_model_source.source_uri:
            raise ValidationException(
                f"Base model '{model_id}' has no weights URI. The model must be fully onboarded before finetuning."
            )
        base_model_uri = base_model_source.source_uri.removeprefix("s3://")
    else:
        model_canonical_name = str(model_id)
        base_model_uri = f"hf://{model_canonical_name}"

    chart = await get_chart(session, chart_name=FINETUNING_CHART_NAME)

    overlays = await list_overlays(
        session, chart_id=chart.id, canonical_name=model_canonical_name, include_generic=True
    )
    overlay_values = [chart.signature] + [overlay.overlay for overlay in overlays]

    # Extract the aimId needed to resolve the correct AIMClusterModel to use as the
    # derivation source for the fine-tuned model. The AIMClusterModel name is passed as
    # modelRef.name in the derivedFrom selector — the aim-engine controller resolves it
    # via the aim.eai.amd.com/source-model label stamped on profiles. Prefer the recipe
    # overlay's aimManifest (the authoritative source for string-based / HF models). For
    # UUID-based re-finetunes the overlay may not carry it, so fall back to the base
    # AIMModel's status.aim_id.
    recipe_aim_id: str | None = None
    for overlay in overlays:
        if overlay.canonical_name == model_canonical_name:
            aim_manifest_data = overlay.overlay.get("aimManifest") if isinstance(overlay.overlay, dict) else None
            if isinstance(aim_manifest_data, dict):
                recipe_aim_id = aim_manifest_data.get("aimId")
            break
    if recipe_aim_id is None and aim_model is not None:
        recipe_aim_id = aim_model.status.aim_id or None
    if recipe_aim_id is None:
        raise ValidationException(
            "Cannot determine aimId for fine-tuning recipe. The recipe overlay must include "
            "aimManifest.aimId, or the base AIMModel must have a known aimId in its status."
        )

    dataset = await select_dataset(session, dataset_id=finetuning_data.dataset_id, namespace=namespace)
    if not dataset:
        raise NotFoundException("Dataset not found")

    # TODO: enforce model name uniqueness (currently FE-only, no race protection)
    # Use a UUID as the S3 path segment so display names with spaces or special chars
    # don't produce invalid or colliding object keys.
    finetune_job_id = str(uuid4())
    finetuning_path = get_finetuned_model_weights_path(model_canonical_name, finetune_job_id, namespace)

    # Build the finetuning configuration
    finetuning_config: dict[str, dict] = {
        "data_conf": {"training_data": {"datasets": [{"path": os.path.join(MINIO_BUCKET, dataset.path)}]}},
        "batchsize_conf": {"total_train_batch_size": finetuning_data.batch_size},
        "overrides": {"lr_multiplier": finetuning_data.learning_rate},
        "training_args": {"num_train_epochs": finetuning_data.epochs},
    }

    # Fan out MLflow lookup and AIMClusterModel resolution in parallel — both are
    # independent I/O calls. The AIMClusterModel lookup resolves which model the
    # fine-tuned AIMModel should derive its serving profiles from. modelRef.name
    # in the derivedFrom selector must be an AIMClusterModel name (not an
    # AIMClusterProfile name) — the aim-engine controller resolves it via the
    # aim.eai.amd.com/source-model label on profiles.
    async def _fetch_cluster_models() -> list:
        return await aims_gateway.list_aims(kube_client)

    mlflow_workloads, cluster_models = await asyncio.gather(
        get_workloads(
            session=session,
            namespace=namespace,
            workload_types=[WorkloadType.WORKSPACE],
            status_filter=[WorkloadStatus.RUNNING],
            chart_name=MLFLOW_CHART_NAME,
        ),
        _fetch_cluster_models(),
    )

    base_model_name: str | None = None
    for model in cluster_models:
        if model.status.status == "Ready" and model.status.aim_id == recipe_aim_id:
            base_model_name = model.metadata.name
            break
    if base_model_name is None:
        raise ValidationException(
            f"No Ready AIMClusterModel found for aimId '{recipe_aim_id}'. "
            "The model must be deployed on the cluster before fine-tuning."
        )

    mlflow_response = WorkloadResponse.model_validate(mlflow_workloads[0]) if mlflow_workloads else None
    if mlflow_response and mlflow_response.endpoints and mlflow_response.endpoints.get("internal"):
        mlflow_uri = mlflow_response.endpoints["internal"]
        if not mlflow_uri.startswith(("http://", "https://")):
            mlflow_uri = f"http://{mlflow_uri}"
        tracking_config = {
            "mlflow_server_uri": mlflow_uri,
            "experiment_name": finetuning_data.display_name,
        }
        finetuning_config["training_args"]["report_to"] = ["mlflow"]
        finetuning_config["training_args"]["logging_steps"] = 10
        finetuning_config["tracking"] = tracking_config
        logger.info(f"Found running MLflow workspace for namespace {namespace} - URI: {mlflow_uri}")
    else:
        logger.info(f"No running MLflow workspace found for namespace {namespace} - skipping MLflow tracking")

    helm_overrides = {
        "bucketStorageHost": MINIO_URL,
        "checkpointsRemote": os.path.join(MINIO_BUCKET, finetuning_path),
        "basemodel": base_model_uri,
        "finetuning_config": finetuning_config,
    }

    if hf_token_secret_name:
        helm_overrides["hfTokenSecret"] = {"name": hf_token_secret_name, "key": "token"}

    await ensure_namespace_aim_base_model(kube_client, namespace)

    workload = await create_workload(
        session=session,
        display_name=finetuning_data.display_name,
        workload_type=WorkloadType.FINE_TUNING,
        chart_id=chart.id,
        namespace=namespace,
        submitter=submitter,
        status=WorkloadStatus.PENDING,
        dataset_id=finetuning_data.dataset_id,
    )

    # WORKLOAD_TYPE_LABEL is the contract with fine_tuning.service._is_fine_tuning_model, which
    # backs GET /v1/projects/{project}/fine-tuning/models. Stamped here so it ends up on both
    # the AIMModel CR (via aim_manifest["labels"]) and the rest of the workload's resources
    # (via apply_manifest's extra_labels). Omitting it makes the resulting AIMModel invisible
    # to the Custom Models page.
    finetuning_labels = {
        MODEL_NAME_LABEL: sanitize_label_value(finetuning_data.display_name),
        WORKLOAD_TYPE_LABEL: WorkloadType.FINE_TUNING.value,
    }

    # Wire up the aimmodel-applier sidecar so it creates the AIMModel CR after training.
    # workload.name becomes the CR name — it's unique and already used as the K8s resource name.
    # Sanitize every label at this boundary: the values flow through yaml.dump → Helm template
    # render → aimmodel-applier kubectl apply, and any non-str (StrEnum, UUID) gets serialized
    # as a YAML sequence and quoted into an invalid label like "[FINE_TUNING]". This mirrors
    # apply_manifest's per-label sanitize for the same reason.
    aim_manifest_labels = {**finetuning_labels, WORKLOAD_ID_LABEL: str(workload.id)}
    aim_manifest: dict[str, Any] = {
        "enabled": True,
        "modelName": workload.name,
        "labels": {k: sanitize_label_value(str(v)) for k, v in aim_manifest_labels.items()},
        "annotations": {DISPLAY_NAME_ANNOTATION: finetuning_data.display_name},
    }

    # For UUID-based models, aimId must be carried forward from the AIMModel spec — the overlay
    # is looked up by canonical name and may not have it. For string-based models, aimId is
    # already in the model's overlay and Helm merges it in automatically.
    if is_finetuned_basemodel and aim_model is not None:
        if aim_model.status.aim_id:
            aim_manifest["aimId"] = aim_model.status.aim_id
        if base_model_source is not None:
            aim_manifest["modelId"] = base_model_source.model_id

    aim_manifest["baseModel"] = {"name": base_model_name, "scope": "Auto"}

    helm_overrides["aimManifest"] = aim_manifest

    logger.info(f"Deploying finetuning workload {workload.id} to namespace {namespace}")

    try:
        overlay_values.append(helm_overrides)

        manifest = await render_helm_template(
            chart=chart,
            name=workload.name,
            namespace=namespace,
            overlays_values=overlay_values,
        )
        workload.manifest = manifest
        await session.flush()
        await apply_manifest(
            kube_client,
            manifest,
            workload,
            namespace,
            submitter,
            extra_labels={**finetuning_labels, MODEL_ID_LABEL: str(workload.id)},
        )
        logger.info(f"Successfully deployed finetuning workload {workload.id}")

    except Exception as e:
        if isinstance(e, ValidationException):
            error_message = f"{e.message}: {e.detail}"
        else:
            error_message = str(e)

        logger.error(f"Failed to deploy finetuning workload {workload.id}: {error_message}")
        workload.status = WorkloadStatus.FAILED
        await session.flush()
        raise

    return FinetuneJobResponse(
        workload_id=workload.id,
        display_name=finetuning_data.display_name,
        base_model=model_canonical_name,
        namespace=namespace,
    )
