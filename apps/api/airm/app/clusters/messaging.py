# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from ..utilities.enums import GPUVendor


class HeartbeatMessage(BaseModel):
    message_type: Literal["heartbeat"]
    last_heartbeat_at: AwareDatetime = Field(description="The heartbeat timestamp of the cluster.")
    cluster_name: str = Field(pattern=r"^[0-9A-Za-z-_]+$", description="The name of the cluster.")


class GPUInformation(BaseModel):
    count: int = Field(description="The number of GPUs available in the node")
    type: str = Field(description="The type of GPU available in the node")
    vendor: GPUVendor = Field(description="The vendor of the GPU available in the node")
    vram_bytes_per_device: int = Field(description="The total VRAM in bytes of each GPU available in the node")
    product_name: str = Field(description="The product name of the GPU available in the node")


class ClusterNode(BaseModel):
    name: str = Field(description="The name of the node.")
    cpu_milli_cores: int = Field(description="The number of CPU milli-cores available in the node.")
    memory_bytes: int = Field(description="The total memory in bytes.")
    ephemeral_storage_bytes: int = Field(description="The total ephemeral storage in bytes.")
    gpu_information: GPUInformation | None = Field(None, description="GPU information if available")
    status: str = Field(description="The status of the node.")
    is_ready: bool = Field(description="Node readiness flag.")


class ClusterNodesMessage(BaseModel):
    message_type: Literal["cluster_nodes"]
    cluster_nodes: list[ClusterNode] = Field(description="The list of nodes in the cluster.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class ClusterNodeUpdateMessage(BaseModel):
    message_type: Literal["cluster_node_update"]
    cluster_node: ClusterNode = Field(description="The node being updated")
    updated_at: AwareDatetime = Field(description="The timestamp of the update")


class ClusterNodeDeleteMessage(BaseModel):
    message_type: Literal["cluster_node_delete"]
    name: str = Field(description="The name of the node being deleted")
    updated_at: AwareDatetime = Field(description="The timestamp of the update")


class PriorityClass(BaseModel):
    name: str = Field(description="The name of the priority class")
    priority: int = Field(description="The priority value (0-100)")
