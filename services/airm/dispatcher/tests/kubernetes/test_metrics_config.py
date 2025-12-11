# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.kubernetes.metrics_config import __get_configmap_data, get_metrics_cluster_info


@pytest.mark.asyncio
@patch("app.kubernetes.metrics_config.client.CoreV1Api")
async def test_get_configmap_data(mock_core_v1_api: MagicMock) -> None:
    # Mock the Kubernetes API response
    mock_configmap = AsyncMock()
    mock_configmap.data = {
        "config.json": '{"GPUConfig": {"CustomLabels": {"ORG_NAME": "test-org", "KUBE_CLUSTER_NAME": "test-cluster"}}}'
    }
    mock_core_v1_api.return_value.read_namespaced_config_map.return_value = mock_configmap

    # Call the function
    namespace = "test-namespace"
    configmap_name = "test-configmap"
    result = await __get_configmap_data(namespace, configmap_name)

    # Assertions
    assert result == {"GPUConfig": {"CustomLabels": {"ORG_NAME": "test-org", "KUBE_CLUSTER_NAME": "test-cluster"}}}
    mock_core_v1_api.return_value.read_namespaced_config_map.assert_called_once_with(configmap_name, namespace)


@pytest.mark.asyncio
@patch("app.kubernetes.metrics_config.__get_configmap_data")
async def test_get_metrics_cluster_info(mock_get_configmap_data: AsyncMock) -> None:
    # Mock the get_configmap_data response
    mock_get_configmap_data.return_value = {
        "GPUConfig": {"CustomLabels": {"ORG_NAME": "test-org", "KUBE_CLUSTER_NAME": "test-cluster"}}
    }

    # Call the function
    namespace = "test-namespace"
    configmap_name = "test-configmap"
    org_name, cluster_name = await get_metrics_cluster_info(namespace, configmap_name)

    # Assertions
    assert org_name == "test-org"
    assert cluster_name == "test-cluster"
    mock_get_configmap_data.assert_called_once_with(namespace, configmap_name)
