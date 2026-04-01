# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from asyncio import Task
from collections.abc import Callable

from aio_pika import abc
from loguru import logger
from starlette.datastructures import State

from ..clusters.repository import get_cluster_by_id
from ..clusters.service import delete_cluster_node, update_cluster_node, update_cluster_nodes, update_last_heartbeat
from ..messaging.schemas import (
    AutoDiscoveredSecretMessage,
    AutoDiscoveredWorkloadComponentMessage,
    ClusterNodeDeleteMessage,
    ClusterNodesMessage,
    ClusterNodeUpdateMessage,
    ClusterQuotasFailureMessage,
    ClusterQuotasStatusMessage,
    HeartbeatMessage,
    MessageAdapter,
    NamespaceDeletedMessage,
    ProjectNamespaceStatusMessage,
    ProjectSecretsUpdateMessage,
    ProjectStorageUpdateMessage,
    UnmanagedNamespaceMessage,
    WorkloadComponentStatusMessage,
    WorkloadStatusMessage,
)
from ..namespaces.service import handle_namespace_deleted, record_unmanaged_namespace, update_project_namespace_status
from ..quotas.service import update_cluster_quotas_from_allocations, update_pending_quotas_to_failed
from ..secrets.service import register_auto_discovered_secret, update_project_secret_status
from ..storages.service import update_configmap_status
from ..utilities.database import session_scope
from ..utilities.keycloak_admin import get_kc_admin_client_from_state
from ..workloads.service import (
    register_auto_discovered_workload_component,
    update_workload_component_status,
    update_workload_status,
)
from .config import (
    RABBITMQ_ADMIN_PASSWORD,
    RABBITMQ_ADMIN_USER,
    RABBITMQ_AIRM_COMMON_QUEUE,
    RABBITMQ_AIRM_COMMON_VHOST,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
)
from .connector import init_connection
from .sender import message_sender_scope


async def start_queue_consumer(
    host: str, port: int, vhost: str, queue_name: str, username: str, password: str, process_message: Callable
) -> None:
    connection = None
    channel = None
    try:
        connection, channel = await init_connection(host, port, vhost, username, password)
        await channel.set_qos(prefetch_count=1)
        queue = await channel.get_queue(queue_name)
        await queue.consume(process_message)
        logger.info(f"Waiting for messages from queue {queue_name}.")

        # Wait until terminate
        await asyncio.Future()
    finally:
        if channel and not channel.is_closed:
            await channel.close()
        if connection and not connection.is_closed:
            await connection.close()


async def __process_message(message: abc.AbstractIncomingMessage, app_state: State) -> None:
    try:
        async with message.process(requeue=True), message_sender_scope() as message_sender, session_scope() as session:
            str_json = message.body.decode()
            logger.info(f"Message Received {RABBITMQ_AIRM_COMMON_QUEUE} {str_json}")
            message_body = MessageAdapter.validate_json(str_json)
            if message.user_id is None:
                logger.warning("Cluster did not authenticate when sending a request")
                return

            cluster = await get_cluster_by_id(session, message.user_id)
            if cluster is None:
                logger.warning(f"Cluster with ID {message.user_id} was not found.")
                return

            if isinstance(message_body, HeartbeatMessage):
                await update_last_heartbeat(session, cluster=cluster, message=message_body)
            elif isinstance(message_body, WorkloadStatusMessage):
                await update_workload_status(session, cluster=cluster, workload_status=message_body)
            elif isinstance(message_body, ClusterNodesMessage):
                await update_cluster_nodes(
                    session, cluster=cluster, message=message_body, message_sender=message_sender
                )
            elif isinstance(message_body, ClusterNodeUpdateMessage):
                await update_cluster_node(session, cluster=cluster, message=message_body, message_sender=message_sender)
            elif isinstance(message_body, ClusterNodeDeleteMessage):
                await delete_cluster_node(session, cluster=cluster, message=message_body, message_sender=message_sender)
            elif isinstance(message_body, ClusterQuotasStatusMessage):
                await update_cluster_quotas_from_allocations(
                    kc_admin=get_kc_admin_client_from_state(app_state),
                    session=session,
                    cluster=cluster,
                    message=message_body,
                )
            elif isinstance(message_body, ClusterQuotasFailureMessage):
                await update_pending_quotas_to_failed(
                    kc_admin=get_kc_admin_client_from_state(app_state),
                    session=session,
                    cluster=cluster,
                    message=message_body,
                )
            elif isinstance(message_body, WorkloadComponentStatusMessage):
                await update_workload_component_status(session, cluster=cluster, message=message_body)
            elif isinstance(message_body, ProjectSecretsUpdateMessage):
                await update_project_secret_status(session, cluster=cluster, message=message_body)
            elif isinstance(message_body, ProjectNamespaceStatusMessage):
                await update_project_namespace_status(
                    kc_admin=get_kc_admin_client_from_state(app_state),
                    session=session,
                    cluster=cluster,
                    message=message_body,
                )
            elif isinstance(message_body, UnmanagedNamespaceMessage):
                await record_unmanaged_namespace(session, cluster=cluster, message=message_body)
            elif isinstance(message_body, NamespaceDeletedMessage):
                await handle_namespace_deleted(
                    kc_admin=get_kc_admin_client_from_state(app_state),
                    session=session,
                    cluster=cluster,
                    message=message_body,
                )
            elif isinstance(message_body, AutoDiscoveredWorkloadComponentMessage):
                await register_auto_discovered_workload_component(session, cluster=cluster, message=message_body)
            elif isinstance(message_body, AutoDiscoveredSecretMessage):
                await register_auto_discovered_secret(session, cluster=cluster, message=message_body)
            elif isinstance(message_body, ProjectStorageUpdateMessage):
                await update_configmap_status(session, cluster=cluster, message=message_body)
            else:
                raise Exception(f"Received unexpected message type: {str_json}")
    except Exception as e:
        logger.exception("Error processing message", e)


def start_consuming_from_common_feedback_queue(app_state: State) -> Task:
    return asyncio.create_task(
        start_queue_consumer(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            vhost=RABBITMQ_AIRM_COMMON_VHOST,
            queue_name=RABBITMQ_AIRM_COMMON_QUEUE,
            username=RABBITMQ_ADMIN_USER,
            password=RABBITMQ_ADMIN_PASSWORD,
            process_message=lambda message: __process_message(message, app_state=app_state),
        ),
        name="mq_message_consumer",
    )
