# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, Field

from airm.messaging.schemas import WorkloadComponentKind
from airm.workloads.constants import WORKLOAD_SUBMITTER_MAX_LENGTH


class WorkloadComponentData(BaseModel):
    name: str = Field(description="The name of the component")
    kind: WorkloadComponentKind = Field(description="The kind of the workload component")
    api_version: str = Field(description="The API version of the component")
    project_id: UUID = Field(description="The ID of the project this component belongs to")
    workload_id: UUID = Field(description="The ID of the workload this component is part of")
    component_id: UUID = Field(description="The ID of the component")
    auto_discovered: bool = Field(description="Indicates if the component was auto-discovered", default=False)
    submitter: str | None = Field(
        None,
        description="The submitter of the workload component, if available",
        max_length=WORKLOAD_SUBMITTER_MAX_LENGTH,
    )
