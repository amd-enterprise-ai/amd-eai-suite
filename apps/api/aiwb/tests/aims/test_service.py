# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs service layer."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ExternalServiceError, NotFoundException, ValidationException
from app.aims.enums import AIMServiceStatus
from app.aims.schemas import AIMDeployRequest
from app.aims.service import (
    _create_cluster_auth_group_for_aim,
    _delete_cluster_auth_group_for_aim,
    chat_with_aim_service,
    deploy_aim,
    get_aim_by_resource_name,
    get_aim_service,
    list_aim_cluster_service_templates,
    list_aim_services,
    list_aim_services_history,
    list_aims,
    list_chattable_aim_services,
    undeploy_aim,
    update_aim_scaling_policy,
)
from tests.factory import (
    create_aim_service_db,
    make_aim_cluster_model,
    make_aim_cluster_service_template,
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
    assert result.resource_name == "my-aim"


@pytest.mark.asyncio
async def test_get_aim_by_resource_name_not_found(kube_client: MagicMock) -> None:
    """Test raises NotFoundException."""
    with patch("app.aims.service.get_aim_by_name", return_value=None):
        with pytest.raises(NotFoundException):
            await get_aim_by_resource_name(kube_client, "missing")


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
        pytest.raises(NotFoundException, match="AIM model 'nonexistent-model' not found"),
    ):
        await deploy_aim(kube_client, req, "ns", "user", mock_cluster_auth_client)


@pytest.mark.asyncio
async def test_deploy_aim_with_camelcase_deploy_request(kube_client: MagicMock) -> None:
    """Test deploy_aim accepts deploy_request parsed from camelCase (as sent by UI)."""
    aim = make_aim_cluster_model()
    svc = make_aim_service_k8s()
    req = AIMDeployRequest(
        model="meta-llama-3-8b",
        imagePullSecrets=["s1"],
        hfToken="hf-secret",
        allowUnoptimized=True,
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
    assert call_kwargs["deploy_request"].allow_unoptimized is True
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
async def test_list_aim_services_history(db_session: AsyncSession) -> None:
    """Test listing history from DB."""
    await create_aim_service_db(db_session, namespace="my-ns")
    await create_aim_service_db(db_session, namespace="my-ns")

    result = await list_aim_services_history(db_session, "my-ns")
    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_aim_cluster_service_templates(kube_client: MagicMock) -> None:
    """Test listing templates."""
    aim = make_aim_cluster_model(name="my-aim")
    template = make_aim_cluster_service_template()

    with (
        patch("app.aims.service.get_aim_by_name", return_value=aim),
        patch("app.aims.service.get_aim_templates_from_k8s", return_value=[template]),
    ):
        result = await list_aim_cluster_service_templates(kube_client, "my-aim")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_aim_cluster_service_templates_aim_not_found(kube_client: MagicMock) -> None:
    """Test raises when AIM not found."""
    with patch("app.aims.service.get_aim_by_name", return_value=None):
        with pytest.raises(NotFoundException):
            await list_aim_cluster_service_templates(kube_client, "missing")


@pytest.mark.asyncio
async def test_list_aim_cluster_service_templates_no_templates(kube_client: MagicMock) -> None:
    """Test raises when no templates found."""
    aim = make_aim_cluster_model()
    with (
        patch("app.aims.service.get_aim_by_name", return_value=aim),
        patch("app.aims.service.get_aim_templates_from_k8s", return_value=[]),
    ):
        with pytest.raises(NotFoundException):
            await list_aim_cluster_service_templates(kube_client, "my-aim")


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
    svc = make_aim_service_k8s()
    with patch("app.aims.service.get_aim_services_from_k8s", return_value=[svc]):
        result = await list_chattable_aim_services(kube_client, "ns")
    assert len(result) == 1


# Tests for chat_with_aim_service


@pytest.mark.asyncio
async def test_chat_with_aim_service_success(kube_client: MagicMock, mock_request: MagicMock) -> None:
    """Test successful chat with AIM service."""
    service_id = uuid4()
    svc = make_aim_service_k8s(workload_id=service_id, status=AIMServiceStatus.RUNNING, model_ref="llama")

    # Mock the endpoints dict that AIMServiceResponse will compute
    with (
        patch("app.aims.service.get_aim_service_from_k8s", return_value=svc),
        patch("app.aims.service.AIMServiceResponse") as mock_response_class,
        patch("app.aims.service.stream_downstream", new_callable=AsyncMock) as mock_stream,
    ):
        mock_response = MagicMock()
        mock_response.endpoints.get.return_value = "http://test-service.workbench.svc.cluster.local"
        mock_response_class.model_validate.return_value = mock_response

        mock_stream.return_value = MagicMock()
        await chat_with_aim_service(kube_client, "ns", service_id, mock_request)

    # Verify stream_downstream was called with internal URL
    mock_stream.assert_called_once()
    call_kwargs = mock_stream.call_args.kwargs
    assert "test-service" in call_kwargs["base_url"]


@pytest.mark.asyncio
async def test_chat_with_aim_service_not_found(kube_client: MagicMock, mock_request: MagicMock) -> None:
    """Test raises NotFoundException when service not found."""
    with patch("app.aims.service.get_aim_service_from_k8s", return_value=None):
        with pytest.raises(NotFoundException, match="not found"):
            await chat_with_aim_service(kube_client, "ns", uuid4(), mock_request)


@pytest.mark.asyncio
async def test_chat_with_aim_service_not_chattable(kube_client: MagicMock, mock_request: MagicMock) -> None:
    """Test raises ValidationException when service is not chattable."""
    svc = make_aim_service_k8s(status=AIMServiceStatus.PENDING)

    with patch("app.aims.service.get_aim_service_from_k8s", return_value=svc):
        with pytest.raises(ValidationException, match="not available for chat"):
            await chat_with_aim_service(kube_client, "ns", uuid4(), mock_request)


@pytest.mark.asyncio
async def test_chat_with_aim_service_no_endpoint(kube_client: MagicMock, mock_request: MagicMock) -> None:
    """Test raises ValidationException when no internal endpoint available."""
    service_id = uuid4()
    svc = make_aim_service_k8s(workload_id=service_id, status=AIMServiceStatus.RUNNING, model_ref="llama")

    with (
        patch("app.aims.service.get_aim_service_from_k8s", return_value=svc),
        patch("app.aims.service.AIMServiceResponse") as mock_response_class,
    ):
        mock_response = MagicMock()
        mock_response.endpoints.get.return_value = None  # No endpoint
        mock_response_class.model_validate.return_value = mock_response

        with pytest.raises(ValidationException, match="No endpoint available"):
            await chat_with_aim_service(kube_client, "ns", service_id, mock_request)


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
