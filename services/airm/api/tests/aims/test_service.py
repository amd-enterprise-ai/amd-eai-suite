# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus
from app.aims.schemas import AIMDeployRequest
from app.aims.service import deploy_aim, get_aim, list_aims, undeploy_aim
from app.apikeys.cluster_auth_client import ClusterAuthClient
from app.apikeys.service import delete_group_from_cluster_auth
from app.utilities.exceptions import ConflictException, NotFoundException
from app.workloads.enums import WorkloadType
from tests.factory import create_aim, create_aim_workload, create_basic_test_environment


@pytest.mark.asyncio
async def test_get_aim_success(db_session: AsyncSession):
    """Test successfully retrieving an AIM by ID."""
    resource_name = "aim-llama-0-1-0"
    image_reference = "docker.io/amdenterpriseai/aim-llama:0.1.0-inference-20251001"
    labels = {"com.amd.aim.model.canonicalName": "test-model", "framework": "pytorch"}
    aim = await create_aim(
        db_session,
        resource_name=resource_name,
        image_reference=image_reference,
        labels=labels,
    )

    result = await get_aim(db_session, aim.id)

    assert result.id == aim.id
    assert result.image_reference == image_reference
    assert result.labels == labels
    # image_name is extracted from image_reference (just the last path segment before colon)
    assert result.image_name == "aim-llama"
    assert result.image_tag == "0.1.0-inference-20251001"


@pytest.mark.asyncio
async def test_get_aim_not_found(db_session: AsyncSession):
    """Test error when AIM with ID doesn't exist."""
    with pytest.raises(NotFoundException, match="AIM with ID '.*' not found"):
        await get_aim(db_session, uuid4())


@pytest.mark.asyncio
async def test_list_aims_empty(db_session: AsyncSession):
    """Test listing AIMs when none exist."""
    env = await create_basic_test_environment(db_session)

    result = await list_aims(db_session, env.project)

    assert result == []


@pytest.mark.asyncio
async def test_list_aims_with_no_workloads(db_session: AsyncSession):
    """Test listing AIMs when they exist but have no workloads."""
    env = await create_basic_test_environment(db_session)
    aim1 = await create_aim(
        db_session,
        resource_name="aim-test-model-chat-0-1-0",
        image_reference="docker.io/amdenterpriseai/aim:0.1.0-test-model-chat-20251001",
    )
    aim2 = await create_aim(
        db_session,
        resource_name="aim-llama-test-model-instruct-0-2-0",
        image_reference="docker.io/amdenterpriseai/aim-llama:0.2.0-test-model-instruct-20251002",
    )

    result = await list_aims(db_session, env.project)

    assert len(result) == 2
    # Use image_reference for keying since that's what we have
    aims_by_ref = {aim.image_reference: aim for aim in result}
    assert "docker.io/amdenterpriseai/aim:0.1.0-test-model-chat-20251001" in aims_by_ref
    assert "docker.io/amdenterpriseai/aim-llama:0.2.0-test-model-instruct-20251002" in aims_by_ref
    assert aims_by_ref["docker.io/amdenterpriseai/aim:0.1.0-test-model-chat-20251001"].workload is None
    assert aims_by_ref["docker.io/amdenterpriseai/aim-llama:0.2.0-test-model-instruct-20251002"].workload is None


@pytest.mark.asyncio
async def test_list_aims_with_workloads(db_session: AsyncSession):
    """Test listing AIMs with their associated workloads."""
    env = await create_basic_test_environment(db_session)
    aim1 = await create_aim(
        db_session,
        resource_name="aim-test-model-chat-0-1-0",
        image_reference="docker.io/amdenterpriseai/aim:0.1.0-test-model-chat-20251001",
    )
    aim2 = await create_aim(
        db_session,
        resource_name="aim-llama-test-model-instruct-0-2-0",
        image_reference="docker.io/amdenterpriseai/aim-llama:0.2.0-test-model-instruct-20251002",
    )

    # Create workload for aim1
    workload1 = await create_aim_workload(
        db_session,
        env.project,
        aim1,
        name="aim-workload-1",
        display_name="AIM-base",
        status=WorkloadStatus.RUNNING.value,
    )

    result = await list_aims(db_session, env.project)

    assert len(result) == 2
    aims_by_ref = {aim.image_reference: aim for aim in result}
    assert aims_by_ref["docker.io/amdenterpriseai/aim:0.1.0-test-model-chat-20251001"].workload is not None
    assert aims_by_ref["docker.io/amdenterpriseai/aim:0.1.0-test-model-chat-20251001"].workload.id == workload1.id
    assert (
        aims_by_ref["docker.io/amdenterpriseai/aim:0.1.0-test-model-chat-20251001"].workload.display_name == "AIM-base"
    )
    assert aims_by_ref["docker.io/amdenterpriseai/aim-llama:0.2.0-test-model-instruct-20251002"].workload is None


@pytest.mark.asyncio
async def test_deploy_aim_success(db_session: AsyncSession, mock_cluster_auth_client):
    """Test successful AIM deployment."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-0-1-0",
        image_reference="docker.io/amdenterpriseai/test-model:0.1.0",
        labels={"com.amd.aim.model.canonicalName": "test-model"},
    )
    deploy_request = AIMDeployRequest()
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.extract_components_and_submit_workload") as mock_submit:
        result = await deploy_aim(
            db_session,
            aim.id,
            deploy_request,
            env.project,
            env.creator,
            "test-token",
            mock_cluster_auth_client,
            mock_message_sender,
        )

    assert result.aim_id == aim.id
    assert result.project.id == env.project.id
    assert result.project.cluster_id == env.project.cluster.id
    assert result.type == WorkloadType.INFERENCE
    assert result.status == WorkloadStatus.PENDING
    assert result.user_inputs == {}
    assert mock_submit.called


@pytest.mark.asyncio
async def test_deploy_aim_with_display_name(db_session: AsyncSession, mock_cluster_auth_client):
    """Test AIM deployment with custom display name."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-0-1-0",
        image_reference="docker.io/amdenterpriseai/test-model:0.1.0",
        labels={"com.amd.aim.model.canonicalName": "test-model"},
    )
    deploy_request = AIMDeployRequest()
    custom_display_name = "My Custom AIM Deployment"
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.extract_components_and_submit_workload"):
        result = await deploy_aim(
            db_session,
            aim.id,
            deploy_request,
            env.project,
            env.creator,
            "test-token",
            mock_cluster_auth_client,
            mock_message_sender,
            display_name=custom_display_name,
        )

    assert result.display_name == custom_display_name


@pytest.mark.asyncio
async def test_deploy_aim_not_found(db_session: AsyncSession, mock_cluster_auth_client):
    """Test deployment error when AIM doesn't exist."""
    env = await create_basic_test_environment(db_session)
    deploy_request = AIMDeployRequest()
    mock_message_sender = AsyncMock()

    with pytest.raises(NotFoundException, match="AIM with ID '.*' not found"):
        await deploy_aim(
            db_session,
            uuid4(),
            deploy_request,
            env.project,
            env.creator,
            "test-token",
            mock_cluster_auth_client,
            mock_message_sender,
        )


@pytest.mark.asyncio
async def test_deploy_aim_already_deployed(db_session: AsyncSession, mock_cluster_auth_client):
    """Test deployment error when AIM is already deployed."""
    env = await create_basic_test_environment(db_session)
    mock_message_sender = AsyncMock()
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-0-1-0",
        image_reference="docker.io/amdenterpriseai/test-model:0.1.0",
        labels={"com.amd.aim.model.canonicalName": "test-model"},
    )

    # Create existing workload
    await create_aim_workload(
        db_session,
        env.project,
        aim,
        name="existing-workload",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
    )

    with pytest.raises(ConflictException, match=f"AIM '{aim.resource_name}' is already deployed in project"):
        await deploy_aim(
            db_session,
            aim.id,
            AIMDeployRequest(),
            env.project,
            env.creator,
            "test-token",
            mock_cluster_auth_client,
            mock_message_sender,
        )


@pytest.mark.asyncio
async def test_deploy_aim_pending_deployment_blocks_new(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that pending deployment blocks new deployment."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-0-1-0",
        image_reference="docker.io/amdenterpriseai/test-model:0.1.0",
        labels={"com.amd.aim.model.canonicalName": "test-model"},
    )

    # Create pending workload
    await create_aim_workload(
        db_session,
        env.project,
        aim,
        name="pending-workload",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING.value,
    )

    deploy_request = AIMDeployRequest()
    mock_message_sender = AsyncMock()

    with pytest.raises(ConflictException):
        await deploy_aim(
            db_session,
            aim.id,
            deploy_request,
            env.project,
            env.creator,
            "test-token",
            mock_cluster_auth_client,
            mock_message_sender,
        )


@pytest.mark.asyncio
async def test_undeploy_aim_success(db_session: AsyncSession, mock_cluster_auth_client):
    """Test successful AIM undeployment."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session)
    workload = await create_aim_workload(
        db_session, env.project, aim, name="undeploy-workload", status=WorkloadStatus.RUNNING.value
    )
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.submit_delete_workload", return_value=None) as mock_delete:
        result = await undeploy_aim(
            db_session, aim.id, env.project, env.creator, mock_cluster_auth_client, mock_message_sender
        )

    assert result is None
    mock_delete.assert_called_once_with(
        session=db_session, workload=workload, user=env.creator, message_sender=mock_message_sender
    )


@pytest.mark.asyncio
async def test_undeploy_aim_not_found(db_session: AsyncSession, mock_cluster_auth_client):
    """Test undeployment error when AIM doesn't exist."""
    env = await create_basic_test_environment(db_session)
    mock_message_sender = AsyncMock()

    with pytest.raises(NotFoundException, match="AIM with ID '.*' not found"):
        await undeploy_aim(db_session, uuid4(), env.project, env.creator, mock_cluster_auth_client, mock_message_sender)


@pytest.mark.asyncio
async def test_undeploy_aim_no_workload(db_session: AsyncSession, mock_cluster_auth_client):
    """Test undeployment error when AIM has no active workload."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session)
    mock_message_sender = AsyncMock()

    with pytest.raises(NotFoundException, match=f"No active workload found for AIM '{aim.resource_name}'"):
        await undeploy_aim(db_session, aim.id, env.project, env.creator, mock_cluster_auth_client, mock_message_sender)


@pytest.mark.asyncio
async def test_undeploy_aim_failed_workload_ignored(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that failed workloads are not considered for undeployment."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session)
    mock_message_sender = AsyncMock()

    # Create failed workload (should be ignored)
    await create_aim_workload(db_session, env.project, aim, name="failed-workload", status=WorkloadStatus.FAILED.value)

    with pytest.raises(NotFoundException, match="No active workload found"):
        await undeploy_aim(db_session, aim.id, env.project, env.creator, mock_cluster_auth_client, mock_message_sender)


@pytest.mark.asyncio
async def test_deploy_aim_with_cluster_auth_group_success(db_session: AsyncSession, mock_cluster_auth_client):
    """Test AIM deployment with successful cluster-auth group creation."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-v1-0",
        image_reference="docker.io/amdenterpriseai/test-model:v1.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
    )

    deploy_request = AIMDeployRequest(
        cache_model=True,
        replicas=1,
        image_pull_secrets=["my-secret"],
        hf_token="hf_test_token",
    )
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.extract_components_and_submit_workload") as mock_submit:
        mock_submit.return_value = None

        result = await deploy_aim(
            session=db_session,
            aim_id=aim.id,
            deploy_request=deploy_request,
            project=env.project,
            creator=env.creator,
            token="test-token",
            cluster_auth_client=mock_cluster_auth_client,
            message_sender=mock_message_sender,
        )

    # Verify workload was created
    assert result.aim_id == aim.id
    assert result.type == WorkloadType.INFERENCE
    assert result.cluster_auth_group_id is not None

    # Verify cluster-auth group was created by trying to delete it (should succeed)
    # If group doesn't exist, delete will fail
    await delete_group_from_cluster_auth(
        db_session, env.organization, env.project, result.cluster_auth_group_id, mock_cluster_auth_client
    )


@pytest.mark.asyncio
async def test_undeploy_aim_cleans_up_cluster_auth_group(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that undeploying an AIM cleans up its cluster-auth group."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-0-1-0",
        image_reference="docker.io/amdenterpriseai/test-model:0.1.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
    )
    # Create a group in the mock client
    group_result = await mock_cluster_auth_client.create_group(name="test-group")
    group_id = group_result["id"]

    # Create workload with cluster_auth_group_id
    workload = await create_aim_workload(
        db_session,
        env.project,
        aim,
        name="undeploy-workload",
        status=WorkloadStatus.RUNNING.value,
        cluster_auth_group_id=group_id,
    )

    # Verify group exists by trying to delete it (should succeed)
    await delete_group_from_cluster_auth(db_session, env.organization, env.project, group_id, mock_cluster_auth_client)

    # Recreate the group since we deleted it
    group_result = await mock_cluster_auth_client.create_group(name="test-group", group_id=group_id)
    workload.cluster_auth_group_id = group_id
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.submit_delete_workload", return_value=None) as mock_delete:
        result = await undeploy_aim(
            db_session, aim.id, env.project, env.creator, mock_cluster_auth_client, mock_message_sender
        )

    assert result is None
    mock_delete.assert_called_once_with(
        session=db_session, workload=workload, user=env.creator, message_sender=mock_message_sender
    )

    # Verify group was deleted by trying to delete it again (should fail)
    with pytest.raises(NotFoundException):
        await delete_group_from_cluster_auth(
            db_session, env.organization, env.project, group_id, mock_cluster_auth_client
        )


@pytest.mark.asyncio
async def test_undeploy_aim_without_cluster_auth_group(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that undeploying an AIM without cluster-auth group works normally."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-0-1-0",
        image_reference="docker.io/amdenterpriseai/test-model:0.1.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
    )
    # Create workload without cluster_auth_group_id
    workload = await create_aim_workload(
        db_session, env.project, aim, name="undeploy-workload", status=WorkloadStatus.RUNNING.value
    )
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.submit_delete_workload", return_value=None) as mock_delete:
        result = await undeploy_aim(
            db_session, aim.id, env.project, env.creator, mock_cluster_auth_client, mock_message_sender
        )

    assert result is None
    mock_delete.assert_called_once_with(
        session=db_session, workload=workload, user=env.creator, message_sender=mock_message_sender
    )


@pytest.mark.asyncio
async def test_deploy_aim_with_cluster_auth_group_failure(db_session: AsyncSession, mock_cluster_auth_client):
    """Test AIM deployment continues when cluster-auth group creation fails."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-v1-0",
        image_reference="docker.io/amdenterpriseai/test-model:v1.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
    )

    # Wrapper that fails group creation
    class FailingClient:
        def __init__(self, client: ClusterAuthClient):
            self._client = client

        async def create_api_key(self, *args, **kwargs):
            return await self._client.create_api_key(*args, **kwargs)

        async def create_group(self, name: str, group_id: str | None = None) -> dict:
            raise Exception("Cluster-auth service unavailable")

        async def delete_group(self, *args, **kwargs):
            return await self._client.delete_group(*args, **kwargs)

    failing_client = FailingClient(mock_cluster_auth_client)

    deploy_request = AIMDeployRequest(
        cache_model=True,
        replicas=1,
        image_pull_secrets=["my-secret"],
        hf_token="hf_test_token",
    )
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.extract_components_and_submit_workload") as mock_submit:
        mock_submit.return_value = None

        # Should not raise an exception even when group creation fails
        result = await deploy_aim(
            session=db_session,
            aim_id=aim.id,
            deploy_request=deploy_request,
            project=env.project,
            creator=env.creator,
            token="test-token",
            cluster_auth_client=failing_client,
            message_sender=mock_message_sender,
        )

    # Verify workload was still created successfully
    assert result.aim_id == aim.id
    assert result.type == WorkloadType.INFERENCE
    # Cluster auth group should be None due to failure
    assert result.cluster_auth_group_id is None


@pytest.mark.asyncio
async def test_deploy_aim_manifest_includes_group_annotation(db_session: AsyncSession, mock_cluster_auth_client):
    """Test that the generated manifest includes cluster-auth group annotation when group is created."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-v1-0",
        image_reference="docker.io/amdenterpriseai/test-model:v1.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
    )

    deploy_request = AIMDeployRequest(
        cache_model=True,
        replicas=1,
        image_pull_secrets=["my-secret"],
        hf_token="hf_test_token",
    )

    submitted_manifest = None
    mock_message_sender = AsyncMock()

    def capture_manifest(session, workload, project, manifest, creator, token, message_sender):
        nonlocal submitted_manifest
        submitted_manifest = manifest

    with patch("app.aims.service.extract_components_and_submit_workload", side_effect=capture_manifest):
        result = await deploy_aim(
            session=db_session,
            aim_id=aim.id,
            deploy_request=deploy_request,
            project=env.project,
            creator=env.creator,
            token="test-token",
            cluster_auth_client=mock_cluster_auth_client,
            message_sender=mock_message_sender,
        )

    # Verify manifest includes cluster-auth annotation
    assert submitted_manifest is not None
    assert len(submitted_manifest) > 0

    aim_service_manifest = submitted_manifest[0]
    routing_spec = aim_service_manifest["spec"]["routing"]
    assert "annotations" in routing_spec
    assert "cluster-auth/allowed-group" in routing_spec["annotations"]
    assert routing_spec["annotations"]["cluster-auth/allowed-group"] == result.cluster_auth_group_id


@pytest.mark.asyncio
async def test_deploy_aim_manifest_no_group_annotation_when_group_fails(
    db_session: AsyncSession, mock_cluster_auth_client
):
    """Test that manifest has no cluster-auth annotation when group creation fails."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-v1-0",
        image_reference="docker.io/amdenterpriseai/test-model:v1.0",
        labels={"com.amd.aim.model.canonicalName": "test/model"},
    )

    # Wrapper that fails group creation
    class FailingClient:
        def __init__(self, client: ClusterAuthClient):
            self._client = client

        async def create_api_key(self, *args, **kwargs):
            return await self._client.create_api_key(*args, **kwargs)

        async def create_group(self, name: str, group_id: str | None = None) -> dict:
            raise Exception("Group creation failed")

        async def delete_group(self, *args, **kwargs):
            return await self._client.delete_group(*args, **kwargs)

    failing_client = FailingClient(mock_cluster_auth_client)

    deploy_request = AIMDeployRequest(
        cache_model=True,
        replicas=1,
        image_pull_secrets=["my-secret"],
        hf_token="hf_test_token",
    )

    submitted_manifest = None
    mock_message_sender = AsyncMock()

    def capture_manifest(session, workload, project, manifest, creator, token, message_sender):
        nonlocal submitted_manifest
        submitted_manifest = manifest

    with patch("app.aims.service.extract_components_and_submit_workload", side_effect=capture_manifest):
        result = await deploy_aim(
            session=db_session,
            aim_id=aim.id,
            deploy_request=deploy_request,
            project=env.project,
            creator=env.creator,
            token="test-token",
            cluster_auth_client=failing_client,
            message_sender=mock_message_sender,
        )

    # Verify manifest does not include cluster-auth annotation
    assert submitted_manifest is not None
    assert len(submitted_manifest) > 0

    aim_service_manifest = submitted_manifest[0]
    routing_spec = aim_service_manifest["spec"]["routing"]
    # Should not have annotations when group creation fails
    assert "annotations" not in routing_spec or "cluster-auth/allowed-group" not in routing_spec.get("annotations", {})


@pytest.mark.asyncio
async def test_deploy_aim_without_canonical_name(db_session: AsyncSession, mock_cluster_auth_client):
    """Test AIM deployment when canonical name is not present in labels."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session, labels={"other.label": "value"})
    deploy_request = AIMDeployRequest()
    mock_message_sender = AsyncMock()

    with patch("app.aims.service.extract_components_and_submit_workload") as mock_submit:
        result = await deploy_aim(
            db_session,
            aim.id,
            deploy_request,
            env.project,
            env.creator,
            "test-token",
            mock_cluster_auth_client,
            mock_message_sender,
        )

    assert result.aim_id == aim.id
    assert result.user_inputs == {}
    assert mock_submit.called
