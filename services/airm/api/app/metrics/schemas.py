# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, Field

from ..projects.schemas import ProjectResponse
from ..utilities.collections.schemas import BasePaginationList
from ..workloads.schemas import WorkloadResponse


class DatapointMetadataBase(BaseModel):
    label: str = Field(
        description="The label for the series that the datapoint belongs to.", min_length=1, max_length=64
    )


class ProjectDatapointMetadata(DatapointMetadataBase):
    project: ProjectResponse = Field(description="The project the datapoint corresponds to")


class Datapoint(BaseModel):
    value: float | None = Field(None, description="The value of the datapoint.")
    timestamp: AwareDatetime = Field(description="The timestamp of the datapoint.")


class DatapointsWithMetadata(BaseModel):
    metadata: DatapointMetadataBase | ProjectDatapointMetadata = Field(description="Metadata for the datapoints.")
    values: list[Datapoint] = Field(description="The list of datapoints corresponding to the metadata.")


class TimeseriesRange(BaseModel):
    start: AwareDatetime = Field(description="The start of the timeseries range.")
    end: AwareDatetime = Field(description="The end of the timeseries range.")
    interval_seconds: int = Field(description="The interval in seconds for the timeseries data.")
    timestamps: list[AwareDatetime] = Field(description="The keys for the datapoints in the timeseries.")


class MetricsTimeseries(BaseModel):
    data: list[DatapointsWithMetadata] = Field(description="The metrics timeseries data points.")
    range: TimeseriesRange = Field(description="The range of the timeseries.")


class UtilizationByProject(BaseModel):
    project: ProjectResponse = Field(description="The project the utilization corresponds to.")
    allocated_gpus_count: int = Field(description="The number of GPUs allocated to the project.")
    utilized_gpus_count: int = Field(description="The number of GPUs currently being utilized by the project.")
    running_workloads_count: int = Field(description="The number of running workloads for the project.")
    pending_workloads_count: int = Field(description="The number of pending workloads for the project.")


class CurrentUtilization(BaseModel):
    timestamp: AwareDatetime = Field(datetime.now(tz=UTC), description="The timestamp of the current utilization data.")
    utilization_by_project: list[UtilizationByProject] = Field(
        description="The GPU utilization by project.",
    )
    total_utilized_gpus_count: int = Field(description="The number of GPUs currently in use.")
    total_running_workloads_count: int = Field(description="The number of running workloads.")
    total_pending_workloads_count: int = Field(description="The number of pending workloads.")


class WorkloadWithMetrics(WorkloadResponse):
    gpu_count: int = Field(description="The number of GPUs allocated to the workload", default=None)
    vram: float = Field(description="The amount of VRAM used by the workload", default=None)
    run_time: int = Field(description="The total run time of the workload in seconds", default=None)
    created_at: AwareDatetime | None = Field(description="The timestamp of when the workload was created", default=None)
    created_by: str = Field(description="The user who created the workload", default=None)


class WorkloadsWithMetrics(BasePaginationList):
    workloads: list[WorkloadWithMetrics]


class DateRange(BaseModel):
    start: AwareDatetime = Field(..., description="Start of the requested time range.")
    end: AwareDatetime = Field(..., description="End of the requested time range.")


class MetricsScalar(BaseModel):
    """
    Represents a scalar metric value at a single point in time.
    Used for point-in-time metrics.
    """

    data: float = Field(..., description="The scalar metric value.")


class MetricsScalarWithRange(MetricsScalar):
    """
    Represents a scalar metric value aggregated over a time range.
    Used for metrics computed over a specified range.
    """

    range: DateRange = Field(..., description="The range for which the scalar metric was computed.")
