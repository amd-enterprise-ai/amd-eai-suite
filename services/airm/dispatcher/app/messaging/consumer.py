# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from asyncio import Task

from aio_pika import abc
from loguru import logger

from airm.messaging.consumer import start_queue_consumer
from airm.messaging.schemas import (
    ClusterQuotasAllocationMessage,
    DeleteWorkloadMessage,
    MessageAdapter,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceDeleteMessage,
    ProjectS3StorageCreateMessage,
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectStorageDeleteMessage,
    WorkloadMessage,
)

from ..namespaces.service import process_namespace_create, process_namespace_delete
from ..quotas.service import process_cluster_quotas_allocation
from ..secrets.service import process_project_secrets_create, process_project_secrets_delete
from ..storages.service import process_project_s3_storage_create, process_project_storage_delete
from ..workloads.service import process_delete_workload, process_workload
from .config import (
    RABBITMQ_AIRM_CLUSTER_INBOUND_QUEUE,
    RABBITMQ_AIRM_CLUSTER_VHOST,
    RABBITMQ_HOST,
    RABBITMQ_PASSWORD,
    RABBITMQ_PORT,
    RABBITMQ_USER,
)


async def __process_message(message: abc.AbstractIncomingMessage) -> None:
    try:
        async with message.process(requeue=True):
            str_json = message.body.decode()
            message_body = MessageAdapter.validate_json(str_json)

            if isinstance(message_body, WorkloadMessage):
                await process_workload(message_body)
            elif isinstance(message_body, ClusterQuotasAllocationMessage):
                await process_cluster_quotas_allocation(message_body)
            elif isinstance(message_body, DeleteWorkloadMessage):
                await process_delete_workload(message_body)
            elif isinstance(message_body, ProjectSecretsCreateMessage):
                await process_project_secrets_create(message_body)
            elif isinstance(message_body, ProjectSecretsDeleteMessage):
                await process_project_secrets_delete(message_body)
            elif isinstance(message_body, ProjectNamespaceCreateMessage):
                await process_namespace_create(message_body)
            elif isinstance(message_body, ProjectNamespaceDeleteMessage):
                await process_namespace_delete(message_body)
            elif isinstance(message_body, ProjectS3StorageCreateMessage):
                await process_project_s3_storage_create(message_body)
            elif isinstance(message_body, ProjectStorageDeleteMessage):
                await process_project_storage_delete(message_body)
            else:
                logger.warning(f"Received unexpected message type: {str_json}")
    except Exception as e:
        logger.exception("Error processing message", e)


def start_consuming_from_message_queue() -> Task:
    return asyncio.create_task(
        start_queue_consumer(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            vhost=RABBITMQ_AIRM_CLUSTER_VHOST,
            queue_name=RABBITMQ_AIRM_CLUSTER_INBOUND_QUEUE,
            username=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD,
            process_message=__process_message,
        ),
        name="mq_message_consumer",
    )
