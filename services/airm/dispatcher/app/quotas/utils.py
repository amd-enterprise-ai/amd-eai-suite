# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from airm.messaging.schemas import ClusterQuotaAllocation, ClusterQuotasAllocationMessage, GPUVendor
from airm.utilities.memory import parse_cpu_value, parse_k8s_memory

from .constants import (
    AMD_GPU_RESOURCE,
    CPU_RESOURCE,
    DEFAULT_COHORT_NAME,
    DEFAULT_RESOURCE_FLAVOUR_NAME,
    EPHEMERAL_STORAGE_RESOURCE,
    KAIWO_QUEUE_CONFIG_DEFAULT_NAME,
    MEMORY_RESOURCE,
    NVIDIA_GPU_RESOURCE,
)
from .schemas import (
    ClusterQueue,
    ClusterQueueSpec,
    Flavor,
    KaiwoQueueConfig,
    KaiwoQueueConfigSpec,
    PreemptionPolicy,
    Resource,
    ResourceFlavour,
    ResourceGroup,
    WorkloadPriorityClass,
)


def convert_to_kaiwo_queue_config(message: ClusterQuotasAllocationMessage) -> KaiwoQueueConfig:
    cluster_queues = []
    covered_resources = [CPU_RESOURCE, MEMORY_RESOURCE, EPHEMERAL_STORAGE_RESOURCE]
    if message.gpu_vendor == GPUVendor.NVIDIA:
        covered_resources.append(NVIDIA_GPU_RESOURCE)
    elif message.gpu_vendor == GPUVendor.AMD:
        covered_resources.append(AMD_GPU_RESOURCE)

    for quota in message.quota_allocations:
        resources = [
            Resource(name=CPU_RESOURCE, nominalQuota=f"{quota.cpu_milli_cores}m"),
            Resource(name=MEMORY_RESOURCE, nominalQuota=str(quota.memory_bytes)),
            Resource(name=EPHEMERAL_STORAGE_RESOURCE, nominalQuota=str(quota.ephemeral_storage_bytes)),
        ]
        if message.gpu_vendor == GPUVendor.NVIDIA:
            resources.append(Resource(name=NVIDIA_GPU_RESOURCE, nominalQuota=str(quota.gpu_count)))
        elif message.gpu_vendor == GPUVendor.AMD:
            resources.append(Resource(name=AMD_GPU_RESOURCE, nominalQuota=str(quota.gpu_count)))

        cluster_queue = ClusterQueue(
            name=quota.quota_name,
            namespaces=quota.namespaces,
            spec=ClusterQueueSpec(
                cohort=DEFAULT_COHORT_NAME,
                flavorFungibility={"whenCanBorrow": "Borrow", "whenCanPreempt": "Preempt"},
                namespaceSelector={},
                preemption=PreemptionPolicy(
                    borrowWithinCohort={"policy": "Never"},
                    reclaimWithinCohort="Any",
                    withinClusterQueue="LowerPriority",
                ),
                queueingStrategy="BestEffortFIFO",
                resourceGroups=[
                    ResourceGroup(
                        coveredResources=covered_resources,
                        flavors=[Flavor(name=DEFAULT_RESOURCE_FLAVOUR_NAME, resources=resources)],
                    )
                ],
                stopPolicy="None",
            ),
        )
        cluster_queues.append(cluster_queue)

    workload_priority_classes = [
        WorkloadPriorityClass(
            metadata={"name": pc.name},
            value=pc.priority,
            description=f"Priority class {pc.name} with priority {pc.priority}",
        )
        for pc in message.priority_classes
    ]

    kaiwo_queue_config_spec = KaiwoQueueConfigSpec(
        resourceFlavors=[ResourceFlavour(name=DEFAULT_RESOURCE_FLAVOUR_NAME)],
        clusterQueues=cluster_queues,
        workloadPriorityClasses=workload_priority_classes,
    )
    return KaiwoQueueConfig(
        apiVersion="kaiwo.silogen.ai/v1alpha1",
        kind="KaiwoQueueConfig",
        metadata={"name": KAIWO_QUEUE_CONFIG_DEFAULT_NAME},
        spec=kaiwo_queue_config_spec,
    )


def convert_to_cluster_quotas_allocations(kaiwo_queue_config: KaiwoQueueConfig) -> list[ClusterQuotaAllocation]:
    quota_allocations = []
    for cluster_queue in kaiwo_queue_config.spec.clusterQueues:
        for resource_group in cluster_queue.spec.resourceGroups:
            for flavor in resource_group.flavors:
                cpu_milli_cores = next(
                    (resource.nominalQuota for resource in flavor.resources if resource.name == CPU_RESOURCE), "0"
                )
                gpu_count = next(
                    (
                        resource.nominalQuota
                        for resource in flavor.resources
                        if resource.name == AMD_GPU_RESOURCE or resource.name == NVIDIA_GPU_RESOURCE
                    ),
                    "0",
                )
                memory_bytes = next(
                    (resource.nominalQuota for resource in flavor.resources if resource.name == MEMORY_RESOURCE), "0"
                )
                ephemeral_storage_bytes = next(
                    (
                        resource.nominalQuota
                        for resource in flavor.resources
                        if resource.name == EPHEMERAL_STORAGE_RESOURCE
                    ),
                    "0",
                )
                quota_allocations.append(
                    ClusterQuotaAllocation(
                        cpu_milli_cores=parse_cpu_value(cpu_milli_cores),
                        gpu_count=int(gpu_count),
                        memory_bytes=parse_k8s_memory(memory_bytes),
                        ephemeral_storage_bytes=parse_k8s_memory(ephemeral_storage_bytes),
                        quota_name=cluster_queue.name,
                        namespaces=cluster_queue.namespaces,
                    )
                )

    return quota_allocations
