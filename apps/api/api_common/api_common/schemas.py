# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Common Pydantic schemas for API services."""

from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ListResponse[T](BaseModel):
    """Generic wrapper for list responses. Use as ListResponse[YourItemType]."""

    data: list[T] = Field(description="List of items")

    model_config = ConfigDict(from_attributes=True)


class BaseEntityPublic(BaseModel):
    """Exposes fields from BaseEntity for API responses."""

    id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime
    created_by: str | None
    updated_by: str | None


class DeleteBatchRequest(BaseModel):
    """Request to delete multiple entities by ID."""

    ids: list[UUID]


class PaginationMetadataResponse(BaseModel):
    """Pagination metadata for paginated responses."""

    has_more: bool
    page_token: str | None = None
    total_returned: int


class PaginationDirection(StrEnum):
    """Pagination direction for time-based queries."""

    FORWARD = "forward"
    BACKWARD = "backward"


class TimeRangePaginationRequest(BaseModel):
    """Pagination with time range for time-series data."""

    start: AwareDatetime = Field(..., description="Start of the time range")
    end: AwareDatetime = Field(..., description="End of the time range")
    page_token: AwareDatetime | None = Field(default=None, description="Token to continue from")
    limit: int = Field(default=1000, ge=1, le=10000, description="Number of items to return")
    direction: PaginationDirection = Field(default=PaginationDirection.FORWARD, description="Direction of pagination")
