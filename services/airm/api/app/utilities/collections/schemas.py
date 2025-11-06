# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import Enum, StrEnum

from pydantic import BaseModel


class PaginationConditions(BaseModel):
    page: int | None = 1
    page_size: int | None = 10


class SortDirection(StrEnum):
    asc = "asc"
    desc = "desc"


class SortCondition(BaseModel):
    field: str
    direction: SortDirection = SortDirection.asc  # default to ascending order


class FilterOperator(Enum):
    EQ = "eq"
    CONTAINS = "contains"


class FilterCondition(BaseModel):
    values: list[str]
    operator: FilterOperator | None  # default to CONTAINS if not specified
    fields: list[str]
    show_all_if_values_empty: bool | None = False


class BaseFilterableList(BaseModel):
    """Base Filterable required fields"""

    filter: list[FilterCondition] | None


class BaseSortableList(BaseModel):
    """Base Sortable required fields"""

    sort: list[SortCondition] | None  # List of dictionaries with 'field' and 'direction' keys


class BasePaginationList(BaseModel):
    """Base Pagination required fields"""

    page: int
    page_size: int
    total: int
