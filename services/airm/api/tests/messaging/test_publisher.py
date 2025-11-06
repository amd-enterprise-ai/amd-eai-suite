# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from aio_pika import abc

from airm.messaging.schemas import DeleteWorkloadMessage, WorkloadMessage
from app.messaging.publisher import submit_message_to_cluster_queue, submit_quotas_allocation_to_cluster_queue


@pytest.mark.asyncio
@patch("app.messaging.publisher.get_connection_to_cluster_vhost")
@patch("app.messaging.publisher.publish_message_to_queue")
async def test_submit_workload_to_cluster_queue(mock_publish_message_to_queue, mock_init_connection_to_user_vhost):
    cluster_id = uuid4()
    manifest = "test_manifest"
    workload_id = uuid4()
    mock_connection = AsyncMock(spec=abc.AbstractConnection)
    mock_channel = AsyncMock(spec=abc.AbstractChannel)
    mock_init_connection_to_user_vhost.return_value = (mock_connection, mock_channel)

    message = WorkloadMessage(message_type="workload", manifest=manifest, user_token="token", workload_id=workload_id)
    await submit_message_to_cluster_queue(cluster_id, message)

    mock_init_connection_to_user_vhost.assert_called_once()

    mock_publish_message_to_queue.assert_called_once()


@pytest.mark.asyncio
@patch("app.messaging.publisher.get_connection_to_cluster_vhost")
@patch("app.messaging.publisher.publish_message_to_queue")
async def test_submit_quotas_allocation_to_cluster_queue(
    mock_publish_message_to_queue, mock_init_connection_to_user_vhost
):
    cluster_id = uuid4()
    gpu_vendor = "AMD"
    quota_allocations = [
        {
            "cpu_milli_cores": 4000,
            "gpu_count": 1,
            "memory_bytes": 10 * (1024**3),
            "ephemeral_storage_bytes": 1 * (1024**3),
            "quota_name": "test_quota",
            "quota_id": uuid4(),
            "namespaces": ["test_quota"],
        },
        {
            "cpu_milli_cores": 8000,
            "gpu_count": 2,
            "memory_bytes": 5 * (1024**3),
            "ephemeral_storage_bytes": 2 * (1024**3),
            "quota_name": "test_quota",
            "quota_id": uuid4(),
            "namespaces": ["test_quota"],
        },
    ]

    mock_connection = AsyncMock(spec=abc.AbstractConnection)
    mock_channel = AsyncMock(spec=abc.AbstractChannel)
    mock_init_connection_to_user_vhost.return_value = (mock_connection, mock_channel)

    await submit_quotas_allocation_to_cluster_queue(quota_allocations, cluster_id, gpu_vendor)

    mock_init_connection_to_user_vhost.assert_called_once()

    mock_publish_message_to_queue.assert_called_once()


@pytest.mark.asyncio
@patch("app.messaging.publisher.get_connection_to_cluster_vhost")
@patch("app.messaging.publisher.publish_message_to_queue")
async def test_submit_delete_workload_to_cluster_queue(
    mock_publish_message_to_queue, mock_init_connection_to_user_vhost
):
    cluster_id = uuid4()
    workload_id = uuid4()
    mock_connection = AsyncMock(spec=abc.AbstractConnection)
    mock_channel = AsyncMock(spec=abc.AbstractChannel)
    mock_init_connection_to_user_vhost.return_value = (mock_connection, mock_channel)

    message = DeleteWorkloadMessage(message_type="delete_workload", workload_id=workload_id)
    await submit_message_to_cluster_queue(cluster_id, message)

    mock_init_connection_to_user_vhost.assert_called_once()
    mock_publish_message_to_queue.assert_called_once()
