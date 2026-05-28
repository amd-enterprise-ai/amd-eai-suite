# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from .enums import (
    WorkloadComponentKind,
    WorkloadComponentStatus,
    WorkloadStatus,
    WorkloadType,
)


class WorkloadMessage(BaseModel):
    message_type: Literal["workload"]
    manifest: str = Field(description="The workload manifest.")
    user_token: str = Field(description="The user's token")
    workload_id: UUID = Field(description="The workload ID.")


class DeleteWorkloadMessage(BaseModel):
    message_type: Literal["delete_workload"]
    workload_id: UUID = Field(description="The workload ID.")


class WorkloadStatusMessage(BaseModel):
    message_type: Literal["workload_status_update"]
    status: WorkloadStatus = Field(description="The status of the workload.")
    workload_id: UUID = Field(description="The workload ID.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
    status_reason: str | None = Field(description="Details if any about the status")


class WorkloadComponentStatusMessage(BaseModel):
    message_type: Literal["workload_component_status_update"]
    id: UUID = Field(description="The component id")
    name: str = Field(description="The name of the component.")
    kind: WorkloadComponentKind = Field(description="The kind of the component.")
    api_version: str = Field(description="The component API version.")
    workload_id: UUID = Field(description="The workload ID.")
    status: WorkloadComponentStatus = Field(description="The status of the component.")
    status_reason: str | None = Field(description="Details if any about the status")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class AutoDiscoveredWorkloadComponentMessage(BaseModel):
    message_type: Literal["auto_discovered_workload_component"]
    project_id: UUID = Field(description="The project ID.")
    workload_id: UUID = Field(description="The workload ID.")
    component_id: UUID = Field(description="The component ID.")
    name: str = Field(description="The name of the component.")
    kind: WorkloadComponentKind = Field(description="The kind of the component.")
    api_version: str = Field(description="The component API version.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
    submitter: str | None = Field(None, description="The submitter of the workload component, if known", max_length=256)
    workload_type: WorkloadType = Field(
        default=WorkloadType.CUSTOM, description="The workload type from airm.silogen.ai/workload-type label"
    )
