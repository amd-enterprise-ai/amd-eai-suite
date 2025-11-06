# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio

import pytest

from airm.messaging.connector import init_connection
from airm.messaging.constants import DEAD_LETTER_QUEUE_NAME
from airm.messaging.consumer import start_queue_consumer
from airm.messaging.publisher import publish_message_to_queue
from airm.messaging.queues import configure_queues


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
