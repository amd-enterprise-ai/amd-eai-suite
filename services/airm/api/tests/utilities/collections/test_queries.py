# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid

import pytest
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base

from app.utilities.collections.queries import apply_filter_to_query, apply_pagination_to_query, apply_sorting_to_query
from app.utilities.collections.schemas import FilterCondition, FilterOperator

Base = declarative_base()


class DummyPagination:
    def __init__(self, page=None, page_size=None):
        self.page = page
        self.page_size = page_size


class DummyModel(Base):  # type: ignore
    __tablename__ = "dummy"
    id = Column(PG_UUID(as_uuid=False), primary_key=True)
    name = Column(String)
    description = Column(String)


# Mock SortCondition for testing
class SortCondition:
    def __init__(self, field, direction="asc"):
        self.field = field
        self.direction = direction


# Mock model for SQLAlchemy
Base = declarative_base()


class User(Base):  # type: ignore
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)


@pytest.fixture
def base_query():
    return select(DummyModel)


@pytest.fixture
def sort_conditions():
    return [
        SortCondition(field="name", direction="asc"),
        SortCondition(field="age", direction="desc"),
    ]


class Test_Sorting_Queries:
    """Test sorting conditions are applied correctly to queries."""

    def test_apply_sorting_to_query(self, monkeypatch, sort_conditions):
        # Patch SortCondition import in the tested module
        monkeypatch.setattr("app.utilities.collections.schemas.SortCondition", SortCondition)
        query = select(User)
        sorted_query = apply_sorting_to_query(query, sort_conditions, [User])
        # Should have two ORDER BY clauses
        assert "ORDER BY" in str(sorted_query)
        assert "users.name ASC" in str(sorted_query)
        assert "users.age DESC" in str(sorted_query)

    def test_apply_sorting_to_query_empty(self, monkeypatch):
        monkeypatch.setattr("app.utilities.collections.schemas.SortCondition", SortCondition)
        query = select(User)
        sorted_query = apply_sorting_to_query(query, [], User)
        # Should not have ORDER BY clause
        assert "ORDER BY" not in str(sorted_query)

    def test_apply_sorting_to_query_invalid_field(self, monkeypatch):
        monkeypatch.setattr("app.utilities.collections.schemas.SortCondition", SortCondition)
        query = select(User)
        sort = [SortCondition(field="nonexistent", direction="asc")]
        sorted_query = apply_sorting_to_query(query, sort, [User])
        # Should not add ORDER BY for invalid field
        assert "ORDER BY" not in str(sorted_query)


def make_filter(fields, operator, values, show_all_if_empty=False):
    return [
        FilterCondition(fields=fields, operator=operator, values=values, show_all_if_values_empty=show_all_if_empty)
    ]


class Test_Filter_Queries:
    """Test filter conditions are applied correctly to queries."""

    def test_eq_operator_on_string_field(self, base_query):
        filters = make_filter(["name"], FilterOperator.EQ, ["Alice"])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)
        assert "dummy.name = :name_1" in sql

    def test_contains_operator_on_string_field(self, base_query):
        filters = make_filter(["description"], FilterOperator.CONTAINS, ["test"])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)
        assert "lower(dummy.description) LIKE" in sql
        assert "%test%" in str(query.compile().params.values())

    def test_eq_operator_on_uuid_field(self, base_query):
        test_uuid = str(uuid.uuid4())
        filters = make_filter(["id"], FilterOperator.EQ, [test_uuid])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)
        assert "dummy.id = :id_1" in sql
        assert test_uuid in str(query.compile().params.values())

    def test_invalid_uuid_value(self, base_query):
        filters = make_filter(["id"], FilterOperator.EQ, ["not-a-uuid"])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        # Should not add any filter due to invalid UUID
        sql = str(query)
        assert "WHERE dummy.id" not in sql

    def test_missing_column_is_ignored(self, base_query):
        filters = make_filter(["nonexistent"], FilterOperator.EQ, ["foo"])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)
        assert "nonexistent" not in sql

    def test_multiple_values_for_eq(self, base_query):
        filters = make_filter(["name"], FilterOperator.EQ, ["Alice", "Bob"])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)
        # Both values should be present as separate filters
        assert sql.count("dummy.name =") == 2

    def test_multiple_fields(self, base_query):
        filters = make_filter(["name", "description"], FilterOperator.EQ, ["Alice", "Bob"])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)

        # Both fields should be present as separate filters joined by OR
        assert sql.count("dummy.name =") == 2
        assert sql.count("dummy.description =") == 2
        # Ensure the SQL contains an OR between the two conditions
        assert "dummy.name = " in sql and "dummy.description = " in sql
        # Check that the two conditions are joined by OR (not AND)
        or_index = sql.find("dummy.name =")
        or_keyword_index = sql.find("OR", or_index)
        assert or_keyword_index != -1

    def test_show_all_if_empty_values_not_set(self, base_query):
        filters = make_filter(["name", "description"], FilterOperator.EQ, [])
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)
        # Both fields should be present as separate filters joined by OR
        assert sql.count("WHERE false") == 1

    def test_show_all_if_empty_values_set(self, base_query):
        filters = make_filter(["name", "description"], FilterOperator.CONTAINS, [], True)
        query = apply_filter_to_query(base_query, filters, [DummyModel])
        sql = str(query)
        # Both fields should be present as separate filters joined by OR
        assert sql.count("WHERE") == 0


class Test_Pagination_Conditions_Queries:
    """Test pagination conditions are applied correctly to queries."""

    def test_apply_pagination_to_query_applies_limit_and_offset(self):
        query = select(User)
        pagination = DummyPagination(page=2, page_size=10)
        paginated_query = apply_pagination_to_query(query, pagination)
        sql = str(paginated_query)
        assert "LIMIT " in sql
        assert "OFFSET " in sql

    def test_apply_pagination_to_query_no_pagination_returns_original(self):
        query = select(User)
        pagination = None
        paginated_query = apply_pagination_to_query(query, pagination)
        assert paginated_query is query

    def test_apply_pagination_to_query_missing_page_size_returns_original(self):
        query = select(User)
        pagination = DummyPagination(page=1, page_size=None)
        paginated_query = apply_pagination_to_query(query, pagination)
        assert paginated_query is query

    def test_apply_pagination_to_query_missing_page_returns_original(self):
        query = select(User)
        pagination = DummyPagination(page=None, page_size=10)
        paginated_query = apply_pagination_to_query(query, pagination)
        assert paginated_query is query

    def test_apply_pagination_to_query_zero_page_and_size_returns_original(self):
        query = select(User)
        pagination = DummyPagination(page=0, page_size=0)
        paginated_query = apply_pagination_to_query(query, pagination)
        assert paginated_query is query
