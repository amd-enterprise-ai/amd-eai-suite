# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Common Pydantic schemas for API services."""

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Query
from pydantic import AwareDatetime, ConfigDict, Field
from pydantic import BaseModel as PydanticBaseModel
from pydantic.alias_generators import to_camel


class QueryParam:
    """Type alias for query-parameter models in router signatures.

    Use ``QueryParam[MyModel]`` instead of ``Annotated[MyModel, Query()]``.
    This is required (instead of ``Depends()``) so that FastAPI resolves the
    model's camelCase aliases for query-parameter names.
    """

    def __class_getitem__(cls, item: type) -> type:  # type: ignore[override]
        return Annotated[item, Query()]  # type: ignore[return-value]


class BaseModel(PydanticBaseModel):
    """Repository-wide base model with automatic camelCase alias generation.

    All API-facing schemas should inherit from this class instead of
    ``pydantic.BaseModel``.  It provides ``alias_generator=to_camel`` so that
    field names are automatically converted between snake_case (Python) and
    camelCase (JSON / OpenAPI).  ``populate_by_name=True`` allows Python code,
    ORM mapping, and ``model_dump()`` to keep using snake_case.

    Strict camelCase enforcement on incoming requests (rejecting snake_case
    keys) is handled by ``CamelCaseMiddleware`` at the HTTP layer.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ListResponse[T](BaseModel):
    """Generic wrapper for list responses. Use as ListResponse[YourItemType]."""

    data: list[T] = Field(description="List of items")


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
