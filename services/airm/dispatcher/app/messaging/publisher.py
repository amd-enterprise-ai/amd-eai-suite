# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from aio_pika import abc

from airm.messaging.connector import get_connection_to_common_vhost as get_common_conn_and_chan
from airm.messaging.publisher import publish_message_to_queue
from airm.messaging.schemas import (
    Message,
)

from .config import (
    RABBITMQ_AIRM_COMMON_QUEUE,
    RABBITMQ_AIRM_COMMON_VHOST,
    RABBITMQ_HOST,
    RABBITMQ_PASSWORD,
    RABBITMQ_PORT,
    RABBITMQ_USER,
)


async def publish_to_common_feedback_queue(
    message: Message, connection: abc.AbstractConnection, channel: abc.AbstractChannel | None = None
):
    await publish_message_to_queue(connection, RABBITMQ_AIRM_COMMON_QUEUE, message.json(), RABBITMQ_USER, channel)


async def get_common_vhost_connection_and_channel():
    return await get_common_conn_and_chan(
        RABBITMQ_HOST,
        RABBITMQ_PORT,
        RABBITMQ_AIRM_COMMON_VHOST,
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )
