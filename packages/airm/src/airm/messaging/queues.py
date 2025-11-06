# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from aio_pika import abc

from airm.messaging.constants import (
    DEAD_LETTER_EXCHANGE,
    DEAD_LETTER_QUEUE_NAME,
    DEAD_LETTER_ROUTING_KEY,
    DEFAULT_QUEUE_ARGUMENTS,
)


async def configure_queues(channel: abc.AbstractChannel, queue_name: str):
    await __configure_dead_letter_queue(channel)
    await __configure_message_queue(channel, queue_name)


async def __configure_dead_letter_queue(channel):
    dl_exchange = await channel.declare_exchange(DEAD_LETTER_EXCHANGE, "direct")
    dl_queue = await channel.declare_queue(DEAD_LETTER_QUEUE_NAME, durable=True, auto_delete=False)
    await dl_queue.bind(dl_exchange, DEAD_LETTER_ROUTING_KEY)


async def __configure_message_queue(channel: abc.AbstractChannel, queue_name: str):
    await channel.declare_queue(queue_name, durable=True, auto_delete=False, arguments=DEFAULT_QUEUE_ARGUMENTS)
