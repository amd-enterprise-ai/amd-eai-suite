# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import json

from _pytest.logging import LogCaptureFixture

from app.utilities.collections.dependencies import (
    get_filter_query_params,
    get_pagination_query_params,
    get_sort_query_params,
)
from app.utilities.collections.schemas import FilterCondition, FilterOperator, PaginationConditions, SortCondition


class Test_Pagination:
    """Test Pagination conditions parsing"""

    def test_get_pagination_query_params_defaults(self):
        # Simulate FastAPI dependency injection with default values
        result = get_pagination_query_params()
        assert isinstance(result, PaginationConditions)
        assert result.page == 1
        assert result.page_size == 10

    def test_get_pagination_query_params_custom_values(self):
        result = get_pagination_query_params(page=3, page_size=25)
        assert isinstance(result, PaginationConditions)
        assert result.page == 3
        assert result.page_size == 25

    def test_get_pagination_query_params_zero_page(self):
        result = get_pagination_query_params(page=0, page_size=10)
        assert result.page == 0
        assert result.page_size == 10

    def test_get_pagination_query_params_none_values(self):
        # Should fallback to None if explicitly passed
        result = get_pagination_query_params(page=None, page_size=None)
        assert result.page is None
        assert result.page_size is None


class Test_Sorting:
    """Test sorting conditions parsing"""

    def test_get_sort_query_params_valid(self, monkeypatch):
        # Patch SortCondition import in the tested module
        monkeypatch.setattr("app.utilities.collections.schemas.SortCondition", SortCondition)
        sort_json = json.dumps([{"field": "name", "direction": "asc"}, {"field": "age", "direction": "desc"}])
        result = get_sort_query_params(sort=sort_json)

        assert isinstance(result, list)
        assert result[0].field == "name"
        assert result[0].direction == "asc"
        assert result[1].field == "age"
        assert result[1].direction == "desc"

    def test_get_sort_query_params_invalid(self, monkeypatch, caplog: LogCaptureFixture):
        monkeypatch.setattr("app.utilities.collections.schemas.SortCondition", SortCondition)
        # Invalid JSON
        result = get_sort_query_params(sort="not a json")
        logs = caplog.get_records("call")
        assert len(logs) == 1
        assert logs[0].message == "Warning - Failed to parse sort query parameter"
        assert result == []

    def test_get_sort_query_params_none(self, monkeypatch):
        monkeypatch.setattr("app.utilities.collections.schemas.SortCondition", SortCondition)
        result = get_sort_query_params(sort=None)
        assert result == []


class Test_Filtering:
    """Test filtering conditions parsing"""

    def test_get_filter_query_params_valid(self):
        # Valid filter JSON string
        filter_json = json.dumps(
            [
                {"fields": ["status"], "operator": "eq", "values": ["active"]},
                {"fields": ["age"], "operator": "contains", "values": ["pending"]},
            ]
        )
        result = get_filter_query_params(filter=filter_json)
        print(result)
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], FilterCondition)
        assert result[0].fields == ["status"]
        assert result[0].operator == FilterOperator.EQ
        assert result[0].values == ["active"]
        assert result[1].fields == ["age"]
        assert result[1].operator == FilterOperator.CONTAINS
        assert result[1].values == ["pending"]

    def test_get_filter_query_params_invalid(self):
        # Invalid JSON string should return empty list
        result = get_filter_query_params(filter="not a json")
        assert result == []

    def test_get_filter_query_params_none(self):
        # None filter should return empty list
        result = get_filter_query_params(filter=None)
        assert result == []

    def test_get_filter_query_params_empty_list(self):
        # Empty list JSON string should return empty list
        result = get_filter_query_params(filter="[]")
        assert result == []
