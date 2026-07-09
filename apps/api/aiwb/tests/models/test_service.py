# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from contextlib import AbstractContextManager
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import DeletionConflictException, NotFoundException, ValidationException
from app.aims.crds import (
    AIMImageMetadata,
    AIMModelMetadata,
    AIMModelProfilesSpec,
    AIMModelResource,
    AIMModelSource,
    AIMModelSpec,
    AIMModelStatusFields,
    ProfileOverrides,
)
from app.charts.config import FINETUNING_CHART_NAME, MLFLOW_CHART_NAME
from app.dispatch.crds import K8sMetadata
from app.dispatch.kube_client import KubernetesClient
from app.minio.client import MinioClient
from app.models.schemas import FinetunableModelResponse, FinetuneCreate
from app.models.service import (
    _extract_s3_prefix,
    delete_model,
    get_aim_model,
    get_finetunable_models,
    run_finetune_model_workload,
)
from app.overlays.models import Overlay
from app.secrets.schemas import SecretResponse
from app.workloads.constants import MODEL_ID_LABEL, MODEL_NAME_LABEL, WORKLOAD_ID_LABEL, WORKLOAD_TYPE_LABEL
from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.schemas import WorkloadResponse
from tests import factory


@pytest.mark.asyncio
async def test_get_aim_model_not_found(test_namespace: str) -> None:
    mock_kube_client = MagicMock()

    with (
        patch("app.models.service.aims_gateway.get_aim_model", return_value=None),
        patch("app.models.service.aims_gateway.find_aim_model_by_label", return_value=None),
        pytest.raises(NotFoundException, match="Model nonexistent not found"),
    ):
        await get_aim_model(mock_kube_client, test_namespace, "nonexistent")


@pytest.mark.asyncio
async def test_get_aim_model_falls_back_to_label_lookup(test_namespace: str) -> None:
    """When name lookup fails, falls back to WORKLOAD_ID_LABEL selector."""
    mock_kube_client = MagicMock()
    model_uuid = str(uuid4())
    aim_model = AIMModelResource.model_validate({"metadata": {"name": "finetuned-model-cr"}, "spec": {}, "status": {}})

    with (
        patch("app.models.service.aims_gateway.get_aim_model", return_value=None),
        patch("app.models.service.aims_gateway.find_aim_model_by_label", return_value=aim_model) as mock_label_lookup,
    ):
        result = await get_aim_model(mock_kube_client, test_namespace, model_uuid)

    mock_label_lookup.assert_called_once_with(mock_kube_client, test_namespace, f"{WORKLOAD_ID_LABEL}={model_uuid}")


@pytest.mark.parametrize(
    "source_uri,expected_prefix",
    [
        ("s3://bucket/path/to/weights/", "path/to/weights/"),
        ("s3://bucket/weights", "weights"),
        ("s3://bucket/a/b/c", "a/b/c"),
        ("s3://bucket-name", ""),  # no path component — guard against empty prefix
    ],
)
def test_extract_s3_prefix(source_uri: str, expected_prefix: str) -> None:
    assert _extract_s3_prefix(source_uri) == expected_prefix


@pytest.mark.asyncio
async def test_delete_model_success(db_session: AsyncSession, test_namespace: str) -> None:
    """Test successfully deleting a model by CR name with S3 cleanup and workload marked DELETED."""
    model_name = "my-finetuned-model"
    workload_id = uuid4()
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_minio_client = MagicMock(spec=MinioClient)

    aim_model = AIMModelResource(
        metadata=K8sMetadata(
            name=model_name,
            namespace=test_namespace,
            labels={WORKLOAD_ID_LABEL: str(workload_id)},
        ),
        spec=AIMModelSpec(model_sources=[AIMModelSource(source_uri="s3://my-bucket/path/to/weights/")]),
    )

    chart = await factory.create_chart(db_session, name="ft-chart")
    workload = await factory.create_workload(
        db_session,
        id=workload_id,
        namespace=test_namespace,
        chart=chart,
        workload_type=WorkloadType.FINE_TUNING,
        status=WorkloadStatus.COMPLETE,
        include_isolation_data=False,
    )

    with (
        patch("app.aims.gateway.get_aim_model", return_value=aim_model) as mock_get,
        patch("app.aims.gateway.list_aim_services_for_model", return_value=[]) as mock_list_services,
        patch("app.aims.gateway.delete_aim_model", new_callable=AsyncMock) as mock_delete_cr,
        patch("app.models.service.delete_from_s3", new_callable=AsyncMock) as mock_delete_s3,
    ):
        await delete_model(mock_kube_client, model_name, test_namespace, mock_minio_client, session=db_session)

        mock_get.assert_called_once_with(mock_kube_client, test_namespace, model_name)
        mock_list_services.assert_called_once_with(mock_kube_client, test_namespace, model_name)
        mock_delete_cr.assert_called_once_with(mock_kube_client, test_namespace, model_name)
        mock_delete_s3.assert_called_once_with("path/to/weights/", mock_minio_client, model_name)

    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.DELETED


@pytest.mark.asyncio
async def test_delete_model_not_found(test_namespace: str) -> None:
    """Test delete_model raises NotFoundException when neither AIMModel CR nor K8s Job exists."""
    model_name = "nonexistent-model"
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_minio_client = MagicMock(spec=MinioClient)

    with (
        patch("app.aims.gateway.get_aim_model", return_value=None),
        patch("app.models.service._find_job_by_name", new_callable=AsyncMock, return_value=None),
        patch("app.models.service._find_job_by_label", new_callable=AsyncMock, return_value=None),
        pytest.raises(NotFoundException, match=f"Model {model_name} not found"),
    ):
        await delete_model(mock_kube_client, model_name, test_namespace, mock_minio_client, session=None)


@pytest.mark.asyncio
async def test_delete_model_cancels_in_progress_job(db_session: AsyncSession, test_namespace: str) -> None:
    """delete_model cancels a PENDING/RUNNING fine-tuning job and marks the workload DELETED."""
    job_name = "wb-finetuning-abc123"
    workload_id = uuid4()
    mock_kube_client = MagicMock()
    mock_kube_client.batch_v1.delete_namespaced_job = AsyncMock()
    mock_minio_client = MagicMock(spec=MinioClient)

    chart = await factory.create_chart(db_session, name="ft-chart-job")
    workload = await factory.create_workload(
        db_session,
        id=workload_id,
        namespace=test_namespace,
        chart=chart,
        workload_type=WorkloadType.FINE_TUNING,
        status=WorkloadStatus.RUNNING,
        include_isolation_data=False,
    )

    mock_job = MagicMock()
    mock_job.metadata.name = job_name
    mock_job.metadata.labels = {WORKLOAD_ID_LABEL: str(workload_id)}

    with (
        patch("app.aims.gateway.get_aim_model", return_value=None),
        patch("app.models.service._find_job_by_name", new_callable=AsyncMock, return_value=mock_job),
        patch("app.aims.gateway.find_aim_model_by_label", new_callable=AsyncMock, return_value=None),
    ):
        await delete_model(mock_kube_client, job_name, test_namespace, mock_minio_client, session=db_session)

    mock_kube_client.batch_v1.delete_namespaced_job.assert_called_once_with(name=job_name, namespace=test_namespace)

    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.DELETED


@pytest.mark.asyncio
async def test_delete_model_cancels_job_and_cleans_completed_model(test_namespace: str) -> None:
    """delete_model deletes the AIMModel CR and S3 weights when a completed model is found by job name."""
    job_name = "wb-finetuning-abc123"
    s3_uri = "s3://bucket/ns/finetuned-models/llama3/run1/checkpoint-final/"

    mock_kube_client = MagicMock()
    mock_kube_client.batch_v1.delete_namespaced_job = AsyncMock()
    mock_minio_client = MagicMock(spec=MinioClient)

    model_id = str(uuid4())
    mock_job = MagicMock()
    mock_job.metadata.name = job_name
    mock_job.metadata.labels = {WORKLOAD_ID_LABEL: model_id}

    mock_aim_model = AIMModelResource(
        metadata=K8sMetadata(name=job_name),
        spec=AIMModelSpec(model_sources=[AIMModelSource(source_uri=s3_uri)]),
    )

    with (
        patch("app.aims.gateway.get_aim_model", new_callable=AsyncMock, return_value=None),
        patch("app.models.service._find_job_by_name", new_callable=AsyncMock, return_value=mock_job),
        patch("app.aims.gateway.find_aim_model_by_label", new_callable=AsyncMock, return_value=mock_aim_model),
        patch("app.aims.gateway.list_aim_services_for_model", new_callable=AsyncMock, return_value=[]),
        patch("app.aims.gateway.delete_aim_model", new_callable=AsyncMock) as mock_delete_cr,
        patch("app.models.service.delete_from_s3", new_callable=AsyncMock) as mock_delete_s3,
    ):
        await delete_model(mock_kube_client, job_name, test_namespace, mock_minio_client, session=None)

    mock_kube_client.batch_v1.delete_namespaced_job.assert_called_once_with(name=job_name, namespace=test_namespace)
    mock_delete_cr.assert_called_once_with(mock_kube_client, test_namespace, job_name)
    mock_delete_s3.assert_called_once()


_DEFAULT = object()


def make_overlay(
    canonical_name: str | None = None,
    compatible_accelerators: list[str] | None = None,
    aim_id: str | None | object = _DEFAULT,
    model_id: str | None | object = _DEFAULT,
    hf_token_required: bool | str | int | None = None,
    **extra_overlay_fields: object,
) -> MagicMock:
    """Build a mock Overlay.

    `aim_id` and `model_id` each default to the canonical_name (the typical real-world
    setup where the overlay's manifest identifiers mirror the model identifier). Pass
    explicit strings to override, or `None` to omit that field; passing `None` for
    both omits the aimManifest entirely. The two parameters can diverge so tests can
    construct overlays where the family identity (aimId) and the artifact identity
    (modelId) differ — the case that motivated EAI-6219. Production code joins on
    `modelId`.

    `hf_token_required` mirrors the overlay's top-level `hfTokenRequired` field (the
    recipe's own declaration of whether the base weights are gated on Hugging Face).
    Omitted when None so tests can exercise the "not declared" case.
    """
    overlay = MagicMock(spec=Overlay)
    overlay.canonical_name = canonical_name
    overlay_data: dict = {**extra_overlay_fields}
    metadata: dict = {}
    if compatible_accelerators is not None:
        metadata["compatibleAccelerators"] = compatible_accelerators
    if hf_token_required is not None:
        metadata["hfTokenRequired"] = hf_token_required
    if metadata:
        overlay_data["metadata"] = metadata
    resolved_aim_id = canonical_name if aim_id is _DEFAULT else aim_id
    resolved_model_id = canonical_name if model_id is _DEFAULT else model_id
    if resolved_aim_id is not None or resolved_model_id is not None:
        aim_manifest: dict = {}
        if resolved_aim_id is not None:
            aim_manifest["aimId"] = resolved_aim_id
        if resolved_model_id is not None:
            aim_manifest["modelId"] = resolved_model_id
        overlay_data["aimManifest"] = aim_manifest
    overlay.overlay = overlay_data
    return overlay


def make_profile(
    spec_aim_id: str | None = None,
    status: str = "Ready",
) -> MagicMock:
    """Build a mock AIMClusterProfile carrying spec.aim_id via typed attributes.

    Status is a typed model — use attribute access, not dict access — to match
    the production crds.py shape.
    """
    profile = MagicMock()
    profile.spec.aim_id = spec_aim_id or ""
    profile.status.status = status
    return profile


def make_cluster_model(
    aim_id: str | None = None,
    status: str = "Ready",
) -> MagicMock:
    """Build a mock AIMClusterModel carrying status.aim_id and status.status."""
    model = MagicMock()
    model.status.aim_id = aim_id or ""
    model.status.status = status
    return model


def patch_cluster_model(aim_id: str, name: str = "default-cluster-model") -> AbstractContextManager[MagicMock]:
    """Patch list_aims to return a single Ready AIMClusterModel with the given aimId."""
    model = make_cluster_model(aim_id=aim_id, status="Ready")
    model.metadata.name = name
    return patch("app.models.service.aims_gateway.list_aims", new_callable=AsyncMock, return_value=[model])


def patch_cluster_profiles(aim_ids: list[str] | None = None) -> AbstractContextManager[MagicMock]:
    """Patch list_aim_cluster_profiles_by_aim_ids to advertise the given aimIds."""
    profiles = [make_profile(spec_aim_id=aim_id) for aim_id in (aim_ids or [])]
    return patch("app.aims.gateway.list_aim_cluster_profiles_by_aim_ids", return_value=profiles)


def make_kube_client() -> AsyncMock:
    return AsyncMock(spec=KubernetesClient)


@pytest.mark.asyncio
async def test_get_finetunable_models_success(db_session: AsyncSession) -> None:
    """Test successfully getting finetunable models from overlays."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("meta-llama/Llama-3.1-8B"),
        make_overlay("microsoft/DialoGPT-medium"),
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["meta-llama/Llama-3.1-8B", "microsoft/DialoGPT-medium"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["meta-llama/Llama-3.1-8B", "microsoft/DialoGPT-medium"]


@pytest.mark.asyncio
async def test_get_finetunable_models_empty(db_session: AsyncSession) -> None:
    """Test get_finetunable_models returns empty list when no overlays exist."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=[]),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={}),
        patch_cluster_profiles([]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert result == []


@pytest.mark.asyncio
async def test_get_finetunable_models_filters_incompatible_gpus(db_session: AsyncSession) -> None:
    """Overlays whose compatibleAccelerators have no intersection with cluster GPU IDs are excluded."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("meta-llama/Llama-3.1-8B", compatible_accelerators=["74a1", "74a9"]),
        make_overlay("big-model/70B", compatible_accelerators=["75a0"]),  # not in cluster
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["meta-llama/Llama-3.1-8B", "big-model/70B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["meta-llama/Llama-3.1-8B"]


@pytest.mark.asyncio
async def test_get_finetunable_models_no_compatible_accelerators_always_included(db_session: AsyncSession) -> None:
    """Overlays without compatibleAccelerators are compatible with all hardware."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("legacy-model/1B"),  # no compatibleAccelerators
        make_overlay("new-model/7B", compatible_accelerators=["75a0"]),  # not in cluster
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["legacy-model/1B", "new-model/7B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["legacy-model/1B"]


@pytest.mark.asyncio
async def test_get_finetunable_models_empty_cluster_gpu_ids_excludes_all_constrained(db_session: AsyncSession) -> None:
    """When the cluster reports no GPU IDs, overlays with compatibleAccelerators are excluded."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("legacy-model/1B"),  # no compatibleAccelerators — always included
        make_overlay("new-model/7B", compatible_accelerators=["74a1"]),  # constrained — excluded
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={}),
        patch_cluster_profiles(["legacy-model/1B", "new-model/7B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["legacy-model/1B"]


@pytest.mark.asyncio
async def test_get_finetunable_models_skips_generic_overlays(db_session: AsyncSession) -> None:
    """Generic overlays (canonical_name=None) are excluded from the finetunable list."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay(None),  # generic overlay
        make_overlay("meta-llama/Llama-3.1-8B"),
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["meta-llama/Llama-3.1-8B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["meta-llama/Llama-3.1-8B"]


@pytest.mark.asyncio
async def test_get_finetunable_models_enriches_gpu_metadata(db_session: AsyncSession) -> None:
    """Each result carries gpu_count and compatible_accelerators from the overlay."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("meta-llama/Llama-3.1-8B", compatible_accelerators=["74a1", "74a9"], finetuningGpus=4),
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["meta-llama/Llama-3.1-8B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert len(result) == 1
    assert isinstance(result[0], FinetunableModelResponse)
    assert result[0].gpu_count == 4
    assert result[0].compatible_accelerators == ["74a1", "74a9"]
    # 74a1 is in the cluster and resolves to a display name; 74a9 is not
    assert result[0].compatible_accelerator_names == ["AMD Instinct MI300X"]


@pytest.mark.asyncio
async def test_get_finetunable_models_gpu_count_none_when_absent(db_session: AsyncSession) -> None:
    """gpu_count is None when finetuningGpus is not set in the overlay."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [make_overlay("meta-llama/Llama-3.1-8B")]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["meta-llama/Llama-3.1-8B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert result[0].gpu_count is None
    assert result[0].compatible_accelerators == []


@pytest.mark.asyncio
async def test_get_finetunable_models_excludes_recipe_without_matching_template(db_session: AsyncSession) -> None:
    """Recipes whose aimManifest.modelId has no matching cluster template are excluded."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("meta-llama/Llama-3.1-8B"),  # template present
        make_overlay("orphan/model-13B"),  # no template
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["meta-llama/Llama-3.1-8B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["meta-llama/Llama-3.1-8B"]


@pytest.mark.asyncio
async def test_get_finetunable_models_excludes_recipe_without_aim_manifest(db_session: AsyncSession) -> None:
    """Recipes lacking aimManifest.modelId are excluded — the cluster cannot vouch for them."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("meta-llama/Llama-3.1-8B", aim_id=None, model_id=None),  # no aimManifest
        make_overlay("microsoft/DialoGPT-medium"),
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["meta-llama/Llama-3.1-8B", "microsoft/DialoGPT-medium"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["microsoft/DialoGPT-medium"]


@pytest.mark.asyncio
async def test_get_finetunable_models_excludes_when_no_templates_present(db_session: AsyncSession) -> None:
    """When the cluster advertises no AIMClusterProfiles, all recipes are hidden."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [make_overlay("meta-llama/Llama-3.1-8B")]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles([]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert result == []


@pytest.mark.asyncio
async def test_get_finetunable_models_combines_template_and_gpu_filters(db_session: AsyncSession) -> None:
    """A recipe is shown only when BOTH a matching template exists AND GPUs are compatible."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("template-and-gpu-ok/A", compatible_accelerators=["74a1"]),
        make_overlay("template-ok-gpu-bad/B", compatible_accelerators=["75a0"]),  # GPU mismatch
        make_overlay("gpu-ok-template-missing/C", compatible_accelerators=["74a1"]),  # no template
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["template-and-gpu-ok/A", "template-ok-gpu-bad/B"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert [m.canonical_name for m in result] == ["template-and-gpu-ok/A"]


@pytest.mark.asyncio
async def test_get_finetunable_models_reflects_templates_added_after_first_call(db_session: AsyncSession) -> None:
    """Recipe hidden when no template, then visible once a matching template appears on the cluster."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [make_overlay("meta-llama/Llama-3.1-8B")]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch(
            "app.aims.gateway.list_aim_cluster_profiles_by_aim_ids",
            side_effect=[[], [make_profile(spec_aim_id="meta-llama/Llama-3.1-8B")]],
        ),
    ):
        before = await get_finetunable_models(db_session, kube_client)
        after = await get_finetunable_models(db_session, kube_client)

    assert before == []
    assert [m.canonical_name for m in after] == ["meta-llama/Llama-3.1-8B"]


@pytest.mark.asyncio
async def test_get_finetunable_models_carries_hf_token_required_from_overlay(db_session: AsyncSession) -> None:
    """Each result mirrors the recipe overlay's top-level hfTokenRequired flag.

    Three overlays cover the full domain: explicitly gated (True), explicitly not gated
    (False), and not declared (None). The UI relies on the True/False/None distinction
    to decide whether to show the HF token section.
    """
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [
        make_overlay("gated/model", hf_token_required=True),
        make_overlay("open/model", hf_token_required=False),
        make_overlay("undeclared/model"),
    ]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["gated/model", "open/model", "undeclared/model"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    by_name = {m.canonical_name: m for m in result}
    assert by_name["gated/model"].hf_token_required is True
    assert by_name["open/model"].hf_token_required is False
    assert by_name["undeclared/model"].hf_token_required is None


@pytest.mark.asyncio
async def test_get_finetunable_models_ignores_non_bool_hf_token_required(db_session: AsyncSession) -> None:
    """A malformed overlay value (string, int) is coerced to None rather than leaking through.

    Guards the contract surfaced to the UI: `hfTokenRequired` is either bool or null,
    never a truthy string that would silently force the token prompt on a non-gated model.
    """
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [make_overlay("weird/model", hf_token_required="yes")]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["weird/model"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert result[0].hf_token_required is None


@pytest.mark.asyncio
async def test_get_finetunable_models_serializes_hf_token_required_as_camel_case(db_session: AsyncSession) -> None:
    """The wire payload uses camelCase `hfTokenRequired` so the UI can read it directly."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [make_overlay("gated/model", hf_token_required=True)]
    kube_client = make_kube_client()

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch_cluster_profiles(["gated/model"]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    payload = result[0].model_dump(by_alias=True)
    assert payload["hfTokenRequired"] is True
    assert "hf_token_required" not in payload


@pytest.mark.parametrize("non_ready_status", ["Pending", "Progressing", "Degraded", "Failed", "NotAvailable"])
@pytest.mark.asyncio
async def test_get_finetunable_models_excludes_recipe_when_template_not_ready(
    db_session: AsyncSession, non_ready_status: str
) -> None:
    """Templates whose status.status is not Ready do not contribute their modelId, even if spec.modelId is populated."""
    finetune_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    overlays = [make_overlay("meta-llama/Llama-3.1-8B")]
    kube_client = make_kube_client()
    not_ready_template = make_profile(spec_aim_id="meta-llama/Llama-3.1-8B", status=non_ready_status)

    with (
        patch("app.models.service.get_chart", return_value=finetune_chart),
        patch("app.models.service.list_overlays", return_value=overlays),
        patch("app.models.service.get_cluster_gpu_device_info", return_value={"74a1": "AMD Instinct MI300X"}),
        patch("app.aims.gateway.list_aim_cluster_profiles_by_aim_ids", return_value=[not_ready_template]),
    ):
        result = await get_finetunable_models(db_session, kube_client)

    assert result == []


@pytest.mark.asyncio
async def test_delete_model_with_active_deployments_raises_conflict(test_namespace: str) -> None:
    """Deleting a model with active AIMService deployments raises DeletionConflictException."""
    model_name = "deployed-model"
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_minio_client = MagicMock(spec=MinioClient)

    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=model_name, namespace=test_namespace),
        spec=AIMModelSpec(model_sources=[AIMModelSource(source_uri="s3://bucket/path/")]),
    )

    with (
        patch("app.aims.gateway.get_aim_model", return_value=aim_model),
        patch("app.aims.gateway.list_aim_services_for_model", return_value=[MagicMock()]),
        patch("app.aims.gateway.delete_aim_model", new_callable=AsyncMock) as mock_delete_cr,
        patch("app.models.service.delete_from_s3", new_callable=AsyncMock) as mock_delete_s3,
        pytest.raises(DeletionConflictException),
    ):
        await delete_model(mock_kube_client, model_name, test_namespace, mock_minio_client)

    mock_delete_cr.assert_not_called()
    mock_delete_s3.assert_not_called()


@pytest.mark.asyncio
async def test_delete_model_force_deletes_with_active_deployments(test_namespace: str) -> None:
    """With force=True, active AIMServices are deleted first, then the model is removed."""
    model_name = "deployed-model"
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_minio_client = MagicMock(spec=MinioClient)

    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=model_name, namespace=test_namespace),
        spec=AIMModelSpec(model_sources=[AIMModelSource(source_uri="s3://bucket/path/")]),
    )
    mock_svc = MagicMock()
    mock_svc.metadata.name = "wb-aim-active-123"
    mock_svc.id = str(uuid4())

    with (
        patch("app.aims.gateway.get_aim_model", return_value=aim_model),
        patch("app.aims.gateway.list_aim_services_for_model", return_value=[mock_svc]),
        patch("app.aims.gateway.delete_aim_service", new_callable=AsyncMock) as mock_delete_svc,
        patch("app.aims.gateway.delete_aim_model", new_callable=AsyncMock) as mock_delete_cr,
        patch("app.models.service.delete_from_s3", new_callable=AsyncMock),
    ):
        await delete_model(mock_kube_client, model_name, test_namespace, mock_minio_client, force=True)

    mock_delete_svc.assert_called_once()
    mock_delete_cr.assert_called_once_with(mock_kube_client, test_namespace, model_name)


@pytest.mark.asyncio
async def test_delete_model_s3_not_found_logs_warning(test_namespace: str) -> None:
    """If S3 weights are missing, delete_model logs a warning and continues without raising."""
    model_name = "model-missing-s3"
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_minio_client = MagicMock(spec=MinioClient)

    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=model_name, namespace=test_namespace),
        spec=AIMModelSpec(model_sources=[AIMModelSource(source_uri="s3://bucket/weights/")]),
    )

    with (
        patch("app.aims.gateway.get_aim_model", return_value=aim_model),
        patch("app.aims.gateway.list_aim_services_for_model", return_value=[]),
        patch("app.aims.gateway.delete_aim_model", new_callable=AsyncMock),
        patch("app.models.service.delete_from_s3", side_effect=NotFoundException("S3 object not found")),
    ):
        # Should not raise — CR is deleted, S3 miss logged as warning
        await delete_model(mock_kube_client, model_name, test_namespace, mock_minio_client)


# ============================================================================
# Orchestration Tests - run_finetune_model_workload
# ============================================================================


@pytest.fixture(autouse=True)
def neutralize_aim_base_provisioning():  # type: ignore[misc]
    """Stub k8s calls that finetune launch performs outside the workload path.

    Both patched targets hit live k8s custom-objects surfaces that finetune
    tests only mock enough for the workload path itself. Tests that assert
    specific provisioning or profile-resolution behavior re-patch these targets
    inside their own with-block.

    list_aims returns a single Ready AIMClusterModel by default so tests that
    don't care about cluster model resolution don't fail the mandatory model
    check introduced with the removal of the aim-base fallback.
    """
    with patch("app.models.service.ensure_namespace_aim_base_model", new_callable=AsyncMock):
        yield


@pytest.mark.asyncio
async def test_run_finetune_model_workload_with_uuid(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload with existing AIMModel UUID (transfer learning)."""
    model_uuid = uuid4()
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=str(model_uuid), namespace=test_namespace),
        spec=AIMModelSpec(model_sources=[AIMModelSource(source_uri="s3://bucket/models/base-model/weights")]),
        status=AIMModelStatusFields(
            status="Ready",
            image_metadata=AIMImageMetadata(model=AIMModelMetadata(canonical_name="meta-llama/Llama-3.1-8B")),
        ),
    )

    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(
        display_name="Finetuned-Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    with (
        patch("app.models.service.aims_gateway.get_aim_model", return_value=aim_model),
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock) as mock_apply,
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model_uuid,
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

        mock_apply.assert_called_once()
        call_kwargs = mock_apply.call_args[1] if mock_apply.call_args[1] else {}
        extra_labels = call_kwargs.get("extra_labels", {})
        assert extra_labels[MODEL_NAME_LABEL] == "Finetuned-Model"
        assert extra_labels[MODEL_ID_LABEL] == str(result.workload_id)

        assert result.display_name == "Finetuned-Model"
        assert result.base_model == "meta-llama/Llama-3.1-8B"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_resolves_weights_from_profiles_overrides(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """A re-finetune base whose weights live under spec.profiles.overrides.modelSources
    (the v1alpha2 imported / fine-tuned shape, with no flat spec.modelSources) succeeds,
    and that override URI is forwarded as the base model URI for training."""
    model_uuid = uuid4()
    override_uri = "s3://bucket/ns/finetuned-models/llama3/run1/checkpoint-final"
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=str(model_uuid), namespace=test_namespace),
        spec=AIMModelSpec(
            model_sources=[],  # legacy flat field empty — weights only in profiles overrides
            profiles=AIMModelProfilesSpec(
                overrides=ProfileOverrides(
                    model_id="meta-llama/Llama-3.1-8B",
                    model_sources=[AIMModelSource(model_id="meta-llama/Llama-3.1-8B", source_uri=override_uri)],
                )
            ),
        ),
        status=AIMModelStatusFields(status="Ready", aim_id="meta-llama/Llama-3.1-8B"),
    )

    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(display_name="Re-Finetuned-Model", dataset_id=dataset.id)

    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}
    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    with (
        patch("app.models.service.aims_gateway.get_aim_model", return_value=aim_model),
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model_uuid,
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

    assert result.base_model == "meta-llama/Llama-3.1-8B"
    assert len(helm_overrides_captured) == 1
    overrides = helm_overrides_captured[0]
    # basemodel is the override weights URI with the s3:// scheme stripped, as the
    # training chart expects.
    assert overrides["basemodel"] == override_uri.removeprefix("s3://")
    # modelId is carried forward from the resolved source so the published AIMModel CR
    # gets the correct artifact identity.
    assert overrides["aimManifest"]["modelId"] == "meta-llama/Llama-3.1-8B"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_with_canonical_name(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload with canonical name (HuggingFace download)."""
    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request
    finetuning_data = FinetuneCreate(
        display_name="HF-Finetuned-Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock) as mock_apply,
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

        mock_apply.assert_called_once()
        call_kwargs = mock_apply.call_args[1] if mock_apply.call_args[1] else {}
        extra_labels = call_kwargs.get("extra_labels", {})
        assert extra_labels[MODEL_NAME_LABEL] == "HF-Finetuned-Model"
        assert extra_labels[MODEL_ID_LABEL] == str(result.workload_id)
        assert result.display_name == "HF-Finetuned-Model"
        assert result.base_model == "meta-llama/Llama-3.1-8B"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_with_single_segment_hf_name(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Single-segment HuggingFace model IDs (for example 'gpt2') should remain supported."""
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(
        display_name="HF-Single-Segment-Finetuned-Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "gpt2"
    mock_overlay.overlay = {"aimManifest": {"aimId": "gpt2", "modelId": "gpt2"}}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch_cluster_model("gpt2"),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
        patch(
            "app.models.service.get_aim_model", new_callable=AsyncMock, side_effect=NotFoundException("not found")
        ) as mock_get_aim_model,
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="gpt2",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

    assert result.base_model == "gpt2"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_includes_mlflow_tracking_when_mlflow_workspace_running(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """Finetuning config gets MLflow tracking from workload endpoints (internal), not output."""
    finetuning_chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    mlflow_chart = await factory.create_chart(db_session, name=MLFLOW_CHART_NAME)
    dataset = await factory.create_dataset(db_session, namespace=test_namespace)
    mlflow_workload = await factory.create_workload(
        db_session,
        namespace=test_namespace,
        chart=mlflow_chart,
        status=WorkloadStatus.RUNNING,
        workload_type=WorkloadType.WORKSPACE,
        include_isolation_data=False,
    )
    mlflow_response = WorkloadResponse.model_validate(mlflow_workload)
    expected_uri = mlflow_response.endpoints["internal"]

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    test_overlay = MagicMock(spec=Overlay)
    test_overlay.canonical_name = "test/model"
    test_overlay.overlay = {"aimManifest": {"aimId": "test/model", "modelId": "test/model"}}

    kube_client = MagicMock()
    with (
        patch("app.models.service.list_overlays", return_value=[test_overlay]),
        patch_cluster_model("test/model"),
        patch("app.models.service.get_workloads", new_callable=AsyncMock, return_value=[mlflow_workload]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=kube_client,
            model_id="test/model",
            finetuning_data=FinetuneCreate(display_name="my-run", dataset_id=dataset.id),
            submitter="test@example.com",
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    overrides = helm_overrides_captured[0]
    assert "finetuning_config" in overrides
    tracking = overrides["finetuning_config"].get("tracking")
    assert tracking is not None
    assert tracking["mlflow_server_uri"] == expected_uri
    assert tracking["experiment_name"] == "my-run"
    assert overrides["finetuning_config"]["training_args"]["report_to"] == ["mlflow"]


@pytest.mark.asyncio
async def test_run_finetune_model_workload_skips_mlflow_tracking_when_no_mlflow_workspace(
    db_session: AsyncSession, test_namespace: str
) -> None:
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    dataset = await factory.create_dataset(db_session, namespace=test_namespace)

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    test_overlay = MagicMock(spec=Overlay)
    test_overlay.canonical_name = "test/model"
    test_overlay.overlay = {"aimManifest": {"aimId": "test/model", "modelId": "test/model"}}

    kube_client = MagicMock()
    with (
        patch("app.models.service.list_overlays", return_value=[test_overlay]),
        patch_cluster_model("test/model"),
        patch("app.models.service.get_workloads", new_callable=AsyncMock, return_value=[]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=kube_client,
            model_id="test/model",
            finetuning_data=FinetuneCreate(display_name="my-run", dataset_id=dataset.id),
            submitter="test@example.com",
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    overrides = helm_overrides_captured[0]
    assert "finetuning_config" in overrides
    assert "tracking" not in overrides["finetuning_config"]


@pytest.mark.asyncio
async def test_run_finetune_model_workload_sets_bucket_storage_host(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """bucketStorageHost in helm overrides uses MINIO_URL so pods do not inherit a stale chart default."""
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    dataset = await factory.create_dataset(db_session, namespace=test_namespace)

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    test_overlay = MagicMock(spec=Overlay)
    test_overlay.canonical_name = "test/model"
    test_overlay.overlay = {"aimManifest": {"aimId": "test/model", "modelId": "test/model"}}

    minio_url = "http://minio.example.svc.cluster.local:80"
    with (
        patch("app.models.service.list_overlays", return_value=[test_overlay]),
        patch_cluster_model("test/model"),
        patch("app.models.service.get_workloads", new_callable=AsyncMock, return_value=[]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
        patch("app.models.service.MINIO_URL", minio_url),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=MagicMock(),
            model_id="test/model",
            finetuning_data=FinetuneCreate(display_name="my-run", dataset_id=dataset.id),
            submitter="test@example.com",
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    overrides = helm_overrides_captured[0]
    assert overrides["bucketStorageHost"] == minio_url


@pytest.mark.asyncio
async def test_run_finetune_model_workload_without_hf_token_does_not_call_get_secret_details(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)
    finetuning_data = FinetuneCreate(
        display_name="No-HF-Token-Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
        patch("app.models.service.get_secret_details") as mock_get_secret,
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )
        mock_get_secret.assert_not_called()


@pytest.mark.asyncio
async def test_run_finetune_model_workload_with_hf_token(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request with HF token secret name
    finetuning_data = FinetuneCreate(
        display_name="HF-Token-Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
        hf_token_secret_name="hf-token-secret",
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    hf_secret = SecretResponse(metadata=K8sMetadata(name="hf-token-secret", namespace=test_namespace))

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest") as mock_render,
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
        patch("app.models.service.get_secret_details", return_value=hf_secret) as mock_get_secret,
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

        # Verify render was called with HF token secret
        call_args = mock_render.call_args
        overlays = call_args[1]["overlays_values"]
        helm_overrides = overlays[-1]

        assert "hfTokenSecret" in helm_overrides
        assert helm_overrides["hfTokenSecret"]["name"] == "hf-token-secret"
        assert helm_overrides["hfTokenSecret"]["key"] == "token"

        mock_get_secret.assert_called_once_with(
            namespace=test_namespace,
            secret_name="hf-token-secret",
            kube_client=mock_kube_client,
        )


@pytest.mark.asyncio
async def test_run_finetune_model_workload_sets_aim_manifest_helm_overrides(
    db_session: AsyncSession, test_namespace: str
) -> None:
    """aimManifest helm overrides are set so the aimmodel-applier sidecar creates the AIMModel CR after training."""
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME)
    dataset = await factory.create_dataset(db_session, namespace=test_namespace)

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    test_overlay = MagicMock(spec=Overlay)
    test_overlay.canonical_name = "test/model"
    test_overlay.overlay = {"aimManifest": {"aimId": "test/model", "modelId": "test/model"}}

    with (
        patch("app.models.service.list_overlays", return_value=[test_overlay]),
        patch_cluster_model("test/model"),
        patch("app.models.service.get_workloads", new_callable=AsyncMock, return_value=[]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=MagicMock(),
            model_id="test/model",
            finetuning_data=FinetuneCreate(display_name="my-finetuned-model", dataset_id=dataset.id),
            submitter="test@example.com",
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    overrides = helm_overrides_captured[0]
    aim_manifest = overrides.get("aimManifest")
    assert aim_manifest is not None, "aimManifest must be in helm overrides to enable the aimmodel-applier sidecar"
    assert aim_manifest["enabled"] is True
    assert aim_manifest["modelName"].startswith("wb-"), "modelName should be the workload's K8s resource name"
    labels = aim_manifest.get("labels", {})
    # WORKLOAD_TYPE_LABEL is the contract with fine_tuning.service._is_fine_tuning_model, which
    # backs GET /v1/projects/{project}/fine-tuning/models. Without it the resulting AIMModel is
    # invisible to the Custom Models page.
    assert labels.get(WORKLOAD_TYPE_LABEL) == WorkloadType.FINE_TUNING.value
    assert labels.get(WORKLOAD_ID_LABEL) == str(result.workload_id)
    assert labels.get(MODEL_NAME_LABEL) == "my-finetuned-model"
    # Every label value MUST be a plain str — if a StrEnum or UUID leaks through,
    # yaml.dump emits it as a YAML sequence and the Helm `quote` filter renders
    # it as `"[FINE_TUNING]"`, which K8s rejects as an invalid label value.
    for key, value in labels.items():
        assert isinstance(value, str) and not isinstance(value, Enum), (
            f"label {key} must be a plain str, got {type(value).__name__}: {value!r}"
        )
    # Belt-and-suspenders: dump through PyYAML and confirm no flow-style sequence
    # leaks into the rendered output for any label value.
    rendered = yaml.dump({"labels": labels})
    assert "[" not in rendered and "]" not in rendered, (
        f"aim_manifest labels must yaml-dump as scalars, not sequences:\n{rendered}"
    )


@pytest.mark.asyncio
async def test_run_finetune_model_workload_uuid_base_uses_aim_id_for_overlay_lookup(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """When a finetuned model (UUID) has no image_metadata canonical_name, spec.aim_id is used
    for overlay lookup so the correct DeepSpeed/bf16 config is applied."""
    model_uuid = uuid4()
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=str(model_uuid), namespace=test_namespace),
        spec=AIMModelSpec(
            model_sources=[AIMModelSource(source_uri="s3://bucket/models/finetuned/weights")],
            aim_id="meta-llama/Llama-3.1-8B",  # stamped by aimmodel-applier; no OCI image metadata
        ),
        # status.aim_id mirrors spec.aim_id — the v1alpha2 controller populates
        # it from spec or discovery, and production code reads from status.
        status=AIMModelStatusFields(status="Ready", aim_id="meta-llama/Llama-3.1-8B"),
    )

    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(
        display_name="Level-2-Finetuned",
        dataset_id=dataset.id,
    )

    mock_kube_client = AsyncMock(spec=KubernetesClient)
    overlay_canonical_names_used: list[str | None] = []
    helm_overrides_captured: list = []

    async def capture_list_overlays(session, chart_id, canonical_name, include_generic=False):  # noqa: ARG001
        overlay_canonical_names_used.append(canonical_name)
        return []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    with (
        patch("app.models.service.aims_gateway.get_aim_model", return_value=aim_model),
        patch("app.models.service.list_overlays", side_effect=capture_list_overlays),
        patch("app.models.service.get_workloads", return_value=[]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        result = await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model_uuid,
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

    assert result.base_model == "meta-llama/Llama-3.1-8B"
    assert overlay_canonical_names_used == ["meta-llama/Llama-3.1-8B"], (
        "Overlay lookup must use the original HF canonical name from aim_id, not the UUID"
    )

    assert len(helm_overrides_captured) == 1
    aim_manifest = helm_overrides_captured[0].get("aimManifest", {})
    assert aim_manifest.get("aimId") == "meta-llama/Llama-3.1-8B", (
        "aimId must be forwarded from the AIMModel spec so the resulting CR gets the correct identifier"
    )
    assert aim_manifest.get("modelId") == aim_model.spec.model_sources[0].model_id


@pytest.mark.asyncio
async def test_run_finetune_model_workload_dataset_not_found(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request with non-existent dataset
    finetuning_data = FinetuneCreate(
        display_name="Model-with-Missing-Dataset",
        dataset_id=uuid4(),  # Non-existent dataset
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        pytest.raises(NotFoundException, match="Dataset not found"),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )


@pytest.mark.parametrize(
    "spec",
    [
        # No weights in either the flat field or any profiles override.
        AIMModelSpec(model_sources=[]),
        # A profiles block exists but its override carries no model sources — still no weights.
        AIMModelSpec(model_sources=[], profiles=AIMModelProfilesSpec(overrides=ProfileOverrides(model_sources=[]))),
    ],
    ids=["no-profiles", "empty-profiles-override"],
)
@pytest.mark.asyncio
async def test_run_finetune_model_workload_model_without_weights(
    db_session: AsyncSession, test_namespace: str, test_user: str, spec: AIMModelSpec
) -> None:
    """When neither the flat spec.modelSources nor profiles.overrides.modelSources
    carries a weights URI, finetuning is rejected with the existing ValidationException."""
    model_uuid = uuid4()
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=str(model_uuid), namespace=test_namespace),
        spec=spec,
        status=AIMModelStatusFields(status="Ready"),
    )

    finetuning_data = FinetuneCreate(
        display_name="Finetuned-Model",
        dataset_id=uuid4(),
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    mock_kube_client = AsyncMock(spec=KubernetesClient)

    with (
        patch("app.models.service.aims_gateway.get_aim_model", return_value=aim_model),
        pytest.raises(ValidationException, match="has no weights URI"),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model_uuid,
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )


@pytest.mark.asyncio
async def test_run_finetune_model_workload_deployment_failure(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Test run_finetune_model_workload sets workload status to FAILED on deployment error."""
    # Create dataset
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")

    # Create chart
    chart = await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    # Create finetuning request
    finetuning_data = FinetuneCreate(
        display_name="Failed-Deployment",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    # Mock dependencies
    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", side_effect=Exception("K8s deployment failed")),
        pytest.raises(Exception, match="K8s deployment failed"),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )


@pytest.mark.asyncio
async def test_run_finetune_model_workload_provisions_namespace_aim_base(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """Launching a finetune provisions the namespace aim-base the published model derives from."""
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(
        display_name="Finetuned-Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
        patch("app.models.service.ensure_namespace_aim_base_model", new_callable=AsyncMock) as mock_ensure,
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

    mock_ensure.assert_awaited_once_with(mock_kube_client, test_namespace)


@pytest.mark.asyncio
async def test_run_finetune_model_workload_provisions_aim_base_before_creating_workload(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """A provisioning failure aborts before any workload is created, leaving no orphan PENDING row."""
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(
        display_name="Finetuned-Model",
        dataset_id=dataset.id,
        batch_size=4,
        learning_rate=0.0001,
        epochs=3,
    )

    mock_kube_client = AsyncMock(spec=KubernetesClient)
    mock_overlay = MagicMock(spec=Overlay)
    mock_overlay.canonical_name = "meta-llama/Llama-3.1-8B"
    mock_overlay.overlay = {"aimManifest": {"aimId": "meta-llama/Llama-3.1-8B", "modelId": "meta-llama/Llama-3.1-8B"}}

    with (
        patch("app.models.service.list_overlays", return_value=[mock_overlay]),
        patch_cluster_model("meta-llama/Llama-3.1-8B"),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.render_helm_template", return_value="mock-manifest"),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock) as mock_apply,
        patch("app.models.service.create_workload", new_callable=AsyncMock) as mock_create_workload,
        patch(
            "app.models.service.ensure_namespace_aim_base_model",
            new_callable=AsyncMock,
            side_effect=RuntimeError("base provisioning failed"),
        ),
        pytest.raises(RuntimeError, match="base provisioning failed"),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

    mock_create_workload.assert_not_called()
    mock_apply.assert_not_called()


@pytest.mark.asyncio
async def test_run_finetune_model_workload_sets_base_model_from_cluster_model(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """aimManifest.baseModel.name is the AIMClusterModel name matching the recipe's aimId.

    The aim-engine controller resolves modelRef by AIMClusterModel name (not AIMClusterProfile
    name). The fine-tuned AIMModel inherits the optimized profiles via the source-model label
    that aim-engine stamps on profiles when it discovers them from the AIMClusterModel.
    """
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(display_name="FT-Model", dataset_id=dataset.id)
    mock_kube_client = AsyncMock(spec=KubernetesClient)

    overlay = make_overlay("meta-llama/Llama-3.1-8B", aim_id="meta-llama/Llama-3.1-8B")

    cluster_model = make_cluster_model(aim_id="meta-llama/Llama-3.1-8B", status="Ready")
    cluster_model.metadata.name = "amdenterpriseai-aim-instinct-meta-llama-3-1-8b-cluster-model"

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    with (
        patch("app.models.service.list_overlays", return_value=[overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.aims_gateway.list_aims", return_value=[cluster_model]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    base_model = helm_overrides_captured[0]["aimManifest"]["baseModel"]
    assert base_model["name"] == "amdenterpriseai-aim-instinct-meta-llama-3-1-8b-cluster-model"
    assert base_model["scope"] == "Auto"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_sets_base_model_from_cluster_model_uuid_base(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """For UUID-based re-finetunes, aimId falls back to aim_model.status.aim_id when the overlay lacks it."""
    model_uuid = uuid4()
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name=str(model_uuid), namespace=test_namespace),
        spec=AIMModelSpec(model_sources=[AIMModelSource(source_uri="s3://bucket/models/base-model/weights")]),
        status=AIMModelStatusFields(
            status="Ready",
            aim_id="meta-llama/Llama-3.1-8B",
            image_metadata=AIMImageMetadata(model=AIMModelMetadata(canonical_name="meta-llama/Llama-3.1-8B")),
        ),
    )

    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(display_name="Re-FT-Model", dataset_id=dataset.id)
    mock_kube_client = AsyncMock(spec=KubernetesClient)

    # Overlay has no aimManifest.aimId — simulates a generic or missing recipe overlay
    overlay_without_aim_id = MagicMock(spec=Overlay)
    overlay_without_aim_id.canonical_name = "meta-llama/Llama-3.1-8B"
    overlay_without_aim_id.overlay = {}

    cluster_model = make_cluster_model(aim_id="meta-llama/Llama-3.1-8B", status="Ready")
    cluster_model.metadata.name = "amdenterpriseai-aim-instinct-meta-llama-3-1-8b-cluster-model"

    helm_overrides_captured: list = []

    async def capture_render(*, chart, name, namespace, overlays_values):  # noqa: ARG001
        helm_overrides_captured.append(overlays_values[-1] if overlays_values else {})
        return ""

    with (
        patch("app.models.service.aims_gateway.get_aim_model", return_value=aim_model),
        patch("app.models.service.list_overlays", return_value=[overlay_without_aim_id]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.aims_gateway.list_aims", return_value=[cluster_model]),
        patch("app.models.service.render_helm_template", side_effect=capture_render),
        patch("app.models.service.apply_manifest", new_callable=AsyncMock),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id=model_uuid,
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )

    assert len(helm_overrides_captured) == 1
    base_model = helm_overrides_captured[0]["aimManifest"]["baseModel"]
    assert base_model["name"] == "amdenterpriseai-aim-instinct-meta-llama-3-1-8b-cluster-model"
    assert base_model["scope"] == "Auto"


@pytest.mark.asyncio
async def test_run_finetune_model_workload_raises_when_no_ready_cluster_model(
    db_session: AsyncSession, test_namespace: str, test_user: str
) -> None:
    """When no Ready AIMClusterModel matches the recipe aimId, a ValidationException is raised.

    There is no fallback — a fine-tuning job without a resolvable model would produce a
    broken AIMModel that can never deploy, so we fail fast before the job is submitted.
    """
    dataset = await factory.create_dataset(db_session, namespace=test_namespace, name="Training Dataset")
    await factory.create_chart(db_session, name=FINETUNING_CHART_NAME, chart_type=WorkloadType.FINE_TUNING)

    finetuning_data = FinetuneCreate(display_name="FT-Model-No-Profile", dataset_id=dataset.id)
    mock_kube_client = AsyncMock(spec=KubernetesClient)

    overlay = make_overlay("meta-llama/Llama-3.1-8B", aim_id="meta-llama/Llama-3.1-8B")
    not_ready_model = make_cluster_model(aim_id="meta-llama/Llama-3.1-8B", status="Pending")

    with (
        patch("app.models.service.list_overlays", return_value=[overlay]),
        patch("app.models.service.get_workloads", return_value=[]),
        patch("app.models.service.aims_gateway.list_aims", return_value=[not_ready_model]),
        pytest.raises(ValidationException),
    ):
        await run_finetune_model_workload(
            session=db_session,
            kube_client=mock_kube_client,
            model_id="meta-llama/Llama-3.1-8B",
            finetuning_data=finetuning_data,
            submitter=test_user,
            namespace=test_namespace,
        )
