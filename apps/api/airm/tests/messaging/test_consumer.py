# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from starlette.datastructures import State

from app.clusters.models import Cluster
from app.messaging.connector import init_connection
from app.messaging.constants import DEAD_LETTER_QUEUE_NAME
from app.messaging.consumer import __process_message, start_queue_consumer
from app.messaging.publisher import publish_message_to_queue
from app.messaging.queues import configure_queues
from app.messaging.schemas import (
    ClusterNodesMessage,
    ClusterQuotasFailureMessage,
    ClusterQuotasStatusMessage,
    HeartbeatMessage,
    ProjectNamespaceStatusMessage,
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
    ProjectStorageUpdateMessage,
    SecretScope,
    WorkloadStatusMessage,
)
from app.utilities.keycloak_admin import KeycloakAdmin


@pytest.mark.asyncio
async def test_start_queue_consumer_message_processing_successful(rabbitmq_service):
    docker_ip, port = rabbitmq_service
    processed_messages = []

    queue_name = "test_queue"

    async def process_message(message):
        processed_messages.append(message)
        await message.ack()

    connection, channel = await init_connection(docker_ip, port, "vh_airm_common", "guest", "guest")
    await configure_queues(channel, queue_name)

    task = asyncio.create_task(
        start_queue_consumer(
            host=docker_ip,
            port=port,
            vhost="vh_airm_common",
            queue_name=queue_name,
            username="guest",
            password="guest",
            process_message=process_message,
        )
    )

    # Allow consumer to initialize
    await asyncio.sleep(1)

    try:
        await publish_message_to_queue(connection, queue_name, "test message", "guest", channel)

        # Wait for message processing
        await asyncio.sleep(1)

        assert len(processed_messages) == 1
        assert processed_messages[0].body == b"test message"

    finally:
        await connection.close()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_consumer_dead_letter_queue(rabbitmq_service):
    docker_ip, port = rabbitmq_service
    queue_name = "test_queue"

    count = 0

    async def process_message(message):
        async with message.process(requeue=True):
            nonlocal count
            count += 1
            raise Exception("Test exception")

    connection, channel = await init_connection(docker_ip, port, "vh_airm_common", "guest", "guest")
    await configure_queues(channel, queue_name)

    task = asyncio.create_task(
        start_queue_consumer(
            host=docker_ip,
            port=port,
            vhost="vh_airm_common",
            queue_name=queue_name,
            username="guest",
            password="guest",
            process_message=process_message,
        )
    )
    await asyncio.sleep(1)
    await publish_message_to_queue(connection, queue_name, "test message", "guest", channel)

    # Wait for message processing
    await asyncio.sleep(1)

    # Message should be processed 21 times (1 + 20 default retry count)
    assert count == 21

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    processed_messages = []

    async def process_dl_message(message):
        async with message.process(requeue=True):
            processed_messages.append(message)

    task = asyncio.create_task(
        start_queue_consumer(
            host=docker_ip,
            port=port,
            vhost="vh_airm_common",
            queue_name=DEAD_LETTER_QUEUE_NAME,
            username="guest",
            password="guest",
            process_message=process_dl_message,
        )
    )

    # Wait for message processing
    await asyncio.sleep(1)

    assert len(processed_messages) == 1
    assert processed_messages[0].body == b"test message"

    await connection.close()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.update_last_heartbeat")
async def test_process_message_update_last_heartbeat(
    mock_update_last_heartbeat: AsyncMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = HeartbeatMessage(
        message_type="heartbeat",
        cluster_name="test_cluster",
        organization_name="test_org",
        last_heartbeat_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, State())

    mock_update_last_heartbeat.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.update_workload_status")
async def test_process_message_update_workload_status(
    update_workload_status: AsyncMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

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

    await __process_message(mock_message, State())

    update_workload_status.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.update_cluster_nodes")
async def test_process_message_update_cluster_nodes(
    update_cluster_nodes: AsyncMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ClusterNodesMessage(
        message_type="cluster_nodes", cluster_nodes=[], updated_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, State())

    update_cluster_nodes.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.get_kc_admin_client_from_state", return_value=AsyncMock(spec=KeycloakAdmin))
@patch("app.messaging.consumer.update_cluster_quotas_from_allocations")
async def test_process_message_update_cluster_quotas_from_allocations(
    update_cluster_quotas_from_allocations: AsyncMock,
    mock_get_kc_admin: MagicMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ClusterQuotasStatusMessage(
        message_type="cluster_quotas_status",
        status="READY",
        quota_allocations=[],
        updated_at=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, State())

    update_cluster_quotas_from_allocations.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.get_kc_admin_client_from_state", return_value=AsyncMock(spec=KeycloakAdmin))
@patch("app.messaging.consumer.update_pending_quotas_to_failed")
async def test_process_message_update_pending_quotas_to_failed(
    mock_update_pending_quotas_to_failed: AsyncMock,
    mock_get_kc_admin: MagicMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ClusterQuotasFailureMessage(
        message_type="cluster_quotas_failure", updated_at=datetime.datetime.now(datetime.UTC)
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, State())

    mock_update_pending_quotas_to_failed.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.update_project_secret_status")
async def test_process_message_update_project_secret_status(
    mock_update_project_secret_status: AsyncMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

    mock_message = AsyncMock()
    mock_message.process = MagicMock()
    message = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=uuid4(),
        secret_scope=SecretScope.PROJECT,
        status=ProjectSecretStatus.SYNCED.value,
        reason="The reason for the update",
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    mock_message.body.decode = lambda: message.json()

    await __process_message(mock_message, State())

    mock_update_project_secret_status.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.get_kc_admin_client_from_state", return_value=AsyncMock(spec=KeycloakAdmin))
@patch("app.messaging.consumer.update_project_namespace_status")
async def test_process_message_update_project_namespace_status(
    mock_update_project_namespace_status: AsyncMock,
    mock_get_kc_admin: MagicMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

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

    await __process_message(mock_message, State())

    mock_update_project_namespace_status.assert_called()


@pytest.mark.asyncio
@patch("app.messaging.consumer.session_scope")
@patch("app.messaging.consumer.message_sender_scope")
@patch(
    "app.messaging.consumer.get_cluster_by_id",
    return_value=Cluster(name="New Test Cluster2", id="f33bf805-2a5f-4f01-8e3b-339fd8c9e093"),
)
@patch("app.messaging.consumer.update_configmap_status")
async def test_process_message_update_configmap_status(
    mock_update_configmap_status: AsyncMock,
    mock_get_cluster: MagicMock,
    mock_sender_scope: MagicMock,
    mock_session_scope: MagicMock,
) -> None:
    mock_session_scope.return_value.__aenter__.return_value = AsyncMock()
    mock_sender_scope.return_value.__aenter__.return_value = AsyncMock()

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

    await __process_message(mock_message, State())

    mock_update_configmap_status.assert_called_once()
