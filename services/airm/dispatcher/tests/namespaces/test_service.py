# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from asyncio import CancelledError
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes.client.exceptions import ApiException

from airm.messaging.schemas import (
    NamespaceStatus,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceDeleteMessage,
    ProjectNamespaceStatusMessage,
)
from app.namespaces.constants import KUEUE_MANAGED_LABEL, PROJECT_ID_LABEL
from app.namespaces.service import (
    __process_namespace_event,
    _publish_namespace_status,
    process_namespace_create,
    process_namespace_delete,
    start_watching_namespace_components,
)


@pytest.mark.asyncio
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_create_success(mock_core_v1_api):
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance

    message = ProjectNamespaceCreateMessage(
        message_type="project_namespace_create", name="test-namespace", project_id=uuid4()
    )

    await process_namespace_create(message)

    mock_core_v1_api.assert_called_once()
    mock_api_instance.create_namespace.assert_called_once()

    call_args = mock_api_instance.create_namespace.call_args
    manifest = call_args.kwargs["body"]

    assert manifest["apiVersion"] == "v1"
    assert manifest["kind"] == "Namespace"
    assert manifest["metadata"]["name"] == "test-namespace"
    assert manifest["metadata"]["labels"][PROJECT_ID_LABEL] == str(message.project_id)
    assert manifest["metadata"]["labels"][KUEUE_MANAGED_LABEL] == "true"


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_create_failure(mock_core_v1_api, mock_publish_status):
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance
    mock_api_instance.create_namespace.side_effect = ApiException("Namespace already exists")

    message = ProjectNamespaceCreateMessage(
        message_type="project_namespace_create", name="test-namespace", project_id=uuid4()
    )

    await process_namespace_create(message)

    mock_publish_status.assert_called_once_with(
        message.project_id,
        NamespaceStatus.FAILED,
        "Failed to create namespace: (Namespace already exists)\nReason: None\n",
    )


@pytest.mark.asyncio
@patch("app.namespaces.service.get_common_vhost_connection_and_channel")
@patch("app.namespaces.service.publish_to_common_feedback_queue")
async def test_publish_namespace_status(mock_publish_queue, mock_get_connection):
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_get_connection.return_value = (mock_connection, mock_channel)
    project_id = uuid4()

    await _publish_namespace_status(project_id, NamespaceStatus.ACTIVE, "Namespace ready")

    mock_get_connection.assert_called_once()
    mock_publish_queue.assert_called_once()

    call_args = mock_publish_queue.call_args
    message = call_args[0][0]

    assert isinstance(message, ProjectNamespaceStatusMessage)
    assert message.message_type == "project_namespace_status"
    assert message.project_id == project_id
    assert message.status == NamespaceStatus.ACTIVE
    assert message.status_reason == "Namespace ready"


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
async def test_process_namespace_event_active_namespace(mock_publish_status):
    mock_resource = MagicMock()
    mock_resource.metadata.name = "test-namespace"
    mock_resource.metadata.labels = {PROJECT_ID_LABEL: "12345"}
    mock_resource.status.phase = "Active"

    await __process_namespace_event(mock_resource, "MODIFIED")

    mock_publish_status.assert_called_once_with("12345", NamespaceStatus.ACTIVE, "Namespace is active")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
async def test_process_namespace_event_terminating_namespace(mock_publish_status):
    mock_resource = MagicMock()
    mock_resource.metadata.name = "test-namespace"
    mock_resource.metadata.labels = {PROJECT_ID_LABEL: "12345"}
    mock_resource.status.phase = "Terminating"

    await __process_namespace_event(mock_resource, "MODIFIED")

    mock_publish_status.assert_called_once_with("12345", NamespaceStatus.TERMINATING, "Namespace is terminating")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
async def test_process_namespace_event_unknown_phase(mock_publish_status):
    mock_resource = MagicMock()
    mock_resource.metadata.name = "test-namespace"
    mock_resource.metadata.labels = {PROJECT_ID_LABEL: "12345"}
    mock_resource.status.phase = "Unknown"

    await __process_namespace_event(mock_resource, "MODIFIED")

    mock_publish_status.assert_called_once_with("12345", NamespaceStatus.FAILED, "Unknown namespace phase: Unknown")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
async def test_process_namespace_event_no_project_id_label(mock_publish_status):
    mock_resource = MagicMock()
    mock_resource.metadata.name = "system-namespace"
    mock_resource.metadata.labels = {}
    mock_resource.status.phase = "Active"

    await __process_namespace_event(mock_resource, "MODIFIED")

    mock_publish_status.assert_not_called()


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
async def test_process_namespace_event_no_labels(mock_publish_status):
    mock_resource = MagicMock()
    mock_resource.metadata.name = "system-namespace"
    mock_resource.metadata.labels = None
    mock_resource.status.phase = "Active"

    await __process_namespace_event(mock_resource, "MODIFIED")

    mock_publish_status.assert_not_called()


@pytest.mark.asyncio
@patch("app.namespaces.service.start_kubernetes_watcher")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_start_watching_namespace_components(mock_core_v1_api, mock_start_watcher):
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance

    task = start_watching_namespace_components()

    assert task is not None
    assert hasattr(task, "cancel")

    task.cancel()
    # in case of warnings
    try:
        await task
    except CancelledError:
        pass


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_delete_success(mock_core_v1_api, mock_publish_status):
    """Test successful namespace deletion."""
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance
    projectid = uuid4()

    mock_namespace = MagicMock()
    mock_namespace.metadata.labels = {PROJECT_ID_LABEL: str(projectid)}
    mock_api_instance.read_namespace.return_value = mock_namespace

    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=projectid
    )

    await process_namespace_delete(message)

    mock_core_v1_api.assert_called_once()
    mock_api_instance.read_namespace.assert_called_once_with(name="test-namespace")
    mock_api_instance.delete_namespace.assert_called_once_with(name="test-namespace")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_delete_project_id_mismatch(mock_core_v1_api, mock_publish_status):
    """Test namespace deletion when project ID doesn't match."""
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance

    # Mock namespace with different project ID
    mock_namespace = MagicMock()
    mock_namespace.metadata.labels = {PROJECT_ID_LABEL: "different-id"}
    mock_api_instance.read_namespace.return_value = mock_namespace

    projectid = uuid4()
    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=projectid
    )

    await process_namespace_delete(message)

    mock_api_instance.read_namespace.assert_called_once_with(name="test-namespace")
    mock_api_instance.delete_namespace.assert_not_called()
    mock_publish_status.assert_called_once_with(projectid, NamespaceStatus.DELETED, "Project namespace not found")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_delete_no_project_id_label(mock_core_v1_api, mock_publish_status):
    """Test namespace deletion when project ID label is missing."""
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance

    # Mock namespace without project ID label
    mock_namespace = MagicMock()
    mock_namespace.metadata.labels = {}
    mock_api_instance.read_namespace.return_value = mock_namespace

    projectid = uuid4()
    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=projectid
    )

    await process_namespace_delete(message)

    mock_api_instance.read_namespace.assert_called_once_with(name="test-namespace")
    mock_api_instance.delete_namespace.assert_not_called()
    mock_publish_status.assert_called_once_with(projectid, NamespaceStatus.DELETED, "Project namespace not found")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_delete_no_labels(mock_core_v1_api, mock_publish_status):
    """Test namespace deletion when labels are None."""
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance

    # Mock namespace with None labels
    mock_namespace = MagicMock()
    mock_namespace.metadata.labels = None
    mock_api_instance.read_namespace.return_value = mock_namespace

    projectid = uuid4()
    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=projectid
    )

    await process_namespace_delete(message)

    mock_api_instance.read_namespace.assert_called_once_with(name="test-namespace")
    mock_api_instance.delete_namespace.assert_not_called()
    mock_publish_status.assert_called_once_with(projectid, NamespaceStatus.DELETED, "Project namespace not found")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_delete_read_failure(mock_core_v1_api, mock_publish_status):
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance
    mock_api_instance.read_namespace.side_effect = ApiException("Namespace not readable")

    projectid = uuid4()
    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=projectid
    )

    await process_namespace_delete(message)

    mock_api_instance.read_namespace.assert_called_once_with(name="test-namespace")
    mock_api_instance.delete_namespace.assert_not_called()
    mock_publish_status.assert_called_once_with(
        projectid, NamespaceStatus.DELETE_FAILED, "Failed to delete namespace: (Namespace not readable)\nReason: None\n"
    )


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_delete_not_found(mock_core_v1_api, mock_publish_status):
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance
    mock_api_instance.read_namespace.side_effect = ApiException(status=404, reason="Namespace not found")

    projectid = uuid4()
    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=projectid
    )

    await process_namespace_delete(message)

    mock_api_instance.read_namespace.assert_called_once_with(name="test-namespace")
    mock_api_instance.delete_namespace.assert_not_called()
    mock_publish_status.assert_called_once_with(projectid, NamespaceStatus.DELETED, "Project namespace not found")


@pytest.mark.asyncio
@patch("app.namespaces.service._publish_namespace_status")
@patch("app.namespaces.service.client.CoreV1Api")
async def test_process_namespace_delete_delete_failure(mock_core_v1_api, mock_publish_status):
    mock_api_instance = MagicMock()
    mock_core_v1_api.return_value = mock_api_instance
    projectid = uuid4()

    mock_namespace = MagicMock()
    mock_namespace.metadata.labels = {PROJECT_ID_LABEL: str(projectid)}
    mock_api_instance.read_namespace.return_value = mock_namespace
    mock_api_instance.delete_namespace.side_effect = ApiException("Delete failed")

    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=projectid
    )

    await process_namespace_delete(message)

    mock_api_instance.read_namespace.assert_called_once_with(name="test-namespace")
    mock_api_instance.delete_namespace.assert_called_once_with(name="test-namespace")
    mock_publish_status.assert_called_once_with(
        projectid, NamespaceStatus.DELETE_FAILED, "Failed to delete namespace: (Delete failed)\nReason: None\n"
    )
