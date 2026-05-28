# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os
from typing import Any
from uuid import UUID

from kubernetes_asyncio.client import ApiException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import DeletionConflictException, NotFoundException, ValidationException

from ..aims import gateway as aims_gateway
from ..aims.crds import AIMModelResource
from ..charts.config import FINETUNING_CHART_NAME, MLFLOW_CHART_NAME
from ..charts.service import get_chart
from ..charts.utils import render_helm_template
from ..cluster.service import get_cluster_gpu_device_info
from ..datasets.repository import select_dataset
from ..dispatch.kube_client import KubernetesClient
from ..dispatch.utils import parse_uuid, sanitize_label_value
from ..minio.client import MinioClient
from ..minio.config import MINIO_BUCKET
from ..overlays.repository import list_overlays
from ..secrets.service import get_secret_details
from ..workloads.constants import (
    CANONICAL_NAME_LABEL,
    MODEL_ID_LABEL,
    MODEL_NAME_LABEL,
    WORKLOAD_ID_LABEL,
    WORKLOAD_TYPE_LABEL,
)
from ..workloads.enums import WorkloadStatus, WorkloadType
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
    - its `aimManifest.aimId` matches an AIMClusterServiceTemplate present on the cluster
      (via `spec.aimId` or `status.profile.aimId`), and
    - its `metadata.compatibleAccelerators` intersect the cluster's GPU device IDs
      (recipes without `compatibleAccelerators` are treated as compatible with all hardware).
    """
    cluster_aim_ids = await _get_cluster_template_aim_ids(kube_client)
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
        compatible_accelerators = metadata.get("compatibleAccelerators") if isinstance(metadata, dict) else None
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
        result.append(
            FinetunableModelResponse(
                canonical_name=overlay.canonical_name,
                # finetuningGpus is an integer in well-formed overlays; Pydantic coerces numeric strings
                gpu_count=overlay_data.get("finetuningGpus"),
                compatible_accelerators=compatible_accelerators or [],
                compatible_accelerator_names=accelerator_names,
            )
        )

    return sorted(result, key=lambda m: m.canonical_name)


async def _get_cluster_template_aim_ids(kube_client: KubernetesClient) -> set[str]:
    """Collect aimIds advertised by Ready AIMClusterServiceTemplate resources on the cluster.

    Only templates with `status.status == "Ready"` contribute their aimIds — Pending,
    Progressing, Degraded, Failed, and NotAvailable templates either lack an aimId yet
    or describe a profile the cluster cannot currently serve.

    Reads both `spec.aimId` (operator-declared) and `status.profile.aimId`
    (controller-derived from the profile YAML's top-level `aim_id`); a template
    contributes its aimId from whichever field is populated.
    """
    templates = await aims_gateway.list_aim_cluster_service_templates(kube_client)
    aim_ids: set[str] = set()
    for template in templates:
        if template.status.get("status") != "Ready":
            continue
        if spec_aim_id := template.spec.get("aimId"):
            aim_ids.add(spec_aim_id)
        if status_aim_id := (template.status.get("profile") or {}).get("aimId"):
            aim_ids.add(status_aim_id)
    return aim_ids


async def list_aim_models(
    kube_client: KubernetesClient,
    namespace: str,
) -> list[AIMModelResource]:
    return await aims_gateway.list_aim_models(kube_client, namespace)


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


async def run_finetune_model_workload(
    session: AsyncSession,
    kube_client: KubernetesClient,
    model_id: UUID | str,
    finetuning_data: FinetuneCreate,
    submitter: str,
    namespace: str,
    display_name: str | None = None,
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

    # Resolve base model: AIMModel CR (UUID) or HuggingFace canonical name (str)
    base_model_uri: str
    if isinstance(model_id, UUID):
        aim_model = await get_aim_model(kube_client, namespace, str(model_id))
        labels = aim_model.metadata.labels or {}
        model_canonical_name = (
            aim_model.status.image_metadata.model.canonical_name or labels.get(CANONICAL_NAME_LABEL) or str(model_id)
        )
        sources = aim_model.spec.model_sources
        if not sources or not sources[0].source_uri:
            raise ValidationException(
                f"Base model '{model_id}' has no weights URI. The model must be fully onboarded before finetuning."
            )
        base_model_uri = sources[0].source_uri
    else:
        model_canonical_name = model_id
        base_model_uri = f"hf://{model_canonical_name}"

    chart = await get_chart(session, chart_name=FINETUNING_CHART_NAME)

    overlays = await list_overlays(
        session, chart_id=chart.id, canonical_name=model_canonical_name, include_generic=True
    )
    overlay_values = [chart.signature] + [overlay.overlay for overlay in overlays]

    dataset = await select_dataset(session, dataset_id=finetuning_data.dataset_id, namespace=namespace)
    if not dataset:
        raise NotFoundException("Dataset not found")

    # TODO: enforce model name uniqueness (currently FE-only, no race protection)
    finetuning_path = get_finetuned_model_weights_path(model_canonical_name, finetuning_data.name, namespace)

    # Build the finetuning configuration
    finetuning_config: dict[str, dict] = {
        "data_conf": {"training_data": {"datasets": [{"path": os.path.join(MINIO_BUCKET, dataset.path)}]}},
        "batchsize_conf": {"total_train_batch_size": finetuning_data.batch_size},
        "overrides": {"lr_multiplier": finetuning_data.learning_rate},
        "training_args": {"num_train_epochs": finetuning_data.epochs},
    }

    # Check for MLflow tracking configuration
    mlflow_workloads = await get_workloads(
        session=session,
        namespace=namespace,
        workload_types=[WorkloadType.WORKSPACE],
        status_filter=[WorkloadStatus.RUNNING],
        chart_name=MLFLOW_CHART_NAME,
    )

    mlflow_response = WorkloadResponse.model_validate(mlflow_workloads[0]) if mlflow_workloads else None
    if mlflow_response and mlflow_response.endpoints and mlflow_response.endpoints.get("internal"):
        mlflow_uri = mlflow_response.endpoints["internal"]
        if not mlflow_uri.startswith(("http://", "https://")):
            mlflow_uri = f"http://{mlflow_uri}"
        tracking_config = {
            "mlflow_server_uri": mlflow_uri,
            "experiment_name": finetuning_data.name,
        }
        finetuning_config["training_args"]["report_to"] = ["mlflow"]
        finetuning_config["training_args"]["logging_steps"] = 10
        finetuning_config["tracking"] = tracking_config
        logger.info(f"Found running MLflow workspace for namespace {namespace} - URI: {mlflow_uri}")
    else:
        logger.info(f"No running MLflow workspace found for namespace {namespace} - skipping MLflow tracking")

    helm_overrides = {
        "checkpointsRemote": os.path.join(MINIO_BUCKET, finetuning_path),
        "basemodel": base_model_uri,
        "finetuning_config": finetuning_config,
    }

    if hf_token_secret_name:
        helm_overrides["hfTokenSecret"] = {"name": hf_token_secret_name, "key": "token"}

    workload = await create_workload(
        session=session,
        display_name=display_name or "",
        workload_type=WorkloadType.FINE_TUNING,
        chart_id=chart.id,
        namespace=namespace,
        submitter=submitter,
        status=WorkloadStatus.PENDING,
        dataset_id=finetuning_data.dataset_id,
    )

    finetuning_labels = {MODEL_NAME_LABEL: sanitize_label_value(finetuning_data.name)}

    # Wire up the aimmodel-applier sidecar so it creates the AIMModel CR after training.
    # workload.name becomes the CR name — it's unique and already used as the K8s resource name.
    # aimId and modelId (ADR 006a template matching) are populated by the workloads_manager chart.
    helm_overrides["aimManifest"] = {
        "enabled": True,
        "modelName": workload.name,
        "labels": {
            **finetuning_labels,
            WORKLOAD_ID_LABEL: str(workload.id),
        },
    }

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
        logger.error(f"Failed to deploy finetuning workload {workload.id}: {e}")
        workload.status = WorkloadStatus.FAILED
        await session.flush()
        raise

    return FinetuneJobResponse(
        workload_id=workload.id,
        model_name=finetuning_data.name,
        base_model=model_canonical_name,
        namespace=namespace,
    )
