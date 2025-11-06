# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import urllib.parse
from uuid import UUID

from aio_pika import abc, connect_robust
from loguru import logger

__connection_to_common_vhost: abc.AbstractConnection | None = None
__channel_for_common_vhost: abc.AbstractChannel | None = None

__cluster_connections: dict[UUID, tuple[abc.AbstractConnection, abc.AbstractChannel]] = {}


async def init_connection(
    host: str, port: int, vhost: str, username: str, password: str
) -> tuple[abc.AbstractConnection, abc.AbstractChannel]:
    encoded_vhost = urllib.parse.quote(vhost, safe="")
    url = f"amqp://{username}:{password}@{host}:{port}/{encoded_vhost}"
    connection = await connect_robust(url)
    channel = await connection.channel()

    return connection, channel


async def get_connection_to_common_vhost(
    host: str, port: int, vhost: str, username: str, password: str
) -> tuple[abc.AbstractConnection, abc.AbstractChannel]:
    global __connection_to_common_vhost, __channel_for_common_vhost

    common_connection_open = __connection_to_common_vhost and not __connection_to_common_vhost.is_closed
    common_channel_open = __channel_for_common_vhost and not __channel_for_common_vhost.is_closed

    if common_connection_open and common_channel_open:
        logger.info("Reusing existing RabbitMQ common connection")
        return __connection_to_common_vhost, __channel_for_common_vhost
    else:
        logger.info("Channel is not open, creating a new connection and channel")
        __connection_to_common_vhost, __channel_for_common_vhost = await init_connection(
            host, port, vhost, username, password
        )
        logger.info(f"Connected to RabbitMQ with url {host}:{port}")
        return __connection_to_common_vhost, __channel_for_common_vhost


async def get_connection_to_cluster_vhost(
    cluster_id: UUID, host: str, port: int, username: str, password: str
) -> tuple[abc.AbstractConnection, abc.AbstractChannel]:
    user_vhost = f"vh_{cluster_id}"

    if cluster_id in __cluster_connections:
        connection, channel = __cluster_connections[cluster_id]
        if not connection.is_closed and not channel.is_closed:
            logger.info(f"Reusing existing RabbitMQ connection for cluster_id {cluster_id}")
            return connection, channel

    connection, channel = await init_connection(host, port, user_vhost, username, password)
    if connection:
        logger.info(f"Connected to RabbitMQ with url {host}:{port}")
        __cluster_connections[cluster_id] = (connection, channel)

    return connection, channel


async def delete_connection_to_cluster_vhost(cluster_id: UUID) -> None:
    global __cluster_connections

    try:
        if cluster_id in __cluster_connections:
            connection, channel = __cluster_connections[cluster_id]
            await connection.close()
            await channel.close()
            del __cluster_connections[cluster_id]
            logger.info(f"Closed RabbitMQ connection for cluster_id {cluster_id}")
        else:
            logger.warning(f"No RabbitMQ connection found for cluster_id {cluster_id}")
    except Exception as e:
        logger.error(f"Error closing RabbitMQ connection for cluster_id {cluster_id}: {e}")
