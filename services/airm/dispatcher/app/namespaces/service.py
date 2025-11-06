# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from uuid import UUID

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from loguru import logger

from airm.messaging.schemas import (
    NamespaceStatus,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceDeleteMessage,
    ProjectNamespaceStatusMessage,
)

from ..kubernetes.watcher import start_kubernetes_watcher
from ..messaging.publisher import get_common_vhost_connection_and_channel, publish_to_common_feedback_queue
from .constants import KUEUE_MANAGED_LABEL, PROJECT_ID_LABEL
from .utils import build_namespace_manifest


async def process_namespace_create(message: ProjectNamespaceCreateMessage):
    logger.info("Project namespace create handler received message")
    logger.debug(f"Processing ProjectNamespaceCreateMessage: {message}")
    try:
        namespace_manifest = build_namespace_manifest(name=message.name, project_id=message.project_id)

        client.CoreV1Api().create_namespace(body=namespace_manifest)

        logger.info(f"Created namespace: {message.name}")

    except Exception as e:
        logger.error(f"Failed to create namespace {message.name}: {e}")
        await _publish_namespace_status(message.project_id, NamespaceStatus.FAILED, f"Failed to create namespace: {e}")


async def process_namespace_delete(message: ProjectNamespaceDeleteMessage):
    logger.info("Project namespace delete handler received message")
    logger.debug(f"Processing ProjectNamespaceDeleteMessage: {message}")
    try:
        v1 = client.CoreV1Api()
        try:
            namespace = v1.read_namespace(name=message.name)
        except ApiException as e:
            if e.status == 404:
                await _publish_namespace_status(
                    message.project_id, NamespaceStatus.DELETED, "Project namespace not found"
                )
                return
            raise

        labels = namespace.metadata.labels or {}

        project_id_label = labels.get(PROJECT_ID_LABEL)
        if not project_id_label or project_id_label != str(message.project_id):
            await _publish_namespace_status(message.project_id, NamespaceStatus.DELETED, "Project namespace not found")
            return

        v1.delete_namespace(name=message.name)
        logger.info(f"Deleted namespace: {message.name}")
    except Exception as e:
        logger.error(f"Failed to delete namespace {message.name}: {e}")
        await _publish_namespace_status(
            message.project_id, NamespaceStatus.DELETE_FAILED, f"Failed to delete namespace: {e}"
        )


async def _publish_namespace_status(project_id: UUID, status: NamespaceStatus, reason: str):
    connection, channel = await get_common_vhost_connection_and_channel()
    await publish_to_common_feedback_queue(
        ProjectNamespaceStatusMessage(
            message_type="project_namespace_status",
            project_id=project_id,
            status=status,
            status_reason=reason,
        ),
        connection,
        channel,
    )
    logger.info(f"Published namespace status message to queue for project {project_id}")


async def __process_namespace_event(resource, event_type):
    try:
        namespace_name = resource.metadata.name
        labels = resource.metadata.labels or {}

        project_id = labels.get(PROJECT_ID_LABEL)
        if not project_id:
            return

        if event_type == "DELETED":
            status = NamespaceStatus.DELETED
            reason = "Namespace has been deleted"
        elif resource.status.phase == "Active":
            status = NamespaceStatus.ACTIVE
            reason = "Namespace is active"
        elif resource.status.phase == "Terminating":
            status = NamespaceStatus.TERMINATING
            reason = "Namespace is terminating"
        else:
            status = NamespaceStatus.FAILED
            reason = f"Unknown namespace phase: {resource.status.phase}"

        await _publish_namespace_status(project_id, status, reason)

    except Exception as e:
        logger.exception("Error processing namespace event", e)


def start_watching_namespace_components() -> asyncio.Task:
    async def __start_watching_namespace_components():
        await start_kubernetes_watcher(
            "namespace_watcher",
            client.CoreV1Api().list_namespace,
            __process_namespace_event,
            label_selector=f"{PROJECT_ID_LABEL},{KUEUE_MANAGED_LABEL}=true",
        )

    return asyncio.create_task(__start_watching_namespace_components())
