# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from aio_pika import DeliveryMode, Message, abc


async def publish_message_to_queue(
    connection: abc.AbstractConnection,
    queue_name: str,
    message_body: str,
    user_id: str,
    channel: abc.AbstractChannel | None = None,
) -> None:
    if channel is None:
        channel = await connection.channel()
    message = Message(
        message_body.encode("utf-8"),
        delivery_mode=DeliveryMode.PERSISTENT,
        user_id=user_id,
    )
    await channel.default_exchange.publish(
        message,
        routing_key=queue_name,
    )
