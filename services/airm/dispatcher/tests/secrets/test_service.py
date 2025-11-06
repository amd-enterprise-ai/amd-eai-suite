# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes.client.exceptions import ApiException

from airm.messaging.schemas import (
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
    SecretsComponentKind,
)
from airm.secrets.constants import (
    EXTERNAL_SECRETS_KIND,
    PROJECT_SECRET_ID_LABEL,
)
from app.secrets.service import (
    __process_external_secret_event,
    __process_kubernetes_secret_event,
    process_project_secrets_create,
    process_project_secrets_delete,
    start_watching_secrets_components,
)

from ..utils import create_mock_k8s_object, create_mock_resource_instance

sample_manifest = """
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: example-external-secret
  namespace: test-project-ns
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: k8s-secret-store
    kind: SecretStore
  target:
    name: synced-secret
  data:
    - secretKey: password
      remoteRef:
        key: my-secret
        property: password
    """

kubernetes_secret_manifest = """
apiVersion: v1
kind: Secret
metadata:
  name: example-hf-secret
stringData:
  token: abc
type: Opaque
"""


def mock_request(method, path, *args, **kwargs):
    if path == "/version":
        return MagicMock(data=json.dumps({"major": "1", "minor": "26", "gitVersion": "v1.26.0"}).encode("utf-8"))
    elif path == "/apis":
        return MagicMock(data=json.dumps({"kind": "APIGroupList", "groups": []}).encode("utf-8"))
    raise ValueError(f"Unhandled path: {path}")


@pytest.mark.asyncio
@patch("app.secrets.service.create_from_dict")
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
async def test_project_secrets_create(
    mock_get_conn_chan,
    mock_api_client_class,
    mock_create_from_dict,
):
    """Test that process_project_secrets_create processes project secrets messages correctly and calls create_from_dict."""

    # Mock the connection return values (avoid real RabbitMQ)
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())

    # Setup the dynamic client
    mock_client = mock_api_client_class.return_value

    project_secrets_create_message = ProjectSecretsCreateMessage(
        manifest=sample_manifest,
        message_type="project_secrets_create",
        secret_name="example-external-secret",
        project_name="test-project-ns",
        project_secret_id=uuid4(),
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )

    await process_project_secrets_create(project_secrets_create_message)

    # Assert create_from_dict was called with correct parameters
    mock_create_from_dict.assert_called_once()
    args, kwargs = mock_create_from_dict.call_args
    assert args[0] is mock_client
    assert args[1]["kind"] == "ExternalSecret"
    assert args[1]["metadata"]["name"] == "example-external-secret"
    assert args[1]["metadata"]["namespace"] == "test-project-ns"


@pytest.mark.asyncio
@patch("app.secrets.service.create_from_dict")
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
async def test_project_secrets_create_kubernetes_secret(
    mock_get_conn_chan,
    mock_api_client_class,
    mock_create_from_dict,
):
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())
    mock_client = mock_api_client_class.return_value

    message = ProjectSecretsCreateMessage(
        manifest=kubernetes_secret_manifest,
        message_type="project_secrets_create",
        secret_name="example-hf-secret",
        project_name="test-project-ns",
        project_secret_id=uuid4(),
        secret_type=SecretsComponentKind.KUBERNETES_SECRET,
    )

    await process_project_secrets_create(message)

    mock_create_from_dict.assert_called_once()
    args, kwargs = mock_create_from_dict.call_args
    assert args[0] is mock_client
    assert args[1]["kind"] == "Secret"
    assert args[1]["metadata"]["labels"][PROJECT_SECRET_ID_LABEL] == str(message.project_secret_id)


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.create_from_dict")
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
async def test_project_secrets_create_invalid_manifest_raises(
    mock_get_conn_chan,
    mock_api_client_class,
    mock_create_from_dict,
    mock_publish_status_message,
):
    """Test that process_project_secrets_create raises an error for invalid manifest and does not call create_from_dict."""
    # Mock the connection return values (avoid real RabbitMQ)
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())

    # Setup the dynamic client
    mock_api_client_class.return_value

    # Invalid manifest (not YAML/JSON)
    invalid_manifest = "not a valid yaml or json"
    mock_project_secret_id = uuid4()

    project_secrets_create_message = ProjectSecretsCreateMessage(
        manifest=invalid_manifest,
        message_type="project_secrets_create",
        secret_name="bad-secret",
        project_name="test-project-ns",
        project_secret_id=mock_project_secret_id,
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )

    await process_project_secrets_create(project_secrets_create_message)

    status_message = mock_publish_status_message.await_args.args[0]

    # Assert create_from_dict was not called
    mock_create_from_dict.assert_not_called()

    # Assert __publish_secrets_component_status_update was called with an error message
    assert isinstance(status_message, ProjectSecretsUpdateMessage)
    assert status_message.status_reason.startswith("Manifest is malformed")
    assert f"secret_type={SecretsComponentKind.EXTERNAL_SECRET.value}" in status_message.status_reason
    assert str(status_message.project_secret_id) == str(mock_project_secret_id)
    assert status_message.message_type == "project_secrets_update"


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.create_from_dict")
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
async def test_project_secrets_create_multiple_resources_raises(
    mock_get_conn_chan,
    _,
    mock_create_from_dict,
    mock_publish_status_message,
):
    """Test that process_project_secrets_create raises an error for manifest with multiple resources and does not call create_from_dict."""
    # Mock the connection return values (avoid real RabbitMQ)
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())

    # Manifest with multiple resources
    multiple_manifest = sample_manifest + "\n---\n" + sample_manifest

    mock_project_secret_id = uuid4()

    project_secrets_create_message = ProjectSecretsCreateMessage(
        manifest=multiple_manifest,
        message_type="project_secrets_create",
        secret_name="bad-secret",
        project_name="test-project-ns",
        project_secret_id=mock_project_secret_id,
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )

    await process_project_secrets_create(project_secrets_create_message)

    status_message = mock_publish_status_message.await_args.args[0]

    # Assert create_from_dict was not called
    mock_create_from_dict.assert_not_called()

    # Assert __publish_secrets_component_status_update was called with an error message
    assert isinstance(status_message, ProjectSecretsUpdateMessage)
    assert status_message.status_reason.startswith("Expected 1 manifest, but got 2")
    assert str(status_message.project_secret_id) == str(mock_project_secret_id)
    assert status_message.message_type == "project_secrets_update"


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.create_from_dict")
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
async def test_project_secrets_create_invalid_resource_kind_raises(
    mock_get_conn_chan,
    _,
    mock_create_from_dict,
    mock_publish_status_message,
):
    """Test that process_project_secrets_create raises an error for manifest with invalid resource kind and does not call create_from_dict."""

    # Mock the connection return values (avoid real RabbitMQ)
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())

    # Manifest with multiple resources
    mistyped_manifest = sample_manifest.replace("kind: ExternalSecret", "kind: SomeResource")
    mock_project_secret_id = uuid4()

    project_secrets_create_message = ProjectSecretsCreateMessage(
        manifest=mistyped_manifest,
        message_type="project_secrets_create",
        secret_name="bad-secret",
        project_name="test-project-ns",
        project_secret_id=mock_project_secret_id,
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )

    await process_project_secrets_create(project_secrets_create_message)

    # Assert create_from_dict was not called
    mock_create_from_dict.assert_not_called()

    status_message = mock_publish_status_message.await_args.args[0]

    # Assert __publish_secrets_component_status_update was called with an error message
    assert isinstance(status_message, ProjectSecretsUpdateMessage)
    assert "Invalid ExternalSecret manifest" in status_message.status_reason
    assert str(status_message.project_secret_id) == str(mock_project_secret_id)
    assert status_message.message_type == "project_secrets_update"


@pytest.mark.asyncio
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.DynamicClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
@patch("app.secrets.service._publish_project_secret_status")
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_installed_version_for_custom_resource", return_value="v1beta1")
async def test_process_delete_external_secret_success(
    __,
    mock_publish_secrets_component_status_update,
    mock_publish_project_secret_status,
    mock_get_connection,
    mock_dynamic_client_class,
    _,
):
    # Mock connection
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_resource = MagicMock()
    mock_resource.kind = "ExternalSecret"
    mock_resource.namespaced = True
    mock_resource.api_version = "v1beta1"

    mock_project_secret_id = uuid4()
    # Create a mock item to be deleted
    mock_item = MagicMock()
    mock_item.metadata.name = "mock-external-secret"
    mock_item.metadata.namespace = "test-namespace"
    mock_item.metadata.labels = {
        PROJECT_SECRET_ID_LABEL: str(mock_project_secret_id),
    }

    mock_resource.get.return_value.items = [mock_item]
    mock_dynamic_client.resources.search.return_value = [mock_resource]

    message = ProjectSecretsDeleteMessage(
        message_type="project_secrets_delete",
        project_secret_id=mock_project_secret_id,
        project_name="test-project",
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )
    await process_project_secrets_delete(message)

    mock_publish_secrets_component_status_update.assert_not_awaited()
    mock_publish_project_secret_status.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.DynamicClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
@patch("app.secrets.service._publish_project_secret_status")
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_installed_version_for_custom_resource", return_value="v1beta1")
async def test_process_delete_external_secret_no_resources_items_found(
    __,
    mock_publish_secrets_component_status_update,
    mock_publish_project_secret_status,
    mock_get_connection,
    mock_dynamic_client_class,
    _,
):
    # Mock connection
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_resource = MagicMock()
    mock_resource.namespaced = True
    mock_resource.get.return_value.items = []

    mock_dynamic_client.resources.search.return_value = [mock_resource]

    mock_project_secret_id = uuid4()

    message = ProjectSecretsDeleteMessage(
        message_type="project_secrets_delete",
        project_secret_id=mock_project_secret_id,
        project_name="test-project",
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )
    await process_project_secrets_delete(message)

    mock_publish_project_secret_status.assert_awaited_with(
        message.project_secret_id,
        ProjectSecretStatus.DELETED,
        f"No resources found for deletion: {PROJECT_SECRET_ID_LABEL}={message.project_secret_id}",
    )
    mock_publish_secrets_component_status_update.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.DynamicClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
@patch("app.secrets.service._publish_project_secret_status")
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_installed_version_for_custom_resource", return_value="v1beta1")
async def test_process_delete_external_secret_no_resources_found(
    __,
    mock_publish_secrets_component_status_update,
    mock_publish_project_secret_status,
    mock_get_connection,
    mock_dynamic_client_class,
    _,
):
    # Mock connection
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_dynamic_client.resources.search.return_value = []
    mock_project_secret_id = uuid4()

    message = ProjectSecretsDeleteMessage(
        message_type="project_secrets_delete",
        project_secret_id=mock_project_secret_id,
        project_name="test-project",
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )
    await process_project_secrets_delete(message)

    mock_publish_project_secret_status.assert_awaited_with(
        message.project_secret_id,
        ProjectSecretStatus.DELETED,
        f"No resources found for deletion: {PROJECT_SECRET_ID_LABEL}={message.project_secret_id}",
    )
    mock_publish_secrets_component_status_update.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.DynamicClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
@patch("app.secrets.service._publish_project_secret_status")
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_installed_version_for_custom_resource", return_value="v1beta1")
async def test_process_delete_external_secret_delete_fails(
    __,
    mock_publish_secrets_component_status_update,
    mock_publish_project_secret_status,
    mock_get_connection,
    mock_dynamic_client_class,
    _,
):
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    mock_project_secret_id = uuid4()

    mock_external_secret = create_mock_k8s_object(
        kind=EXTERNAL_SECRETS_KIND,
        name="mock-external-secret",
        namespace="test-project-ns",
        api_version="v1beta1",
        labels={PROJECT_SECRET_ID_LABEL: str(mock_project_secret_id)},
    )

    mock_resource_instance = create_mock_resource_instance([mock_external_secret])

    mock_resource = MagicMock()
    mock_resource.kind = EXTERNAL_SECRETS_KIND
    mock_resource.api_version = "v1beta1"
    mock_resource.namespaced = True
    mock_resource.get.return_value = mock_resource_instance

    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_dynamic_client.resources.search.return_value = [mock_resource]

    mock_resource.delete.side_effect = ApiException(status=500, reason="Internal Server Error")

    message = ProjectSecretsDeleteMessage(
        message_type="project_secrets_delete",
        project_secret_id=mock_project_secret_id,
        project_name="test-project-ns",
        secret_type=SecretsComponentKind.EXTERNAL_SECRET,
    )

    await process_project_secrets_delete(message)

    mock_publish_project_secret_status.assert_not_awaited()

    mock_publish_secrets_component_status_update.assert_awaited_once()

    status_message = mock_publish_secrets_component_status_update.await_args.args[0]

    assert isinstance(status_message, ProjectSecretsUpdateMessage)
    assert status_message.status == ProjectSecretStatus.DELETE_FAILED
    assert str(status_message.project_secret_id) == str(mock_project_secret_id)
    assert "Deletion failed" in status_message.status_reason
    assert "Internal Server Error" in status_message.status_reason


@pytest.mark.asyncio
@patch("app.secrets.service.client.ApiClient")
@patch("app.secrets.service.DynamicClient")
@patch("app.secrets.service.get_common_vhost_connection_and_channel")
@patch("app.secrets.service._publish_project_secret_status")
@patch("app.secrets.service.__publish_secrets_component_status_update")
async def test_process_delete_kubernetes_secret_success(
    mock_publish_secrets_component_status_update,
    mock_publish_project_secret_status,
    mock_get_connection,
    mock_dynamic_client_class,
    _,
):
    """Test deleting Kubernetes Secret (e.g., Hugging Face token) successfully."""
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_resource = MagicMock()
    mock_resource.kind = "Secret"
    mock_resource.namespaced = True
    mock_resource.api_version = "v1"

    mock_project_secret_id = uuid4()
    # Create a mock Kubernetes Secret to be deleted
    mock_item = MagicMock()
    mock_item.metadata.name = "mock-hf-token"
    mock_item.metadata.namespace = "test-namespace"
    mock_item.metadata.labels = {
        PROJECT_SECRET_ID_LABEL: str(mock_project_secret_id),
    }

    mock_resource.get.return_value.items = [mock_item]
    mock_dynamic_client.resources.search.return_value = [mock_resource]

    message = ProjectSecretsDeleteMessage(
        message_type="project_secrets_delete",
        project_secret_id=mock_project_secret_id,
        project_name="test-project",
        secret_type=SecretsComponentKind.KUBERNETES_SECRET,
    )
    await process_project_secrets_delete(message)

    # Verify no error messages were published
    mock_publish_secrets_component_status_update.assert_not_awaited()
    mock_publish_project_secret_status.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_status_for_external_secret")
async def test_process_external_secret_event_success(mock_get_status, mock_publish):
    # Create mock resource
    mock_resource = MagicMock()
    mock_resource.metadata.name = "test-external-secret"
    mock_resource.metadata.namespace = "test-project-ns"
    project_secret_id = str(uuid4())
    mock_resource.metadata.labels = {PROJECT_SECRET_ID_LABEL: project_secret_id}
    mock_resource.status = MagicMock()
    mock_resource.status.conditions = [
        {"type": "Ready", "status": "True", "reason": "SecretSynced", "message": "Secret was synced"}
    ]

    # Set the return value for the status function
    mock_get_status.return_value = (ProjectSecretStatus.SYNCED, "Secret was synced")

    # Call the function under test
    await __process_external_secret_event(mock_resource, "ADDED")

    # Verify that __publish_secrets_component_status_update was called once
    mock_publish.assert_awaited_once()

    # Get the message that was passed to __publish_secrets_component_status_update
    status_message = mock_publish.await_args.args[0]

    # Verify the ProjectSecretsUpdateMessage has correct properties
    assert isinstance(status_message, ProjectSecretsUpdateMessage)
    assert status_message.status_reason == "Secret was synced"
    assert str(status_message.project_secret_id) == str(project_secret_id)
    assert status_message.message_type == "project_secrets_update"


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
async def test_process_external_secret_event_missing_secret_id(mock_publish):
    resource = MagicMock()
    resource.metadata.name = "test-external-secret"
    resource.metadata.namespace = "test-project-ns"

    await __process_external_secret_event(resource, "ADDED")

    mock_publish.assert_not_called()


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_status_for_external_secret")
async def test_process_external_secret_event_error(mock_get_status, mock_publish):
    # Create mock resource
    mock_resource = MagicMock()
    mock_resource.metadata.name = "test-external-secret"
    mock_resource.metadata.namespace = "test-project-ns"
    project_secret_id = str(uuid4())
    mock_resource.metadata.labels = {PROJECT_SECRET_ID_LABEL: project_secret_id}
    mock_resource.status = MagicMock()
    mock_resource.status.conditions = [
        {
            "type": "Ready",
            "status": "False",
            "reason": "SecretSyncedError",
            "message": "could not get secret data from provider.",
        }
    ]

    # Set the return value for the status function
    mock_get_status.return_value = (
        ProjectSecretStatus.SYNCED_ERROR,
        "could not get secret data from provider.",
    )  # Call the function under test

    # Call the function under test
    await __process_external_secret_event(mock_resource, "ERROR")

    # Verify that __publish_secrets_component_status_update was called once
    mock_publish.assert_awaited_once()

    # Get the message that was passed to __publish_secrets_component_status_update
    status_message = mock_publish.await_args.args[0]

    # Verify the ProjectSecretsUpdateMessage has correct properties
    assert isinstance(status_message, ProjectSecretsUpdateMessage)
    assert status_message.status_reason == "could not get secret data from provider."
    assert str(status_message.project_secret_id) == str(project_secret_id)
    assert status_message.message_type == "project_secrets_update"


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_status_for_kubernetes_secret")
async def test_process_kubernetes_secret_event_success(mock_get_status, mock_publish):
    project_secret_id = str(uuid4())
    resource = MagicMock()
    resource.metadata = MagicMock()
    resource.metadata.labels = {PROJECT_SECRET_ID_LABEL: project_secret_id}

    mock_get_status.return_value = (ProjectSecretStatus.SYNCED, "Secret materialized")

    await __process_kubernetes_secret_event(resource, "ADDED")

    mock_publish.assert_awaited_once()
    status_message = mock_publish.await_args.args[0]
    assert status_message.status == ProjectSecretStatus.SYNCED
    assert status_message.status_reason == "Secret materialized"
    assert str(status_message.project_secret_id) == project_secret_id


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
async def test_process_kubernetes_secret_event_missing_label(mock_publish):
    resource = MagicMock()
    resource.metadata = MagicMock()
    resource.metadata.labels = {}

    await __process_kubernetes_secret_event(resource, "ADDED")

    mock_publish.assert_not_called()


@pytest.mark.asyncio
@patch("app.secrets.service.__publish_secrets_component_status_update")
@patch("app.secrets.service.get_status_for_kubernetes_secret")
async def test_process_kubernetes_secret_event_error(mock_get_status, mock_publish):
    project_secret_id = str(uuid4())
    resource = MagicMock()
    resource.metadata = MagicMock()
    resource.metadata.labels = {PROJECT_SECRET_ID_LABEL: project_secret_id}

    mock_get_status.side_effect = ValueError("boom")

    await __process_kubernetes_secret_event(resource, "ADDED")

    mock_publish.assert_not_called()


@pytest.mark.asyncio
@patch("app.secrets.service.start_kubernetes_watcher_if_resource_exists")
@patch("app.secrets.service.get_installed_version_for_custom_resource")
async def test_start_watching_secrets_components(mock_version, mocked_optional_watcher):
    # Configure mock_watcher to return a completed future

    mocked_optional_watcher.return_value = asyncio.Future()
    mocked_optional_watcher.return_value.set_result(None)

    await start_watching_secrets_components()

    assert mocked_optional_watcher.call_count == 2  # external + kubernetes secret
    assert mock_version.call_count == 1

    optional_watcher_names = [
        call_item.args[0] if call_item.args else call_item.kwargs.get("watcher_name")
        for call_item in mocked_optional_watcher.call_args_list
    ]
    assert "external_secret_watcher" in optional_watcher_names
    assert "kubernetes_secret_watcher" in optional_watcher_names
