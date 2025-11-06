# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from kubernetes.client import ApiException
from kubernetes.client.models import (
    V1CustomResourceDefinition,
    V1CustomResourceDefinitionSpec,
    V1CustomResourceDefinitionVersion,
)

from airm.workloads.constants import WORKLOAD_ID_LABEL
from app.kubernetes.watcher import __watch_k8s_resources, get_installed_version_for_custom_resource


def test___watch_k8s_resources():
    callback = AsyncMock()
    callback.return_value = True
    mock_resource = MagicMock()
    mock_resource.kind = "Job"
    mock_resource.metadata.name = "test-job"
    mock_resource.metadata.labels = {WORKLOAD_ID_LABEL: uuid4()}
    watch_function = MagicMock()
    watch_function.__name__ = "test_watch_function"

    with patch("app.kubernetes.watcher.watch", return_value=MagicMock()) as mock_watch:
        mock_watch.Watch.return_value.stream.side_effect = [
            [{"type": "ADDED", "object": mock_resource, "raw_object": MagicMock()}]
        ]

        thread = threading.Thread(
            target=__watch_k8s_resources,
            args=("test_watch_function", watch_function, callback, asyncio.new_event_loop()),
            daemon=True,
        )
        thread.start()

        time.sleep(0.1)
        callback.assert_called_with(mock_resource, "ADDED")


def test_get_installed_version_for_custom_resource_returns_version_when_crd_has_storage_version():
    mock_client = MagicMock()
    versions = [
        V1CustomResourceDefinitionVersion(name="v1alpha1", served=True, storage=False),
        V1CustomResourceDefinitionVersion(name="v1beta1", served=True, storage=True),
    ]
    crd_spec = V1CustomResourceDefinitionSpec(
        versions=versions, group="example.com", names={"plural": "resources"}, scope="Namespaced"
    )
    mock_crd = V1CustomResourceDefinition(spec=crd_spec)
    mock_client.ApiextensionsV1Api.return_value.read_custom_resource_definition.return_value = mock_crd

    result = get_installed_version_for_custom_resource(mock_client, "example.com", "resources")
    assert result == "v1beta1"


def test_get_installed_version_for_custom_resource_returns_version_when_crd_has_served_version():
    mock_client = MagicMock()
    versions = [
        V1CustomResourceDefinitionVersion(name="v1alpha1", served=True, storage=False),
        V1CustomResourceDefinitionVersion(name="v1beta1", served=False, storage=False),
    ]
    crd_spec = V1CustomResourceDefinitionSpec(
        versions=versions, group="example.com", names={"plural": "resources"}, scope="Namespaced"
    )
    mock_crd = V1CustomResourceDefinition(spec=crd_spec)
    mock_client.ApiextensionsV1Api.return_value.read_custom_resource_definition.return_value = mock_crd

    result = get_installed_version_for_custom_resource(mock_client, "example.com", "resources")
    assert result == "v1alpha1"


def test_get_installed_version_for_custom_resource_returns_none_when_crd_not_found():
    mock_client = MagicMock()
    mock_client.ApiextensionsV1Api.return_value.read_custom_resource_definition.side_effect = ApiException(status=404)

    result = get_installed_version_for_custom_resource(mock_client, "example.com", "resources")
    assert result is None


def test_get_installed_version_for_custom_resource_raises_exception_for_other_api_errors():
    mock_client = MagicMock()
    mock_client.ApiextensionsV1Api.return_value.read_custom_resource_definition.side_effect = ApiException(status=500)

    with pytest.raises(ApiException):
        get_installed_version_for_custom_resource(mock_client, "example.com", "resources")
