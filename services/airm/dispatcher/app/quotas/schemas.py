# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any, Literal

from pydantic import BaseModel


class Resource(BaseModel):
    name: Literal["cpu", "memory", "ephemeral-storage", "amd.com/gpu", "nvidia.com/gpu"]
    nominalQuota: str


class Flavor(BaseModel):
    name: str
    resources: list[Resource]


class ResourceGroup(BaseModel):
    coveredResources: list[str]
    flavors: list[Flavor]


class PreemptionPolicy(BaseModel):
    borrowWithinCohort: dict
    reclaimWithinCohort: str
    withinClusterQueue: str


class ClusterQueueSpec(BaseModel):
    flavorFungibility: dict
    namespaceSelector: dict
    cohort: str | None = None
    preemption: PreemptionPolicy
    queueingStrategy: str
    resourceGroups: list[ResourceGroup]
    stopPolicy: str


class ClusterQueue(BaseModel):
    name: str
    spec: ClusterQueueSpec
    namespaces: list[str] = []


class ResourceFlavour(BaseModel):
    name: str


class WorkloadPriorityClass(BaseModel):
    metadata: dict[str, Any]
    value: int
    description: str


class KaiwoQueueConfigSpec(BaseModel):
    clusterQueues: list[ClusterQueue]
    resourceFlavors: list[ResourceFlavour]
    workloadPriorityClasses: list[WorkloadPriorityClass] = []


class KaiwoQueueConfig(BaseModel):
    apiVersion: str
    kind: str
    metadata: dict[str, Any]
    spec: KaiwoQueueConfigSpec
