# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from ..aims.constants import AIM_SERVICE_RESOURCE
from ..aims.schemas import AIMServiceResponse
from ..workloads.constants import DEPLOYMENT_RESOURCE, JOB_RESOURCE
from ..workloads.enums import WorkloadStatus, WorkloadType


class ResourceType(StrEnum):
    """Resource types for workloads and AIM services."""

    DEPLOYMENT = DEPLOYMENT_RESOURCE
    JOB = JOB_RESOURCE
    AIM_SERVICE = AIM_SERVICE_RESOURCE


class ChattableResponse(BaseModel):
    """Response model for chattable resources in a namespace.

    Combines both AIM services and workloads that support chat functionality.
    """

    aim_services: list[AIMServiceResponse] = Field(
        default_factory=list,
        alias="aimServices",
        description="List of chattable AIM services",
    )
    workloads: list[Any] = Field(
        default_factory=list,
        description="List of chattable workloads (finetuned models)",
    )

    model_config = ConfigDict(populate_by_name=True)


class NamespaceWorkloadMetrics(BaseModel):
    """Metrics for a single resource (AIM service or workload)."""

    id: UUID = Field(..., description="The unique ID of the resource")
    name: str = Field(..., description="The name of the resource")
    display_name: str | None = Field(None, alias="displayName", description="The display name of the resource")
    type: WorkloadType = Field(..., description="The type of the resource (INFERENCE, FINE_TUNING, WORKSPACE)")
    status: WorkloadStatus = Field(..., description="The current status of the resource")
    resource_type: ResourceType = Field(
        ..., alias="resourceType", description="The resource type (Deployment, Job, AIMService)"
    )
    gpu_count: int | None = Field(None, alias="gpuCount", description="The number of GPUs allocated to the resource")
    vram: float | None = Field(None, description="The amount of VRAM used by the resource in bytes")
    created_at: AwareDatetime | None = Field(
        None, alias="createdAt", description="The timestamp of when the resource was created"
    )
    created_by: str | None = Field(None, alias="createdBy", description="The user who created the resource")

    model_config = ConfigDict(populate_by_name=True)


class NamespaceWorkloadMetricsListPaginated(BaseModel):
    """Response model for paginated namespace workload metrics.

    Contains metrics for resources in a namespace with pagination.
    """

    data: list[NamespaceWorkloadMetrics] = Field(..., description="List of resources with their metrics")
    total: int = Field(..., description="Total number of resources")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page", alias="pageSize")
    total_pages: int = Field(..., description="Total number of pages", alias="totalPages")

    model_config = ConfigDict(populate_by_name=True)


class ResourceStatusCount(BaseModel):
    """Count of resources for a specific status."""

    status: WorkloadStatus = Field(..., description="The resource status")
    count: int = Field(..., description="The number of resources in this status")


class NamespaceStatsCounts(BaseModel):
    """Response model for namespace statistics counts.

    Contains aggregated counts of resources (AIM services + workloads) grouped by status.
    This is a lightweight response without computing metrics.
    """

    namespace: str = Field(..., description="The namespace name")
    total: int = Field(..., description="The total number of resources (AIM services + workloads)")
    status_counts: list[ResourceStatusCount] = Field(
        ..., description="The total count of resources grouped by status", alias="statusCounts"
    )

    model_config = ConfigDict(populate_by_name=True)
