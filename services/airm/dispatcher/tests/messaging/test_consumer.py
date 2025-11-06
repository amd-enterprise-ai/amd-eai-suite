# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
import yaml

from airm.messaging.schemas import (
    DeleteWorkloadMessage,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceDeleteMessage,
    ProjectS3StorageCreateMessage,
    ProjectStorageDeleteMessage,
    WorkloadMessage,
)
from app.messaging.consumer import __process_message

mock_yaml = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: sample-deployment\n  labels:\n    app: sample-app\nspec:\n  replicas: 2\n  selector:\n    matchLabels:\n      app: sample-app\n  template:\n    metadata:\n      labels:\n        app: sample-app\n    spec:\n      containers:\n      - name: sample-container\n        image: nginx:1.14.2\n        ports:\n        - containerPort: 80\n"

parsed_mock_yaml = yaml.safe_load(mock_yaml)


@pytest.mark.asyncio
async def test_process_workload_message_valid_workload_message():
    global mock_yaml
    global parsed_mock_yaml
    message = MagicMock()
    message.body.decode.return_value = mock_yaml
    message.process = MagicMock()
    workload_message = WorkloadMessage(
        manifest=mock_yaml, message_type="workload", user_token="some_token", workload_id=uuid4()
    )

    with (
        patch("app.messaging.consumer.process_workload") as mock_process_workload,
        patch(
            "airm.messaging.schemas.MessageAdapter.validate_json",
            return_value=workload_message,
        ),
    ):
        await __process_message(message)

        # Verify the mock was called with correct arguments
        message.process.assert_called_once()
        mock_process_workload.assert_called_once_with(workload_message)


@pytest.mark.asyncio
async def test_process_workload_message_unexpected_message_type():
    message = MagicMock()
    message.body.decode.return_value = '{"unexpected": "message"}'
    message.process = MagicMock()

    with patch("airm.messaging.schemas.MessageAdapter.validate_json", return_value={"unexpected": "message"}):
        await __process_message(message)
        message.process.assert_called_once()


@pytest.mark.asyncio
async def test_process_delete_workload_valid_message():
    message = MagicMock()
    message.body.decode.return_value = mock_yaml
    message.process = MagicMock()
    delete_workload_message = DeleteWorkloadMessage(workload_id=uuid4(), message_type="delete_workload")

    with (
        patch("app.messaging.consumer.process_delete_workload") as mock_process_delete_workload,
        patch(
            "airm.messaging.schemas.MessageAdapter.validate_json",
            return_value=delete_workload_message,
        ),
    ):
        await __process_message(message)

        # Verify the mock was called with correct arguments
        message.process.assert_called_once()
        mock_process_delete_workload.assert_called_once_with(delete_workload_message)


@pytest.mark.asyncio
async def test_process_namespace_create_valid_message():
    message = MagicMock()
    message.body.decode.return_value = (
        '{"message_type": "project_namespace_create", "name": "test-namespace", "project_id": "12345"}'
    )
    message.process = MagicMock()
    namespace_create_message = ProjectNamespaceCreateMessage(
        message_type="project_namespace_create", name="test-namespace", project_id=uuid4()
    )

    with (
        patch("app.messaging.consumer.process_namespace_create") as mock_process_namespace_create,
        patch(
            "airm.messaging.schemas.MessageAdapter.validate_json",
            return_value=namespace_create_message,
        ),
    ):
        await __process_message(message)

        # Verify the mock was called with correct arguments
        message.process.assert_called_once()
        mock_process_namespace_create.assert_called_once_with(namespace_create_message)


@pytest.mark.asyncio
async def test_process_namespace_delete_valid_message():
    message = MagicMock()
    message.body.decode.return_value = (
        '{"message_type": "project_namespace_delete", "name": "test-namespace", "project_id": "12345"}'
    )
    message.process = MagicMock()
    namespace_delete_message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete", name="test-namespace", project_id=uuid4()
    )

    with (
        patch("app.messaging.consumer.process_namespace_delete") as mock_process_namespace_delete,
        patch(
            "airm.messaging.schemas.MessageAdapter.validate_json",
            return_value=namespace_delete_message,
        ),
    ):
        await __process_message(message)

        # Verify the mock was called with correct arguments
        message.process.assert_called_once()
        mock_process_namespace_delete.assert_called_once_with(namespace_delete_message)


@pytest.mark.asyncio
async def test_process_s3_storage_create_valid_message():
    message = MagicMock()
    message.body.decode.return_value = (
        '{"message_type": "project_s3_storage_create", '
        '"project_storage_id": "12345678-1234-5678-1234-567812345678", '
        '"project_name": "test-proj", '
        '"storage_name": "new-storage", '
        '"secret_key_name": "secret1", '
        '"access_key_name": "secret2", '
        '"bucket_url": "http://localhost:9001/browser/mybucket", '
        '"secret_name": "storage-credentials"}'
    )
    message.process = MagicMock()

    s3_storage_create_message = ProjectS3StorageCreateMessage(
        message_type="project_s3_storage_create",
        project_storage_id=UUID("12345678-1234-5678-1234-567812345678"),
        project_name="test-proj",
        storage_name="new-storage",
        secret_key_name="secret1",
        access_key_name="secret2",
        bucket_url="http://localhost:9001/browser/mybucket",
        secret_name="storage-credentials",
    )

    with (
        patch("app.messaging.consumer.process_project_s3_storage_create") as mock_process_project_s3_storage_create,
        patch(
            "airm.messaging.schemas.MessageAdapter.validate_json",
            return_value=s3_storage_create_message,
        ),
    ):
        await __process_message(message)

        message.process.assert_called_once()
        mock_process_project_s3_storage_create.assert_called_once_with(s3_storage_create_message)


@pytest.mark.asyncio
async def test_process_project_storage_delete_message():
    message_body = ProjectStorageDeleteMessage(
        message_type="project_storage_delete",
        project_storage_id=uuid4(),
        project_name="test-proj",
        storage_name="test-storage",
    )
    message = MagicMock()
    message.body.decode.return_value = message_body.model_dump_json()
    message.process = MagicMock()
    with (
        patch("app.messaging.consumer.process_project_storage_delete") as mock_process_storage_delete,
        patch("app.messaging.consumer.MessageAdapter.validate_json", return_value=message_body),
    ):
        from app.messaging.consumer import __process_message

        await __process_message(message)
        message.process.assert_called_once()
        mock_process_storage_delete.assert_called_once_with(message_body)
