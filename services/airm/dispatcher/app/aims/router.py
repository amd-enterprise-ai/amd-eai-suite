# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from fastapi import APIRouter, Depends, status

from ..messaging.publisher import get_common_vhost_connection_and_channel
from .service import publish_aim_cluster_models_message_to_queue

router = APIRouter(tags=["AIMs"])


@router.post(
    "/aims/cluster-models",
    operation_id="send_aim_cluster_models",
    summary="Send AIM cluster models",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def send_aim_cluster_models(conn=Depends(get_common_vhost_connection_and_channel)):
    connection, channel = conn
    await publish_aim_cluster_models_message_to_queue(connection, channel)
