# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from fastapi import APIRouter, Depends, status

from ..messaging.publisher import get_common_vhost_connection_and_channel
from .service import publish_cluster_nodes_message_to_queue

router = APIRouter(tags=["Clusters"])


@router.post(
    "/clusters/nodes",
    operation_id="send_cluster_nodes",
    summary="Send cluster nodes",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def send_cluster_nodes(conn=Depends(get_common_vhost_connection_and_channel)):
    connection, channel = conn
    await publish_cluster_nodes_message_to_queue(connection, channel)
