# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

from aio_pika import abc

from airm.messaging.schemas import HeartbeatMessage

from ..config.app_config import AppConfig
from ..messaging.publisher import publish_to_common_feedback_queue


async def publish_heartbeat_message_to_queue(
    connection: abc.AbstractConnection, channel: abc.AbstractChannel | None = None
) -> HeartbeatMessage:
    config = AppConfig()
    cluster_name = config.get_cluster_name()
    org_name = config.get_org_name()

    message = HeartbeatMessage(
        message_type="heartbeat",
        last_heartbeat_at=datetime.now(UTC),
        cluster_name=cluster_name,
        organization_name=org_name,
    )
    await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)
    return message
