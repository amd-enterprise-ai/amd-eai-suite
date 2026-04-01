# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for cluster resources endpoint."""

from unittest.mock import AsyncMock, Mock

import pytest
from kubernetes_asyncio.client import V1Node, V1NodeList, V1NodeStatus

from app.cluster.service import get_cluster_resources, parse_cpu_value, parse_memory_value


def test_parse_cpu_value():
    """Test CPU value parsing."""
    assert parse_cpu_value("1") == 1000
    assert parse_cpu_value("500m") == 500
    assert parse_cpu_value("2.5") == 2500
    assert parse_cpu_value("") == 0


def test_parse_memory_value():
    """Test memory value parsing."""
    assert parse_memory_value("1024Ki") == 1024 * 1024
    assert parse_memory_value("1Mi") == 1024 * 1024
    assert parse_memory_value("1Gi") == 1024 * 1024 * 1024
    assert parse_memory_value("1000") == 1000
    assert parse_memory_value("") == 0


@pytest.mark.asyncio
async def test_get_cluster_resources():
    """Test getting cluster resources."""
    # Create mock Kubernetes client
    mock_kube_client = Mock()

    # Create mock node
    mock_node = Mock(spec=V1Node)
    mock_node.status = Mock(spec=V1NodeStatus)

    # Set up allocatable resources
    allocatable = {
        "cpu": "4",
        "memory": "8Gi",
        "ephemeral-storage": "100Gi",
        "nvidia.com/gpu": "2",
    }
    mock_node.status.allocatable = allocatable

    # Set node as ready
    mock_condition = Mock()
    mock_condition.type = "Ready"
    mock_condition.status = "True"
    mock_node.status.conditions = [mock_condition]

    # Mock to_dict method
    mock_node.to_dict = Mock(return_value={"status": {"allocatable": allocatable}})

    # Create mock node list response
    mock_response = Mock(spec=V1NodeList)
    mock_response.items = [mock_node]

    # Set up async mock for list_node
    mock_kube_client.core_v1 = Mock()
    mock_kube_client.core_v1.list_node = AsyncMock(return_value=mock_response)

    # Call the service function
    result = await get_cluster_resources(mock_kube_client)

    # Verify the result
    assert result.data.total_node_count == 1
    assert result.data.available_resources.cpu_milli_cores == 4000
    assert result.data.available_resources.memory_bytes == 8 * 1024 * 1024 * 1024
    assert result.data.available_resources.ephemeral_storage_bytes == 100 * 1024 * 1024 * 1024
    assert result.data.available_resources.gpu_count == 2


@pytest.mark.asyncio
async def test_get_cluster_resources_multiple_nodes():
    """Test getting cluster resources with multiple nodes."""
    # Create mock Kubernetes client
    mock_kube_client = Mock()

    # Create two mock nodes
    nodes = []
    for i in range(2):
        mock_node = Mock(spec=V1Node)
        mock_node.status = Mock(spec=V1NodeStatus)

        allocatable = {
            "cpu": "8",
            "memory": "16Gi",
            "ephemeral-storage": "200Gi",
            "amd.com/gpu": "4",
        }
        mock_node.status.allocatable = allocatable

        mock_condition = Mock()
        mock_condition.type = "Ready"
        mock_condition.status = "True"
        mock_node.status.conditions = [mock_condition]

        mock_node.to_dict = Mock(return_value={"status": {"allocatable": allocatable}})

        nodes.append(mock_node)

    # Create mock node list response
    mock_response = Mock(spec=V1NodeList)
    mock_response.items = nodes

    # Set up async mock for list_node
    mock_kube_client.core_v1 = Mock()
    mock_kube_client.core_v1.list_node = AsyncMock(return_value=mock_response)

    # Call the service function
    result = await get_cluster_resources(mock_kube_client)

    # Verify the result (2 nodes)
    assert result.data.total_node_count == 2
    assert result.data.available_resources.cpu_milli_cores == 16000  # 8000 * 2
    assert result.data.available_resources.memory_bytes == 32 * 1024 * 1024 * 1024  # 16Gi * 2
    assert result.data.available_resources.ephemeral_storage_bytes == 400 * 1024 * 1024 * 1024  # 200Gi * 2
    assert result.data.available_resources.gpu_count == 8  # 4 * 2
