# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import Enum, StrEnum

from pydantic import Field, field_validator
from pydantic.alias_generators import to_snake

from api_common.schemas import BaseModel


class PaginationConditions(BaseModel):
    """Base pagination query inputs.

    Subclasses can override these defaults and tighten bounds (see AIWB
    endpoint schemas, which cap ``page_size`` at 100). The base bounds
    keep callers safe from obvious abuses: page must be 1-indexed and
    positive, page_size must be at least 1.
    """

    page: int | None = Field(default=1, ge=1)
    page_size: int | None = Field(default=10, ge=1)


class SortDirection(StrEnum):
    asc = "asc"
    desc = "desc"


class SortCondition(BaseModel):
    field: str
    direction: SortDirection = SortDirection.asc  # default to ascending order

    @field_validator("field")
    @classmethod
    def _normalize_field(cls, v: str) -> str:
        return to_snake(v)


class FilterOperator(Enum):
    EQ = "eq"
    CONTAINS = "contains"


class FilterCondition(BaseModel):
    values: list[str]
    operator: FilterOperator | None  # default to CONTAINS if not specified
    fields: list[str]
    show_all_if_values_empty: bool | None = False

    @field_validator("fields")
    @classmethod
    def _normalize_fields(cls, v: list[str]) -> list[str]:
        return [to_snake(f) for f in v]


class BaseFilterableList(BaseModel):
    """Base Filterable required fields"""

    filter: list[FilterCondition] | None


class BaseSortableList(BaseModel):
    """Base Sortable required fields"""

    sort: list[SortCondition] | None  # List of dictionaries with 'field' and 'direction' keys


class PaginationMetadata(BaseModel):
    """Pagination metadata block emitted under `pagination` in list responses.

    `totalPages` is intentionally not exposed — clients derive it as
    `ceil(total / pageSize)` when needed.
    """

    page: int
    page_size: int
    total: int


class BasePaginationList(BaseModel):
    """Base envelope for paginated list responses.

    Subclasses declare only the typed `data` field, e.g.:

        class InferenceDeploymentsList(BasePaginationList):
            data: list[InferenceDeploymentResponse]

    Wire shape:
        { "data": [...], "pagination": { "page": 1, "pageSize": 10, "total": N } }
    """

    pagination: PaginationMetadata
