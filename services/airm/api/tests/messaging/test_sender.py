# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from airm.messaging.schemas import ClusterQuotaAllocation, ClusterQuotasAllocationMessage, GPUVendor
from app.messaging.sender import MessageSender, message_sender_scope
from app.quotas.utils import format_quotas_allocation_message


@pytest.mark.asyncio
async def test_message_sender_queues_messages():
    """Test that MessageSender queues messages without sending them immediately."""
    sender = MessageSender()
    cluster_id = uuid4()
    message = AsyncMock()

    await sender.enqueue(cluster_id, message)

    assert len(sender._messages) == 1
    assert sender._messages[0] == (cluster_id, message)


@pytest.mark.asyncio
async def test_message_sender_flush_sends_all_messages():
    """Test that flush sends all queued messages."""
    with (
        patch("app.messaging.sender.get_connection_to_cluster_vhost") as mock_connect,
        patch("app.messaging.sender.publish_message_to_queue") as mock_publish,
    ):
        # Create mock connection and channel objects (not AsyncMock)
        mock_connection = object()
        mock_channel = object()
        mock_connect.return_value = (mock_connection, mock_channel)
        mock_publish.return_value = None

        sender = MessageSender()
        cluster_id1 = uuid4()
        cluster_id2 = uuid4()

        # Create messages with MagicMock for json() to avoid async issues
        message1 = MagicMock()
        message2 = MagicMock()
        message1.json.return_value = '{"test": "message1"}'
        message2.json.return_value = '{"test": "message2"}'

        await sender.enqueue(cluster_id1, message1)
        await sender.enqueue(cluster_id2, message2)

        await sender.flush()

        assert mock_publish.await_count == 2
        assert len(sender._messages) == 0


@pytest.mark.asyncio
async def test_message_sender_scope_sends_on_success():
    """Test that message_sender_scope sends messages on successful exit."""
    with (
        patch("app.messaging.sender.get_connection_to_cluster_vhost") as mock_connect,
        patch("app.messaging.sender.publish_message_to_queue") as mock_publish,
    ):
        # Create mock connection and channel objects (not AsyncMock)
        mock_connection = object()
        mock_channel = object()
        mock_connect.return_value = (mock_connection, mock_channel)
        mock_publish.return_value = None

        cluster_id = uuid4()

        # Create message with MagicMock for json() to avoid async issues
        message = MagicMock()
        message.json.return_value = '{"test": "message"}'

        async with message_sender_scope() as message_sender:
            await message_sender.enqueue(cluster_id, message)

        mock_publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_sender_scope_discards_on_exception():
    """Test that message_sender_scope discards messages on exception."""
    with (
        patch("app.messaging.sender.get_connection_to_cluster_vhost") as mock_connect,
        patch("app.messaging.sender.publish_message_to_queue") as mock_publish,
    ):
        # Create mock connection and channel objects (not AsyncMock)
        mock_connection = object()
        mock_channel = object()
        mock_connect.return_value = (mock_connection, mock_channel)
        mock_publish.return_value = None

        cluster_id = uuid4()

        # Create message with MagicMock for json() to avoid async issues
        message = MagicMock()
        message.json.return_value = '{"test": "message"}'

        with pytest.raises(ValueError):
            async with message_sender_scope() as message_sender:
                await message_sender.enqueue(cluster_id, message)
                raise ValueError("Transaction failed")

        mock_publish.assert_not_awaited()


def test_format_quotas_allocation_message():
    """Test that format_quotas_allocation_message creates correct message."""
    quota_allocations = [
        ClusterQuotaAllocation(
            quota_name="project1",
            cpu_milli_cores=1000,
            memory_bytes=1024,
            ephemeral_storage_bytes=2048,
            gpu_count=2,
            namespaces=["project1"],
        )
    ]
    gpu_vendor = GPUVendor.NVIDIA

    message = format_quotas_allocation_message(quota_allocations, gpu_vendor)

    assert isinstance(message, ClusterQuotasAllocationMessage)
    assert message.message_type == "cluster_quotas_allocation"
    assert message.gpu_vendor == GPUVendor.NVIDIA
    assert message.quota_allocations == quota_allocations
    assert len(message.priority_classes) > 0  # Should have default priority classes
