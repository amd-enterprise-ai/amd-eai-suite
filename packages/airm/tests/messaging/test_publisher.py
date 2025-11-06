# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio

import pytest
from aio_pika.exceptions import ChannelPreconditionFailed

from airm.messaging.connector import init_connection
from airm.messaging.publisher import publish_message_to_queue
from airm.messaging.queues import configure_queues


@pytest.mark.asyncio
async def test_publish_message_incorrect_user(rabbitmq_service):
    docker_ip, port = rabbitmq_service
    queue_name = "test_queue"

    connection, channel = await init_connection(docker_ip, port, "vh_airm_common", "guest", "guest")
    await configure_queues(channel, queue_name)

    # Allow consumer to initialize
    await asyncio.sleep(1)

    with pytest.raises(ChannelPreconditionFailed) as exc_info:
        await publish_message_to_queue(connection, queue_name, "test message", "new_user", channel)

    assert "user_id property set to" in str(exc_info.value)
    await connection.close()
