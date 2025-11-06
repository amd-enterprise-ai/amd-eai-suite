# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from fastapi import APIRouter, Depends, status

from airm.messaging.schemas import HeartbeatMessage

from ..messaging.publisher import get_common_vhost_connection_and_channel
from .service import publish_heartbeat_message_to_queue

router = APIRouter(tags=["Heartbeats"])


@router.post(
    "/heartbeats",
    operation_id="send_heartbeat_message",
    summary="Send heartbeat message",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=HeartbeatMessage,
)
async def send_heartbeat(conn=Depends(get_common_vhost_connection_and_channel)):
    connection, channel = conn
    message = await publish_heartbeat_message_to_queue(connection, channel)
    return message
