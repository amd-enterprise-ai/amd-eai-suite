# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from contextlib import asynccontextmanager
from uuid import UUID

from loguru import logger

from airm.messaging.connector import get_connection_to_cluster_vhost
from airm.messaging.publisher import publish_message_to_queue
from airm.messaging.schemas import Message

from .config import RABBITMQ_ADMIN_PASSWORD, RABBITMQ_ADMIN_USER, RABBITMQ_HOST, RABBITMQ_PORT


class MessageSender:
    """
    Collects messages during a transaction and sends them only after successful completion.

    Usage:
        sender = MessageSender()
        await sender.enqueue(cluster_id, message)  # Queues the message
        await sender.flush()  # Sends all queued messages
    """

    def __init__(self):
        self._messages: list[tuple[UUID, Message]] = []

    async def enqueue(self, cluster_id: UUID, message: Message) -> None:
        """
        Queue a message to be sent after transaction commits.

        Args:
            cluster_id: The cluster to send the message to
            message: The message to send
        """
        self._messages.append((cluster_id, message))

    async def flush(self) -> None:
        """
        Send all queued messages to RabbitMQ.

        This should only be called after the database transaction has successfully committed.
        Messages are sent one at a time and removed from the queue after successful delivery.
        If a message fails to send, an exception is raised and remaining messages stay queued.
        """
        while self._messages:
            cluster_id, message = self._messages[0]
            logger.info(f"Sending {message.message_type} message to cluster {cluster_id}")
            connection, channel = await get_connection_to_cluster_vhost(
                cluster_id, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD
            )
            await publish_message_to_queue(connection, f"{cluster_id}", message.json(), RABBITMQ_ADMIN_USER, channel)
            self._messages.pop(0)  # Only remove after successful send


@asynccontextmanager
async def message_sender_scope():
    """
    Context manager providing a MessageSender that flushes on successful exit.

    The transaction enforcement works through the context manager lifecycle:
    1. Messages are queued during the `with` block (transaction in progress)
    2. If an exception occurs, the except block discards queued messages
    3. If no exception occurs, flush() is called in the else block (after transaction commits)

    When used with FastAPI's session_scope():
    - async with session_scope() manages the DB transaction
    - async with message_sender_scope() manages message queueing
    - Both complete successfully → session commits, then messages flush
    - Either fails → both rollback, no messages sent

    Yields:
        MessageSender: A callable message sender instance

    Usage:
        async with message_sender_scope() as message_sender:
            await message_sender.enqueue(cluster_id, message)
            # Transaction completes...
        # Messages are sent here after successful completion
    """
    sender = MessageSender()
    try:
        yield sender
    except Exception:
        # Transaction failed, discard queued messages
        raise
    else:
        # Transaction succeeded, send all queued messages
        await sender.flush()


async def get_message_sender():
    """
    FastAPI dependency that provides a message sender with automatic flushing.

    Used as a dependency of get_session to enforce transactional ordering:
    - get_session depends on this, so message_sender is resolved first
    - Cleanup happens in reverse: session (commit) → message_sender (flush)
    - This ensures DB commits BEFORE messages are sent

    Yields:
        MessageSender: A message sender that flushes after endpoint completion
    """
    async with message_sender_scope() as sender:
        yield sender
