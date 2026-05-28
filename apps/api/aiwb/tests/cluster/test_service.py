# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for cluster resources endpoint."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from kubernetes_asyncio.client import V1Node, V1NodeList, V1NodeStatus

from app.cluster.service import get_cluster_gpu_device_ids, get_cluster_resources, parse_cpu_value, parse_memory_value


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


def make_node(
    device_id: str | None = None,
    ready: bool = True,
    allocatable: dict | None = None,
    beta_device_id: str | None = None,
) -> Mock:
    """Build a mock V1Node.

    Args:
        device_id: Value for the amd.com/gpu.device-id label.
        ready: Whether the node has a Ready=True condition.
        allocatable: Dict of allocatable resources (cpu, memory, etc.).
        beta_device_id: Value for the beta.amd.com/gpu.device-id label.
    """
    node = Mock(spec=V1Node)
    node.status = Mock(spec=V1NodeStatus)

    condition = Mock()
    condition.type = "Ready"
    condition.status = "True" if ready else "False"
    node.status.conditions = [condition]

    labels: dict[str, str] = {}
    if device_id:
        labels["amd.com/gpu.device-id"] = device_id
    if beta_device_id:
        labels["beta.amd.com/gpu.device-id"] = beta_device_id
    metadata = Mock()
    metadata.labels = labels
    node.metadata = metadata

    if allocatable is not None:
        node.status.allocatable = allocatable
        node.to_dict = Mock(return_value={"status": {"allocatable": allocatable}})

    return node


@pytest.mark.asyncio
async def test_get_cluster_resources():
    allocatable = {"cpu": "4", "memory": "8Gi", "ephemeral-storage": "100Gi", "amd.com/gpu": "2"}
    result = await get_cluster_resources(make_kube_client([make_node(allocatable=allocatable)]))

    assert result.data.total_node_count == 1
    assert result.data.available_resources.cpu_milli_cores == 4000
    assert result.data.available_resources.memory_bytes == 8 * 1024 * 1024 * 1024
    assert result.data.available_resources.ephemeral_storage_bytes == 100 * 1024 * 1024 * 1024
    assert result.data.available_resources.gpu_count == 2


@pytest.mark.asyncio
async def test_get_cluster_resources_multiple_nodes():
    allocatable = {"cpu": "8", "memory": "16Gi", "ephemeral-storage": "200Gi", "amd.com/gpu": "4"}
    nodes = [make_node(allocatable=allocatable), make_node(allocatable=allocatable)]
    result = await get_cluster_resources(make_kube_client(nodes))

    assert result.data.total_node_count == 2
    assert result.data.available_resources.cpu_milli_cores == 16000
    assert result.data.available_resources.memory_bytes == 32 * 1024 * 1024 * 1024
    assert result.data.available_resources.ephemeral_storage_bytes == 400 * 1024 * 1024 * 1024
    assert result.data.available_resources.gpu_count == 8


def make_kube_client(nodes: list[Mock]) -> Mock:
    """Build a mock KubernetesClient whose list_node returns the given nodes."""
    mock_response = Mock(spec=V1NodeList)
    mock_response.items = nodes

    mock_kube_client = Mock()
    mock_kube_client.core_v1 = Mock()
    mock_kube_client.core_v1.list_node = AsyncMock(return_value=mock_response)
    return mock_kube_client


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_returns_device_ids():
    result = await get_cluster_gpu_device_ids(make_kube_client([make_node("74a1"), make_node("74a9")]))

    assert result == {"74a1", "74a9"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_deduplicates():
    result = await get_cluster_gpu_device_ids(
        make_kube_client([make_node("74a1"), make_node("74a1"), make_node("74a1")])
    )

    assert result == {"74a1"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_no_label_returns_empty():
    result = await get_cluster_gpu_device_ids(make_kube_client([make_node(device_id=None), make_node(device_id=None)]))

    assert result == set()


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_excludes_not_ready_nodes():
    result = await get_cluster_gpu_device_ids(
        make_kube_client([make_node("74a1", ready=True), make_node("74b0", ready=False)])
    )

    assert result == {"74a1"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_falls_back_to_beta_label():
    result = await get_cluster_gpu_device_ids(make_kube_client([make_node("74a1"), make_node(beta_device_id="74b0")]))

    assert result == {"74a1", "74b0"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_propagates_kube_error():
    mock_kube_client = Mock()
    mock_kube_client.core_v1 = Mock()
    mock_kube_client.core_v1.list_node = AsyncMock(side_effect=RuntimeError("kube unavailable"))

    with patch("app.cluster.service.logger") as mock_logger:
        with pytest.raises(RuntimeError, match="kube unavailable"):
            await get_cluster_gpu_device_ids(mock_kube_client)

    mock_logger.error.assert_called_once()
