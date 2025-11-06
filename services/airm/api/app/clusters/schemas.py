# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, computed_field

from airm.messaging.schemas import GPUVendor, PriorityClass

from ..utilities.schema import BaseEntityPublic
from .constants import DEFAULT_PRIORITY_CLASSES


class ClusterStatus(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    VERIFYING = "verifying"


class ClusterIn(BaseModel):
    base_url: str | None = Field(
        min_length=1, max_length=1024, description="The base URL of the cluster.", default=None
    )

    model_config = ConfigDict(extra="forbid")


class ClusterNameEdit(BaseModel):
    name: str = Field(
        None, description="The name of the cluster.", min_length=2, max_length=64, pattern="^[0-9A-Za-z-_]+$"
    )

    model_config = ConfigDict(extra="forbid")


class ClusterResponse(ClusterIn, BaseEntityPublic):
    name: str | None = Field(None, description="The name of the cluster")
    last_heartbeat_at: AwareDatetime | None = Field(None, description="The heartbeat timestamp of the cluster.")

    @computed_field
    def status(self) -> ClusterStatus:
        if self.last_heartbeat_at is None:
            return ClusterStatus.VERIFYING
        if datetime.now(tz=UTC) - self.last_heartbeat_at > timedelta(minutes=5):
            return ClusterStatus.UNHEALTHY
        return ClusterStatus.HEALTHY

    model_config = ConfigDict(from_attributes=True)


class ClustersStats(BaseModel):
    total_cluster_count: int = Field(description="The total number of clusters.")
    total_node_count: int = Field(description="The total number of nodes across all clusters.")
    available_node_count: int = Field(description="The number of available nodes across all clusters.")
    total_gpu_node_count: int = Field(description="The total number of GPU nodes across all clusters.")
    total_gpu_count: int = Field(description="The total number of GPUs across all clusters.")
    available_gpu_count: int = Field(description="The number of available GPUs across all clusters.")
    allocated_gpu_count: int = Field(description="The number of allocated GPUs across all clusters.")


class ClusterWithUserSecret(ClusterResponse):
    user_secret: str = Field(description="Secret to access a cluster's virtual host in RabbitMQ.")


class GPUInfo(BaseModel):
    vendor: GPUVendor = Field(description="The vendor of the GPU(s) available.")
    type: str = Field(description="The type of GPU available.")
    memory_bytes_per_device: int = Field(description="The available GPU memory in bytes, per GPU.")
    name: str = Field(description="The name of the GPU available.")


class ClusterNodeResponse(BaseModel):
    id: UUID = Field(description="The ID of the node.")
    name: str = Field(description="The name of the node.")
    cpu_milli_cores: int = Field(description="The number of CPU milli-cores available in the node.")
    memory_bytes: int = Field(description="The total memory in bytes.")
    ephemeral_storage_bytes: int = Field(description="The total ephemeral storage in bytes.")
    gpu_count: int = Field(0, description="The number of GPUs available in the node.")
    gpu_info: GPUInfo | None = Field(None, description="The GPU information available in the node.")
    updated_at: AwareDatetime = Field(description="The timestamp the node was last updated.")
    status: str = Field(description="The status of the node.")

    model_config = ConfigDict(from_attributes=True)


class ClusterNodes(BaseModel):
    cluster_nodes: list[ClusterNodeResponse]


class ClusterResources(BaseModel):
    cpu_milli_cores: int = Field(description="The number of CPUs.")
    memory_bytes: int = Field(description="The total memory in bytes.")
    ephemeral_storage_bytes: int = Field(description="The total ephemeral storage in bytes.")
    gpu_count: int = Field(description="The number of GPUs.")


class ClusterWithResources(ClusterResponse):
    available_resources: ClusterResources = Field(description="The available resources in the cluster.")
    allocated_resources: ClusterResources = Field(description="The allocated resources in the cluster.")

    total_node_count: int = Field(description="The total number of nodes in the cluster.")
    available_node_count: int = Field(description="The number of available nodes in the cluster.")

    assigned_quota_count: int = Field(description="The number of quotas assigned to the cluster.")
    gpu_info: GPUInfo | None = Field(None, description="The GPU information available in the cluster")

    @computed_field(description="The priority classes available in the cluster.")
    def priority_classes(self) -> list[PriorityClass]:
        return DEFAULT_PRIORITY_CLASSES

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gpu_allocation_percentage(self) -> float:
        """GPU allocation percentage."""
        allocated = self.allocated_resources.gpu_count
        available = self.available_resources.gpu_count
        return (allocated / available * 100) if available > 0 else 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cpu_allocation_percentage(self) -> float:
        """CPU allocation percentage."""
        allocated = self.allocated_resources.cpu_milli_cores
        available = self.available_resources.cpu_milli_cores
        return (allocated / available * 100) if available > 0 else 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memory_allocation_percentage(self) -> float:
        """Memory allocation percentage."""
        allocated = self.allocated_resources.memory_bytes
        available = self.available_resources.memory_bytes
        return (allocated / available * 100) if available > 0 else 0

    model_config = ConfigDict(from_attributes=True)


class Clusters(BaseModel):
    clusters: list[ClusterWithResources]
