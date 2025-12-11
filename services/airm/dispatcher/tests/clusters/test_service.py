# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client.models import V1Node, V1NodeList, V1NodeStatus, V1ObjectMeta

from airm.messaging.schemas import ClusterNode, GPUInformation, GPUVendor
from app.clusters.service import (
    __get_cluster_nodes,
    __publish_cluster_nodes_message_to_queue,
    publish_cluster_nodes_message_to_queue,
)


@pytest.mark.asyncio
async def test_publish_cluster_nodes_message_to_queue() -> None:
    fake_connection = MagicMock()
    fake_channel = MagicMock()
    fake_cluster_nodes = [MagicMock()]

    with (
        patch("app.clusters.service.__get_cluster_nodes", return_value=fake_cluster_nodes),
        patch("app.clusters.service.__publish_cluster_nodes_message_to_queue") as mock_publish,
    ):
        await publish_cluster_nodes_message_to_queue(fake_connection, fake_channel)

        mock_publish.assert_awaited_once_with(fake_cluster_nodes, fake_connection, fake_channel)


@pytest.mark.asyncio
async def test___publish_cluster_nodes_message_to_queue() -> None:
    fake_node = MagicMock(spec=ClusterNode)
    fake_cluster_nodes = [fake_node]

    fake_connection = MagicMock()
    fake_channel = MagicMock()

    with patch("app.clusters.service.publish_to_common_feedback_queue") as mock_publish:
        await __publish_cluster_nodes_message_to_queue(
            fake_cluster_nodes, connection=fake_connection, channel=fake_channel
        )

        assert mock_publish.await_count == 1
        assert mock_publish.await_args is not None
        kwargs = mock_publish.await_args.kwargs

        message = kwargs["message"]
        assert message.message_type == "cluster_nodes"
        assert message.cluster_nodes == fake_cluster_nodes


@pytest.mark.parametrize(
    "nodes,statuses,gpu_infos,expected",
    [
        (
            [("node-1", {"cpu": "2000m", "memory": "8Gi", "ephemeral-storage": "50Gi"})],
            [("Ready", True)],
            [None],
            [
                ClusterNode(
                    name="node-1",
                    cpu_milli_cores=2000,
                    memory_bytes=8 * 1024**3,
                    ephemeral_storage_bytes=50 * 1024**3,
                    gpu_information=None,
                    status="Ready",
                    is_ready=True,
                )
            ],
        ),
        # Single node: missing storage, NotReady, with GPU
        (
            [("node-2", {"cpu": "1000m", "memory": "4Gi", "ephemeral-storage": "5Gi"})],
            [("NotReady", False)],
            [
                GPUInformation(
                    count=1,
                    type="gfx908",
                    vendor=GPUVendor.AMD,
                    vram_bytes_per_device=16 * 1024**3,
                    product_name="MI100",
                )
            ],
            [
                ClusterNode(
                    name="node-2",
                    cpu_milli_cores=1000,
                    memory_bytes=4 * 1024**3,
                    ephemeral_storage_bytes=5 * 1024**3,
                    gpu_information=GPUInformation(
                        count=1,
                        type="gfx908",
                        vendor=GPUVendor.AMD,
                        vram_bytes_per_device=16 * 1024**3,
                        product_name="MI100",
                    ),
                    status="NotReady",
                    is_ready=False,
                )
            ],
        ),
        # Two nodes: one Ready, one Unknown
        (
            [
                ("node-3", {"cpu": "500m", "memory": "2Gi", "ephemeral-storage": "10Gi"}),
                ("node-4", {"cpu": "750m", "memory": "3Gi", "ephemeral-storage": "5Gi"}),
            ],
            [("Ready", True), ("Unknown", False)],
            [None, None],
            [
                ClusterNode(
                    name="node-3",
                    cpu_milli_cores=500,
                    memory_bytes=2 * 1024**3,
                    ephemeral_storage_bytes=10 * 1024**3,
                    gpu_information=None,
                    status="Ready",
                    is_ready=True,
                ),
                ClusterNode(
                    name="node-4",
                    cpu_milli_cores=750,
                    memory_bytes=3 * 1024**3,
                    ephemeral_storage_bytes=5 * 1024**3,
                    gpu_information=None,
                    status="Unknown",
                    is_ready=False,
                ),
            ],
        ),
    ],
)
def test___get_cluster_nodes(nodes, statuses, gpu_infos, expected):
    mock_nodes = []
    for name, allocatable in nodes:
        node = MagicMock(spec=V1Node)
        node.metadata = MagicMock(spec=V1ObjectMeta)
        node.metadata.name = name
        node.status = MagicMock(spec=V1NodeStatus)
        node.status.allocatable = allocatable
        mock_nodes.append(node)

    with (
        patch("app.clusters.service.client") as mock_client,
        patch("app.clusters.service.get_node_status", side_effect=statuses),
        patch("app.clusters.service.get_gpu_info", side_effect=gpu_infos),
    ):
        mock_core_v1 = MagicMock()
        mock_core_v1.list_node.return_value = V1NodeList(items=mock_nodes)
        mock_client.ApiClient.return_value = MagicMock()
        mock_client.CoreV1Api.return_value = mock_core_v1

        result = __get_cluster_nodes()

        # Validate number of nodes
        assert len(result) == len(expected)

        # Compare each node’s fields
        for got, exp in zip(result, expected):
            assert got == exp
