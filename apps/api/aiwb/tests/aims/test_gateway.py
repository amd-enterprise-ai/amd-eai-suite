# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for aims gateway layer - K8s interaction functions."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes.client.exceptions import ApiException

from app.aims.crds import AIMClusterModelResource
from app.aims.enums import AIMClusterModelStatus, AIMServiceStatus
from app.aims.gateway import (
    _get_aims_by_name,
    _get_httproutes_for_aim_services,
    create_aim_service,
    delete_aim_service,
    get_aim_by_name,
    get_aim_service_by_id,
    is_aim_service_chattable,
    list_aim_cluster_service_templates,
    list_aim_services,
    list_aims,
    patch_aim_service_scaling_policy,
)
from app.aims.schemas import AIMDeployRequest
from tests.factory import make_aim_cluster_model, make_aim_cluster_service_template, make_aim_service_k8s


@pytest.fixture
def kube_client() -> MagicMock:
    """Mock K8s client."""
    mock = MagicMock()
    mock.custom_objects = MagicMock()
    mock.custom_objects.list_cluster_custom_object = AsyncMock(return_value={"items": []})
    mock.custom_objects.get_cluster_custom_object = AsyncMock()
    mock.custom_objects.list_namespaced_custom_object = AsyncMock(return_value={"items": []})
    mock.custom_objects.create_namespaced_custom_object = AsyncMock()
    mock.custom_objects.delete_namespaced_custom_object = AsyncMock()
    mock.custom_objects.patch_namespaced_custom_object = AsyncMock()
    mock.get_events_for_resource = AsyncMock(return_value=[])
    return mock


@pytest.mark.asyncio
async def test_list_aims(kube_client: MagicMock) -> None:
    """Test listing AIMs."""
    aim = make_aim_cluster_model()
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": [aim.model_dump(by_alias=True)]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aims(kube_client)

    assert len(result) == 1
    assert result[0].metadata.name == "llama3-8b"


@pytest.mark.asyncio
async def test_list_aims_with_status_filter(kube_client: MagicMock) -> None:
    """Test listing AIMs with status filter."""
    ready = make_aim_cluster_model(name="ready", status=AIMClusterModelStatus.READY)
    pending = make_aim_cluster_model(name="pending", status=AIMClusterModelStatus.PENDING)
    kube_client.custom_objects.list_cluster_custom_object.return_value = {
        "items": [ready.model_dump(by_alias=True), pending.model_dump(by_alias=True)]
    }

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aims(kube_client, statuses=[AIMClusterModelStatus.READY])

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

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await get_aim_by_name(kube_client, "my-aim")

    assert result is not None
    assert result.metadata.name == "my-aim"


@pytest.mark.asyncio
async def test_get_aim_by_name_not_found(kube_client: MagicMock) -> None:
    """Test returns None when not found."""
    kube_client.custom_objects.get_cluster_custom_object.side_effect = ApiException(status=404, reason="Not Found")

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await get_aim_by_name(kube_client, "missing")
    assert result is None


@pytest.mark.asyncio
async def test_list_aim_services(kube_client: MagicMock) -> None:
    """Test listing AIMServices."""
    svc = make_aim_service_k8s()
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_services(kube_client, "test-ns")

    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_aim_service_by_id(kube_client: MagicMock) -> None:
    """Test getting AIMService by ID."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid)
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await get_aim_service_by_id(kube_client, "test-ns", wid)

    assert result is not None


@pytest.mark.asyncio
async def test_get_aim_service_by_id_not_found(kube_client: MagicMock) -> None:
    """Test returns None when service not found."""
    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await get_aim_service_by_id(kube_client, "test-ns", uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_create_aim_service(kube_client: MagicMock) -> None:
    """Test creating AIMService."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(model="img")
    svc = make_aim_service_k8s()
    kube_client.custom_objects.create_namespaced_custom_object.return_value = svc.model_dump(by_alias=True)

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await create_aim_service(kube_client, "test-ns", aim, req, "user", "wb-aim-test123", "test-group-id")

    assert result is not None
    kube_client.custom_objects.create_namespaced_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_create_aim_service_manifest_uses_camelcase_for_cluster(kube_client: MagicMock) -> None:
    """Test manifest sent to K8s API uses camelCase for imagePullSecrets, allowUnoptimized, autoScaling."""
    aim = make_aim_cluster_model()
    req = AIMDeployRequest(
        model="img",
        image_pull_secrets=["secret1"],
        allow_unoptimized=True,
        min_replicas=2,
        max_replicas=8,
        auto_scaling={"metrics": []},
    )
    svc = make_aim_service_k8s()
    kube_client.custom_objects.create_namespaced_custom_object.return_value = svc.model_dump(by_alias=True)

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        await create_aim_service(kube_client, "test-ns", aim, req, "user", "wb-aim-test456", "test-group-id")

    call_args = kube_client.custom_objects.create_namespaced_custom_object.call_args
    manifest = call_args.kwargs["body"]
    spec = manifest["spec"]
    assert "imagePullSecrets" in spec
    assert spec["imagePullSecrets"][0]["name"] == "secret1"
    assert spec["template"]["allowUnoptimized"] is True
    assert spec["minReplicas"] == 2
    assert spec["maxReplicas"] == 8
    assert "autoScaling" in spec


@pytest.mark.asyncio
async def test_create_aim_service_crd_not_available(kube_client: MagicMock) -> None:
    """Test raises when CRD not available."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        with pytest.raises(RuntimeError, match="CRD not available"):
            await create_aim_service(
                kube_client,
                "ns",
                make_aim_cluster_model(),
                AIMDeployRequest(model="x"),
                "u",
                "wb-aim-test",
                "test-group-id",
            )


@pytest.mark.asyncio
async def test_delete_aim_service(kube_client: MagicMock) -> None:
    """Test deleting AIMService."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid, name="my-svc")
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await delete_aim_service(kube_client, "test-ns", wid)

    assert result == "my-svc"


@pytest.mark.asyncio
async def test_delete_aim_service_not_found(kube_client: MagicMock) -> None:
    """Test raises when service not found."""
    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        with pytest.raises(ValueError, match="No AIMService found"):
            await delete_aim_service(kube_client, "test-ns", uuid4())


@pytest.mark.asyncio
async def test_patch_aim_service_scaling_policy(kube_client: MagicMock) -> None:
    """Test patching scaling policy."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid, min_replicas=2, max_replicas=10)
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.patch_namespaced_custom_object.return_value = svc.model_dump(by_alias=True)

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await patch_aim_service_scaling_policy(kube_client, "ns", wid, 2, 10, {})

    assert result.spec.min_replicas == 2


def test_is_aim_service_chattable_true() -> None:
    """Test service is chattable when RUNNING with chat tag."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.RUNNING, model_ref="llama")
    aim = make_aim_cluster_model(name="llama", tags=["chat"])
    aims_by_name = {"llama": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is True


def test_is_aim_service_chattable_false_wrong_status() -> None:
    """Test service not chattable when not RUNNING."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.PENDING, model_ref="llama")
    aim = make_aim_cluster_model(name="llama", tags=["chat"])
    aims_by_name = {"llama": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is False


def test_is_aim_service_chattable_false_no_chat_tag() -> None:
    """Test service not chattable without chat tag."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.RUNNING, model_ref="llama")
    aim = make_aim_cluster_model(name="llama", tags=["text-generation"])  # No chat tag
    aims_by_name = {"llama": aim}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is False


def test_is_aim_service_chattable_false_aim_not_found() -> None:
    """Test service not chattable when AIM not found."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.RUNNING, model_ref="missing")
    aims_by_name: dict[str, AIMClusterModelResource] = {}

    result = is_aim_service_chattable(svc, aims_by_name)

    assert result is False


@pytest.mark.asyncio
async def test_list_aim_cluster_service_templates(kube_client: MagicMock) -> None:
    """Test listing templates."""
    t = make_aim_cluster_service_template()
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": [t.model_dump(by_alias=True)]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_cluster_service_templates(kube_client)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_aims_handles_exception(kube_client: MagicMock) -> None:
    """Test list_aims returns empty on exception."""
    kube_client.custom_objects.list_cluster_custom_object.side_effect = Exception("API error")

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aims(kube_client)

    assert result == []


@pytest.mark.asyncio
async def test_get_aim_by_name_handles_non_404_exception(kube_client: MagicMock) -> None:
    """Test get_aim_by_name handles non-404 exceptions."""
    kube_client.custom_objects.get_cluster_custom_object.side_effect = Exception("Server error")

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await get_aim_by_name(kube_client, "test")

    assert result is None


@pytest.mark.asyncio
async def test_list_aim_services_handles_exception(kube_client: MagicMock) -> None:
    """Test list_aim_services returns empty on exception."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = Exception("API error")

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_services(kube_client, "ns")

    assert result == []


@pytest.mark.asyncio
async def test_get_aim_service_by_id_handles_exception(kube_client: MagicMock) -> None:
    """Test get_aim_service_by_id returns None on exception."""
    kube_client.custom_objects.list_namespaced_custom_object.side_effect = Exception("API error")

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await get_aim_service_by_id(kube_client, "ns", uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_patch_aim_service_crd_not_available(kube_client: MagicMock) -> None:
    """Test patch raises when CRD not available."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        with pytest.raises(RuntimeError, match="CRD not available"):
            await patch_aim_service_scaling_policy(kube_client, "ns", uuid4(), 2, 10, {})


@pytest.mark.asyncio
async def test_patch_aim_service_handles_patch_error(kube_client: MagicMock) -> None:
    """Test patch raises RuntimeError on K8s patch failure."""
    wid = uuid4()
    svc = make_aim_service_k8s(workload_id=wid)
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.patch_namespaced_custom_object.side_effect = Exception("Patch failed")

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        with pytest.raises(RuntimeError, match="Failed to update scaling policy"):
            await patch_aim_service_scaling_policy(kube_client, "ns", wid, 2, 10, {})


@pytest.mark.asyncio
async def test_list_aim_cluster_service_templates_crd_not_found(kube_client: MagicMock) -> None:
    """Test returns empty when CRD not found."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        result = await list_aim_cluster_service_templates(kube_client)
    assert result == []


@pytest.mark.asyncio
async def test_list_aim_cluster_service_templates_handles_exception(kube_client: MagicMock) -> None:
    """Test handles exception gracefully."""
    kube_client.custom_objects.list_cluster_custom_object.side_effect = Exception("Error")

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_cluster_service_templates(kube_client)

    assert result == []


@pytest.mark.asyncio
async def test_delete_aim_service_crd_not_available(kube_client: MagicMock) -> None:
    """Test delete raises when CRD not available."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        with pytest.raises(RuntimeError, match="CRD not available"):
            await delete_aim_service(kube_client, "ns", uuid4())


@pytest.mark.asyncio
async def test_get_aim_by_name_crd_not_available(kube_client: MagicMock) -> None:
    """Test get_aim_by_name returns None when CRD not available."""
    with patch("app.aims.gateway.get_resource_version", return_value=None):
        result = await get_aim_by_name(kube_client, "test")
    assert result is None


@pytest.mark.asyncio
async def test_list_aim_services_with_chattable_filter(kube_client: MagicMock) -> None:
    """Test listing services with chattable filter."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.RUNNING, model_ref="llama")
    aim = make_aim_cluster_model(name="llama", tags=["chat"])
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": [aim.model_dump(by_alias=True)]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_services(kube_client, "test-ns", chattable_only=True)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_aim_services_chattable_filters_out_non_chattable(kube_client: MagicMock) -> None:
    """Test chattable filter excludes non-chattable services."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.PENDING)  # Not RUNNING
    kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": [svc.model_dump(by_alias=True)]}
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": []}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
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

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await _get_aims_by_name(kube_client)

    assert len(result) == 2
    assert "llama" in result
    assert "mistral" in result
    assert result["llama"].metadata.name == "llama"
    assert result["mistral"].metadata.name == "mistral"


@pytest.mark.asyncio
async def test_list_aim_cluster_service_templates_with_model_name(kube_client: MagicMock) -> None:
    """Test listing templates filtered by model name."""
    t = make_aim_cluster_service_template(model_name="llama")
    kube_client.custom_objects.list_cluster_custom_object.return_value = {"items": [t.model_dump(by_alias=True)]}

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        result = await list_aim_cluster_service_templates(kube_client, model_name="llama")

    assert len(result) == 1
    # Verify label selector was used
    kube_client.custom_objects.list_cluster_custom_object.assert_called_once()
    call_kwargs = kube_client.custom_objects.list_cluster_custom_object.call_args.kwargs
    assert "llama" in call_kwargs.get("label_selector", "")


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

    with patch("app.aims.gateway.get_resource_version", return_value="v1alpha1"):
        # Filter to only include RUNNING and PENDING (exclude DELETED)
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
