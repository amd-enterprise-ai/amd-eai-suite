# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from collections.abc import Callable

from loguru import logger

from airm.messaging.connector import init_connection


async def start_queue_consumer(
    host: str, port: int, vhost: str, queue_name: str, username: str, password: str, process_message: Callable
) -> None:
    connection = None
    channel = None
    try:
        connection, channel = await init_connection(host, port, vhost, username, password)
        await channel.set_qos(prefetch_count=1)
        queue = await channel.get_queue(queue_name)
        await queue.consume(process_message)
        logger.info(f"Waiting for messages from queue {queue_name}.")

        # Wait until terminate
        await asyncio.Future()
    finally:
        if channel and not channel.is_closed:
            await channel.close()
        if connection and not connection.is_closed:
            await connection.close()
