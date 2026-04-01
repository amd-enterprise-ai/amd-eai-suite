# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from ..messaging.schemas import WorkloadComponentKind, WorkloadComponentStatus, WorkloadStatus
from ..utilities.schema import BaseEntityPublic
from .enums import WorkloadType


class WorkloadResponse(BaseEntityPublic):
    project_id: UUID = Field(description="The ID of the project")
    cluster_id: UUID = Field(description="The ID of the cluster")
    status: WorkloadStatus = Field(description="The status of the workload")
    display_name: str | None = Field(None, description="The display name of the workload")
    type: WorkloadType | None = Field(None, description="The type of the workload")

    model_config = ConfigDict(from_attributes=True)


class Workloads(BaseModel):
    data: list[WorkloadResponse]


class WorkloadComponent(BaseEntityPublic):
    name: str = Field(description="The name of the component.")
    kind: WorkloadComponentKind = Field(description="The kind of the component.")
    api_version: str = Field(description="The component API version.")
    status: WorkloadComponentStatus = Field(description="The status of the component.")
    status_reason: str | None = Field(None, description="Details if any about the status")

    model_config = ConfigDict(from_attributes=True)


class WorkloadWithComponents(WorkloadResponse):
    components: list[WorkloadComponent] = Field(description="The components of the workload")


class WorkloadMetricsDetailsResponse(BaseModel):
    name: str | None = Field(None, description="The display name of the workload")
    workload_id: UUID = Field(description="The unique identifier of the workload")
    created_by: str | None = Field(None, description="The user who created the workload")
    cluster_name: str | None = Field(None, description="The name of the cluster running the workload")
    cluster_id: UUID = Field(description="The ID of the cluster running the workload")
    nodes_in_use: int = Field(description="The number of nodes in use by the workload")
    gpu_devices_in_use: int = Field(description="The number of GPU devices in use by the workload")
    created_at: AwareDatetime = Field(description="The timestamp when the workload was created")
    updated_at: AwareDatetime = Field(description="The timestamp when the workload was last updated")
    queue_time: int = Field(description="Total time the workload spent queued (pending) in seconds", default=0)
    running_time: int = Field(description="Total running time of the workload in seconds", default=0)


class WorkloadsStats(BaseModel):
    running_workloads_count: int = Field(description="The number of running workloads")
    pending_workloads_count: int = Field(description="The number of pending workloads")


class WorkloadComponentIn(BaseModel):
    name: str = Field(description="The name of the component.")
    kind: WorkloadComponentKind = Field(description="The kind of the component.")
    api_version: str = Field(description="The component API version.")
    workload_id: UUID = Field(description="The workload ID.")
    id: UUID | None = Field(description="The ID of the workload component, if it was created elsewhere.", default=None)


class WorkloadStatusCount(BaseModel):
    status: WorkloadStatus = Field(description="The workload status category.")
    count: int = Field(description="The number of workloads currently in this status.")


class WorkloadStatusStats(BaseModel):
    name: str = Field(description="The name of the entity (project or cluster).", min_length=2, max_length=64)
    total_workloads: int = Field(description="The total number of workloads.")
    statusCounts: list[WorkloadStatusCount] = Field(description="The total count of workloads grouped by status.")
