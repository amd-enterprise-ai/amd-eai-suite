# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from app.utilities.collections.schemas import (
    BaseFilterableList,
    BasePaginationList,
    BaseSortableList,
    FilterCondition,
    FilterOperator,
    PaginationConditions,
    SortCondition,
    SortDirection,
)


class Test_Pagination_Schemas:
    """Test Collections (sort, filter, pagination) schemas including the field validator."""

    def test_pagination_conditions_defaults(self):
        pc = PaginationConditions()
        assert pc.page == 1
        assert pc.page_size == 10

        pc2 = PaginationConditions(page=2, page_size=25)
        assert pc2.page == 2
        assert pc2.page_size == 25

    def test_base_pagination_list_required_fields(self):
        with pytest.raises(ValidationError):
            BasePaginationList()  # missing required fields

        bpl = BasePaginationList(page=1, page_size=10, total=100)
        assert bpl.page == 1
        assert bpl.page_size == 10
        assert bpl.total == 100


class Test_Sort_Schemas:
    """Test Sorting schemas including the field validator."""

    def test_sort_direction_enum(self):
        assert SortDirection.asc == "asc"
        assert SortDirection.desc == "desc"
        assert SortDirection.asc.value == "asc"

    def test_sort_condition_defaults(self):
        sc = SortCondition(field="name")
        assert sc.field == "name"
        assert sc.direction == SortDirection.asc

        sc2 = SortCondition(field="date", direction=SortDirection.desc)
        assert sc2.direction == SortDirection.desc

        with pytest.raises(ValidationError):
            SortCondition()  # missing required field

    def test_base_sortable_list(self):
        bsl = BaseSortableList(sort=None)
        assert bsl.sort is None

        bsl2 = BaseSortableList(sort=[SortCondition(field="f", direction=SortDirection.desc)])
        assert isinstance(bsl2.sort, list)
        assert bsl2.sort[0].direction == SortDirection.desc


class Test_Filter_Schemas:
    """Test Filtering schemas including the field validator."""

    def test_filter_operator_enum(self):
        assert FilterOperator.EQ.value == "eq"
        assert FilterOperator.CONTAINS.value == "contains"

    def test_filter_condition_required_fields(self):
        fc = FilterCondition(values=["abc"], operator=FilterOperator.EQ, fields=["name"])
        assert fc.values == ["abc"]
        assert fc.operator == FilterOperator.EQ
        assert fc.fields == ["name"]

        # operator is optional, but required by type
        with pytest.raises(ValidationError):
            FilterCondition(values=["abc"], fields=["name"])

    def test_base_filterable_list(self):
        # filter is required, so pass None or an empty list if optional behavior is desired
        bfl = BaseFilterableList(filter=None)
        assert bfl.filter is None

        bfl2 = BaseFilterableList(
            filter=[FilterCondition(values=["x"], operator=FilterOperator.CONTAINS, fields=["f"])]
        )
        assert isinstance(bfl2.filter, list)
        assert bfl2.filter[0].fields == ["f"]
