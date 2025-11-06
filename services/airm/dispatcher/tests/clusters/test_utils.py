# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
from kubernetes.client import V1Node, V1NodeCondition, V1NodeSpec, V1NodeStatus, V1ObjectMeta

from airm.messaging.schemas import GPUInformation, GPUVendor
from app.clusters.constants import GPU_CAPACITY_KEY, GPU_DEVICE_ID_LABELS, GPU_PRODUCT_NAME_LABELS, GPU_VRAM_LABELS
from app.clusters.utils import get_gpu_info, get_node_status


@pytest.mark.parametrize(
    "conditions,unschedulable,expected_status,expected_ready",
    [
        ([], False, "Unknown", False),
        # Ready = True
        ([V1NodeCondition(type="Ready", status="True")], False, "Ready", True),
        # Ready = False
        ([V1NodeCondition(type="Ready", status="False")], False, "NotReady", False),
        # Unschedulable overrides
        ([V1NodeCondition(type="Ready", status="True")], True, "Ready, SchedulingDisabled", False),
        # Problematic condition: DiskPressure
        (
            [V1NodeCondition(type="Ready", status="True"), V1NodeCondition(type="DiskPressure", status="True")],
            False,
            "Ready, DiskPressure",
            True,
        ),
        # Unknown since no conditions
        ([], True, "Unknown", False),
    ],
)
def test_get_node_status(conditions, unschedulable, expected_status, expected_ready):
    node = V1Node(status=V1NodeStatus(conditions=conditions or []), spec=V1NodeSpec(unschedulable=unschedulable))
    status, ready = get_node_status(node)
    assert status == expected_status
    assert ready == expected_ready


@pytest.mark.parametrize(
    "capacity,labels,expected_gpu_info",
    [
        # No GPU
        ({}, {}, None),
        # GPU capacity, without labels
        (
            {GPU_CAPACITY_KEY: "2"},
            {},
            GPUInformation(
                count=2, type="Unknown", vendor=GPUVendor.AMD, vram_bytes_per_device=0, product_name="Unknown"
            ),
        ),
        # All AMD labels
        (
            {GPU_CAPACITY_KEY: "8"},
            {
                GPU_DEVICE_ID_LABELS[0]: "74a9",
                GPU_PRODUCT_NAME_LABELS[0]: "AMD_Instinct_MI300X_OAM",
                GPU_VRAM_LABELS[0]: "192G",
            },
            GPUInformation(
                count=8,
                type="74a9",
                vendor=GPUVendor.AMD,
                vram_bytes_per_device=192 * (1024**3),
                product_name="AMD Instinct MI300X OAM",
            ),
        ),
        # All AMD Beta labels
        (
            {GPU_CAPACITY_KEY: "8"},
            {
                GPU_DEVICE_ID_LABELS[1]: "74a9",
                GPU_PRODUCT_NAME_LABELS[1]: "AMD_Instinct_MI300X_OAM",
                GPU_VRAM_LABELS[1]: "192G",
            },
            GPUInformation(
                count=8,
                type="74a9",
                vendor=GPUVendor.AMD,
                vram_bytes_per_device=192 * (1024**3),
                product_name="AMD Instinct MI300X OAM",
            ),
        ),
    ],
)
def test_get_gpu_info(capacity, labels, expected_gpu_info):
    node = V1Node(
        status=V1NodeStatus(capacity=capacity or {}),
        metadata=V1ObjectMeta(labels=labels or {}),
    )
    result = get_gpu_info(node)
    if expected_gpu_info is None:
        assert result is None
    else:
        assert isinstance(result, GPUInformation)
        assert result == expected_gpu_info
