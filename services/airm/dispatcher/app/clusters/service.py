# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

from aio_pika import abc
from kubernetes import client
from loguru import logger

from airm.messaging.schemas import ClusterNode, ClusterNodesMessage
from airm.utilities.memory import parse_cpu_value, parse_k8s_memory

from ..messaging.publisher import publish_to_common_feedback_queue
from .utils import get_gpu_info, get_node_status


async def publish_cluster_nodes_message_to_queue(
    connection: abc.AbstractConnection, channel: abc.AbstractChannel
) -> None:
    cluster_nodes = __get_cluster_nodes()
    await __publish_cluster_nodes_message_to_queue(cluster_nodes, connection, channel)


def __get_cluster_nodes() -> list[ClusterNode]:
    api_client = client.ApiClient()
    core_v1 = client.CoreV1Api(api_client)
    nodes_list = core_v1.list_node()

    cluster_nodes = []

    for node in nodes_list.items:
        name = node.metadata.name
        status, is_ready = get_node_status(node)

        cpu_str = node.status.allocatable.get("cpu")
        cpu_milli_cores = parse_cpu_value(cpu_str)

        memory_str = node.status.allocatable.get("memory")

        memory_bytes = parse_k8s_memory(memory_str)

        storage_str = node.status.allocatable.get("ephemeral-storage")
        ephemeral_storage_bytes = parse_k8s_memory(storage_str)

        cluster_node = ClusterNode(
            name=name,
            cpu_milli_cores=cpu_milli_cores,
            memory_bytes=memory_bytes,
            ephemeral_storage_bytes=ephemeral_storage_bytes,
            gpu_information=get_gpu_info(node),
            status=status,
            is_ready=is_ready,
        )

        cluster_nodes.append(cluster_node)

    logger.info(f"Retrieved {len(cluster_nodes)} cluster nodes")
    return cluster_nodes


async def __publish_cluster_nodes_message_to_queue(
    cluster_nodes: list[ClusterNode], connection: abc.AbstractConnection, channel: abc.AbstractChannel | None = None
) -> None:
    message = ClusterNodesMessage(
        message_type="cluster_nodes",
        cluster_nodes=cluster_nodes,
        updated_at=datetime.now(UTC),
    )

    await publish_to_common_feedback_queue(message=message, connection=connection, channel=channel)
