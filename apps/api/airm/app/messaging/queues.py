# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from aio_pika import abc
from loguru import logger

from ..messaging.connector import get_connection_to_cluster_vhost, get_connection_to_common_vhost
from .config import (
    RABBITMQ_ADMIN_PASSWORD,
    RABBITMQ_ADMIN_USER,
    RABBITMQ_AIRM_COMMON_QUEUE,
    RABBITMQ_AIRM_COMMON_VHOST,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
)
from .constants import DEAD_LETTER_EXCHANGE, DEAD_LETTER_QUEUE_NAME, DEAD_LETTER_ROUTING_KEY, DEFAULT_QUEUE_ARGUMENTS


async def configure_queues(channel: abc.AbstractChannel, queue_name: str) -> None:
    await __configure_dead_letter_queue(channel)
    await __configure_message_queue(channel, queue_name)


async def __configure_dead_letter_queue(channel: abc.AbstractChannel) -> None:
    dl_exchange = await channel.declare_exchange(DEAD_LETTER_EXCHANGE, "direct")
    dl_queue = await channel.declare_queue(DEAD_LETTER_QUEUE_NAME, durable=True, auto_delete=False)
    await dl_queue.bind(dl_exchange, DEAD_LETTER_ROUTING_KEY)


async def __configure_message_queue(channel: abc.AbstractChannel, queue_name: str) -> None:
    await channel.declare_queue(queue_name, durable=True, auto_delete=False, arguments=DEFAULT_QUEUE_ARGUMENTS)


async def configure_queues_for_cluster(cluster_id):
    logger.info(f"Configuring queue for cluster: {cluster_id}")
    connection, channel = await get_connection_to_cluster_vhost(
        cluster_id, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD
    )
    logger.info(f"Connection: {connection}, Channel: {channel}")
    await configure_queues(channel, f"{cluster_id}")
    logger.info(f"Sucessfully connected to: {cluster_id}")


async def configure_queues_for_common_vhost():
    logger.info("Configuring queues for common_vhost")
    connection, channel = await get_connection_to_common_vhost(
        RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_AIRM_COMMON_VHOST, RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD
    )
    logger.info(f"Connection: {connection}, Channel: {channel}")
    await configure_queues(channel, RABBITMQ_AIRM_COMMON_QUEUE)
    logger.info(f"Sucessfully connected to: {RABBITMQ_AIRM_COMMON_QUEUE}")
