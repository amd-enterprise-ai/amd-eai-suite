# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Cluster resources service for AIWB API."""

from loguru import logger

from ..dispatch.kube_client import KubernetesClient
from .schemas import AvailableResources, ClusterResourcesData, ClusterResourcesResponse


def parse_cpu_value(cpu_str: str) -> int:
    """Parse Kubernetes CPU value to milli-cores.

    Examples:
        - "1" -> 1000 milli-cores
        - "500m" -> 500 milli-cores
        - "2.5" -> 2500 milli-cores
    """
    if not cpu_str:
        return 0

    cpu_str = cpu_str.strip()
    if cpu_str.endswith("m"):
        # Already in milli-cores
        return int(cpu_str[:-1])
    else:
        # In cores, convert to milli-cores
        return int(float(cpu_str) * 1000)


def parse_memory_value(memory_str: str) -> int:
    """Parse Kubernetes memory value to bytes.

    Supports units: Ki, Mi, Gi, Ti, K, M, G, T, and plain bytes.
    """
    if not memory_str:
        return 0

    memory_str = memory_str.strip()

    # Handle binary units (Ki, Mi, Gi, Ti)
    if memory_str.endswith("Ki"):
        return int(memory_str[:-2]) * 1024
    elif memory_str.endswith("Mi"):
        return int(memory_str[:-2]) * 1024 * 1024
    elif memory_str.endswith("Gi"):
        return int(memory_str[:-2]) * 1024 * 1024 * 1024
    elif memory_str.endswith("Ti"):
        return int(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024

    # Handle decimal units (K, M, G, T)
    elif memory_str.endswith("K"):
        return int(float(memory_str[:-1]) * 1000)
    elif memory_str.endswith("M"):
        return int(float(memory_str[:-1]) * 1000 * 1000)
    elif memory_str.endswith("G"):
        return int(float(memory_str[:-1]) * 1000 * 1000 * 1000)
    elif memory_str.endswith("T"):
        return int(float(memory_str[:-1]) * 1000 * 1000 * 1000 * 1000)

    # Plain bytes
    else:
        return int(memory_str)


def get_gpu_count_from_node(node: dict) -> int:
    """Extract GPU count from a Kubernetes node.

    Looks for nvidia.com/gpu or amd.com/gpu in allocatable resources.
    """
    allocatable = node.get("status", {}).get("allocatable", {})

    # Check for NVIDIA GPUs
    nvidia_gpus = allocatable.get("nvidia.com/gpu", "0")
    if nvidia_gpus and nvidia_gpus != "0":
        return int(nvidia_gpus)

    # Check for AMD GPUs
    amd_gpus = allocatable.get("amd.com/gpu", "0")
    if amd_gpus and amd_gpus != "0":
        return int(amd_gpus)

    return 0


async def get_cluster_resources(kube_client: KubernetesClient) -> ClusterResourcesResponse:
    """Get available cluster resources by querying Kubernetes API.

    Queries all nodes in the cluster and aggregates their allocatable resources.
    Only counts resources from ready nodes.

    Args:
        kube_client: Kubernetes client instance

    Returns:
        ClusterResourcesResponse with aggregated cluster resources
    """
    try:
        # List all nodes in the cluster
        nodes_response = await kube_client.core_v1.list_node()
        nodes = nodes_response.items if hasattr(nodes_response, "items") else []

        total_cpu_milli_cores = 0
        total_memory_bytes = 0
        total_storage_bytes = 0
        total_gpu_count = 0
        ready_node_count = 0

        for node in nodes:
            # Check if node is ready
            is_ready = False
            if hasattr(node, "status") and node.status and hasattr(node.status, "conditions"):
                for condition in node.status.conditions or []:
                    if condition.type == "Ready" and condition.status == "True":
                        is_ready = True
                        break

            if not is_ready:
                continue

            ready_node_count += 1

            # Get allocatable resources
            if hasattr(node, "status") and node.status and hasattr(node.status, "allocatable"):
                allocatable = node.status.allocatable

                # Parse CPU
                if hasattr(allocatable, "get"):
                    cpu_str = allocatable.get("cpu", "0")
                    memory_str = allocatable.get("memory", "0")
                    storage_str = allocatable.get("ephemeral-storage", "0")
                else:
                    # Handle dict-like object
                    cpu_str = getattr(allocatable, "cpu", "0")
                    memory_str = getattr(allocatable, "memory", "0")
                    storage_str = getattr(allocatable, "ephemeral_storage", "0")

                total_cpu_milli_cores += parse_cpu_value(cpu_str)
                total_memory_bytes += parse_memory_value(memory_str)
                total_storage_bytes += parse_memory_value(storage_str)

                # Count GPUs
                # Convert node object to dict for GPU parsing
                node_dict = node.to_dict() if hasattr(node, "to_dict") else {}
                total_gpu_count += get_gpu_count_from_node(node_dict)

        logger.info(
            f"Cluster resources: {ready_node_count} ready nodes, "
            f"{total_cpu_milli_cores}m CPU, "
            f"{total_memory_bytes} bytes memory, "
            f"{total_gpu_count} GPUs"
        )

        return ClusterResourcesResponse(
            data=ClusterResourcesData(
                available_resources=AvailableResources(
                    cpu_milli_cores=total_cpu_milli_cores,
                    memory_bytes=total_memory_bytes,
                    ephemeral_storage_bytes=total_storage_bytes,
                    gpu_count=total_gpu_count,
                ),
                total_node_count=ready_node_count,
            )
        )

    except Exception as e:
        logger.error(f"Failed to get cluster resources: {e}")
        raise
