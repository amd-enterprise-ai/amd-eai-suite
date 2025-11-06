# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from loguru import logger

from airm.messaging.connector import get_connection_to_cluster_vhost, get_connection_to_common_vhost
from airm.messaging.queues import configure_queues

from .config import (
    RABBITMQ_ADMIN_PASSWORD,
    RABBITMQ_ADMIN_USER,
    RABBITMQ_AIRM_COMMON_QUEUE,
    RABBITMQ_AIRM_COMMON_VHOST,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
)


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
