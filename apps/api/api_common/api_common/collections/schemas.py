# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import math
from enum import Enum, StrEnum

from pydantic import computed_field, field_validator
from pydantic.alias_generators import to_snake

from api_common.schemas import BaseModel


class PaginationConditions(BaseModel):
    page: int | None = 1
    page_size: int | None = 10


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


class BasePaginationList(PaginationConditions):
    """Base Pagination response fields for paginated lists."""

    total: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        if not self.page_size:
            return 1
        return max(1, math.ceil(self.total / self.page_size))
