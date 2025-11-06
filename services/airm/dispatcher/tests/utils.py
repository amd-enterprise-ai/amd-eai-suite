# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock

from kubernetes.dynamic.resource import ResourceInstance


def create_mock_resource_instance(items=None):
    if items is None:
        items = []

    mock_resource_instance = MagicMock(spec=ResourceInstance)

    mock_resource_instance.items = items

    return mock_resource_instance


def create_mock_k8s_object(kind, name, namespace, api_version, labels=None, annotations=None):
    metadata = MagicMock()
    metadata.name = name
    metadata.namespace = namespace
    metadata.labels = labels
    metadata.annotations = annotations

    mock_obj = MagicMock()
    mock_obj.kind = kind
    mock_obj.api_version = api_version
    mock_obj.metadata = metadata

    return mock_obj
