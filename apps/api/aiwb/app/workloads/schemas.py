# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, computed_field, model_validator

from api_common.schemas import BaseEntityPublic, BaseModel

from ..logs.schemas import LogLevel, LogType
from ..workspaces.enums import WORKSPACE_URL_SUFFIX_MAPPING
from .enums import WorkloadStatus, WorkloadType
from .utils import get_workload_host_from_HTTPRoute_manifest, get_workload_internal_url


class DisplayNameQuery(BaseModel):
    display_name: str | None = Field(default=None, description="User-friendly display name for the workload")


class WorkloadListQuery(BaseModel):
    workload_type: list[WorkloadType] = Field(default_factory=list, description="Filter by workload type(s)")
    status_filter: list[WorkloadStatus] = Field(default_factory=list, description="Filter by workload status")


class WorkloadStreamQuery(BaseModel):
    start_time: datetime | None = Field(default=None, description="Start time for streaming (ISO format)")
    level: LogLevel | None = Field(default=None, description="Filter logs at this level and above")
    log_type: LogType = Field(default=LogType.WORKLOAD, description="Type of logs: 'workload' or 'event'")
    delay: int = Field(default=1, ge=1, le=30, description="Delay between polls (1-30 seconds)")


class WorkloadResponse(BaseEntityPublic):
    """Base workload schema."""

    name: str
    display_name: str
    type: WorkloadType
    status: WorkloadStatus
    namespace: str
    chart_id: UUID | None = None
    dataset_id: UUID | None = None
    manifest: str = Field(default="", exclude=True)
    chart_name: str | None = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def extract_chart_name(cls, data: Any) -> Any:
        if hasattr(data, "chart") and data.chart:
            data.__dict__["chart_name"] = data.chart.name
        return data

    @computed_field
    def endpoints(self) -> dict[str, str]:
        # Skip computation for deleted workloads
        if self.status not in [WorkloadStatus.PENDING, WorkloadStatus.RUNNING]:
            return {}

        internal = get_workload_internal_url(self.name, self.namespace)
        external = get_workload_host_from_HTTPRoute_manifest(manifest=self.manifest)

        suffix = WORKSPACE_URL_SUFFIX_MAPPING.get(self.chart_name or "", "")
        if suffix:
            internal += suffix
            if external:
                external += suffix

        endpoints = {"internal": internal}
        if external:
            endpoints["external"] = external
        return endpoints
