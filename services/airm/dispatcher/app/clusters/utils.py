# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from kubernetes.client.models import V1Node

from airm.messaging.schemas import GPUInformation, GPUVendor
from airm.utilities.memory import parse_gpu_vram_memory

from .constants import (
    GPU_CAPACITY_KEY,
    GPU_DEVICE_ID_LABELS,
    GPU_PRODUCT_NAME_LABELS,
    GPU_VRAM_LABELS,
    PROBLEMATIC_NODE_CONDITIONS,
)


def get_node_status(node: V1Node) -> tuple[str, bool]:
    if not node.status.conditions:
        return "Unknown", False

    status_parts = []
    is_ready = False

    for condition in node.status.conditions:
        if condition.type == "Ready":
            if condition.status == "True":
                status_parts.append("Ready")
                is_ready = True
            else:
                status_parts.append("NotReady")
            break

    if node.spec and node.spec.unschedulable:
        status_parts.append("SchedulingDisabled")
        is_ready = False

    if not status_parts:
        status_parts.append("Unknown")

    for condition in node.status.conditions:
        if condition.type in PROBLEMATIC_NODE_CONDITIONS and condition.status == "True":
            status_parts.append(condition.type)

    combined_status = ", ".join(status_parts)

    return combined_status, is_ready


def get_gpu_info(node: V1Node) -> GPUInformation | None:
    gpu_capacity = node.status.capacity.get(GPU_CAPACITY_KEY)
    if not gpu_capacity:
        return None

    labels: dict[str, str] = node.metadata.labels or {}

    gpu_type = next((labels[k] for k in GPU_DEVICE_ID_LABELS if k in labels), "Unknown")
    product_name = next((labels[k].replace("_", " ") for k in GPU_PRODUCT_NAME_LABELS if k in labels), "Unknown")
    vram_bytes = next((parse_gpu_vram_memory(labels[k]) for k in GPU_VRAM_LABELS if k in labels), 0)

    return GPUInformation(
        count=int(gpu_capacity),
        type=gpu_type,
        vendor=GPUVendor.AMD,
        vram_bytes_per_device=vram_bytes,
        product_name=product_name,
    )
