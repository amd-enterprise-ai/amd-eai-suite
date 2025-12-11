# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes.client.exceptions import ApiException

from airm.messaging.schemas import (
    AIMServiceStatus,
    CommonComponentStatus,
    ConfigMapStatus,
    CronJobStatus,
    DaemonSetStatus,
    DeleteWorkloadMessage,
    IngressStatus,
    KaiwoJobStatus,
    KaiwoServiceStatus,
    PodStatus,
    ServiceStatus,
    StatefulSetStatus,
    WorkloadComponentKind,
    WorkloadComponentStatusMessage,
    WorkloadMessage,
    WorkloadStatus,
)
from airm.workloads.constants import COMPONENT_ID_LABEL, PROJECT_ID_LABEL, WORKLOAD_ID_LABEL
from app.quotas.constants import (
    KAIWO_RESOURCE_API_GROUP,
)
from app.workloads.constants import (
    AIM_SERVICE_API_GROUP,
    AIM_SERVICE_RESOURCE_PLURAL,
    AUTO_DISCOVERED_WORKLOAD_ANNOTATION,
    KAIWO_JOB_RESOURCE_PLURAL,
    KAIWO_SERVICE_RESOURCE_PLURAL,
    WORKLOAD_SUBMITTER_ANNOTATION,
)
from app.workloads.schemas import WorkloadComponentData
from app.workloads.service import (
    __process_workload_component_event,
    __publish_auto_discovered_workload_component,
    __publish_workload_component_status_update,
    process_delete_workload,
    process_workload,
    start_watching_workload_components,
)
from app.workloads.utils import (
    get_status_for_aim_service,
    get_status_for_ingress,
    get_status_for_kaiwo_job,
    get_status_for_kaiwo_service,
)

from ..utils import create_mock_k8s_object, create_mock_resource_instance

sample_manifest = """
apiVersion: v1
kind: Deployment
metadata:
  labels:
    airm.silogen.ai/workload-id: d330e767-854f-45b7-a06e-dcdb0277974c
    airm.silogen.ai/component-id: 2aa18e92-002c-45b7-a06e-dcdb0277974c
    airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
  name: test-deploy
  namespace: test-quota
spec:
  template:
    metadata:
      labels:
        airm.silogen.ai/workload-id: '12345'
        airm.silogen.ai/project-id: 'd330e767-f120-430e-854f-f28277f04de5'
        kueue.x-k8s.io/queue-name: test-quota
    spec:
      containers:
      - image: test-image
        name: test-container
    """

KAIWO_RESOURCE_VERSION = "v1alphav1"
AIM_SERVICE_VERSION = "v1alpha1"


def mock_request(method, path, *args, **kwargs):
    if path == "/version":
        return MagicMock(data=json.dumps({"major": "1", "minor": "26", "gitVersion": "v1.26.0"}).encode("utf-8"))
    elif path == "/apis":
        return MagicMock(data=json.dumps({"kind": "APIGroupList", "groups": []}).encode("utf-8"))
    raise ValueError(f"Unhandled path: {path}")


@pytest.mark.asyncio
@patch("app.workloads.service.client.ApiClient")
@patch("app.workloads.service.DynamicClient")
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
async def test_process_workload(
    mock_get_conn_chan: AsyncMock, mock_dynamic_client_class: MagicMock, _: MagicMock
) -> None:
    """Test that process_workload processes workload messages correctly."""

    # Mock the connection return values (avoid real RabbitMQ)
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())

    # Setup the dynamic client
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_api = MagicMock()
    mock_dynamic_client.resources.get.return_value = mock_api

    workload_message = WorkloadMessage(
        manifest=sample_manifest,
        message_type="workload",
        user_token="some_token",
        workload_id=uuid4(),
    )

    await process_workload(workload_message)

    # Verify the resources.get call is made with the correct API version and kind from the manifest
    mock_dynamic_client.resources.get.assert_called_once_with(api_version="v1", kind="Deployment")

    # Verify create is called with the correct manifest and namespace
    mock_api.create.assert_called_once()
    args, kwargs = mock_api.create.call_args
    assert kwargs["namespace"] == "test-quota"
    assert "body" in kwargs
    assert kwargs["body"]["kind"] == "Deployment"
    assert kwargs["body"]["metadata"]["name"] == "test-deploy"


@pytest.mark.asyncio
@patch("app.workloads.service.client.ApiClient")
@patch("app.workloads.service.DynamicClient")
@patch("app.workloads.service.publish_to_common_feedback_queue")
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
async def test_process_workload_general_exception(
    mock_get_conn_chan: AsyncMock,
    mock_publish_to_common_feedback_queue: MagicMock,
    mock_dynamic_client_class: MagicMock,
    _: MagicMock,
) -> None:
    """Test that process_workload handles exceptions correctly."""

    # Mock the connection return values (avoid real RabbitMQ)
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())

    workload_message = WorkloadMessage(
        manifest=sample_manifest,
        message_type="workload",
        user_token="some_token",
        workload_id=uuid4(),
    )

    # Simulate a general exception
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_dynamic_client.resources.get.side_effect = Exception("General exception")

    # Call function
    await process_workload(workload_message)

    call_kwargs = mock_publish_to_common_feedback_queue.call_args[1]  # Get keyword arguments
    published_message = call_kwargs["message"]

    # Now you can make assertions about specific fields
    assert published_message.kind == WorkloadComponentKind.DEPLOYMENT
    assert published_message.status == CommonComponentStatus.CREATE_FAILED
    assert "General exception" in published_message.status_reason

    # If you want to verify specific IDs from the sample manifest
    assert str(published_message.workload_id) == "d330e767-854f-45b7-a06e-dcdb0277974c"
    assert str(published_message.id) == "2aa18e92-002c-45b7-a06e-dcdb0277974c"


@pytest.mark.asyncio
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
@patch("app.workloads.service.publish_to_common_feedback_queue")
async def test_publish_workload_component_status_update(
    mock_publish_to_queue: MagicMock, mock_get_conn_chan: AsyncMock
) -> None:
    """Test that __publish_workload_component_status_update publishes the correct message."""

    # Mock the connection and channel
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_get_conn_chan.return_value = (mock_connection, mock_channel)

    # Create a sample WorkloadComponentStatusMessage
    test_message = WorkloadComponentStatusMessage(
        name="test-deployment",
        kind=WorkloadComponentKind.DEPLOYMENT,
        api_version="apps/v1",
        workload_id=uuid4(),
        id=uuid4(),
        status="Running",
        status_reason="Deployment is running successfully.",
        message_type="workload_component_status_update",
        updated_at=datetime.now(UTC),
    )

    # Call the function with the message
    await __publish_workload_component_status_update(test_message)

    # Verify that get_common_vhost_connection_and_channel was called
    mock_get_conn_chan.assert_called_once()

    # Verify that publish_to_common_feedback_queue was called with the correct message
    mock_publish_to_queue.assert_called_once()

    # Get the message that was passed to publish_to_common_feedback_queue
    published_message = mock_publish_to_queue.call_args[1].get("message")

    # Assert that the published message is the same as our test message
    assert published_message is test_message

    # Verify that the correct connection and channel were used
    assert mock_publish_to_queue.call_args[1]["connection"] == mock_connection
    assert mock_publish_to_queue.call_args[1]["channel"] == mock_channel


@pytest.mark.asyncio
@patch("app.workloads.service.client.ApiClient")
@patch("app.workloads.service.DynamicClient")
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
@patch("app.workloads.service.__publish_workload_status")
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_delete_workload_success(
    mock_publish_workload_component_status_update: AsyncMock,
    mock_publish_workload_status: AsyncMock,
    mock_get_connection: AsyncMock,
    mock_dynamic_client_class: MagicMock,
    _: MagicMock,
) -> None:
    # Mock connection
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_resource = MagicMock()
    mock_resource.kind = "Job"
    mock_resource.namespaced = True

    # Create a mock item to be deleted
    mock_item = MagicMock()
    mock_item.metadata.name = "mock-deployment"
    mock_item.metadata.namespace = "default"
    mock_item.metadata.labels = {
        "airm.silogen.ai/workload-id": str(uuid4()),
        "airm.silogen.ai/component-id": str(uuid4()),
    }
    mock_item.kind = "Deployment"
    mock_item.apiVersion = "apps/v1"

    mock_resource.get.return_value.items = [mock_item]
    mock_dynamic_client.resources.search.return_value = [mock_resource]

    message = DeleteWorkloadMessage(message_type="delete_workload", workload_id=uuid4())
    await process_delete_workload(message)

    mock_publish_workload_component_status_update.assert_not_awaited()
    mock_publish_workload_status.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.workloads.service.client.ApiClient")
@patch("app.workloads.service.DynamicClient")
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
@patch("app.workloads.service.__publish_workload_status")
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_delete_workload_no_resources_items_found(
    mock_publish_workload_component_status_update: AsyncMock,
    mock_publish_workload_status: AsyncMock,
    mock_get_connection: AsyncMock,
    mock_dynamic_client_class: MagicMock,
    _: MagicMock,
) -> None:
    # Mock connection
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_resource = MagicMock()
    mock_resource.kind = "Job"
    mock_resource.namespaced = True
    mock_resource.get.return_value.items = []

    mock_dynamic_client.resources.search.return_value = [mock_resource]

    message = DeleteWorkloadMessage(message_type="delete_workload", workload_id=uuid4())
    await process_delete_workload(message)

    mock_publish_workload_status.assert_awaited_with(
        message.workload_id,
        WorkloadStatus.DELETED.value,
        f"No resources found for deletion: {WORKLOAD_ID_LABEL}={message.workload_id}",
    )
    mock_publish_workload_component_status_update.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.workloads.service.client.ApiClient")
@patch("app.workloads.service.DynamicClient")
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
@patch("app.workloads.service.__publish_workload_status")
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_delete_workload_no_resources_found(
    mock_publish_workload_component_status_update: AsyncMock,
    mock_publish_workload_status: AsyncMock,
    mock_get_connection: AsyncMock,
    mock_dynamic_client_class: MagicMock,
    _: MagicMock,
) -> None:
    # Mock connection
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_dynamic_client.resources.search.return_value = []

    message = DeleteWorkloadMessage(message_type="delete_workload", workload_id=uuid4())
    await process_delete_workload(message)

    mock_publish_workload_status.assert_awaited_with(
        message.workload_id,
        WorkloadStatus.DELETED.value,
        f"No resources found for deletion: {WORKLOAD_ID_LABEL}={message.workload_id}",
    )
    mock_publish_workload_component_status_update.assert_not_awaited()


@patch("app.workloads.service.client.ApiClient")
@patch("app.workloads.service.DynamicClient")
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
@patch("app.workloads.service.__publish_workload_status")
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_delete_workload_handles_resource_exception(
    mock_publish_workload_component_status_update: AsyncMock,
    mock_publish_workload_status: AsyncMock,
    mock_get_connection: AsyncMock,
    mock_dynamic_client_class: MagicMock,
    _: MagicMock,
) -> None:
    # Mock connection
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    # Setup fake dynamic client resource search
    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_resource = MagicMock()
    mock_resource.kind = "Job"
    mock_resource.namespaced = True
    mock_resource.get.return_value.items = []
    mock_resource.get.side_effect = Exception("Resource listing failed")

    mock_dynamic_client.resources.search.return_value = [mock_resource]

    message = DeleteWorkloadMessage(message_type="delete_workload", workload_id=uuid4())
    await process_delete_workload(message)

    # No messages are sent if the kubernetes search api throws exception
    mock_publish_workload_status.assert_not_awaited()
    mock_publish_workload_component_status_update.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.workloads.service.client.ApiClient")
@patch("app.workloads.service.DynamicClient")
@patch("app.workloads.service.get_common_vhost_connection_and_channel")
@patch("app.workloads.service.__publish_workload_status")
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_delete_workload_delete_fails(
    mock_publish_workload_component_status_update: AsyncMock,
    mock_publish_workload_status: AsyncMock,
    mock_get_connection: AsyncMock,
    mock_dynamic_client_class: MagicMock,
    _: MagicMock,
) -> None:
    mock_get_connection.return_value = (MagicMock(), MagicMock())

    workload_id = uuid4()
    component_id = uuid4()
    project_id = uuid4()

    mock_deployment = create_mock_k8s_object(
        kind="Deployment",
        name="mock-deployment",
        namespace="default",
        labels={
            WORKLOAD_ID_LABEL: str(workload_id),
            COMPONENT_ID_LABEL: str(component_id),
            PROJECT_ID_LABEL: str(project_id),
        },
        api_version="apps/v1",
    )
    mock_resource_instance = create_mock_resource_instance([mock_deployment])

    mock_resource = MagicMock()
    mock_resource.kind = "Deployment"
    mock_resource.api_version = "apps/v1"
    mock_resource.namespaced = True
    mock_resource.get.return_value = mock_resource_instance

    mock_dynamic_client = mock_dynamic_client_class.return_value
    mock_dynamic_client.resources.search.return_value = [mock_resource]

    mock_resource.delete.side_effect = ApiException(status=500, reason="Internal Server Error")

    message = DeleteWorkloadMessage(message_type="delete_workload", workload_id=workload_id)

    await process_delete_workload(message)

    mock_publish_workload_status.assert_not_awaited()

    mock_publish_workload_component_status_update.assert_awaited_once()
    assert mock_publish_workload_component_status_update.await_args is not None
    status_message = mock_publish_workload_component_status_update.await_args.args[0]

    assert isinstance(status_message, WorkloadComponentStatusMessage)
    assert status_message.kind == WorkloadComponentKind.DEPLOYMENT
    assert status_message.name == "mock-deployment"
    assert status_message.status == CommonComponentStatus.DELETE_FAILED.value
    assert status_message.api_version == "apps/v1"
    assert str(status_message.workload_id) == str(workload_id)
    assert str(status_message.id) == str(component_id)
    assert "Deletion failed" in status_message.status_reason
    assert "Internal Server Error" in status_message.status_reason


@pytest.mark.parametrize(
    "kind, api_version, plural, expected_status_function",
    [
        (
            WorkloadComponentKind.KAIWO_SERVICE,
            KAIWO_RESOURCE_API_GROUP,
            KAIWO_SERVICE_RESOURCE_PLURAL,
            get_status_for_kaiwo_service,
        ),
        (
            WorkloadComponentKind.KAIWO_JOB,
            KAIWO_RESOURCE_API_GROUP,
            KAIWO_JOB_RESOURCE_PLURAL,
            get_status_for_kaiwo_job,
        ),
        (
            WorkloadComponentKind.AIM_SERVICE,
            AIM_SERVICE_API_GROUP,
            AIM_SERVICE_RESOURCE_PLURAL,
            get_status_for_aim_service,
        ),
    ],
)
@pytest.mark.asyncio
async def test_start_watching_workload_components_kaiwo(
    kind: str, api_version: str, plural: str, expected_status_function: object
) -> None:
    with (
        patch("app.workloads.service.start_generic_configmap_watcher") as mock_config_watcher,
        patch("app.workloads.service.start_kubernetes_watcher") as mock_watcher,
        patch("app.workloads.service.__process_workload_component_event") as mock_process,
        patch("app.workloads.service.get_common_vhost_connection_and_channel", return_value=(AsyncMock(), AsyncMock())),
        patch("app.workloads.service.publish_to_common_feedback_queue"),
        patch("app.workloads.service.get_installed_version_for_custom_resource"),
    ):
        mock_watcher.return_value = asyncio.Future()
        mock_watcher.return_value.set_result(None)

        mock_config_watcher.return_value = asyncio.Future()
        mock_config_watcher.return_value.set_result(None)

        start_watching_workload_components()
        await asyncio.sleep(0.1)

        for call_args in mock_watcher.call_args_list:
            if call_args[1].get("plural") == plural and call_args[1].get("group") == api_version:
                lambda_func = call_args[0][2]  # Get the lambda from the matching call
                break

        sample_kaiwo_resource = {
            "apiVersion": f"{api_version}/{plural}",
            "kind": kind,
            "metadata": {
                "name": "test-resource",
                "labels": {WORKLOAD_ID_LABEL: uuid4(), COMPONENT_ID_LABEL: uuid4(), PROJECT_ID_LABEL: uuid4()},
            },
            "status": {"status": "RUNNING"},
        }

        await lambda_func(sample_kaiwo_resource, "DELETED")

        mock_process.assert_called_with(sample_kaiwo_resource, "DELETED", expected_status_function)


@pytest.mark.parametrize(
    "kind, api_version, expected_status",
    [
        (WorkloadComponentKind.INGRESS, "networking.k8s.io/v1", CommonComponentStatus.DELETED),
        (
            WorkloadComponentKind.KAIWO_SERVICE,
            f"{KAIWO_RESOURCE_API_GROUP}/{KAIWO_RESOURCE_VERSION}",
            CommonComponentStatus.DELETED,
        ),
        (
            WorkloadComponentKind.KAIWO_JOB,
            f"{KAIWO_RESOURCE_API_GROUP}/{KAIWO_RESOURCE_VERSION}",
            CommonComponentStatus.DELETED,
        ),
        (
            WorkloadComponentKind.AIM_SERVICE,
            f"{AIM_SERVICE_API_GROUP}/{AIM_SERVICE_VERSION}",
            CommonComponentStatus.DELETED,
        ),
        (WorkloadComponentKind.SERVICE, "v1", CommonComponentStatus.DELETED),
        (WorkloadComponentKind.CONFIG_MAP, "v1", CommonComponentStatus.DELETED),
        (WorkloadComponentKind.DAEMON_SET, "apps/v1", CommonComponentStatus.DELETED),
        (WorkloadComponentKind.STATEFUL_SET, "apps/v1", CommonComponentStatus.DELETED),
        (WorkloadComponentKind.POD, "v1", CommonComponentStatus.DELETED),
        (WorkloadComponentKind.CRON_JOB, "batch/v1", CommonComponentStatus.DELETED),
    ],
)
@pytest.mark.asyncio
async def test_process_generic_event_deleted(kind: str, api_version: str, expected_status: object) -> None:
    mock_resource = MagicMock()
    mock_resource.kind = kind
    mock_resource.api_version = api_version
    mock_resource.metadata.name = "resource-one"
    workload_id = str(uuid4())
    component_id = str(uuid4())
    project_id = str(uuid4())
    mock_resource.metadata.labels = {
        WORKLOAD_ID_LABEL: workload_id,
        COMPONENT_ID_LABEL: component_id,
        PROJECT_ID_LABEL: project_id,
    }
    mock_resource.metadata.annotations = None

    # Mock dependencies
    with patch("app.workloads.service.__publish_workload_component_status_update") as mock_publish:
        await __process_workload_component_event(mock_resource, "DELETED", get_status_for_kaiwo_job)

        # Verify the status update was published
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[0][0]
        assert call_args.name == "resource-one"  # Resource
        assert call_args.status == expected_status
        assert call_args.kind == kind
        assert str(call_args.workload_id) == str(workload_id)  # workload_id
        assert str(call_args.id) == str(component_id)  # component_id


@pytest.mark.parametrize(
    "kind, api_version, status",
    [
        (WorkloadComponentKind.INGRESS, "networking.k8s.io/v1", IngressStatus.ADDED),
        (
            WorkloadComponentKind.KAIWO_SERVICE,
            f"{KAIWO_RESOURCE_API_GROUP}/{KAIWO_RESOURCE_VERSION}",
            KaiwoServiceStatus.RUNNING,
        ),
        (
            WorkloadComponentKind.KAIWO_JOB,
            f"{KAIWO_RESOURCE_API_GROUP}/{KAIWO_RESOURCE_VERSION}",
            KaiwoJobStatus.RUNNING,
        ),
        (
            WorkloadComponentKind.AIM_SERVICE,
            f"{AIM_SERVICE_API_GROUP}/{AIM_SERVICE_VERSION}",
            AIMServiceStatus.RUNNING,
        ),
        (WorkloadComponentKind.SERVICE, "v1", ServiceStatus.READY),
        (WorkloadComponentKind.CONFIG_MAP, "v1", ConfigMapStatus.ADDED),
        (WorkloadComponentKind.DAEMON_SET, "apps/v1", DaemonSetStatus.PENDING),
        (WorkloadComponentKind.STATEFUL_SET, "apps/v1", StatefulSetStatus.PENDING),
        (WorkloadComponentKind.POD, "v1", PodStatus.RUNNING),
        (WorkloadComponentKind.CRON_JOB, "batch/v1", CronJobStatus.RUNNING),
    ],
)
@pytest.mark.asyncio
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_event_success(mock_publish: AsyncMock, kind: str, api_version: str, status: object) -> None:
    # Create mock resource
    mock_resource = MagicMock()
    mock_resource.kind = kind
    mock_resource.api_version = api_version
    mock_resource.metadata.name = "resource-one"
    workload_id = str(uuid4())
    component_id = str(uuid4())
    project_id = str(uuid4())
    mock_resource.metadata.labels = {
        WORKLOAD_ID_LABEL: workload_id,
        COMPONENT_ID_LABEL: component_id,
        PROJECT_ID_LABEL: project_id,
    }
    mock_resource.metadata.annotations = None

    mock_get_status = MagicMock()
    mock_get_status.return_value = (status, "Resource has been added to the cluster.")

    # Call the function under test
    await __process_workload_component_event(mock_resource, "ADDED", mock_get_status)

    # Verify that __publish_workload_component_status_update was called once
    mock_publish.assert_awaited_once()
    assert mock_publish.await_args is not None
    # Get the message that was passed to __publish_workload_component_status_update
    status_message = mock_publish.await_args.args[0]

    # Verify the WorkloadComponentStatusMessage has correct properties
    assert isinstance(status_message, WorkloadComponentStatusMessage)
    assert status_message.kind.value == kind
    assert status_message.name == "resource-one"
    assert status_message.api_version == api_version
    assert status_message.status == status
    assert status_message.status_reason == "Resource has been added to the cluster."
    assert str(status_message.workload_id) == str(workload_id)
    assert str(status_message.id) == str(component_id)
    assert status_message.message_type == "workload_component_status_update"


@pytest.mark.parametrize(
    "labels",
    [
        {WORKLOAD_ID_LABEL: str(uuid4())},
        {COMPONENT_ID_LABEL: str(uuid4())},
    ],
)
@pytest.mark.asyncio
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_event_missing_labels(mock_publish: AsyncMock, labels: dict[str, str]) -> None:
    resource = MagicMock()
    resource.kind = "Ingress"
    resource.metadata.name = "test-ingress"
    resource.metadata.labels = labels

    await __process_workload_component_event(resource, "ADDED", get_status_for_ingress)

    mock_publish.assert_not_called()


@pytest.mark.asyncio
@patch("app.workloads.service.start_generic_configmap_watcher")
@patch("app.workloads.service.start_kubernetes_watcher")
@patch("app.workloads.service.start_kubernetes_watcher_if_resource_exists")
@patch("app.workloads.service.get_installed_version_for_custom_resource")
async def test_start_watching_workload_components(
    mock_version: MagicMock,
    mocked_optional_watcher: MagicMock,
    mock_watcher: MagicMock,
    mock_configmap_watcher: MagicMock,
) -> None:
    # Configure mock_watcher to return a completed future
    mock_watcher.return_value = asyncio.Future()
    mock_watcher.return_value.set_result(None)

    mocked_optional_watcher.return_value = asyncio.Future()
    mocked_optional_watcher.return_value.set_result(None)

    mock_configmap_watcher.return_value = asyncio.Future()
    mock_configmap_watcher.return_value.set_result(None)

    mock_version.return_value = "v1"

    await start_watching_workload_components()

    # Includes job, deployment, configmap, service, kaiwojob, kaiwoservice, aimservice, statefulset, daemonset, cronjob, pod
    assert mock_watcher.call_count == 10
    assert mock_configmap_watcher.call_count == 1

    assert mocked_optional_watcher.call_count == 2  # httproute, ingress
    assert mock_version.call_count == 4  # KaiwoJob, KaiwoService, HTTPRoute, AIMService

    optional_watcher_names = [
        call_item.kwargs.get("watcher_name") for call_item in mocked_optional_watcher.call_args_list if call_item.kwargs
    ]
    assert "http_route_watcher" in optional_watcher_names
    assert "ingress_watcher" in optional_watcher_names


@patch("app.workloads.service.__publish_auto_discovered_workload_component")
@patch("app.workloads.service.__publish_workload_component_status_update")
async def test_process_workload_component_event_handles_auto_discovered_components(
    mock_publish_workload_component_status_update: AsyncMock,
    mock_publish_auto_discovered_workload_component: AsyncMock,
) -> None:
    mock_resource = MagicMock()
    mock_resource.kind = "KaiwoJob"
    mock_resource.api_version = "v1alphav1"
    mock_resource.metadata.name = "service-one"
    workload_id = str(uuid4())
    component_id = str(uuid4())
    project_id = str(uuid4())
    mock_resource.metadata.labels = {
        WORKLOAD_ID_LABEL: workload_id,
        COMPONENT_ID_LABEL: component_id,
        PROJECT_ID_LABEL: project_id,
    }
    mock_resource.metadata.annotations = {
        WORKLOAD_SUBMITTER_ANNOTATION: "submitter",
        AUTO_DISCOVERED_WORKLOAD_ANNOTATION: "true",
    }

    mock_get_status = MagicMock()
    mock_get_status.return_value = (KaiwoJobStatus.STARTING, "KaiwoJob is available")

    await __process_workload_component_event(mock_resource, "ADDED", mock_get_status)

    mock_publish_auto_discovered_workload_component.assert_called_once()
    mock_publish_workload_component_status_update.assert_called_once()


@patch("app.workloads.service.get_common_vhost_connection_and_channel")
@patch("app.workloads.service.publish_to_common_feedback_queue")
async def test_publish_auto_discovered_workload_component(
    mock_publish: MagicMock,
    mock_get_conn_chan: AsyncMock,
) -> None:
    mock_get_conn_chan.return_value = (AsyncMock(), AsyncMock())
    workload_id = uuid4()
    component_id = uuid4()
    project_id = uuid4()

    workload_component_data = WorkloadComponentData(
        workload_id=workload_id,
        component_id=component_id,
        project_id=project_id,
        kind=WorkloadComponentKind.KAIWO_JOB,
        name="job",
        api_version="v1alpha1",
        auto_discovered=True,
        submitter="test-submitter",
    )
    await __publish_auto_discovered_workload_component(workload_component_data)

    mock_publish.assert_called_once()
    published_message = mock_publish.call_args[1]["message"]
    assert published_message.kind == WorkloadComponentKind.KAIWO_JOB
    assert published_message.name == "job"
    assert published_message.api_version == "v1alpha1"
    assert str(published_message.workload_id) == str(workload_id)
    assert str(published_message.component_id) == str(component_id)
    assert str(published_message.project_id) == str(project_id)
    assert published_message.submitter == "test-submitter"
