# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes.client.exceptions import ApiException

from airm.messaging.schemas import (
    ConfigMapStatus,
    ProjectS3StorageCreateMessage,
    ProjectStorageDeleteMessage,
    ProjectStorageStatus,
)
from app.storages.constants import PROJECT_STORAGE_ID_LABEL
from app.storages.service import (
    _process_configmap_event,
    _publish_s3_storage_status,
    process_project_s3_storage_create,
    process_project_storage_delete,
    process_storage_delete_error,
)


@pytest.mark.asyncio
@patch("app.storages.service.build_configmap_manifest")
@patch("app.storages.service.client.CoreV1Api.create_namespaced_config_map")
@patch("app.storages.service.logger")
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
async def test_process_project_s3_storage_create_success(
    mock_publish_status, mock_logger, mock_create_configmap, mock_build_manifest
):
    mock_build_manifest.return_value = {"metadata": {"name": "configmap"}}
    mock_create_configmap.return_value = MagicMock()
    message = ProjectS3StorageCreateMessage(
        message_type="project_s3_storage_create",
        project_storage_id=uuid4(),
        project_name="test-proj",
        storage_name="new-storage",
        secret_name="storage-credentials",
        secret_key_name="secret1",
        access_key_name="secret2",
        bucket_url="http://localhost:9001/browser/mybucket",
    )
    await process_project_s3_storage_create(message)
    mock_build_manifest.assert_called_once()
    mock_create_configmap.assert_called_once()
    mock_logger.info.assert_called_with(
        f"Created ConfigMap for S3 storage: {message.storage_name} in namespace: {message.project_name}"
    )
    mock_publish_status.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.storages.service.build_configmap_manifest")
@patch("app.storages.service.client.CoreV1Api.create_namespaced_config_map")
@patch("app.storages.service.logger")
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
async def test_process_project_s3_storage_create_failure(
    mock_publish_status, mock_logger, mock_create_configmap, mock_build_manifest
):
    mock_build_manifest.return_value = {"metadata": {"name": "configmap"}}
    mock_create_configmap.side_effect = Exception("ConfigMap error!")
    message = ProjectS3StorageCreateMessage(
        message_type="project_s3_storage_create",
        project_storage_id=uuid4(),
        project_name="test-proj",
        storage_name="new-storage",
        secret_name="storage-credentials",
        secret_key_name="secret1",
        access_key_name="secret2",
        bucket_url="http://localhost:9001/browser/mybucket",
    )
    await process_project_s3_storage_create(message)
    mock_logger.error.assert_called()
    mock_publish_status.assert_awaited_with(
        message.project_storage_id,
        ProjectStorageStatus.FAILED,
        "Failed to create ConfigMap: ConfigMap error!",
    )


@pytest.mark.asyncio
@patch("app.storages.service.get_common_vhost_connection_and_channel", new_callable=AsyncMock)
@patch("app.storages.service.publish_to_common_feedback_queue", new_callable=AsyncMock)
@patch("app.storages.service.logger")
async def test_publish_s3_storage_status(mock_logger, mock_publish, mock_get_conn):
    project_storage_id = uuid4()
    status = ConfigMapStatus.ADDED
    reason = "Test reason"
    mock_get_conn.return_value = ("conn", "chan")
    await _publish_s3_storage_status(project_storage_id, status, reason)
    mock_publish.assert_awaited()
    mock_logger.info.assert_called_with(f"Published S3 storage status message to queue {project_storage_id}")


@pytest.mark.asyncio
@patch("app.storages.service.get_status_for_config_map")
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
@patch("app.storages.service.logger")
async def test_process_configmap_event_added(mock_logger, mock_publish_status, mock_get_status):
    resource = MagicMock()
    resource.metadata = MagicMock()
    resource.metadata.labels = {"airm.silogen.ai/project-storage-id": "1234"}
    mock_get_status.return_value = (ConfigMapStatus.ADDED.value, "Added")
    await _process_configmap_event(resource, "ADDED")
    mock_publish_status.assert_awaited_with(
        "1234",
        "Added",
        "Added",
    )
    mock_logger.info.assert_called()


@pytest.mark.asyncio
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
@patch("app.storages.service.logger")
async def test_process_configmap_event_failed(mock_logger, mock_publish_status):
    resource = MagicMock()
    resource.metadata = MagicMock()
    resource.metadata.labels = {"airm.silogen.ai/project-storage-id": "1234"}
    await _process_configmap_event(resource, "MODIFIED")
    mock_publish_status.assert_not_awaited()
    mock_logger.info.assert_not_called()


@pytest.mark.asyncio
@patch("app.storages.service.logger")
async def test_process_configmap_event_missing_metadata(mock_logger):
    resource = MagicMock()
    resource.metadata = None
    await _process_configmap_event(resource, "ADDED")
    mock_logger.warning.assert_called_with("ConfigMap event missing metadata")


@pytest.mark.asyncio
@patch("app.storages.service.logger")
async def test_process_configmap_event_missing_label(mock_logger):
    resource = MagicMock()
    resource.metadata = MagicMock()
    resource.metadata.labels = {}
    await _process_configmap_event(resource, "ADDED")
    mock_logger.warning.assert_called_with("ConfigMap event missing required labels: project_storage_id")


@pytest.mark.asyncio
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
@patch("app.storages.service.logger")
async def test_process_storage_delete_error_sync(mock_logger, mock_publish_status):
    api_resource = MagicMock()
    api_resource.kind = "ConfigMap"
    delete_err = ApiException("delete failed")
    item = {"metadata": {"labels": {"airm.silogen.ai/project-storage-id": str(uuid4())}}}

    await process_storage_delete_error(api_resource, delete_err, item)

    mock_logger.error.assert_called()
    mock_publish_status.assert_awaited()


@pytest.mark.asyncio
@patch("app.storages.service.delete_resources_by_label", new_callable=AsyncMock)
@patch("app.storages.service.logger")
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
async def test_process_project_storage_delete_success(
    mock_delete_resources,
    mock_logger,
    mock_publish_status,
):
    mock_delete_resources.return_value = True
    message = ProjectStorageDeleteMessage(
        message_type="project_storage_delete",
        project_storage_id=uuid4(),
        project_name="test-proj",
        storage_name="test-storage",
    )
    await process_project_storage_delete(message)
    mock_delete_resources.assert_awaited()
    mock_logger.warning.assert_not_called()
    mock_publish_status.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.storages.service.delete_resources_by_label", new_callable=AsyncMock)
@patch("app.storages.service.logger")
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
@patch("app.storages.service.client.ApiClient")
@patch("app.storages.service.DynamicClient")
async def test_process_project_storage_delete_none_found(
    mock_dynamic_client,
    mock_api_client,
    mock_publish_status,
    mock_logger,
    mock_delete_resources,
):
    mock_k8s_client = MagicMock()
    mock_api_client.return_value = mock_k8s_client
    mock_dynamic_client.return_value = MagicMock()

    mock_delete_resources.return_value = False
    message = ProjectStorageDeleteMessage(
        message_type="project_storage_delete",
        project_storage_id=uuid4(),
        project_name="test-proj",
        storage_name="test-storage",
    )
    label_selector = f"{PROJECT_STORAGE_ID_LABEL}={message.project_storage_id}"
    await process_project_storage_delete(message)
    mock_delete_resources.assert_awaited()
    mock_logger.warning.assert_called_with(f"No ConfigMaps found with label selector '{label_selector}'")
    mock_publish_status.assert_awaited_with(
        message.project_storage_id,
        ProjectStorageStatus.DELETED,
        f"No ConfigMaps found for deletion: {label_selector}",
    )


@pytest.mark.asyncio
@patch("app.storages.service.delete_resources_by_label", side_effect=Exception("delete error"))
@patch("app.storages.service._publish_s3_storage_status", new_callable=AsyncMock)
@patch("app.storages.service.logger")
async def test_process_project_storage_delete_exception(mock_logger, mock_publish_status, mock_delete_resources):
    message = ProjectStorageDeleteMessage(
        message_type="project_storage_delete",
        project_storage_id=uuid4(),
        project_name="test-proj",
        storage_name="test-storage",
    )
    await process_project_storage_delete(message)
    mock_publish_status.assert_awaited()
    mock_logger.exception.assert_called()
