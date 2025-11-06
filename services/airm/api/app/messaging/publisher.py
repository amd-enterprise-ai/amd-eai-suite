# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from airm.messaging.connector import get_connection_to_cluster_vhost
from airm.messaging.publisher import publish_message_to_queue
from airm.messaging.schemas import ClusterQuotaAllocation, ClusterQuotasAllocationMessage, GPUVendor, Message

from ..clusters.constants import DEFAULT_PRIORITY_CLASSES
from .config import RABBITMQ_ADMIN_PASSWORD, RABBITMQ_ADMIN_USER, RABBITMQ_HOST, RABBITMQ_PORT


async def submit_message_to_cluster_queue(cluster_id: UUID, message: Message):
    connection, channel = await get_connection_to_cluster_vhost(
        cluster_id, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD
    )
    await publish_message_to_queue(connection, f"{cluster_id}", message.json(), RABBITMQ_ADMIN_USER, channel)


async def submit_quotas_allocation_to_cluster_queue(
    quota_allocations: list[ClusterQuotaAllocation], cluster_id: UUID, gpu_vendor: GPUVendor | None
):
    message = ClusterQuotasAllocationMessage(
        message_type="cluster_quotas_allocation",
        gpu_vendor=gpu_vendor,
        quota_allocations=quota_allocations,
        priority_classes=DEFAULT_PRIORITY_CLASSES,
    )

    connection, channel = await get_connection_to_cluster_vhost(
        cluster_id, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_ADMIN_USER, RABBITMQ_ADMIN_PASSWORD
    )
    await publish_message_to_queue(connection, f"{cluster_id}", message.json(), RABBITMQ_ADMIN_USER, channel)
