# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from airm.messaging.schemas import (
    ClusterNodesMessage,
    ClusterQuotasFailureMessage,
    ClusterQuotasStatusMessage,
    HeartbeatMessage,
    ProjectNamespaceStatusMessage,
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
    ProjectStorageUpdateMessage,
    WorkloadStatusMessage,
)
from app.clusters.models import Cluster
from app.messaging.consumer import __process_message
from app.utilities.keycloak_admin import KeycloakAdmin


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
    ),
)
@patch("app.messaging.consumer.update_last_heartbeat")
async def test_process_message_update_last_heartbeat(mock_update_last_heartbeat, _, __):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = HeartbeatMessage(
        message_type="heartbeat",
        cluster_name="test_cluster",
        organization_name="test_org",
        last_heartbeat_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, AsyncMock(spec=KeycloakAdmin()))

    mock_update_last_heartbeat.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
    ),
)
@patch("app.messaging.consumer.update_workload_status")
async def test_process_message_update_workload_status(update_workload_status, _, __):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = WorkloadStatusMessage(
        message_type="workload_status_update",
        status="Running",
        workload_id=uuid4(),
        updated_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
        status_reason="a reason",
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, AsyncMock(spec=KeycloakAdmin()))

    update_workload_status.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
    ),
)
@patch("app.messaging.consumer.update_cluster_nodes")
async def test_process_message_update_cluster_nodes(update_cluster_nodes, _, __):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ClusterNodesMessage(
        message_type="cluster_nodes",
        cluster_nodes=[],
        updated_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, AsyncMock(spec=KeycloakAdmin()))

    update_cluster_nodes.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
    ),
)
@patch("app.messaging.consumer.update_cluster_quotas_from_allocations")
async def test_process_message_update_cluster_quotas_from_allocations(update_cluster_quotas_from_allocations, _, __):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ClusterQuotasStatusMessage(
        message_type="cluster_quotas_status",
        status="READY",
        quota_allocations=[],
        updated_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, MagicMock())

    update_cluster_quotas_from_allocations.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
    ),
)
@patch("app.messaging.consumer.update_pending_quotas_to_failed")
async def test_process_message_update_pending_quotas_to_failed(_, __, mock_update_pending_quotas_to_failed):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ClusterQuotasFailureMessage(
        message_type="cluster_quotas_failure",
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, AsyncMock(spec=KeycloakAdmin()))

    mock_update_pending_quotas_to_failed.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
    ),
)
@patch("app.messaging.consumer.update_project_secret_status")
async def test_process_message_update_project_secret_status(_, __, mock_update_project_secret_status):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=uuid4(),
        status=ProjectSecretStatus.SYNCED.value,
        reason="The reason for the update",
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, AsyncMock(spec=KeycloakAdmin()))

    mock_update_project_secret_status.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
    ),
)
@patch("app.messaging.consumer.get_kc_admin_client_from_state", return_value=MagicMock())
@patch("app.messaging.consumer.update_project_namespace_status")
async def test_process_message_update_project_namespace_status(
    mock_update_project_namespace_status, mock_get_kc_admin, _, __
):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ProjectNamespaceStatusMessage(
        message_type="project_namespace_status",
        project_id=uuid4(),
        status="Active",
        status_reason="namespace is ready",
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, MagicMock())

    mock_update_project_namespace_status.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(
        name="New Test Cluster2",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093",
        organization_id="08ccd4e0-3bef-480c-8e08-a21f47f51421",
    ),
)
@patch("app.messaging.consumer.update_configmap_status")
async def test_process_message_update_configmap_status(mock_update_configmap_status, mock_get_cluster, _):
    mock_message = AsyncMock()
    mock_message.process = MagicMock()

    project_storage_id = uuid4()
    message = ProjectStorageUpdateMessage(
        message_type="project_storage_update",
        project_storage_id=project_storage_id,
        status="Added",
        status_reason="Storage configmap successfully created",
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, AsyncMock(spec=KeycloakAdmin()))

    mock_update_configmap_status.assert_called_once()
