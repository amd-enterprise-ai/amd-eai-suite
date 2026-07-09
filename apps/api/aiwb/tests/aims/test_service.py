# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs service layer."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes_asyncio.client import ApiException
from pydantic.alias_generators import to_camel

from api_common.exceptions import ExternalServiceError, NotFoundException, ValidationException
from app.aims.constants import AIM_COND_HTTP_ROUTE_READY, AIM_COND_INFERENCE_SERVICE_READY
from app.aims.crds import (
    AIMModelProfilesDerivedFrom,
    AIMModelProfilesSpec,
    AIMModelResource,
    AIMModelSource,
    AIMModelSpec,
    AIMModelStatusFields,
    AIMProfileResource,
    AIMProfileStatus,
    AIMServiceResource,
    AIMServiceSpec,
    AIMServiceStatusFields,
    ProfileOverrides,
    ProfileSelector,
    ResolvedRef,
)
from app.aims.enums import AcceleratorType, AIMModelStatus, AIMServiceStatus, OptimizationMetric
from app.aims.schemas import AIMDeployRequest
from app.aims.service import (
    _create_cluster_auth_group_for_aim,
    _delete_cluster_auth_group_for_aim,
    deploy_aim,
    get_aim_by_resource_name,
    get_aim_cluster_profile,
    get_aim_profile,
    get_aim_service,
    list_aim_cluster_profiles,
    list_aim_services,
    list_aims,
    list_chattable_aim_services,
    undeploy_aim,
    update_aim_scaling_policy,
)
from app.custom_models.constants import IMPORT_ERROR_ANNOTATION, IMPORT_STATE_ANNOTATION
from app.dispatch.crds import K8sMetadata
from app.workloads.constants import MODEL_NAME_LABEL, MODEL_SOURCE_TYPE_LABEL
from app.workloads.enums import ModelSourceType
from tests.factory import (
    make_aim_cluster_model,
    make_aim_cluster_profile,
    make_aim_service_k8s,
)


@pytest.fixture
def kube_client() -> MagicMock:
    """Mock K8s client."""
    return MagicMock()


@pytest.mark.asyncio
async def test_list_aims(kube_client: MagicMock) -> None:
    """Test list_aims service function."""
    aim = make_aim_cluster_model()
    with patch("app.aims.service.get_aims_from_k8s", return_value=[aim]):
        result = await list_aims(kube_client)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_aim_by_resource_name_success(kube_client: MagicMock) -> None:
    """Test successful retrieval."""
    aim = make_aim_cluster_model(name="my-aim")
    with patch("app.aims.service.get_aim_by_name", return_value=aim):
        result = await get_aim_by_resource_name(kube_client, "my-aim")
    assert result.metadata.name == "my-aim"


@pytest.mark.asyncio
async def test_get_aim_by_resource_name_not_found(kube_client: MagicMock) -> None:
    """Test raises NotFoundException."""
    with patch("app.aims.service.get_aim_by_name", return_value=None):
        with pytest.raises(NotFoundException):
            await get_aim_by_resource_name(kube_client, "missing")


@pytest.mark.asyncio
async def test_list_aims_passes_through_discovered_hardware(kube_client: MagicMock) -> None:
    """The catalog returns the AIMClusterModel resource as-is; the engine's
    ``status.discoveredProfiles.byHardware`` survives unchanged so consumers
    can read accelerator metadata directly from the resource."""
    aim = make_aim_cluster_model(
        name="llama3-8b",
        accelerator_type="gpu",
        accelerator_model="MI300X",
        accelerator_count=1,
    )

    with patch("app.aims.service.get_aims_from_k8s", return_value=[aim]):
        result = await list_aims(kube_client)

    assert len(result) == 1
    assert result[0].status.discovered_profiles is not None
    by_hardware = result[0].status.discovered_profiles.by_hardware
    assert len(by_hardware) == 1
    entry = by_hardware[0]
    assert entry.accelerator_type == "gpu"
    assert entry.accelerator_model == "MI300X"
    assert entry.accelerator_count == 1
    assert entry.supported is True


@pytest.mark.asyncio
async def test_list_aims_passes_through_multiple_hardware_groups(kube_client: MagicMock) -> None:
    """When the engine publishes multiple hardware groups, every group is
    surfaced verbatim and in order — the UI renders the AIM's full set of
    runtime options without picking a representative."""
    aim = AIMModelResource.model_validate(
        {
            "metadata": {"name": "multi-hw", "namespace": "ns"},
            "spec": {"image": "img"},
            "status": {
                "status": "Ready",
                "discoveredProfiles": {
                    "byHardware": [
                        {
                            "acceleratorType": "gpu",
                            "acceleratorModel": "MI300X",
                            "acceleratorCount": 1,
                            "supported": True,
                        },
                        {
                            "acceleratorType": "gpu",
                            "acceleratorModel": "MI300X",
                            "acceleratorCount": 2,
                            "supported": True,
                        },
                        {
                            "acceleratorType": "gpu",
                            "acceleratorModel": "MI300X",
                            "acceleratorCount": 8,
                            "supported": False,
                        },
                    ],
                },
            },
        }
    )

    with patch("app.aims.service.get_aims_from_k8s", return_value=[aim]):
        result = await list_aims(kube_client)

    assert result[0].status.discovered_profiles is not None
    by_hardware = result[0].status.discovered_profiles.by_hardware
    assert len(by_hardware) == 3
    assert [h.accelerator_count for h in by_hardware] == [1, 2, 8]
    assert [h.supported for h in by_hardware] == [True, True, False]
    assert all(h.accelerator_type == "gpu" and h.accelerator_model == "MI300X" for h in by_hardware)


@pytest.mark.asyncio
async def test_list_aims_passes_through_unknown_accelerator_type(kube_client: MagicMock) -> None:
    """Hardware groups with an accelerator family AIWB doesn't model still
    surface in the response — the raw engine value is passed through verbatim
    so the UI doesn't lose useful data."""
    aim = make_aim_cluster_model(
        name="unknown-hw",
        accelerator_type="tpu",
        accelerator_model="TPU_V5",
        accelerator_count=4,
    )

    with patch("app.aims.service.get_aims_from_k8s", return_value=[aim]):
        result = await list_aims(kube_client)

    assert result[0].status.discovered_profiles is not None
    by_hardware = result[0].status.discovered_profiles.by_hardware
    assert len(by_hardware) == 1
    entry = by_hardware[0]
    assert entry.accelerator_type == "tpu"
    assert entry.accelerator_model == "TPU_V5"
    assert entry.accelerator_count == 4


@pytest.mark.asyncio
async def test_list_aims_passes_through_aim_without_discovery(kube_client: MagicMock) -> None:
    """AIMs whose engine hasn't populated discoveredProfiles yet still appear
    in the catalog (no filter); ``status.discovered_profiles`` is ``None`` on
    the response, matching the underlying CRD shape."""
    aim = make_aim_cluster_model(name="no-discovery")

    with patch("app.aims.service.get_aims_from_k8s", return_value=[aim]):
        result = await list_aims(kube_client)

    assert len(result) == 1
    assert result[0].status.discovered_profiles is None


@pytest.mark.asyncio
async def test_list_aims_filters_by_accelerator_type_single(kube_client: MagicMock) -> None:
    """Single-value `accelerator_type=[CPU]` returns only AIMs with a CPU footprint;
    AIMs with unknown or missing accelerator families are excluded."""
    cpu_aim = make_aim_cluster_model(
        name="cpu-aim",
        accelerator_type="cpu",
        accelerator_model="EPYC_ZEN5",
    )
    gpu_aim = make_aim_cluster_model(
        name="gpu-aim",
        accelerator_type="gpu",
        accelerator_model="MI300X",
        accelerator_count=1,
    )
    unknown_aim = make_aim_cluster_model(
        name="unknown-aim",
        accelerator_type="tpu",
    )

    with patch("app.aims.service.get_aims_from_k8s", return_value=[cpu_aim, gpu_aim, unknown_aim]):
        result = await list_aims(kube_client, accelerator_type=[AcceleratorType.CPU])

    assert len(result) == 1
    assert result[0].metadata.name == "cpu-aim"
    assert result[0].status.discovered_profiles is not None
    assert result[0].status.discovered_profiles.by_hardware[0].accelerator_type == "cpu"


@pytest.mark.asyncio
async def test_list_aims_filters_by_accelerator_type_multiple(kube_client: MagicMock) -> None:
    """Multi-value `accelerator_type=[CPU, GPU]` ORs the requested families together
    — both the CPU and GPU AIMs match, the unknown-family AIM does not."""
    cpu_aim = make_aim_cluster_model(name="cpu-aim", accelerator_type="cpu", accelerator_model="EPYC_ZEN5")
    gpu_aim = make_aim_cluster_model(name="gpu-aim", accelerator_type="gpu", accelerator_model="MI300X")
    unknown_aim = make_aim_cluster_model(name="unknown-aim", accelerator_type="tpu")

    with patch("app.aims.service.get_aims_from_k8s", return_value=[cpu_aim, gpu_aim, unknown_aim]):
        result = await list_aims(kube_client, accelerator_type=[AcceleratorType.CPU, AcceleratorType.GPU])

    names = {aim.metadata.name for aim in result}
    assert names == {"cpu-aim", "gpu-aim"}


@pytest.mark.asyncio
async def test_list_aims_filter_excludes_aims_with_no_hardware(kube_client: MagicMock) -> None:
    """AIMs whose engine hasn't published a hardware breakdown drop out when a
    filter is set (no way to know if they match), but reappear when the filter
    is removed — same behavior as the prior scalar implementation."""
    aim = make_aim_cluster_model(name="no-discovery")

    with patch("app.aims.service.get_aims_from_k8s", return_value=[aim]):
        filtered = await list_aims(kube_client, accelerator_type=[AcceleratorType.CPU])
        unfiltered = await list_aims(kube_client)

    assert filtered == []
    assert len(unfiltered) == 1
    assert unfiltered[0].status.discovered_profiles is None


@pytest.mark.asyncio
async def test_list_aims_filter_matches_when_any_group_matches(kube_client: MagicMock) -> None:
    """An AIM with mixed hardware groups (hypothetical CPU+GPU AIM) matches a
    filter requesting either family — surfacing the AIM in both CPU-only and
    GPU-only catalog views."""
    aim = AIMModelResource.model_validate(
        {
            "metadata": {"name": "mixed-aim", "namespace": "ns"},
            "spec": {"image": "img"},
            "status": {
                "status": "Ready",
                "discoveredProfiles": {
                    "byHardware": [
                        {"acceleratorType": "cpu", "acceleratorModel": "EPYC_ZEN5", "supported": True},
                        {
                            "acceleratorType": "gpu",
                            "acceleratorModel": "MI300X",
                            "acceleratorCount": 1,
                            "supported": True,
                        },
                    ],
                },
            },
        }
    )

    with patch("app.aims.service.get_aims_from_k8s", return_value=[aim]):
        cpu_result = await list_aims(kube_client, accelerator_type=[AcceleratorType.CPU])
        gpu_result = await list_aims(kube_client, accelerator_type=[AcceleratorType.GPU])

    assert len(cpu_result) == 1
    assert cpu_result[0].metadata.name == "mixed-aim"
    assert len(gpu_result) == 1
    assert gpu_result[0].metadata.name == "mixed-aim"


@pytest.mark.asyncio
async def test_discovered_hardware_survives_list_and_detail(kube_client: MagicMock) -> None:
    """The discovered hardware breakdown survives both the list and detail
    call paths. AIWB no longer enriches the response, so this is essentially a
    contract lock-in — both endpoints return the AIMClusterModel as-is, with
    the engine's ``status.discoveredProfiles.byHardware`` intact."""
    aim = make_aim_cluster_model(
        name="llama3-8b",
        accelerator_type="gpu",
        accelerator_model="MI300X",
        accelerator_count=1,
    )

    with patch("app.aims.service.get_aim_by_name", return_value=aim):
        result = await get_aim_by_resource_name(kube_client, "llama3-8b")

    assert result.status.discovered_profiles is not None
    by_hardware = result.status.discovered_profiles.by_hardware
    assert len(by_hardware) == 1
    entry = by_hardware[0]
    assert entry.accelerator_type == "gpu"
    assert entry.accelerator_model == "MI300X"
    assert entry.accelerator_count == 1


@pytest.mark.asyncio
async def test_deploy_aim(kube_client: MagicMock) -> None:
    """Test deploying an AIM with model name."""
    aim = make_aim_cluster_model()
    svc = make_aim_service_k8s()
    req = AIMDeployRequest(model="meta-llama-3-8b")
    mock_cluster_auth_client = AsyncMock()
    mock_cluster_auth_client.create_group.return_value = {"id": "group-123", "name": "test-group"}

    with (
        patch("app.aims.service.get_aim_by_name", return_value=aim),
        patch("app.aims.service.create_aim_service_in_k8s", return_value=svc),
    ):
        result = await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)

    assert result is not None


@pytest.mark.asyncio
async def test_deploy_aim_with_resource_name(kube_client: MagicMock) -> None:
    """Test deploying an AIM using resource_name."""
    aim = make_aim_cluster_model(name="my-aim")
    svc = make_aim_service_k8s()
    req = AIMDeployRequest(model="my-aim")
    mock_cluster_auth_client = AsyncMock()
    mock_cluster_auth_client.create_group.return_value = {"id": "group-123", "name": "test-group"}

    with (
        patch("app.aims.service.get_aim_by_name", return_value=aim),
        patch("app.aims.service.create_aim_service_in_k8s", return_value=svc),
    ):
        result = await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)

    assert result is not None


@pytest.mark.asyncio
async def test_deploy_aim_not_found_raises_error(kube_client: MagicMock) -> None:
    """Test deploy raises NotFoundException when model not found."""
    req = AIMDeployRequest(model="nonexistent-model")
    mock_cluster_auth_client = AsyncMock()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=None),
        pytest.raises(NotFoundException, match="'nonexistent-model' not found"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)


@pytest.mark.asyncio
async def test_deploy_finetuned_aim_propagates_aimmodel_labels(kube_client: MagicMock) -> None:
    """User-given name comes from AIMModel labels; canonical name (slash-preserved) comes from spec.modelSources."""
    model_labels = {
        MODEL_NAME_LABEL: "my-finetune",
        # System labels — present on AIMModel but must not reach the gateway call
        "airm.silogen.ai/workload-id": str(uuid4()),
        "app.kubernetes.io/managed-by": "aim-model-controller",
    }
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name="wb-finetune-job", namespace="ns", labels=model_labels),
        spec=AIMModelSpec(
            model_sources=[AIMModelSource(model_id="Qwen/Qwen2.5-0.5B-Instruct", source_uri="s3://bucket/path")]
        ),
        status=AIMModelStatusFields(),
    )
    req = AIMDeployRequest(model="wb-finetune-job")
    mock_cluster_auth_client = AsyncMock()
    mock_cluster_auth_client.create_group.return_value = {"id": "group-id"}

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=aim_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=None),
        patch("app.aims.service._create_cluster_auth_group_for_aim", return_value="group-id"),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)

        call_kwargs = mock_create.call_args.kwargs
        # User-given name comes from MODEL_NAME_LABEL on the AIMModel.
        assert call_kwargs["display_name"] == "my-finetune"
        # Canonical name comes from spec.model_sources (slash-preserved).
        assert call_kwargs["canonical_name"] == "Qwen/Qwen2.5-0.5B-Instruct"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile_name", "mi300x-throughput-fp8"),
        ("image_pull_secrets", ["registry-credentials"]),
        ("hf_token", "hf-secret-name"),
    ],
)
async def test_deploy_finetuned_aim_rejects_disallowed_overrides(
    kube_client: MagicMock, field: str, value: object
) -> None:
    """Fine-tuned deployments reject profile_name, image pull secrets, and hf_token."""
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name="wb-finetune-job", namespace="ns"),
        spec=AIMModelSpec(),
        status=AIMModelStatusFields(),
    )
    req = AIMDeployRequest(model="wb-finetune-job", **{field: value})
    mock_cluster_auth_client = AsyncMock()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=aim_model),
        pytest.raises(ValidationException, match=to_camel(field)),
    ):
        await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)


@pytest.mark.asyncio
async def test_deploy_finetuned_aim_accepts_profile_selector_and_overrides(kube_client: MagicMock) -> None:
    """Fine-tuned deployments propagate selector criteria and profileOverrides to the manifest builder."""
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name="wb-finetune-job", namespace="ns"),
        spec=AIMModelSpec(),
        status=AIMModelStatusFields(),
    )
    req = AIMDeployRequest(
        model="wb-finetune-job",
        metric=OptimizationMetric.LATENCY,
        precision="fp8",
        gpu_model="MI300X",
        gpu_count=2,
        engine_args={"max-model-len": 8192},
        engine_env=[{"name": "VLLM_LOGGING_LEVEL", "value": "DEBUG"}],
    )
    mock_cluster_auth_client = AsyncMock()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=aim_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=None),
        patch("app.aims.service._create_cluster_auth_group_for_aim", return_value="group-id"),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)

    assert mock_create.call_args.kwargs["resolved_profile_name"] is None
    deploy_request = mock_create.call_args.kwargs["deploy_request"]
    assert deploy_request.metric == OptimizationMetric.LATENCY
    assert deploy_request.precision == "fp8"
    assert deploy_request.gpu_model == "MI300X"
    assert deploy_request.gpu_count == 2
    assert deploy_request.engine_args == {"max-model-len": 8192}
    assert deploy_request.engine_env == [{"name": "VLLM_LOGGING_LEVEL", "value": "DEBUG"}]


def _make_custom_namespace_aim_model(
    *,
    status: AIMModelStatus = AIMModelStatus.READY,
    hf_token_required: bool = False,
    import_annotations: dict[str, str] | None = None,
) -> AIMModelResource:
    annotations = {"airm.silogen.ai/display-name": "Custom Display", **(import_annotations or {})}
    return AIMModelResource(
        metadata=K8sMetadata(
            name="custom-model",
            namespace="ns",
            labels={MODEL_SOURCE_TYPE_LABEL: ModelSourceType.CUSTOM, MODEL_NAME_LABEL: "custom-display"},
            annotations=annotations,
        ),
        spec=AIMModelSpec(
            profiles=AIMModelProfilesSpec(
                derived_from=AIMModelProfilesDerivedFrom(selector=ProfileSelector(role="base")),
                overrides=ProfileOverrides(model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
            )
        ),
        status=AIMModelStatusFields(
            status=status,
            image_metadata={"model": {"hfTokenRequired": hf_token_required}},
        ),
    )


def _make_ready_profile(
    *, name: str = "custom-profile", with_image_ref: bool = True, status: str = "Ready"
) -> AIMProfileResource:
    annotations = {"aim.eai.amd.com/deployment-image-ref": "docker.io/amd/tinyllama:1.0.0"} if with_image_ref else {}
    return AIMProfileResource(
        metadata=K8sMetadata(name=name, namespace="ns", annotations=annotations),
        status=AIMProfileStatus(status=status),
    )


@pytest.mark.asyncio
async def test_deploy_custom_model_requires_ready_aimmodel(kube_client: MagicMock) -> None:
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model(status=AIMModelStatus.PENDING)

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile()),
        pytest.raises(ValidationException, match="AIMModel status"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", None)


@pytest.mark.asyncio
async def test_deploy_custom_model_rejected_when_weight_import_failed(kube_client: MagicMock) -> None:
    """A failed HF→S3 weight import blocks deploy even though the AIMModel and its
    AIMProfile are Ready (profiles derive from the base image, not the weights)."""
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model(
        import_annotations={
            IMPORT_STATE_ANNOTATION: "Failed",
            IMPORT_ERROR_ANNOTATION: "MinIO returned HTTP 500 (disk full)",
        },
    )

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile()),
        pytest.raises(ValidationException, match="weight import failed.*disk full"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", None)


@pytest.mark.asyncio
async def test_deploy_custom_model_rejected_while_weight_import_in_progress(kube_client: MagicMock) -> None:
    """An in-flight weight import blocks deploy even when a Ready profile exists."""
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model(
        import_annotations={IMPORT_STATE_ANNOTATION: "Importing"},
    )

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile()),
        pytest.raises(ValidationException, match="weight import is still in progress"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", None)


@pytest.mark.asyncio
async def test_deploy_custom_model_succeeds_when_weight_import_ready(kube_client: MagicMock) -> None:
    """A completed weight import (import-state=Ready) does not block deploy."""
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model(
        import_annotations={IMPORT_STATE_ANNOTATION: "Ready"},
    )

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile()),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", None)

    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_deploy_custom_model_requires_profile(kube_client: MagicMock) -> None:
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=None),
        pytest.raises(ValidationException, match="no namespace AIMProfile"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", None)


@pytest.mark.asyncio
async def test_deploy_custom_model_requires_ready_profile(kube_client: MagicMock) -> None:
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile(status="Pending")),
        pytest.raises(ValidationException, match="AIMProfile 'custom-profile' status"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", None)


@pytest.mark.asyncio
async def test_deploy_custom_model_succeeds_without_deployment_image_annotation(kube_client: MagicMock) -> None:
    """v1alpha2 AIMProfiles embed image in spec overrides; deployment-image-ref annotation is not required."""
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile(with_image_ref=False)),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", None)

    mock_create.assert_awaited_once()
    assert mock_create.call_args.kwargs["resolved_profile_name"] == "custom-profile"
    assert mock_create.call_args.kwargs["is_fine_tuned"] is False


@pytest.mark.asyncio
async def test_deploy_custom_model_passes_deploy_display_name(kube_client: MagicMock) -> None:
    """A display name on the deploy request is forwarded as deploy_display_name,
    while the model identity (display_name) stays the onboarded model name."""
    req = AIMDeployRequest(model="custom-model", display_name="My TinyLlama")
    custom_model = _make_custom_namespace_aim_model()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile()),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", None)

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["deploy_display_name"] == "My TinyLlama"
    assert call_kwargs["display_name"] == "custom-display"


@pytest.mark.asyncio
async def test_deploy_custom_model_without_display_name_passes_none(kube_client: MagicMock) -> None:
    """When the deploy request omits a display name, deploy_display_name is None
    so the manifest falls back to the onboarded model identity."""
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile()),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", None)

    assert mock_create.call_args.kwargs["deploy_display_name"] is None


@pytest.mark.asyncio
async def test_deploy_custom_model_ignores_deploy_profile_fields_when_namespace_profile_ready(
    kube_client: MagicMock,
) -> None:
    """Custom deploy pins the onboarded profile; extra selector fields on the request are ignored."""
    req = AIMDeployRequest(
        model="custom-model",
        metric=OptimizationMetric.LATENCY,
        precision="fp8",
        gpu_model="MI300X",
        gpu_count=2,
    )
    custom_model = _make_custom_namespace_aim_model()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile()),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", None)

    assert mock_create.call_args.kwargs["resolved_profile_name"] == "custom-profile"


@pytest.mark.asyncio
async def test_deploy_finetuned_pins_namespace_profile_when_ready(kube_client: MagicMock) -> None:
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name="wb-finetune-job", namespace="ns"),
        spec=AIMModelSpec(),
        status=AIMModelStatusFields(),
    )
    req = AIMDeployRequest(model="wb-finetune-job", metric=OptimizationMetric.LATENCY, precision="fp8")

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=aim_model),
        patch("app.aims.service.find_aim_profile_for_model", return_value=_make_ready_profile(name="ft-profile")),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", None)

    assert mock_create.call_args.kwargs["resolved_profile_name"] == "ft-profile"


@pytest.mark.asyncio
async def test_deploy_finetuned_falls_back_when_profile_lookup_fails(kube_client: MagicMock) -> None:
    aim_model = AIMModelResource(
        metadata=K8sMetadata(name="wb-finetune-job", namespace="ns"),
        spec=AIMModelSpec(),
        status=AIMModelStatusFields(),
    )
    req = AIMDeployRequest(model="wb-finetune-job", precision="fp8")

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=aim_model),
        patch(
            "app.aims.service.find_aim_profile_for_model",
            side_effect=ApiException(status=503, reason="Service Unavailable"),
        ),
        patch("app.aims.service.create_namespace_aim_service_in_k8s", new_callable=AsyncMock) as mock_create,
    ):
        mock_create.return_value = AIMServiceResource(
            metadata=K8sMetadata(name="wb-aim-test", namespace="ns"),
            spec=AIMServiceSpec(),
        )
        await deploy_aim(kube_client, req, "ns", "user", None)

    assert mock_create.call_args.kwargs["resolved_profile_name"] is None


@pytest.mark.asyncio
async def test_deploy_custom_model_profile_lookup_error_raises_external_service_error(
    kube_client: MagicMock,
) -> None:
    req = AIMDeployRequest(model="custom-model")
    custom_model = _make_custom_namespace_aim_model()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=None),
        patch("app.aims.service.get_aim_model_from_k8s", return_value=custom_model),
        patch(
            "app.aims.service.find_aim_profile_for_model",
            side_effect=ApiException(status=503, reason="Service Unavailable"),
        ),
        pytest.raises(ExternalServiceError, match="Failed to look up AIMProfile for custom model"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", None)


@pytest.mark.asyncio
async def test_deploy_aim_with_camelcase_deploy_request(kube_client: MagicMock) -> None:
    """Test deploy_aim accepts deploy_request parsed from camelCase (as sent by UI)."""
    aim = make_aim_cluster_model()
    svc = make_aim_service_k8s()
    req = AIMDeployRequest(
        model="meta-llama-3-8b",
        imagePullSecrets=["s1"],
        hfToken="hf-secret",
        minReplicas=1,
        maxReplicas=5,
        autoScaling={"metrics": []},
    )
    mock_cluster_auth_client = AsyncMock()
    mock_cluster_auth_client.create_group.return_value = {"id": "group-123", "name": "test-group"}

    with (
        patch("app.aims.service.get_aim_by_name", return_value=aim),
        patch("app.aims.service.create_aim_service_in_k8s", return_value=svc) as mock_create,
    ):
        result = await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)

    assert result is not None
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["deploy_request"].image_pull_secrets == ["s1"]
    assert call_kwargs["deploy_request"].hf_token == "hf-secret"
    assert call_kwargs["deploy_request"].min_replicas == 1
    assert call_kwargs["deploy_request"].max_replicas == 5
    assert call_kwargs["deploy_request"].auto_scaling == {"metrics": []}


@pytest.mark.asyncio
async def test_deploy_aim_with_cluster_auth(kube_client: MagicMock) -> None:
    """Test deploying an AIM with cluster-auth group creation."""
    aim = make_aim_cluster_model(name="llama3-8b")
    svc = make_aim_service_k8s()
    req = AIMDeployRequest(model="llama3-8b")

    mock_cluster_auth_client = AsyncMock()
    mock_cluster_auth_client.create_group.return_value = {"id": "group-123", "name": "llama3-8b-wb-aim-a1b2c3d4"}

    with (
        patch("app.aims.service.get_aim_by_name", return_value=aim),
        patch("app.aims.service.create_aim_service_in_k8s", return_value=svc) as mock_create,
    ):
        result = await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)

    assert result is not None
    mock_cluster_auth_client.create_group.assert_called_once()
    # Verify group_id was passed to k8s creation
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["cluster_auth_group_id"] == "group-123"


@pytest.mark.asyncio
async def test_deploy_aim_cluster_auth_failure_raises(kube_client: MagicMock) -> None:
    """Test deploy fails when cluster-auth group creation fails."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="meta-llama-3-8b")

    mock_cluster_auth_client = AsyncMock()
    mock_cluster_auth_client.create_group.side_effect = Exception("Cluster-auth service unavailable")

    with (
        patch("app.aims.service.get_aim_by_name", return_value=aim),
        pytest.raises(Exception, match="Cluster-auth service unavailable"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)


@pytest.mark.asyncio
async def test_undeploy_aim(kube_client: MagicMock) -> None:
    """Test undeploying an AIM."""
    svc = make_aim_service_k8s()
    mock_cluster_auth_client = AsyncMock()
    with (
        patch("app.aims.service.get_aim_service_from_k8s", return_value=svc),
        patch("app.aims.service.delete_aim_service_from_k8s", return_value="svc-name"),
    ):
        await undeploy_aim(kube_client, uuid4(), "ns", mock_cluster_auth_client)


@pytest.mark.asyncio
async def test_undeploy_aim_with_cluster_auth_group(kube_client: MagicMock) -> None:
    """Test undeploy deletes cluster-auth group when present."""
    service_id = uuid4()
    svc = make_aim_service_k8s()
    svc.spec.routing = {"annotations": {"cluster-auth/allowed-group": "group-123"}}

    mock_cluster_auth_client = AsyncMock()

    with (
        patch("app.aims.service.get_aim_service_from_k8s", return_value=svc),
        patch("app.aims.service.delete_aim_service_from_k8s", return_value="svc-name"),
    ):
        await undeploy_aim(kube_client, service_id, "ns", mock_cluster_auth_client)

    mock_cluster_auth_client.delete_group.assert_called_once_with("group-123")


@pytest.mark.asyncio
async def test_undeploy_aim_cluster_auth_deletion_failure_raises(kube_client: MagicMock) -> None:
    """Test undeploy fails when cluster-auth group deletion fails."""
    service_id = uuid4()
    svc = make_aim_service_k8s()
    svc.spec.routing = {"annotations": {"cluster-auth/allowed-group": "group-123"}}

    mock_cluster_auth_client = AsyncMock()
    mock_cluster_auth_client.delete_group.side_effect = Exception("Cluster-auth service unavailable")

    with (
        patch("app.aims.service.get_aim_service_from_k8s", return_value=svc),
        pytest.raises(Exception, match="Cluster-auth service unavailable"),
    ):
        await undeploy_aim(kube_client, service_id, "ns", mock_cluster_auth_client)


@pytest.mark.asyncio
async def test_undeploy_aim_without_cluster_auth_group(kube_client: MagicMock) -> None:
    """Test undeploy when no cluster-auth group annotation exists."""
    service_id = uuid4()
    svc = make_aim_service_k8s()
    svc.spec.routing = {}

    mock_cluster_auth_client = AsyncMock()

    with (
        patch("app.aims.service.get_aim_service_from_k8s", return_value=svc),
        patch("app.aims.service.delete_aim_service_from_k8s", return_value="svc-name"),
    ):
        await undeploy_aim(kube_client, service_id, "ns", mock_cluster_auth_client)

    # Verify delete_group was not called
    mock_cluster_auth_client.delete_group.assert_not_called()


@pytest.mark.asyncio
async def test_undeploy_aim_not_found(kube_client: MagicMock) -> None:
    """Test undeploy raises when service not found."""
    mock_cluster_auth_client = AsyncMock()
    with patch("app.aims.service.get_aim_service_from_k8s", return_value=None):
        with pytest.raises(NotFoundException):
            await undeploy_aim(kube_client, uuid4(), "ns", mock_cluster_auth_client)


@pytest.mark.asyncio
async def test_list_aim_services(kube_client: MagicMock) -> None:
    """Test listing AIMServices."""
    svc = make_aim_service_k8s()
    with patch("app.aims.service.get_aim_services_from_k8s", return_value=[svc]):
        result = await list_aim_services(kube_client, "ns")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_aim_services_returns_resolved_profile_name_only(kube_client: MagicMock) -> None:
    """status.resolvedProfile carries only the reference name on the wire. Joining
    against the AIMProfile catalog for spec details is the FE's responsibility now
    (was previously inlined here, but coupled the services endpoint to the profile
    catalog and hid RBAC failures as silent empty rows)."""
    svc = make_aim_service_k8s(profile_name="llama3-8b-latency")
    svc.status = AIMServiceStatusFields(
        status=AIMServiceStatus.RUNNING,
        resolved_profile=ResolvedRef(name="llama3-8b-latency"),
    )

    with patch("app.aims.service.get_aim_services_from_k8s", return_value=[svc]):
        result = await list_aim_services(kube_client, "ns")

    assert len(result) == 1
    resolved = result[0].status.resolved_profile
    assert resolved is not None
    assert resolved.name == "llama3-8b-latency"
    # No profile catalog lookups happen here anymore.
    assert not hasattr(resolved, "spec") or getattr(resolved, "spec", None) is None


@pytest.mark.asyncio
async def test_get_aim_service(kube_client: MagicMock) -> None:
    """Test getting single AIMService."""
    svc = make_aim_service_k8s()
    with patch("app.aims.service.get_aim_service_from_k8s", return_value=svc):
        result = await get_aim_service(kube_client, "ns", uuid4())
    assert result is not None


@pytest.mark.asyncio
async def test_get_aim_service_not_found(kube_client: MagicMock) -> None:
    """Test raises when not found."""
    with patch("app.aims.service.get_aim_service_from_k8s", return_value=None):
        with pytest.raises(NotFoundException):
            await get_aim_service(kube_client, "ns", uuid4())


@pytest.mark.asyncio
async def test_list_aim_cluster_profiles_filters_by_aim_ids(kube_client: MagicMock) -> None:
    """Delegates to the gateway with the supplied aimId list."""
    profile = make_aim_cluster_profile(aim_id="org/my-aim")
    with patch(
        "app.aims.service.get_aim_cluster_profiles_from_k8s",
        return_value=[profile],
    ) as mock_gateway:
        result = await list_aim_cluster_profiles(kube_client, aim_ids=["org/my-aim"])

    assert len(result) == 1
    mock_gateway.assert_awaited_once_with(kube_client, aim_ids=["org/my-aim"])


@pytest.mark.asyncio
async def test_list_aim_cluster_profiles_no_filter(kube_client: MagicMock) -> None:
    """Omitting aim_ids lists every profile cluster-wide."""
    profiles = [make_aim_cluster_profile(aim_id="org/a"), make_aim_cluster_profile(aim_id="org/b")]
    with patch(
        "app.aims.service.get_aim_cluster_profiles_from_k8s",
        return_value=profiles,
    ) as mock_gateway:
        result = await list_aim_cluster_profiles(kube_client)

    assert len(result) == 2
    mock_gateway.assert_awaited_once_with(kube_client, aim_ids=None)


@pytest.mark.asyncio
async def test_list_aim_cluster_profiles_returns_empty(kube_client: MagicMock) -> None:
    """No matching profiles returns an empty list (not an exception)."""
    with patch("app.aims.service.get_aim_cluster_profiles_from_k8s", return_value=[]):
        result = await list_aim_cluster_profiles(kube_client, aim_ids=["org/unknown"])

    assert result == []


@pytest.mark.asyncio
async def test_get_aim_cluster_profile_returns_match(kube_client: MagicMock) -> None:
    """Direct GET by name returns the matching profile."""
    profile = make_aim_cluster_profile(name="profile-x", aim_id="org/my-aim")
    with patch("app.aims.service.get_aim_cluster_profile_from_k8s", return_value=profile) as mock_gateway:
        result = await get_aim_cluster_profile(kube_client, "profile-x")

    assert result is profile
    mock_gateway.assert_awaited_once_with(kube_client, "profile-x")


@pytest.mark.asyncio
async def test_get_aim_cluster_profile_not_found(kube_client: MagicMock) -> None:
    """Missing profile maps to NotFoundException so the router returns 404."""
    with patch("app.aims.service.get_aim_cluster_profile_from_k8s", return_value=None):
        with pytest.raises(NotFoundException):
            await get_aim_cluster_profile(kube_client, "missing-profile")


@pytest.mark.asyncio
async def test_get_aim_profile_returns_match(kube_client: MagicMock) -> None:
    """Direct GET by name in a namespace returns the matching profile."""
    profile = make_aim_cluster_profile(name="profile-x", aim_id="org/ft-aim")
    with patch("app.aims.service.get_aim_profile_from_k8s", return_value=profile) as mock_gateway:
        result = await get_aim_profile(kube_client, "test-ns", "profile-x")

    assert result is profile
    mock_gateway.assert_awaited_once_with(kube_client, "test-ns", "profile-x")


@pytest.mark.asyncio
async def test_get_aim_profile_not_found(kube_client: MagicMock) -> None:
    """Missing namespace-scoped profile maps to NotFoundException."""
    with patch("app.aims.service.get_aim_profile_from_k8s", return_value=None):
        with pytest.raises(NotFoundException):
            await get_aim_profile(kube_client, "test-ns", "missing")


@pytest.mark.asyncio
async def test_update_aim_scaling_policy(kube_client: MagicMock) -> None:
    """Test updating scaling policy."""
    svc = make_aim_service_k8s(min_replicas=2, max_replicas=10)
    with patch("app.aims.service.patch_aim_service_scaling_policy_in_k8s", return_value=svc):
        result = await update_aim_scaling_policy(kube_client, "ns", uuid4(), 2, 10, {"metrics": []})
    assert result.spec.min_replicas == 2


@pytest.mark.asyncio
async def test_update_aim_scaling_policy_not_found(kube_client: MagicMock) -> None:
    """Test raises when not found."""
    with patch("app.aims.service.patch_aim_service_scaling_policy_in_k8s", side_effect=ValueError("Not found")):
        with pytest.raises(NotFoundException):
            await update_aim_scaling_policy(kube_client, "ns", uuid4(), 2, 10, {"metrics": []})


@pytest.mark.asyncio
async def test_update_aim_scaling_policy_external_error(kube_client: MagicMock) -> None:
    """Test raises ExternalServiceError on runtime error."""
    with patch("app.aims.service.patch_aim_service_scaling_policy_in_k8s", side_effect=RuntimeError("K8s error")):
        with pytest.raises(ExternalServiceError):
            await update_aim_scaling_policy(kube_client, "ns", uuid4(), 2, 10, {"metrics": []})


@pytest.mark.asyncio
async def test_list_chattable_aim_services(kube_client: MagicMock) -> None:
    """Test listing chattable services."""
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(conditions=conditions)
    with patch("app.aims.service.get_aim_services_from_k8s", return_value=[svc]):
        result = await list_chattable_aim_services(kube_client, "ns")
    assert len(result) == 1


# Tests for cluster-auth helper functions


@pytest.mark.asyncio
async def test_create_cluster_auth_group_for_aim_success() -> None:
    """Test successful cluster-auth group creation."""
    mock_client = AsyncMock()
    mock_client.create_group.return_value = {"id": "group-456", "name": "test-group"}

    group_id = await _create_cluster_auth_group_for_aim(
        cluster_auth_client=mock_client,
        aim_model_name="llama3-8b",
        aim_service_name="wb-aim-a1b2c3d4",
    )

    assert group_id == "group-456"
    mock_client.create_group.assert_called_once()
    call_kwargs = mock_client.create_group.call_args.kwargs
    assert call_kwargs["name"] == "llama3-8b-wb-aim-a1b2c3d4"


@pytest.mark.asyncio
async def test_delete_cluster_auth_group_for_aim_success() -> None:
    """Test successful cluster-auth group deletion."""
    mock_client = AsyncMock()

    await _delete_cluster_auth_group_for_aim(
        cluster_auth_client=mock_client,
        group_id="group-789",
        aim_service_name="wb-aim-test",
    )

    mock_client.delete_group.assert_called_once_with("group-789")
