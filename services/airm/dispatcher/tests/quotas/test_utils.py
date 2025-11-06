# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from airm.messaging.schemas import ClusterQuotaAllocation, ClusterQuotasAllocationMessage, GPUVendor, PriorityClass
from app.quotas.constants import (
    AMD_GPU_RESOURCE,
    CPU_RESOURCE,
    DEFAULT_COHORT_NAME,
    DEFAULT_RESOURCE_FLAVOUR_NAME,
    EPHEMERAL_STORAGE_RESOURCE,
    KAIWO_QUEUE_CONFIG_DEFAULT_NAME,
    MEMORY_RESOURCE,
)
from app.quotas.schemas import (
    ClusterQueue,
    ClusterQueueSpec,
    Flavor,
    KaiwoQueueConfig,
    KaiwoQueueConfigSpec,
    PreemptionPolicy,
    Resource,
    ResourceGroup,
)
from app.quotas.service import convert_to_cluster_quotas_allocations, convert_to_kaiwo_queue_config


def test_convert_to_kaiwo_queue_config_amd():
    quotas = ClusterQuotasAllocationMessage(
        message_type="cluster_quotas_allocation",
        gpu_vendor=GPUVendor.AMD,
        quota_allocations=[
            ClusterQuotaAllocation(
                quota_name="quota-1",
                cpu_milli_cores=4000,
                gpu_count=8,
                memory_bytes=8192,
                ephemeral_storage_bytes=2048,
                namespaces=["quota-1"],
            )
        ],
        priority_classes=[
            PriorityClass(
                name="high-priority",
                priority=1000,
            )
        ],
    )
    result = convert_to_kaiwo_queue_config(quotas)

    expected_result = {
        "apiVersion": "kaiwo.silogen.ai/v1alpha1",
        "kind": "KaiwoQueueConfig",
        "metadata": {"name": KAIWO_QUEUE_CONFIG_DEFAULT_NAME},
        "spec": {
            "resourceFlavors": [{"name": DEFAULT_RESOURCE_FLAVOUR_NAME}],
            "workloadPriorityClasses": [
                {
                    "metadata": {"name": "high-priority"},
                    "value": 1000,
                    "description": "Priority class high-priority with priority 1000",
                },
            ],
            "clusterQueues": [
                {
                    "name": "quota-1",
                    "namespaces": ["quota-1"],
                    "spec": {
                        "flavorFungibility": {"whenCanBorrow": "Borrow", "whenCanPreempt": "Preempt"},
                        "cohort": DEFAULT_COHORT_NAME,
                        "namespaceSelector": {},
                        "preemption": {
                            "borrowWithinCohort": {"policy": "Never"},
                            "reclaimWithinCohort": "Any",
                            "withinClusterQueue": "LowerPriority",
                        },
                        "queueingStrategy": "BestEffortFIFO",
                        "resourceGroups": [
                            {
                                "coveredResources": ["cpu", "memory", "ephemeral-storage", "amd.com/gpu"],
                                "flavors": [
                                    {
                                        "name": DEFAULT_RESOURCE_FLAVOUR_NAME,
                                        "resources": [
                                            {"name": "cpu", "nominalQuota": "4000m"},
                                            {"name": "memory", "nominalQuota": "8192"},
                                            {"name": "ephemeral-storage", "nominalQuota": "2048"},
                                            {"name": "amd.com/gpu", "nominalQuota": "8"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "stopPolicy": "None",
                    },
                }
            ],
        },
    }

    assert result.model_dump() == expected_result


def test_convert_to_kaiwo_queue_config_nvidia():
    quotas = ClusterQuotasAllocationMessage(
        message_type="cluster_quotas_allocation",
        gpu_vendor=GPUVendor.NVIDIA,
        quota_allocations=[
            ClusterQuotaAllocation(
                quota_name="quota-1",
                cpu_milli_cores=4000,
                gpu_count=2,
                memory_bytes=8192,
                ephemeral_storage_bytes=2048,
                namespaces=["quota-1"],
            )
        ],
        priority_classes=[
            PriorityClass(
                name="high-priority",
                priority=1000,
            )
        ],
    )
    result = convert_to_kaiwo_queue_config(quotas)

    expected_result = {
        "apiVersion": "kaiwo.silogen.ai/v1alpha1",
        "kind": "KaiwoQueueConfig",
        "metadata": {"name": KAIWO_QUEUE_CONFIG_DEFAULT_NAME},
        "spec": {
            "resourceFlavors": [{"name": DEFAULT_RESOURCE_FLAVOUR_NAME}],
            "workloadPriorityClasses": [
                {
                    "metadata": {"name": "high-priority"},
                    "value": 1000,
                    "description": "Priority class high-priority with priority 1000",
                },
            ],
            "clusterQueues": [
                {
                    "name": "quota-1",
                    "namespaces": ["quota-1"],
                    "spec": {
                        "flavorFungibility": {"whenCanBorrow": "Borrow", "whenCanPreempt": "Preempt"},
                        "cohort": DEFAULT_COHORT_NAME,
                        "namespaceSelector": {},
                        "preemption": {
                            "borrowWithinCohort": {"policy": "Never"},
                            "reclaimWithinCohort": "Any",
                            "withinClusterQueue": "LowerPriority",
                        },
                        "queueingStrategy": "BestEffortFIFO",
                        "resourceGroups": [
                            {
                                "coveredResources": ["cpu", "memory", "ephemeral-storage", "nvidia.com/gpu"],
                                "flavors": [
                                    {
                                        "name": DEFAULT_RESOURCE_FLAVOUR_NAME,
                                        "resources": [
                                            {"name": "cpu", "nominalQuota": "4000m"},
                                            {"name": "memory", "nominalQuota": "8192"},
                                            {"name": "ephemeral-storage", "nominalQuota": "2048"},
                                            {"name": "nvidia.com/gpu", "nominalQuota": "2"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "stopPolicy": "None",
                    },
                }
            ],
        },
    }

    assert result.model_dump() == expected_result


def test_convert_to_kaiwo_queue_config_multiple_quotas():
    quotas = ClusterQuotasAllocationMessage(
        message_type="cluster_quotas_allocation",
        gpu_vendor=None,
        quota_allocations=[
            ClusterQuotaAllocation(
                quota_name="quota-1",
                cpu_milli_cores=2000,
                gpu_count=0,
                memory_bytes=2048,
                ephemeral_storage_bytes=1024,
                namespaces=["quota-1"],
            ),
            ClusterQuotaAllocation(
                quota_name="quota-2",
                cpu_milli_cores=1000,
                gpu_count=0,
                memory_bytes=1024,
                ephemeral_storage_bytes=512,
                namespaces=["quota-2"],
            ),
        ],
        priority_classes=[
            PriorityClass(
                name="high-priority",
                priority=1000,
            )
        ],
    )
    result = convert_to_kaiwo_queue_config(quotas)

    expected_result = {
        "apiVersion": "kaiwo.silogen.ai/v1alpha1",
        "kind": "KaiwoQueueConfig",
        "metadata": {"name": KAIWO_QUEUE_CONFIG_DEFAULT_NAME},
        "spec": {
            "resourceFlavors": [{"name": DEFAULT_RESOURCE_FLAVOUR_NAME}],
            "workloadPriorityClasses": [
                {
                    "metadata": {"name": "high-priority"},
                    "value": 1000,
                    "description": "Priority class high-priority with priority 1000",
                },
            ],
            "clusterQueues": [
                {
                    "name": "quota-1",
                    "namespaces": ["quota-1"],
                    "spec": {
                        "flavorFungibility": {"whenCanBorrow": "Borrow", "whenCanPreempt": "Preempt"},
                        "cohort": DEFAULT_COHORT_NAME,
                        "namespaceSelector": {},
                        "preemption": {
                            "borrowWithinCohort": {"policy": "Never"},
                            "reclaimWithinCohort": "Any",
                            "withinClusterQueue": "LowerPriority",
                        },
                        "queueingStrategy": "BestEffortFIFO",
                        "resourceGroups": [
                            {
                                "coveredResources": ["cpu", "memory", "ephemeral-storage"],
                                "flavors": [
                                    {
                                        "name": DEFAULT_RESOURCE_FLAVOUR_NAME,
                                        "resources": [
                                            {"name": "cpu", "nominalQuota": "2000m"},
                                            {"name": "memory", "nominalQuota": "2048"},
                                            {"name": "ephemeral-storage", "nominalQuota": "1024"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "stopPolicy": "None",
                    },
                },
                {
                    "name": "quota-2",
                    "namespaces": ["quota-2"],
                    "spec": {
                        "flavorFungibility": {"whenCanBorrow": "Borrow", "whenCanPreempt": "Preempt"},
                        "cohort": DEFAULT_COHORT_NAME,
                        "namespaceSelector": {},
                        "preemption": {
                            "borrowWithinCohort": {"policy": "Never"},
                            "reclaimWithinCohort": "Any",
                            "withinClusterQueue": "LowerPriority",
                        },
                        "queueingStrategy": "BestEffortFIFO",
                        "resourceGroups": [
                            {
                                "coveredResources": ["cpu", "memory", "ephemeral-storage"],
                                "flavors": [
                                    {
                                        "name": DEFAULT_RESOURCE_FLAVOUR_NAME,
                                        "resources": [
                                            {"name": "cpu", "nominalQuota": "1000m"},
                                            {"name": "memory", "nominalQuota": "1024"},
                                            {"name": "ephemeral-storage", "nominalQuota": "512"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "stopPolicy": "None",
                    },
                },
            ],
        },
    }

    assert result.model_dump() == expected_result


def test_convert_to_kaiwo_queue_config_no_quotas():
    result = convert_to_kaiwo_queue_config(
        ClusterQuotasAllocationMessage(
            message_type="cluster_quotas_allocation",
            gpu_vendor=None,
            quota_allocations=[],
            priority_classes=[
                PriorityClass(
                    name="high-priority",
                    priority=1000,
                )
            ],
        )
    )

    # Expected output for an empty quota allocations list
    expected_result = {
        "apiVersion": "kaiwo.silogen.ai/v1alpha1",
        "kind": "KaiwoQueueConfig",
        "metadata": {"name": KAIWO_QUEUE_CONFIG_DEFAULT_NAME},
        "spec": {
            "resourceFlavors": [{"name": DEFAULT_RESOURCE_FLAVOUR_NAME}],
            "clusterQueues": [],
            "workloadPriorityClasses": [
                {
                    "metadata": {"name": "high-priority"},
                    "value": 1000,
                    "description": "Priority class high-priority with priority 1000",
                },
            ],
        },
    }

    assert result.model_dump() == expected_result


def test_convert_to_cluster_quotas_allocations():
    queue_config = KaiwoQueueConfig(
        apiVersion="v1",
        kind="KaiwoQueueConfig",
        metadata={},
        spec=KaiwoQueueConfigSpec(
            clusterQueues=[
                ClusterQueue(
                    name="test-queue",
                    namespaces=["test-queue"],
                    spec=ClusterQueueSpec(
                        flavorFungibility={},
                        namespaceSelector={},
                        cohort="test-cohort",
                        preemption=PreemptionPolicy(
                            borrowWithinCohort={},
                            reclaimWithinCohort="strict",
                            withinClusterQueue="fair",
                        ),
                        queueingStrategy="fifo",
                        stopPolicy="none",
                        resourceGroups=[
                            ResourceGroup(
                                coveredResources=[
                                    CPU_RESOURCE,
                                    MEMORY_RESOURCE,
                                    EPHEMERAL_STORAGE_RESOURCE,
                                    AMD_GPU_RESOURCE,
                                ],
                                flavors=[
                                    Flavor(
                                        name="default",
                                        resources=[
                                            Resource(name=CPU_RESOURCE, nominalQuota="2000m"),
                                            Resource(name=MEMORY_RESOURCE, nominalQuota="4096"),
                                            Resource(name=EPHEMERAL_STORAGE_RESOURCE, nominalQuota="10240"),
                                            Resource(name=AMD_GPU_RESOURCE, nominalQuota="2"),
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                ),
                ClusterQueue(
                    name="test-queue-2",
                    namespaces=["test-queue-2"],
                    spec=ClusterQueueSpec(
                        flavorFungibility={},
                        namespaceSelector={},
                        cohort="test-cohort",
                        preemption=PreemptionPolicy(
                            borrowWithinCohort={},
                            reclaimWithinCohort="strict",
                            withinClusterQueue="fair",
                        ),
                        queueingStrategy="fifo",
                        stopPolicy="none",
                        resourceGroups=[
                            ResourceGroup(
                                coveredResources=[
                                    CPU_RESOURCE,
                                    MEMORY_RESOURCE,
                                    EPHEMERAL_STORAGE_RESOURCE,
                                    AMD_GPU_RESOURCE,
                                ],
                                flavors=[
                                    Flavor(
                                        name="default",
                                        resources=[
                                            Resource(name=CPU_RESOURCE, nominalQuota="2"),
                                            Resource(name=MEMORY_RESOURCE, nominalQuota="4Ki"),
                                            Resource(name=EPHEMERAL_STORAGE_RESOURCE, nominalQuota="1Ki"),
                                            Resource(name=AMD_GPU_RESOURCE, nominalQuota="2"),
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                ),
            ],
            resourceFlavors=[],
            workloadPriorityClasses=[
                {
                    "metadata": {"name": "high-priority"},
                    "value": 1000,
                    "description": "Priority class high-priority with priority 1000",
                },
            ],
        ),
    )

    allocations = convert_to_cluster_quotas_allocations(queue_config)

    assert len(allocations) == 2
    assert allocations[0].cpu_milli_cores == 2000
    assert allocations[0].gpu_count == 2
    assert allocations[0].memory_bytes == 4096
    assert allocations[0].ephemeral_storage_bytes == 10240
    assert allocations[0].quota_name == "test-queue"
    assert allocations[0].namespaces == ["test-queue"]

    assert allocations[1].cpu_milli_cores == 2000
    assert allocations[1].gpu_count == 2
    assert allocations[1].memory_bytes == 4096
    assert allocations[1].ephemeral_storage_bytes == 1024
    assert allocations[1].quota_name == "test-queue-2"
    assert allocations[1].namespaces == ["test-queue-2"]


def test_convert_to_cluster_quotas_allocations_missing_resources():
    queue_config = KaiwoQueueConfig(
        apiVersion="v1",
        kind="KaiwoQueueConfig",
        metadata={},
        spec=KaiwoQueueConfigSpec(
            clusterQueues=[
                ClusterQueue(
                    name="test-queue",
                    namespaces=["test-queue"],
                    spec=ClusterQueueSpec(
                        flavorFungibility={},
                        namespaceSelector={},
                        cohort="test-cohort",
                        preemption=PreemptionPolicy(
                            borrowWithinCohort={},
                            reclaimWithinCohort="strict",
                            withinClusterQueue="fair",
                        ),
                        queueingStrategy="fifo",
                        stopPolicy="none",
                        resourceGroups=[
                            ResourceGroup(
                                coveredResources=[CPU_RESOURCE, MEMORY_RESOURCE],
                                flavors=[
                                    Flavor(
                                        name="default",
                                        resources=[],
                                    )
                                ],
                            )
                        ],
                    ),
                )
            ],
            resourceFlavors=[],
            workloadPriorityClasses=[
                {
                    "metadata": {"name": "high-priority"},
                    "value": 1000,
                    "description": "Priority class high-priority with priority 1000",
                },
            ],
        ),
    )

    allocations = convert_to_cluster_quotas_allocations(queue_config)

    assert len(allocations) == 1
    assert allocations[0].cpu_milli_cores == 0
    assert allocations[0].gpu_count == 0
    assert allocations[0].memory_bytes == 0
    assert allocations[0].ephemeral_storage_bytes == 0
    assert allocations[0].quota_name == "test-queue"
    assert allocations[0].namespaces == ["test-queue"]
