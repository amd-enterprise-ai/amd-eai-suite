# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..projects.schemas import ProjectResponse
from ..utilities.schema import BaseEntityPublic
from ..workloads.enums import WorkloadType
from .enums import WorkloadStatus


class ManagedWorkloadCreate(BaseModel):  # used only as a base
    type: WorkloadType = Field(..., description="The specific type of managed workload to create")
    user_inputs: dict[str, Any] = Field({}, description="The user inputs for the workload")
    display_name: str | None = Field(None, description="User-friendly display name for the workload")


class ChartWorkloadCreate(ManagedWorkloadCreate):
    chart_id: UUID = Field(..., description="The ID of the chart associated with the workload")
    model_id: UUID | None = Field(None, description="The ID of the model associated with the workload")
    dataset_id: UUID | None = Field(None, description="The ID of the dataset associated with the workload")


class AIMWorkloadCreate(ManagedWorkloadCreate):
    aim_id: UUID = Field(None, description="The ID of the AIM associated with the workload")


class AllocatedResources(BaseModel):
    gpu_count: int | None = Field(description="Allocated GPUs for the workload")
    vram: float | None = Field(description="VRAM in MBs currently in use for the workload")


class ManagedWorkloadResponse(BaseEntityPublic):
    """Base response schema for managed workloads."""

    display_name: str = Field(..., description="User-friendly display name for the workload")
    name: str = Field(..., description="Name used in the cluster for the workload")
    project: ProjectResponse = Field(..., description="The Project the workload it related to")
    status: WorkloadStatus = Field(..., description="The status of the workload")
    type: WorkloadType = Field(..., description="The specific type of the managed workload")
    user_inputs: dict[str, Any] = Field({}, description="User-provided inputs/overrides")
    output: dict[str, Any] | None = Field(None, description="Output from the workload, e.g., endpoint")
    allocated_resources: AllocatedResources | None = Field(
        None, description="Resource information for the workload, including GPU, VRAM, and storage limits"
    )
    cluster_auth_group_id: str | None = Field(None, description="The cluster-auth group ID for access control")

    model_config = ConfigDict(from_attributes=True)


class ChartWorkloadResponse(ManagedWorkloadResponse):
    """Response schema for chart-based workloads (inference, fine-tuning, etc)."""

    chart_id: UUID = Field(..., description="The associated chart ID")
    model_id: UUID | None = Field(None, description="The associated inference model ID")
    dataset_id: UUID | None = Field(None, description="The associated dataset ID")
    capabilities: list[str] = Field(
        default_factory=list, deprecated=True, description="Deprecated: used to check if a model is chat-capable"
    )

    model_config = ConfigDict(from_attributes=True)


class AIMWorkloadResponse(ManagedWorkloadResponse):
    """Response schema for AIM workloads."""

    aim_id: UUID = Field(..., description="The ID of the associated AIM")

    model_config = ConfigDict(from_attributes=True)
