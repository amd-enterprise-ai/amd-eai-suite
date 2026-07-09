# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import json

import pytest
from _pytest.logging import LogCaptureFixture
from pydantic import Field, ValidationError

from api_common.collections import (
    FilterCondition,
    FilterOperator,
    PaginationConditions,
    SortCondition,
    SortDirection,
    get_filter_query_params,
    get_pagination_query_params,
    get_sort_query_params,
    sort_list,
)
from api_common.schemas import BaseModel

# -- Pagination --


def test_get_pagination_query_params_defaults():
    result = get_pagination_query_params(page=1, page_size=10)
    assert isinstance(result, PaginationConditions)
    assert result.page == 1
    assert result.page_size == 10


def test_get_pagination_query_params_custom_values():
    result = get_pagination_query_params(page=3, page_size=25)
    assert isinstance(result, PaginationConditions)
    assert result.page == 3
    assert result.page_size == 25


def test_get_pagination_query_params_rejects_zero_page():
    # PaginationConditions enforces page >= 1 — page=0 is not a valid 1-indexed page.
    with pytest.raises(ValidationError):
        get_pagination_query_params(page=0, page_size=10)


def test_get_pagination_query_params_none_values():
    result = get_pagination_query_params(page=None, page_size=None)
    assert result.page is None
    assert result.page_size is None


# -- Sorting --


def test_get_sort_query_params_valid():
    sort_json = json.dumps([{"field": "name", "direction": "asc"}, {"field": "age", "direction": "desc"}])
    result = get_sort_query_params(sort=sort_json)

    assert isinstance(result, list)
    assert result[0].field == "name"
    assert result[0].direction == "asc"
    assert result[1].field == "age"
    assert result[1].direction == "desc"


def test_get_sort_query_params_normalizes_camel_case():
    sort_json = json.dumps([{"field": "createdAt", "direction": "desc"}])
    result = get_sort_query_params(sort=sort_json)

    assert len(result) == 1
    assert result[0].field == "created_at"
    assert result[0].direction == "desc"


def test_get_sort_query_params_invalid(caplog: LogCaptureFixture) -> None:
    result = get_sort_query_params(sort="not a json")
    logs = caplog.get_records("call")
    assert len(logs) == 1
    assert logs[0].message == "Warning - Failed to parse sort query parameter"
    assert result == []


def test_get_sort_query_params_none():
    result = get_sort_query_params(sort=None)
    assert result == []


# -- Filtering --


def test_get_filter_query_params_valid():
    filter_json = json.dumps(
        [
            {"fields": ["status"], "operator": "eq", "values": ["active"]},
            {"fields": ["age"], "operator": "contains", "values": ["pending"]},
        ]
    )
    result = get_filter_query_params(filter=filter_json)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], FilterCondition)
    assert result[0].fields == ["status"]
    assert result[0].operator == FilterOperator.EQ
    assert result[0].values == ["active"]
    assert result[1].fields == ["age"]
    assert result[1].operator == FilterOperator.CONTAINS
    assert result[1].values == ["pending"]


def test_get_filter_query_params_normalizes_camel_case():
    filter_json = json.dumps([{"fields": ["displayName", "createdBy"], "operator": "contains", "values": ["test"]}])
    result = get_filter_query_params(filter=filter_json)
    assert len(result) == 1
    assert result[0].fields == ["display_name", "created_by"]


def test_get_filter_query_params_invalid():
    result = get_filter_query_params(filter="not a json")
    assert result == []


def test_get_filter_query_params_none():
    result = get_filter_query_params(filter=None)
    assert result == []


def test_get_filter_query_params_empty_list():
    result = get_filter_query_params(filter="[]")
    assert result == []


# -- SortCondition normalization --


def test_sort_condition_normalizes_camel_case():
    c = SortCondition(field="createdAt", direction="desc")
    assert c.field == "created_at"


def test_sort_condition_preserves_snake_case():
    c = SortCondition(field="created_at", direction="asc")
    assert c.field == "created_at"


def test_sort_condition_preserves_single_word():
    c = SortCondition(field="name", direction="asc")
    assert c.field == "name"


# -- FilterCondition normalization --


def test_filter_condition_normalizes_camel_case():
    c = FilterCondition(fields=["displayName", "createdBy"], operator="contains", values=["x"])
    assert c.fields == ["display_name", "created_by"]


def test_filter_condition_preserves_snake_case():
    c = FilterCondition(fields=["display_name"], operator="eq", values=["x"])
    assert c.fields == ["display_name"]


# -- sort_list --


class _MetricsItem(BaseModel):
    display_name: str | None = Field(default=None)
    created_by: str | None = Field(default=None)


def test_sort_list_with_pydantic_models():
    items = [
        _MetricsItem(display_name="B", created_by="bob"),
        _MetricsItem(display_name="A", created_by="alice"),
    ]
    result = sort_list(items, sort_by="created_by", sort_order=SortDirection.asc)
    assert result[0].created_by == "alice"
    assert result[1].created_by == "bob"


def test_sort_list_via_sort_condition():
    """SortCondition normalizes to snake_case, then sort_list receives the correct attribute name."""
    items = [
        _MetricsItem(display_name="B", created_by="alice"),
        _MetricsItem(display_name="A", created_by="bob"),
    ]
    condition = SortCondition(field="createdBy", direction="asc")
    result = sort_list(items, sort_by=condition.field, sort_order=condition.direction)
    assert result[0].created_by == "alice"
    assert result[1].created_by == "bob"
