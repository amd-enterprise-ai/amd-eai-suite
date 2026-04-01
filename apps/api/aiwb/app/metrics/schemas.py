# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from .constants import MAX_DAYS_FOR_METRICS


class MetricsTimeRange(BaseModel):
    """Validated start/end time range for metrics queries."""

    start: AwareDatetime = Field(description="Start time. ISO 8601 with timezone (e.g. UTC: ...Z or +00:00).")
    end: AwareDatetime = Field(description="End time. ISO 8601 with timezone (e.g. UTC: ...Z or +00:00).")

    @model_validator(mode="after")
    def validate_range(self) -> "MetricsTimeRange":
        # Prometheus works on second precision — truncate sub-second component
        self.start = self.start.replace(microsecond=0)
        self.end = self.end.replace(microsecond=0)

        now = datetime.now(UTC)
        if self.start >= self.end:
            raise ValueError("start time must be before end time")
        if self.start < now - timedelta(days=MAX_DAYS_FOR_METRICS):
            raise ValueError(f"start time must be within the last {MAX_DAYS_FOR_METRICS} days")
        if self.end > now + timedelta(minutes=1):
            raise ValueError("end time must not be in the future")
        return self


class DatapointMetadataBase(BaseModel):
    label: str = Field(
        description="The label for the series that the datapoint belongs to.", min_length=1, max_length=64
    )


class Datapoint(BaseModel):
    value: float | None = Field(None, description="The value of the datapoint.")
    timestamp: AwareDatetime = Field(description="The timestamp of the datapoint.")


class DatapointsWithMetadata(BaseModel):
    metadata: DatapointMetadataBase = Field(description="Metadata for the datapoints.")
    values: list[Datapoint] = Field(description="The list of datapoints corresponding to the metadata.")


class DateRange(BaseModel):
    start: AwareDatetime = Field(..., description="Start of the requested time range.")
    end: AwareDatetime = Field(..., description="End of the requested time range.")


class TimeseriesRange(DateRange):
    interval_seconds: int = Field(description="The interval in seconds for the timeseries data.")
    timestamps: list[AwareDatetime] = Field(description="The keys for the datapoints in the timeseries.")


class MetricsTimeseries(BaseModel):
    data: list[DatapointsWithMetadata] = Field(description="The metrics timeseries data points.")
    range: TimeseriesRange = Field(description="The range of the timeseries.")


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
