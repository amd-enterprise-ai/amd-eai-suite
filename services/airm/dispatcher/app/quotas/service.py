# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import UTC, datetime

from kubernetes import client
from kubernetes.utils import create_from_dict
from loguru import logger

from airm.messaging.schemas import (
    ClusterQuotasAllocationMessage,
    ClusterQuotasFailureMessage,
    ClusterQuotasStatusMessage,
)

from ..kubernetes.watcher import get_installed_version_for_custom_resource, start_kubernetes_watcher
from ..messaging.publisher import get_common_vhost_connection_and_channel, publish_to_common_feedback_queue
from .constants import KAIWO_RESOURCE_API_GROUP, KAIWO_RESOURCE_PLURAL
from .schemas import KaiwoQueueConfig
from .utils import convert_to_cluster_quotas_allocations, convert_to_kaiwo_queue_config


async def process_cluster_quotas_allocation(message: ClusterQuotasAllocationMessage):
    logger.info("Cluster quotas allocation handler received message")
    logger.debug(f"Processing ClusterQuotasAllocationMessage: {message}")
    kaiwo_queue_config = convert_to_kaiwo_queue_config(message)

    k8s_client = client.ApiClient()
    try:
        create_from_dict(k8s_client, kaiwo_queue_config.model_dump(), apply=True, namespace=None, force_conflicts=True)
    except Exception as e:
        logger.exception("Failed to create manifest due to error", e)
        await __publish_quotas_failure_message(reason=f"Failed to create manifest: {e}")


async def __process_kaiwo_queue_config_event(resource, event_type):
    message = ClusterQuotasStatusMessage(
        message_type="cluster_quotas_status",
        updated_at=datetime.now(UTC),
        quota_allocations=[],
    )
    status = resource.get("status", {}).get("status", None)
    if event_type == "DELETED":
        await __publish_quotas_allocations_status_message(message)
    elif status == "READY":
        quotas = convert_to_cluster_quotas_allocations(KaiwoQueueConfig.model_validate(resource))
        message.quota_allocations = quotas
        await __publish_quotas_allocations_status_message(message)
    elif status == "FAILED":
        await __publish_quotas_failure_message()


async def __publish_quotas_allocations_status_message(message: ClusterQuotasStatusMessage):
    connection, channel = await get_common_vhost_connection_and_channel()
    await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)
    logger.info(f"Published quotas allocation status message to queue {message.json()}")


async def __publish_quotas_failure_message(reason: str | None = None):
    connection, channel = await get_common_vhost_connection_and_channel()
    message = ClusterQuotasFailureMessage(
        message_type="cluster_quotas_failure",
        updated_at=datetime.now(UTC),
        reason=reason,
    )
    await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)
    logger.info(f"Published quotas failure message to queue {message.json()}")


def start_watching_kaiwo_queue_config() -> asyncio.Task:
    async def __start_watching_workload_components():
        await start_kubernetes_watcher(
            "kaiwo_queue_config_watcher",
            client.CustomObjectsApi().list_cluster_custom_object,
            __process_kaiwo_queue_config_event,
            group=KAIWO_RESOURCE_API_GROUP,
            version=get_installed_version_for_custom_resource(client, KAIWO_RESOURCE_API_GROUP, KAIWO_RESOURCE_PLURAL),
            plural=KAIWO_RESOURCE_PLURAL,
        )

    return asyncio.create_task(__start_watching_workload_components())
