# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for aims gateway layer - K8s interaction functions."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes_asyncio.client import ApiException

from api_common.exceptions import ConflictException, ExternalServiceError
from app.aims.constants import AIM_COND_HTTP_ROUTE_READY, AIM_COND_INFERENCE_SERVICE_READY, NAMESPACE_AIM_MODEL_LABEL
from app.aims.crds import AIMModelResource, ResolvedRef
from app.aims.enums import AIMModelStatus, AIMServiceStatus
from app.aims.gateway import (
    _get_aims_by_name,
    _get_httproutes_for_aim_services,
    create_aim_model,
    create_aim_service,
    create_namespace_aim_service,
    delete_aim_model,
    delete_aim_service,
    get_aim_by_name,
    get_aim_cluster_profile_by_name,
    get_aim_model,
    get_aim_profile_by_name,
    get_aim_service_by_id,
    is_aim_service_chattable,
    list_aim_cluster_profiles_by_aim_ids,
    list_aim_models,
    list_aim_profiles_by_aim_ids,
    list_aim_service_replicas,
    list_aim_services,
    list_aim_services_for_model,
    list_aims,
    patch_aim_model,
    patch_aim_service_scaling_policy,
)
from app.aims.schemas import AIMDeployRequest
from tests.factory import make_aim_cluster_model, make_aim_cluster_profile, make_aim_service_k8s


def _make_pod(
    name: str = "pod-abc",
    phase: str = "Running",
    ready: bool = True,
    gpu_limits: dict[str, str] | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    """Build a minimal mock K8s pod for list_aim_service_replicas tests."""
    pod = MagicMock()
    pod.metadata.name = name
    pod.metadata.creation_timestamp = created_at or datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    pod.status.phase = phase
    cs = MagicMock()
    cs.ready = ready
    pod.status.container_statuses = [cs]
    container = MagicMock()
    container.resources.limits = gpu_limits or {}
    pod.spec.containers = [container]
    return pod


def _pods_result(*pods: MagicMock) -> MagicMock:
    """Wrap pod mocks in an object that mimics the k8s list response."""
    result = MagicMock()
    result.items = list(pods)
    return result


@pytest.fixture
def kube_client() -> MagicMock:
    """Mock K8s client."""
    mock = MagicMock()
    mock.custom_objects = MagicMock()
    mock.custom_objects.list_cluster_custom_object = AsyncMock(return_value={"items": []})
    mock.custom_objects.get_cluster_custom_object = AsyncMock()
    mock.custom_objects.get_namespaced_custom_object = AsyncMock()
    mock.custom_objects.list_namespaced_custom_object = AsyncMock(return_value={"items": []})
    mock.custom_objects.create_namespaced_custom_object = AsyncMock()
    mock.custom_objects.delete_namespaced_custom_object = AsyncMock()
    mock.custom_objects.patch_namespaced_custom_object = AsyncMock()
    mock.get_events_for_resource = AsyncMock(return_value=[])
    mock.core_v1 = MagicMock()
    mock.core_v1.list_namespaced_pod = AsyncMock(return_value=_pods_result())
    return mock


@pytest.mark.asyncio
async def test_list_aims(kube_client: MagicMock) -> None:
    """Test listing AIMs."""
    aim = make_aim_cluster_model()
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": [aim.model_dump(by_alias=True)]}

    result = await list_aims(kube_client)

    assert len(result) == 1
    assert result[0].metadata.name == "llama3-8b"


@pytest.mark.asyncio
async def test_list_aims_with_status_filter(kube_client: MagicMock) -> None:
    """Test listing AIMs with status filter."""
    ready = make_aim_cluster_model(name="ready", status=AIMModelStatus.READY)
    pending = make_aim_cluster_model(name="pending", status=AIMModelStatus.PENDING)
    kube_client.custom_objects.list_cluster_custom_object.return_value = {
        "items": [ready.model_dump(by_alias=True), pending.model_dump(by_alias=True)]
    }

    result = await list_aims(kube_client, statuses=[AIMModelStatus.READY])

    assert len(result) == 1
    assert result[0].metadata.name == "ready"


@pytest.mark.asyncio
async def test_list_aims_crd_not_found(kube_client: MagicMock) -> None:
    """Test returns empty when CRD not found."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        result = await list_aims(kube_client)
    assert result == []


@pytest.mark.asyncio
async def test_get_aim_by_name(kube_client: MagicMock) -> None:
    """Test getting AIM by name."""
    aim = make_aim_cluster_model(name="my-aim")
    kube_client.custom_objects.get_cluster_custom_object.return_value = aim.model_dump(by_alias=True)

    result = await get_aim_by_name(kube_client, "my-aim")

    assert result is not None
    assert result.metadata.name == "my-aim"


@pytest.mark.asyncio
async def test_get_aim_by_name_not_found(kube_client: MagicMock) -> None:
    """Test returns None when not found."""
    kube_client.custom_objects.get_cluster_custom_object.side_effect = ApiException(status=404, reason="Not Found")

    result = await get_aim_by_name(kube_client, "missing")
    assert result is None


@pytest.mark.asyncio
async def test_list_aim_services(kube_client: MagicMock) -> None:
    """Test listing AIMServices."""
    svc = make_aim_service_k8s()
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}

    # `list_aim_services` enriches results via HTTPRoute / KServe lookups which
    # call `get_resource_version`; patch it so the helper resolves a version
    # without a real kube client. AIM call sites now read AIM_API_VERSION
    # directly so no patch is needed for the AIM list call itself.
    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_services(kube_client, "test-ns")

    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_aim_service_by_id(kube_client: MagicMock) -> None:
    """Test getting AIMService by ID."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid)
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}

    result = await get_aim_service_by_id(kube_client, "test-ns", wid)

    assert result is not None


@pytest.mark.asyncio
async def test_get_aim_service_by_id_not_found(kube_client: MagicMock) -> None:
    """Test returns None when service not found."""
    result = await get_aim_service_by_id(kube_client, "test-ns", uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_create_aim_service(kube_client: MagicMock) -> None:
    """Test creating AIMService."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="img")
    svc = make_aim_service_k8s()
    kube_client.custom_objects.create_namespaced_custom_object.return_value = svc.model_dump(by_alias=True)

    result = await create_aim_service(kube_client, "test-ns", aim, req, "user", "wb-aim-test123", "test-group-id")

    assert result is not None
    kube_client.custom_objects.create_namespaced_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_create_aim_service_manifest_uses_camelcase_for_cluster(kube_client: MagicMock) -> None:
    """Manifest sent to K8s API uses camelCase for imagePullSecrets, profile.name, autoScaling."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="img",
        image_pull_secrets=["secret1"],
        profile_name="profile-a",
        min_replicas=2,
        max_replicas=8,
        auto_scaling={"metrics": []},
    )
    svc = make_aim_service_k8s()
    kube_client.custom_objects.create_namespaced_custom_object.return_value = svc.model_dump(by_alias=True)

    await create_aim_service(kube_client, "test-ns", aim, req, "user", "wb-aim-test456", "test-group-id")

    call_args = kube_client.custom_objects.create_namespaced_custom_object.call_args
    manifest = call_args.kwargs["body"]
    spec = manifest["spec"]
    assert "imagePullSecrets" in spec
    assert spec["imagePullSecrets"][0]["name"] == "secret1"
    assert spec["profile"]["name"] == "profile-a"
    assert "template" not in spec
    assert spec["minReplicas"] == 2
    assert spec["maxReplicas"] == 8
    assert "autoScaling" in spec


@pytest.mark.asyncio
async def test_create_namespace_aim_service(kube_client: MagicMock) -> None:
    """Test creating namespace-model AIMService."""
    req = AIMDeployRequest(model="wb-model")
    svc = make_aim_service_k8s()
    kube_client.custom_objects.create_namespaced_custom_object.return_value = svc.model_dump(by_alias=True)

    result = await create_namespace_aim_service(
        kube_client=kube_client,
        namespace="test-ns",
        model_name="wb-model",
        deploy_request=req,
        submitter="user",
        service_name="wb-aim-test123",
        cluster_auth_group_id="test-group-id",
        display_name="My Custom Model",
        canonical_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        is_fine_tuned=False,
    )

    assert result is not None
    call_args = kube_client.custom_objects.create_namespaced_custom_object.call_args
    labels = call_args.kwargs["body"]["metadata"]["labels"]
    assert labels[NAMESPACE_AIM_MODEL_LABEL] == "true"
    assert "aiwb.apps.eai.amd.com/fine-tuned" not in labels


@pytest.mark.asyncio
async def test_delete_aim_service(kube_client: MagicMock) -> None:
    """Test deleting AIMService."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid, name="my-svc")
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}

    result = await delete_aim_service(kube_client, "test-ns", wid)

    assert result == "my-svc"


@pytest.mark.asyncio
async def test_delete_aim_service_not_found(kube_client: MagicMock) -> None:
    """Test raises when service not found."""
    with pytest.raises(ValueError, match="No AIMService found"):
        await delete_aim_service(kube_client, "test-ns", uuid4())


@pytest.mark.asyncio
async def test_patch_aim_service_scaling_policy(kube_client: MagicMock) -> None:
    """Test patching scaling policy."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid, min_replicas=2, max_replicas=10)
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.patch_namespaced_custom_object.return_value = svc.model_dump(by_alias=True)

    result = await patch_aim_service_scaling_policy(kube_client, "ns", wid, 2, 10, {})

    assert result.spec.min_replicas == 2


def test_is_aim_service_chattable_true() -> None:
    """Test service is chattable when conditions are ready and has chat tag."""
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(
        status=AIMServiceStatus.RUNNING,
        model_ref="llama",
        conditions=conditions,
    )
    aim = make_aim_cluster_model(name="llama", tags=["chat"])
    aims_by_name = {"llama": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is True


def test_is_aim_service_chattable_false_missing_conditions() -> None:
    """Test service not chattable when conditions are not ready."""
    svc = make_aim_service_k8s(
        status=AIMServiceStatus.PENDING,
        model_ref="llama",
    )
    aim = make_aim_cluster_model(name="llama", tags=["chat"])
    aims_by_name = {"llama": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is False


def test_is_aim_service_chattable_false_no_chat_tag() -> None:
    """Test service not chattable without chat tag."""
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(
        status=AIMServiceStatus.RUNNING,
        model_ref="llama",
        conditions=conditions,
    )
    aim = make_aim_cluster_model(name="llama", tags=["text-generation"])  # No chat tag
    aims_by_name = {"llama": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is False


def test_is_aim_service_chattable_false_aim_not_found() -> None:
    """Test service not chattable when AIM not found."""
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(
        status=AIMServiceStatus.RUNNING,
        model_ref="missing",
        conditions=conditions,
    )
    aims_by_name: dict[str, AIMModelResource] = {}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is False


def test_is_aim_service_chattable_uses_spec_model_name_when_resolved_model_name_is_canonical_id() -> None:
    """Chattable check must look up the AIM by spec.model.name, not status.resolvedModel.name.

    Under the v1alpha2 profile reconciler, status.resolvedModel.name holds the
    canonical model id (e.g. "amd/Llama-3.1-8B-Instruct-FP8-KV"), which contains
    a slash and is not the AIMClusterModel resource name. aims_by_name is keyed
    by resource name, so using the canonical id misses the lookup.
    """
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(
        status=AIMServiceStatus.RUNNING,
        model_ref="llama3-8b",
        conditions=conditions,
    )
    # Simulate v1alpha2 profile reconciler: status carries the canonical id
    # (with a slash) while spec.model.name remains the K8s resource name.
    svc.status.resolved_model = ResolvedRef(name="amd/Llama-3.1-8B-Instruct-FP8-KV")

    aim = make_aim_cluster_model(name="llama3-8b", tags=["chat"])
    # Map is keyed by spec resource name; the canonical id is intentionally absent
    # to prove the lookup uses spec.model.name.
    aims_by_name = {"llama3-8b": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is True


def test_is_aim_service_chattable_degraded_but_healthy() -> None:
    """Test DEGRADED service is chattable if conditions are healthy."""
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(
        status=AIMServiceStatus.DEGRADED,
        model_ref="llama",
        conditions=conditions,
    )
    aim = make_aim_cluster_model(name="llama", tags=["chat"])
    aims_by_name = {"llama": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is True


def test_is_aim_service_chattable_namespace_model_label() -> None:
    """Namespace AIMModel services are chat-capable without catalog lookup."""
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(
        status=AIMServiceStatus.RUNNING,
        model_ref="custom-model",
        conditions=conditions,
    )
    svc.metadata.labels[NAMESPACE_AIM_MODEL_LABEL] = "true"
    aims_by_name: dict[str, AIMModelResource] = {}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is True


@pytest.mark.asyncio
async def test_list_aim_cluster_profiles_by_aim_ids(kube_client: MagicMock) -> None:
    """Test listing AIMClusterProfiles."""
    t = make_aim_cluster_profile()
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": [t.model_dump(by_alias=True)]}

    result = await list_aim_cluster_profiles_by_aim_ids(kube_client)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_aims_handles_exception(kube_client: MagicMock) -> None:
    """Test list_aims returns empty on exception."""
    kube_client.custom_objects.list_cluster_custom_object.side_effect = Exception("API error")

    result = await list_aims(kube_client)

    assert result == []


@pytest.mark.asyncio
async def test_get_aim_by_name_handles_non_404_exception(kube_client: MagicMock) -> None:
    """Test get_aim_by_name handles non-404 exceptions."""
    kube_client.custom_objects.get_cluster_custom_object.side_effect = Exception("Server error")

    result = await get_aim_by_name(kube_client, "test")

    assert result is None


@pytest.mark.asyncio
async def test_list_aim_services_handles_exception(kube_client: MagicMock) -> None:
    """Test list_aim_services returns empty on exception."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = Exception("API error")

    result = await list_aim_services(kube_client, "ns")

    assert result == []


@pytest.mark.asyncio
async def test_get_aim_service_by_id_handles_exception(kube_client: MagicMock) -> None:
    """Test get_aim_service_by_id returns None on exception."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = Exception("API error")

    result = await get_aim_service_by_id(kube_client, "ns", uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_patch_aim_service_handles_patch_error(kube_client: MagicMock) -> None:
    """Test patch raises RuntimeError on K8s patch failure."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid)
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.patch_namespaced_custom_object.side_effect = Exception("Patch failed")

    with pytest.raises(RuntimeError, match="Failed to update scaling policy"):
        await patch_aim_service_scaling_policy(kube_client, "ns", wid, 2, 10, {})


@pytest.mark.asyncio
async def test_list_aim_cluster_profiles_propagates_api_errors(kube_client: MagicMock) -> None:
    """RBAC and other ApiException failures must propagate as ExternalServiceError —
    swallowing them as an empty list hides the cause (e.g. SA missing list verb)."""
    kube_client.custom_objects.list_cluster_custom_object.side_effect = ApiException(
        status=403,
        reason="Forbidden",
    )

    with pytest.raises(ExternalServiceError, match="Forbidden"):
        await list_aim_cluster_profiles_by_aim_ids(kube_client)


@pytest.mark.asyncio
async def test_list_aim_profiles_propagates_api_errors(kube_client: MagicMock) -> None:
    """Namespace-scoped variant must also surface RBAC failures rather than masking them."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = ApiException(
        status=403,
        reason="Forbidden",
    )

    with pytest.raises(ExternalServiceError, match="Forbidden"):
        await list_aim_profiles_by_aim_ids(kube_client, namespace="ns")


@pytest.mark.asyncio
async def test_get_aim_cluster_profile_by_name_returns_match(kube_client: MagicMock) -> None:
    """Direct K8s GET by name returns the validated CR."""
    profile = make_aim_cluster_profile(name="profile-x", aim_id="org/llama")
    kube_client.custom_objects.get_cluster_custom_object.return_value = profile.model_dump(by_alias=True)

    result = await get_aim_cluster_profile_by_name(kube_client, "profile-x")

    assert result is not None
    assert result.metadata.name == "profile-x"
    call_kwargs = kube_client.custom_objects.get_cluster_custom_object.call_args.kwargs
    assert call_kwargs["name"] == "profile-x"


@pytest.mark.asyncio
async def test_get_aim_cluster_profile_by_name_returns_none_on_404(kube_client: MagicMock) -> None:
    """404 from K8s maps to None so the service can raise NotFoundException."""
    kube_client.custom_objects.get_cluster_custom_object.side_effect = ApiException(status=404, reason="Not Found")

    result = await get_aim_cluster_profile_by_name(kube_client, "missing")
    assert result is None


@pytest.mark.asyncio
async def test_get_aim_cluster_profile_by_name_propagates_api_errors(kube_client: MagicMock) -> None:
    """RBAC and other non-404 ApiException failures surface as ExternalServiceError."""
    kube_client.custom_objects.get_cluster_custom_object.side_effect = ApiException(status=403, reason="Forbidden")

    with pytest.raises(ExternalServiceError, match="Forbidden"):
        await get_aim_cluster_profile_by_name(kube_client, "anything")


@pytest.mark.asyncio
async def test_get_aim_profile_by_name_returns_match(kube_client: MagicMock) -> None:
    """Direct K8s GET by name in a namespace returns the validated CR."""
    profile = make_aim_cluster_profile(name="profile-y", aim_id="org/ft")
    kube_client.custom_objects.get_namespaced_custom_object.return_value = profile.model_dump(by_alias=True)

    result = await get_aim_profile_by_name(kube_client, "test-ns", "profile-y")

    assert result is not None
    assert result.metadata.name == "profile-y"
    call_kwargs = kube_client.custom_objects.get_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["namespace"] == "test-ns"
    assert call_kwargs["name"] == "profile-y"


@pytest.mark.asyncio
async def test_get_aim_profile_by_name_returns_none_on_404(kube_client: MagicMock) -> None:
    """404 maps to None for the namespace-scoped variant too."""
    kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404, reason="Not Found")

    result = await get_aim_profile_by_name(kube_client, "test-ns", "missing")
    assert result is None


@pytest.mark.asyncio
async def test_get_aim_profile_by_name_propagates_api_errors(kube_client: MagicMock) -> None:
    """Non-404 ApiException surfaces as ExternalServiceError for the namespace variant."""
    kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=403, reason="Forbidden")

    with pytest.raises(ExternalServiceError, match="Forbidden"):
        await get_aim_profile_by_name(kube_client, "test-ns", "anything")


@pytest.mark.asyncio
async def test_get_aim_by_name_crd_not_available(kube_client: MagicMock) -> None:
    """Test get_aim_by_name returns None when CRD not available."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        result = await get_aim_by_name(kube_client, "test")
    assert result is None


@pytest.mark.asyncio
async def test_list_aim_services_with_chattable_filter(kube_client: MagicMock) -> None:
    """Test listing services with chattable filter."""
    conditions = [
        {"type": AIM_COND_INFERENCE_SERVICE_READY, "status": "True"},
        {"type": AIM_COND_HTTP_ROUTE_READY, "status": "True"},
    ]
    svc = make_aim_service_k8s(status=AIMServiceStatus.RUNNING, model_ref="llama", conditions=conditions)
    aim = make_aim_cluster_model(name="llama", tags=["chat"])
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": [aim.model_dump(by_alias=True)]}

    # See test_list_aim_services for why the HTTPRoute/KServe path needs a
    # patched version resolver while the AIM-flow does not.
    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_services(kube_client, "test-ns", chattable_only=True)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_aim_services_chattable_filters_out_non_chattable(kube_client: MagicMock) -> None:
    """Test chattable filter excludes non-chattable services."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.PENDING)  # Not RUNNING
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": []}

    result = await list_aim_services(kube_client, "test-ns", chattable_only=True)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_aims_by_name(kube_client: MagicMock) -> None:
    """Test _get_aims_by_name returns AIMs indexed by name."""
    aim1 = make_aim_cluster_model(name="llama")
    aim2 = make_aim_cluster_model(name="mistral")
    kube_client.custom_objects.list_cluster_custom_object.return_value = {
        "items": [aim1.model_dump(by_alias=True), aim2.model_dump(by_alias=True)]
    }

    result = await _get_aims_by_name(kube_client)

    assert len(result) == 2
    assert "llama" in result
    assert "mistral" in result
    assert result["llama"].metadata.name == "llama"
    assert result["mistral"].metadata.name == "mistral"


@pytest.mark.asyncio
async def test_list_aim_cluster_profiles_filters_by_aim_id(kube_client: MagicMock) -> None:
    """Each requested aimId is pushed to the API server as a field selector.

    aim-engine added ``spec.aimId`` to the AIMClusterProfile CRD's
    ``selectableFields``, so the gateway delegates filtering to the API
    server. Multi-id requests fan out to N calls (K8s field selectors are
    equality-only) and the gateway never re-applies the filter in Python.
    """
    llama = make_aim_cluster_profile(name="llama-profile", aim_id="org/llama")
    cohere = make_aim_cluster_profile(name="cohere-profile", aim_id="org/cohere")

    list_mock = kube_client.custom_objects.list_cluster_custom_object

    list_mock.side_effect = lambda **kwargs: {
        "spec.aimId=org/llama": {"items": [llama.model_dump(by_alias=True)]},
        "spec.aimId=org/cohere": {"items": [cohere.model_dump(by_alias=True)]},
    }[kwargs["field_selector"]]

    result = await list_aim_cluster_profiles_by_aim_ids(kube_client, aim_ids=["org/llama"])
    assert {p.metadata.name for p in result} == {"llama-profile"}
    assert list_mock.call_args.kwargs["field_selector"] == "spec.aimId=org/llama"

    list_mock.reset_mock()
    result = await list_aim_cluster_profiles_by_aim_ids(kube_client, aim_ids=["org/llama", "org/cohere"])
    assert {p.metadata.name for p in result} == {"llama-profile", "cohere-profile"}
    field_selectors = [c.kwargs["field_selector"] for c in list_mock.call_args_list]
    assert field_selectors == ["spec.aimId=org/llama", "spec.aimId=org/cohere"]


@pytest.mark.asyncio
async def test_list_aim_cluster_profiles_no_filter_omits_field_selector(kube_client: MagicMock) -> None:
    """No aim_ids → single unfiltered list call, no field selector sent.

    Guards against accidentally adding a client-side filter once the
    server-side narrowing is in place: the kube call's items are returned
    verbatim.
    """
    llama = make_aim_cluster_profile(name="llama-profile", aim_id="org/llama")
    mistral = make_aim_cluster_profile(name="mistral-profile", aim_id="org/mistral")
    list_mock = kube_client.custom_objects.list_cluster_custom_object
    list_mock.return_value = {"items": [llama.model_dump(by_alias=True), mistral.model_dump(by_alias=True)]}

    result = await list_aim_cluster_profiles_by_aim_ids(kube_client, aim_ids=None)

    assert {p.metadata.name for p in result} == {"llama-profile", "mistral-profile"}
    assert list_mock.call_count == 1
    assert "field_selector" not in list_mock.call_args.kwargs


@pytest.mark.asyncio
async def test_list_aim_profiles_filters_by_aim_id(kube_client: MagicMock) -> None:
    """Namespaced variant pushes the aimId filter to the API server too."""
    llama = make_aim_cluster_profile(name="llama-profile", aim_id="org/llama")
    cohere = make_aim_cluster_profile(name="cohere-profile", aim_id="org/cohere")

    list_mock = kube_client.custom_objects.list_namespaced_custom_object
    list_mock.side_effect = lambda **kwargs: {
        "spec.aimId=org/llama": {"items": [llama.model_dump(by_alias=True)]},
        "spec.aimId=org/cohere": {"items": [cohere.model_dump(by_alias=True)]},
    }[kwargs["field_selector"]]

    result = await list_aim_profiles_by_aim_ids(kube_client, namespace="ns", aim_ids=["org/llama"])
    assert {p.metadata.name for p in result} == {"llama-profile"}
    assert list_mock.call_args.kwargs["field_selector"] == "spec.aimId=org/llama"
    assert list_mock.call_args.kwargs["namespace"] == "ns"

    list_mock.reset_mock()
    result = await list_aim_profiles_by_aim_ids(kube_client, namespace="ns", aim_ids=["org/llama", "org/cohere"])
    assert {p.metadata.name for p in result} == {"llama-profile", "cohere-profile"}
    field_selectors = [c.kwargs["field_selector"] for c in list_mock.call_args_list]
    assert field_selectors == ["spec.aimId=org/llama", "spec.aimId=org/cohere"]


@pytest.mark.asyncio
async def test_list_aim_profiles_no_filter_omits_field_selector(kube_client: MagicMock) -> None:
    """No aim_ids → single namespaced list, no field selector sent."""
    llama = make_aim_cluster_profile(name="llama-profile", aim_id="org/llama")
    list_mock = kube_client.custom_objects.list_namespaced_custom_object
    list_mock.return_value = {"items": [llama.model_dump(by_alias=True)]}

    result = await list_aim_profiles_by_aim_ids(kube_client, namespace="ns")

    assert {p.metadata.name for p in result} == {"llama-profile"}
    assert list_mock.call_count == 1
    assert "field_selector" not in list_mock.call_args.kwargs


@pytest.mark.asyncio
async def test_list_aim_services_with_status_filter(kube_client: MagicMock) -> None:
    """Test status_filter includes only specified statuses."""
    svc_running = make_aim_service_k8s(status=AIMServiceStatus.RUNNING)
    svc_deleted = make_aim_service_k8s(status=AIMServiceStatus.DELETED)
    svc_pending = make_aim_service_k8s(status=AIMServiceStatus.PENDING)

    kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [
            svc_running.model_dump(by_alias=True),
            svc_deleted.model_dump(by_alias=True),
            svc_pending.model_dump(by_alias=True),
        ]
    }

    # Filter to only include RUNNING and PENDING (exclude DELETED). The
    # HTTPRoute/KServe enrichment helpers still resolve the served version,
    # so patch get_resource_version (see test_list_aim_services).
    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_services(
            kube_client, "test-ns", status_filter=[AIMServiceStatus.RUNNING, AIMServiceStatus.PENDING]
        )

    assert len(result) == 2
    statuses = {svc.status.status for svc in result}
    assert AIMServiceStatus.RUNNING in statuses
    assert AIMServiceStatus.PENDING in statuses
    assert AIMServiceStatus.DELETED not in statuses


@pytest.mark.asyncio
async def test_get_httproutes_for_aim_services_indexes_by_name(kube_client: MagicMock) -> None:
    """Test HTTPRoutes are indexed by AIMService owner name."""
    httproute_item = {
        "metadata": {
            "name": "my-route",
            "namespace": "test-ns",
            "ownerReferences": [{"kind": "AIMService", "name": "my-svc", "controller": True, "uid": "123"}],
        },
        "spec": {
            "rules": [
                {
                    "backendRefs": [{"kind": "Service", "name": "my-svc-predictor", "port": 80}],
                    "matches": [{"path": {"type": "PathPrefix", "value": "/v1/chat"}}],
                }
            ]
        },
    }
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [httproute_item]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1"):
        result = await _get_httproutes_for_aim_services(kube_client, "test-ns")

    assert "my-svc" in result
    assert result["my-svc"].metadata.name == "my-route"
    assert len(result["my-svc"].spec.rules) == 1


@pytest.mark.asyncio
async def test_get_httproutes_for_aim_services_empty(kube_client: MagicMock) -> None:
    """Test returns empty dict when no HTTPRoutes found."""
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    with patch("app.aims.gateway.get_resource_version", return_value="v1"):
        result = await _get_httproutes_for_aim_services(kube_client, "test-ns")

    assert result == {}


@pytest.mark.asyncio
async def test_get_httproutes_for_aim_services_skips_non_aimservice(kube_client: MagicMock) -> None:
    """Test skips HTTPRoutes not owned by AIMService."""
    httproute_item = {
        "metadata": {
            "name": "my-route",
            "namespace": "test-ns",
            "ownerReferences": [{"kind": "Other", "name": "other-svc", "controller": True, "uid": "123"}],
        },
        "spec": {"rules": []},
    }
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [httproute_item]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1"):
        result = await _get_httproutes_for_aim_services(kube_client, "test-ns")

    assert result == {}


@pytest.mark.asyncio
async def test_get_httproutes_for_aim_services_requires_controller(kube_client: MagicMock) -> None:
    """Test only indexes owner references with controller=True."""
    httproute_item = {
        "metadata": {
            "name": "my-route",
            "namespace": "test-ns",
            "ownerReferences": [{"kind": "AIMService", "name": "my-svc", "controller": False, "uid": "123"}],
        },
        "spec": {"rules": []},
    }
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [httproute_item]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1"):
        result = await _get_httproutes_for_aim_services(kube_client, "test-ns")

    assert result == {}


@pytest.mark.asyncio
async def test_get_httproutes_for_aim_services_crd_missing(kube_client: MagicMock) -> None:
    """Test returns empty dict when HTTPRoute CRD not found."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        result = await _get_httproutes_for_aim_services(kube_client, "test-ns")

    assert result == {}
    # Verify we didn't try to list when CRD doesn't exist
    kube_client.custom_objects.list_namespaced_custom_object.assert_not_called()


@pytest.mark.asyncio
async def test_get_httproutes_for_aim_services_handles_exception(kube_client: MagicMock) -> None:
    """Test handles exception gracefully."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = Exception("API error")

    with patch("app.aims.gateway.get_resource_version", return_value="v1"):
        result = await _get_httproutes_for_aim_services(kube_client, "test-ns")

    assert result == {}
    # Verify the API was called despite the error
    kube_client.custom_objects.list_namespaced_custom_object.assert_called_once()


# =============================================================================
# list_aim_service_replicas
# =============================================================================


def _setup_pod_serialization(kube_client: MagicMock, pod_dicts: list[dict]) -> None:
    """Wire sanitize_for_serialization to return successive dicts for each pod call."""
    kube_client._api_client.sanitize_for_serialization.side_effect = pod_dicts


@pytest.mark.asyncio
async def test_list_aim_service_replicas_returns_parsed_replica(kube_client: MagicMock) -> None:
    """Returns raw pod dicts serialized from Kubernetes objects."""
    pod = _make_pod(name="pod-abc")
    pod_dict = {"metadata": {"name": "pod-abc"}, "status": {"phase": "Running"}}
    kube_client.core_v1.list_namespaced_pod.return_value = _pods_result(pod)
    _setup_pod_serialization(kube_client, [pod_dict])

    result = await list_aim_service_replicas(kube_client, "test-ns", uuid4())

    assert len(result) == 1
    assert result[0]["metadata"]["name"] == "pod-abc"
    assert result[0]["status"]["phase"] == "Running"


@pytest.mark.asyncio
async def test_list_aim_service_replicas_sorted_by_name(kube_client: MagicMock) -> None:
    """Results are sorted alphabetically by metadata.name."""
    pods = [_make_pod(name=n) for n in ("pod-zzz", "pod-aaa", "pod-mmm")]
    pod_dicts = [{"metadata": {"name": n}} for n in ("pod-zzz", "pod-aaa", "pod-mmm")]
    kube_client.core_v1.list_namespaced_pod.return_value = _pods_result(*pods)
    _setup_pod_serialization(kube_client, pod_dicts)

    result = await list_aim_service_replicas(kube_client, "test-ns", uuid4())

    assert [r["metadata"]["name"] for r in result] == ["pod-aaa", "pod-mmm", "pod-zzz"]


@pytest.mark.asyncio
async def test_list_aim_service_replicas_skips_pods_without_name(kube_client: MagicMock) -> None:
    """Pods missing a metadata name are silently skipped."""
    named = _make_pod(name="pod-ok")
    unnamed = _make_pod()
    unnamed.metadata.name = None
    kube_client.core_v1.list_namespaced_pod.return_value = _pods_result(named, unnamed)
    _setup_pod_serialization(kube_client, [{"metadata": {"name": "pod-ok"}}])

    result = await list_aim_service_replicas(kube_client, "test-ns", uuid4())

    assert len(result) == 1
    assert result[0]["metadata"]["name"] == "pod-ok"


@pytest.mark.asyncio
async def test_list_aim_service_replicas_handles_exception(kube_client: MagicMock) -> None:
    """Returns an empty list when the k8s API call fails."""
    kube_client.core_v1.list_namespaced_pod.side_effect = Exception("API error")

    result = await list_aim_service_replicas(kube_client, "test-ns", uuid4())

    assert result == []


# --- get_aim_model ---


@pytest.mark.asyncio
async def test_get_aim_model(kube_client: MagicMock) -> None:
    """Test getting a namespace-scoped AIMModel by name."""
    raw = {"metadata": {"name": "ft-model", "namespace": "test-ns"}, "spec": {"modelSources": []}}
    kube_client.custom_objects.get_namespaced_custom_object.return_value = raw

    result = await get_aim_model(kube_client, "test-ns", "ft-model")

    assert result is not None
    assert isinstance(result, AIMModelResource)
    assert result.metadata.name == "ft-model"


@pytest.mark.asyncio
async def test_get_aim_model_404(kube_client: MagicMock) -> None:
    """Test returns None when AIMModel resource does not exist (404)."""
    kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404, reason="Not Found")

    result = await get_aim_model(kube_client, "test-ns", "missing")

    assert result is None


@pytest.mark.asyncio
async def test_get_aim_model_non_404_exception(kube_client: MagicMock) -> None:
    """Test non-404 exceptions are re-raised so callers aren't silently misled."""
    kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(
        status=500, reason="Server error"
    )

    with pytest.raises(ApiException):
        await get_aim_model(kube_client, "test-ns", "ft-model")


# --- list_aim_services_for_model ---


@pytest.mark.asyncio
async def test_list_aim_services_for_model(kube_client: MagicMock) -> None:
    """Test listing AIMServices that reference a specific model."""
    matching = make_aim_service_k8s(model_ref="ft-model")
    other = make_aim_service_k8s(model_ref="other-model")
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [matching.model_dump(by_alias=True), other.model_dump(by_alias=True)]
    }

    result = await list_aim_services_for_model(kube_client, "test-ns", "ft-model")

    assert len(result) == 1
    assert result[0].spec.model["name"] == "ft-model"


@pytest.mark.asyncio
async def test_list_aim_services_for_model_no_matches(kube_client: MagicMock) -> None:
    """Test returns empty when no services reference the model."""
    svc = make_aim_service_k8s(model_ref="other-model")
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}

    result = await list_aim_services_for_model(kube_client, "test-ns", "ft-model")

    assert result == []


@pytest.mark.asyncio
async def test_list_aim_services_for_model_propagates_non_404_exception(kube_client: MagicMock) -> None:
    """Non-404 exceptions propagate so the active-deployment guard is never silently bypassed."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = Exception("API error")

    with pytest.raises(Exception, match="API error"):
        await list_aim_services_for_model(kube_client, "test-ns", "ft-model")


@pytest.mark.asyncio
async def test_list_aim_services_for_model_returns_empty_on_404(kube_client: MagicMock) -> None:
    """404 from the API returns empty list — model has no services."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = ApiException(status=404, reason="Not Found")

    result = await list_aim_services_for_model(kube_client, "test-ns", "ft-model")

    assert result == []


# --- delete_aim_model ---


@pytest.mark.asyncio
async def test_delete_aim_model(kube_client: MagicMock) -> None:
    """Test successful deletion of AIMModel."""
    await delete_aim_model(kube_client, "test-ns", "ft-model")

    kube_client.custom_objects.delete_namespaced_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_delete_aim_model_404(kube_client: MagicMock) -> None:
    """Test no-ops when AIMModel resource does not exist (404)."""
    kube_client.custom_objects.delete_namespaced_custom_object.side_effect = ApiException(
        status=404, reason="Not Found"
    )

    await delete_aim_model(kube_client, "test-ns", "missing")

    # Should not raise


@pytest.mark.asyncio
async def test_delete_aim_model_non_404_exception(kube_client: MagicMock) -> None:
    """Test re-raises non-404 exceptions."""
    kube_client.custom_objects.delete_namespaced_custom_object.side_effect = Exception("Server error")

    with pytest.raises(Exception, match="Server error"):
        await delete_aim_model(kube_client, "test-ns", "ft-model")


# --- create_aim_model ---


def _aim_model_manifest(name: str = "my-aim-model") -> dict:
    return {
        "apiVersion": "aim.eai.amd.com/v1alpha1",
        "kind": "AIMModel",
        "metadata": {"name": name, "namespace": "test-ns"},
        "spec": {"modelSources": [{"modelId": "owner/model", "sourceUri": "hf://owner/model"}]},
    }


@pytest.mark.asyncio
async def test_create_aim_model_success(kube_client: MagicMock) -> None:
    """create_aim_model returns the parsed AIMModelResource on a 200/201 response."""
    manifest = _aim_model_manifest()
    kube_client.custom_objects.create_namespaced_custom_object.return_value = manifest

    result = await create_aim_model(kube_client, "test-ns", manifest)

    assert isinstance(result, AIMModelResource)
    assert result.metadata.name == "my-aim-model"
    kube_client.custom_objects.create_namespaced_custom_object.assert_called_once()
    call_kwargs = kube_client.custom_objects.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "aimmodels"
    assert call_kwargs["namespace"] == "test-ns"
    assert call_kwargs["body"] is manifest


@pytest.mark.asyncio
async def test_create_aim_model_409_maps_to_conflict_exception(kube_client: MagicMock) -> None:
    """API server 409 is mapped to ConflictException so callers don't need to know about ApiException."""
    kube_client.custom_objects.create_namespaced_custom_object.side_effect = ApiException(status=409, reason="Conflict")

    with pytest.raises(ConflictException, match="already exists"):
        await create_aim_model(kube_client, "test-ns", _aim_model_manifest())


@pytest.mark.asyncio
async def test_create_aim_model_non_409_propagates(kube_client: MagicMock) -> None:
    """Non-409 ApiException propagates unchanged so generic K8s errors surface as 5xx."""
    kube_client.custom_objects.create_namespaced_custom_object.side_effect = ApiException(
        status=500, reason="Internal Server Error"
    )

    with pytest.raises(ApiException):
        await create_aim_model(kube_client, "test-ns", _aim_model_manifest())


# --- patch_aim_model ---


@pytest.mark.asyncio
async def test_patch_aim_model_success(kube_client: MagicMock) -> None:
    """patch_aim_model returns the parsed AIMModelResource and uses merge-patch."""
    patched_manifest = _aim_model_manifest(name="my-aim-model")
    kube_client.custom_objects.patch_namespaced_custom_object.return_value = patched_manifest

    result = await patch_aim_model(
        kube_client, "test-ns", "my-aim-model", {"metadata": {"annotations": {"foo": "bar"}}}
    )

    assert isinstance(result, AIMModelResource)
    assert result.metadata.name == "my-aim-model"
    call_kwargs = kube_client.custom_objects.patch_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "aimmodels"
    assert call_kwargs["name"] == "my-aim-model"
    assert call_kwargs["_content_type"] == "application/merge-patch+json"


@pytest.mark.parametrize("status,reason", [(500, "Internal Server Error"), (422, "Unprocessable Entity")])
@pytest.mark.asyncio
async def test_patch_aim_model_wraps_api_exception_as_external_service_error(
    kube_client: MagicMock, status: int, reason: str
) -> None:
    """K8s ApiException wraps as ExternalServiceError so the onboard endpoint's
    documented 502 response is honoured. Status passthrough (e.g. surfacing
    admission 422 or upstream 5xx directly) requires registering an async
    ApiException handler — the FastAPI app only registers the sync
    ``kubernetes.client.exceptions.ApiException`` today, so a bare re-raise
    of ``kubernetes_asyncio.client.ApiException`` would fall through to the
    generic handler as an opaque 500. Tracked as a separate follow-up."""
    api_error = ApiException(status=status, reason=reason)
    kube_client.custom_objects.patch_namespaced_custom_object.side_effect = api_error

    with pytest.raises(ExternalServiceError, match="Failed to patch AIMModel 'my-aim-model'") as exc_info:
        await patch_aim_model(kube_client, "test-ns", "my-aim-model", {"metadata": {}})
    assert exc_info.value.__cause__ is api_error


@pytest.mark.asyncio
async def test_list_aim_models_with_label_selector(kube_client: MagicMock) -> None:
    """Test list_aim_models passes label_selector to Kubernetes API."""
    model_manifest = _aim_model_manifest(name="ft-model-1")
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [model_manifest]}

    result = await list_aim_models(kube_client, "test-ns", label_selector="workload-type=FINE_TUNING")

    assert len(result) == 1
    assert result[0].metadata.name == "ft-model-1"
    kube_client.custom_objects.list_namespaced_custom_object.assert_called_once()
    call_kwargs = kube_client.custom_objects.list_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["label_selector"] == "workload-type=FINE_TUNING"


@pytest.mark.asyncio
async def test_list_aim_services_runs_helpers_concurrently(kube_client: MagicMock) -> None:
    """The three enrichment helpers must run concurrently when chattable_only=True.

    Each helper waits on a shared barrier released only after all three have
    started. Sequential execution would deadlock on asyncio.wait_for and
    fail the test.
    """
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    barrier = asyncio.Event()
    call_count = 0
    expected_calls = 3

    def make_gated(return_value):
        async def gated(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == expected_calls:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), timeout=1.0)
            return return_value

        return gated

    httproutes_gate = make_gated({})
    isvc_gate = make_gated({})
    aims_gate = make_gated({})

    with (
        patch("app.aims.gateway._get_httproutes_for_aim_services", side_effect=httproutes_gate),
        patch("app.aims.gateway._get_isvc_names", side_effect=isvc_gate),
        patch("app.aims.gateway._get_aims_by_name", side_effect=aims_gate),
    ):
        await list_aim_services(kube_client, "test-ns", chattable_only=True)

    assert call_count == expected_calls


@pytest.mark.asyncio
async def test_list_aim_services_skips_aims_lookup_when_not_chattable(kube_client: MagicMock) -> None:
    """When chattable_only is False, _get_aims_by_name must not be called.

    The K8s call for cluster-scoped AIMs is expensive; the helper short-circuits
    to an empty dict instead of hitting the API server.
    """
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    with (
        patch("app.aims.gateway._get_httproutes_for_aim_services", new=AsyncMock(return_value={})),
        patch("app.aims.gateway._get_isvc_names", new=AsyncMock(return_value={})),
        patch("app.aims.gateway._get_aims_by_name", new=AsyncMock(return_value={})) as mock_aims,
    ):
        await list_aim_services(kube_client, "test-ns", chattable_only=False)

    mock_aims.assert_not_called()
