# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Cluster resources service for AIWB API."""

from loguru import logger

from ..custom_models.constants import DEFAULT_AIM_DEPLOYMENT_IMAGE_REF, RADEON_AIM_DEPLOYMENT_IMAGE_REF
from ..dispatch.kube_client import KubernetesClient
from .constants import (
    AMD_GPU_DEVICE_ID_LABEL,
    AMD_GPU_DEVICE_ID_LABEL_BETA,
    AMD_GPU_PRODUCT_NAME_LABEL,
    AMD_GPU_PRODUCT_NAME_LABEL_BETA,
    AMD_GPU_RESOURCE,
)
from .schemas import (
    AimImageFamily,
    AvailableResources,
    ClusterAccelerator,
    ClusterResourcesData,
    ClusterResourcesResponse,
)
from .utils import (
    get_amd_gpu_allocatable_from_node,
    is_node_ready,
    node_device_id_and_product_name,
    parse_container_image_repository_and_tag,
    preferred_accelerator_product_name,
)


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
    amd_gpus = allocatable.get(AMD_GPU_RESOURCE, "0")
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
            if not is_node_ready(node):
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

    except Exception:
        logger.exception("Failed to get cluster resources")
        raise


async def get_cluster_gpu_device_info(kube_client: KubernetesClient) -> dict[str, str]:
    """Get AMD GPU device IDs and display names from ready cluster nodes.

    Returns a dict mapping device_id → display_name. Display name is read from
    the amd.com/gpu.product-name node label (underscores replaced with spaces).
    Falls back to the raw device ID when the label is absent.
    """
    try:
        nodes_response = await kube_client.core_v1.list_node()
        nodes = nodes_response.items if hasattr(nodes_response, "items") else []

        device_info: dict[str, str] = {}
        for node in nodes:
            if not is_node_ready(node):
                continue

            if hasattr(node, "metadata") and node.metadata:
                labels = node.metadata.labels or {}
                device_id = labels.get(AMD_GPU_DEVICE_ID_LABEL) or labels.get(AMD_GPU_DEVICE_ID_LABEL_BETA)
                if device_id:
                    product_name = labels.get(AMD_GPU_PRODUCT_NAME_LABEL) or labels.get(AMD_GPU_PRODUCT_NAME_LABEL_BETA)
                    device_info[device_id] = product_name.replace("_", " ") if product_name else device_id

        return device_info

    except Exception:
        logger.exception("Failed to get cluster GPU device info")
        raise


async def get_cluster_accelerators(kube_client: KubernetesClient) -> list[ClusterAccelerator]:
    """List accelerator products on the cluster with allocatable GPU counts per device id."""
    try:
        nodes_response = await kube_client.core_v1.list_node()
        nodes = nodes_response.items if hasattr(nodes_response, "items") else []

        aggregates: dict[str, tuple[str, int]] = {}
        for node in nodes:
            if not is_node_ready(node):
                continue
            identity = node_device_id_and_product_name(node)
            if identity is None:
                continue
            device_id, product_name = identity
            node_dict = node.to_dict() if hasattr(node, "to_dict") else {}
            gpu_count = get_amd_gpu_allocatable_from_node(node_dict)
            if device_id in aggregates:
                existing_name, existing_count = aggregates[device_id]
                name = preferred_accelerator_product_name(device_id, existing_name, product_name)
                aggregates[device_id] = (name, existing_count + gpu_count)
            else:
                aggregates[device_id] = (product_name, gpu_count)

        return [
            ClusterAccelerator(
                device_id=device_id,
                product_name=product_name,
                allocatable_count=count,
            )
            for device_id, (product_name, count) in sorted(aggregates.items(), key=lambda item: item[0])
        ]

    except Exception:
        logger.exception("Failed to get cluster accelerators")
        raise


async def get_cluster_gpu_device_ids(kube_client: KubernetesClient) -> set[str]:
    """Get AMD GPU device type IDs present in the cluster.
    Returns a set of hex device type IDs (e.g. {"74a1", "74a9"}).
    """
    try:
        nodes_response = await kube_client.core_v1.list_node()
        nodes = nodes_response.items if hasattr(nodes_response, "items") else []

        device_ids: set[str] = set()
        for node in nodes:
            if not is_node_ready(node):
                continue

            if hasattr(node, "metadata") and node.metadata:
                labels = node.metadata.labels or {}
                device_id = labels.get(AMD_GPU_DEVICE_ID_LABEL) or labels.get(AMD_GPU_DEVICE_ID_LABEL_BETA)
                if device_id:
                    device_ids.add(device_id)

        return device_ids

    except Exception:
        logger.exception("Failed to get cluster GPU device IDs")
        raise


def _resolve_cluster_base_image_ref(accelerators: list[ClusterAccelerator]) -> str:
    """Pick a temporary base image ref from detected accelerator names.

    Hybrid clusters (both Instinct and Radeon) collapse to the Instinct
    image; per-accelerator image selection is deferred.
    """
    names = [entry.product_name.casefold() for entry in accelerators]
    if any("instinct" in name for name in names):
        return DEFAULT_AIM_DEPLOYMENT_IMAGE_REF
    if any("radeon" in name for name in names):
        return RADEON_AIM_DEPLOYMENT_IMAGE_REF
    return DEFAULT_AIM_DEPLOYMENT_IMAGE_REF


async def get_cluster_base_image_ref(kube_client: KubernetesClient) -> str:
    """Return the base image ref for the accelerators detected in the cluster.

    Falls back to the default image ref when accelerators cannot be read.
    """
    try:
        accelerators = await get_cluster_accelerators(kube_client)
    except Exception as exc:
        logger.warning(f"Failed to read cluster accelerators for image discovery; using default image ref: {exc}")
        accelerators = []
    return _resolve_cluster_base_image_ref(accelerators)


async def get_aim_image_families(kube_client: KubernetesClient) -> list[AimImageFamily]:
    """Return runtime-profile image families derived from cluster accelerator labels."""
    image_ref = await get_cluster_base_image_ref(kube_client)
    repository, tag = parse_container_image_repository_and_tag(image_ref)
    family_name = repository.rsplit("/", 1)[-1]
    families = (
        AimImageFamily(
            family_id="automatic",
            display_name="Automatic",
            repository=None,
            tags=[],
        ),
        AimImageFamily(
            family_id=family_name,
            display_name=family_name,
            repository=repository,
            tags=[tag],
        ),
    )
    return [family.model_copy(deep=True) for family in families]
