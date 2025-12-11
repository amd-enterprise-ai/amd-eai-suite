# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic import DynamicClient
from loguru import logger

from airm.messaging.schemas import (
    ConfigMapStatus,
    ProjectS3StorageCreateMessage,
    ProjectStorageDeleteMessage,
    ProjectStorageUpdateMessage,
)
from app.kubernetes.generic_watchers import start_generic_configmap_watcher

from ..kubernetes.utils import delete_resources_by_label
from ..messaging.publisher import get_common_vhost_connection_and_channel, publish_to_common_feedback_queue
from ..utilities.attribute_utils import extract_label_id
from ..workloads.utils import get_status_for_config_map
from .constants import PROJECT_STORAGE_ID_LABEL
from .utils import build_configmap_manifest


async def process_project_s3_storage_create(message: ProjectS3StorageCreateMessage) -> None:
    logger.info("Project S3 storage create handler received message")
    logger.debug(f"Processing ProjectS3StorageCreateMessage: {message}")
    try:
        configmap_manifest = build_configmap_manifest(
            name=f"{message.storage_name}-info-config-map",
            namespace=message.project_name,
            bucket_url=message.bucket_url,
            project_storage_id=message.project_storage_id,
            secret_key_name=message.secret_key_name,
            access_key_name=message.access_key_name,
            secret_name=message.secret_name,
        )
        client.CoreV1Api().create_namespaced_config_map(namespace=message.project_name, body=configmap_manifest)
        logger.info(f"Created ConfigMap for S3 storage: {message.storage_name} in namespace: {message.project_name}")
    except Exception as e:
        logger.error(f"Failed to create ConfigMap for S3 storage {message.storage_name}: {e}")
        await _publish_s3_storage_status(
            message.project_storage_id, ConfigMapStatus.FAILED, f"Failed to create ConfigMap: {e}"
        )
        return


async def process_storage_delete_error(api_resource: Any, delete_err: ApiException, item: dict) -> None:
    project_storage_id = extract_label_id(item, PROJECT_STORAGE_ID_LABEL)

    status_reason = f"Deletion failed for resource {getattr(api_resource, 'kind', str(api_resource))} project_storage_id={project_storage_id}: {delete_err}"
    logger.error(f"{status_reason}\nException: {delete_err}")

    if project_storage_id:
        await _publish_s3_storage_status(
            project_storage_id,
            ConfigMapStatus.FAILED,
            status_reason,
        )


async def process_project_storage_delete(message: ProjectStorageDeleteMessage) -> None:
    logger.info("Project storage delete handler received message")
    logger.debug(f"Processing ProjectStorageDeleteMessage: {message}")
    label_selector = f"{PROJECT_STORAGE_ID_LABEL}={message.project_storage_id}"

    try:
        k8s_client = client.ApiClient()
        dynamic_client = DynamicClient(k8s_client)

        allowed_kinds = ["ConfigMap"]
        deleted_any = await delete_resources_by_label(
            dynamic_client,
            label_selector,
            allowed_kinds,
            process_storage_delete_error,
            message.project_name,
        )

        if not deleted_any:
            logger.warning(f"No ConfigMaps found with label selector '{label_selector}'")
            await _publish_s3_storage_status(
                message.project_storage_id,
                ConfigMapStatus.DELETED,
                f"No ConfigMaps found for deletion: {label_selector}",
            )

    except Exception as ex:
        await _publish_s3_storage_status(
            message.project_storage_id,
            ConfigMapStatus.FAILED,
            f"Error deleting ConfigMap with label '{label_selector}': {ex}",
        )
        logger.exception(f"Error deleting ConfigMap with label '{label_selector}' : {ex}")


async def _publish_s3_storage_status(project_storage_id: UUID, status: ConfigMapStatus, reason: str) -> None:
    connection, channel = await get_common_vhost_connection_and_channel()
    await publish_to_common_feedback_queue(
        ProjectStorageUpdateMessage(
            message_type="project_storage_update",
            project_storage_id=project_storage_id,
            status=status,
            status_reason=reason,
            updated_at=datetime.now(UTC),
        ),
        connection,
        channel,
    )
    logger.info(f"Published S3 storage status message to queue {project_storage_id}")


async def _process_configmap_event(resource, event_type):
    try:
        metadata = getattr(resource, "metadata", None)
        if not metadata:
            logger.warning("ConfigMap event missing metadata")
            return

        labels = getattr(metadata, "labels", {}) or {}
        project_storage_id = labels.get(PROJECT_STORAGE_ID_LABEL)
        if not project_storage_id:
            logger.warning("ConfigMap event missing required labels: project_storage_id")
            return

        status, status_reason = get_status_for_config_map(resource, event_type)

        if status:
            await _publish_s3_storage_status(
                project_storage_id,
                status,
                status_reason,
            )
            logger.info(
                f"Published S3 storage status for project_storage_id={project_storage_id}, status={status}, reason={status_reason}"
            )

    except Exception as e:
        logger.exception("Error processing ConfigMap event", e)


def start_watching_storages_components() -> asyncio.Task:
    async def __start_watching_storages_components():
        await start_generic_configmap_watcher(
            callback=_process_configmap_event,
            component_name="storages",
            label_selector=PROJECT_STORAGE_ID_LABEL,
        )

    return asyncio.create_task(__start_watching_storages_components())
