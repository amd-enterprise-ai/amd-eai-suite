# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.dialects.postgresql import UUID

from .schemas import FilterCondition, FilterOperator, PaginationConditions, SortCondition, SortDirection


def get_count_query[T](query: Select[T]) -> Select[int]:
    """
    Creates a count query from a SQLAlchemy query object.
    """
    # Create a count query based on the original query's statement
    count_query = select(func.count()).select_from(query.subquery())
    # Ensure no ordering is applied to the count query
    count_query = count_query.order_by(None)
    return count_query


def apply_sorting_to_query[T](query: Select[T], sort: list[SortCondition], model: list[type[T]]) -> Select[T]:
    """
    Applies sorting conditions to a SQLAlchemy Select query based on a list of sort specifications.

    Args:
        query (Select[T]): The initial SQLAlchemy Select query to which sorting will be applied.
        sort (List[SortCondition]): A list of sorting conditions, where each condition is a dictionary
            containing the 'field' to sort by and the 'direction' ('asc' or 'desc').
        model (Type[T]): The SQLAlchemy model class used to resolve column attributes for sorting.

    Returns:
        Select[T]: The query object with the specified sorting applied.

    Notes:
        - If a field specified in the sort condition does not exist on the model, it will be ignored.
        - If no sort conditions are provided, the original query is returned unchanged.
    """

    sorted_query = query
    if sort:
        for spec in sort:
            field_name = getattr(spec, "field", None)
            direction = getattr(spec, "direction", SortDirection.asc)
            # Find the matching column from any of the models
            column = None
            if isinstance(field_name, str):
                for m in model:
                    column = getattr(m, field_name, None)
                    if column is not None:
                        break

            if column is not None:
                if direction == SortDirection.asc:
                    sorted_query = sorted_query.order_by(asc(column))
                elif direction == SortDirection.desc:
                    sorted_query = sorted_query.order_by(desc(column))

    return sorted_query


def apply_filter_to_query[T](query: Select[T], filter: list[FilterCondition], model: list[type[T]]) -> Select[T]:
    """
    Applies a list of filter conditions to a SQLAlchemy Select query for a given model.

    Args:
        query (Select[T]): The initial SQLAlchemy Select query to which filters will be applied.
        filter (List[FilterCondition]): A list of filter condition dictionaries, each specifying a field, operator, and values.
        model (Type[T]): The SQLAlchemy model class used to resolve column attributes for filtering.

    Returns:
        Select[T]: The modified SQLAlchemy Select query with the specified filters applied.

    Raises:
        ValueError: If an unsupported filter operator is encountered.

    Notes:
        - Supports 'EQ' (equals) and 'CONTAINS' (case-insensitive substring match) operators.
        - Automatically converts filter values to UUID strings if the target column type is UUID.
        - Ignores filters for fields that do not exist on the model.
    """

    filter_query = query

    if filter:
        for spec in filter:
            field_names = getattr(spec, "fields", [])
            operator: FilterOperator = getattr(spec, "operator", FilterOperator.EQ)
            values: list[str] = getattr(spec, "values", [])
            show_all_if_values_empty: bool = getattr(spec, "show_all_if_values_empty", False)

            # Ensure field_names is a list
            if isinstance(field_names, str):
                field_names = [field_names]
            elif not isinstance(field_names, list):
                field_names = []

            columns = []
            for field_name in field_names:
                for m in model:
                    column = getattr(m, field_name, None)
                    if column is not None:
                        columns.append(column)
                        break

            # Handle UUID fields: convert value(s) to UUID if any column type is UUID
            for _, column in enumerate(columns):
                if column is not None and hasattr(column, "type") and isinstance(column.type, UUID):
                    try:
                        values = [str(uuid.UUID(v)) for v in values]
                    except Exception:
                        values = []
                    break  # Only need to convert once if any column is UUID

            if columns:
                if not values and not show_all_if_values_empty:
                    # Add a condition that will never be true (e.g., column.in_([]))
                    filter_query = filter_query.where(False)
                    continue
                or_conditions = []
                for column in columns:
                    if operator == FilterOperator.EQ:
                        or_conditions.extend([column == value for value in values])
                    elif operator == FilterOperator.CONTAINS:
                        or_conditions.extend([column.ilike(f"%{value}%") for value in values])
                    else:
                        raise ValueError(f"Unsupported filter operator: {operator}")
                if or_conditions:
                    filter_query = filter_query.where(or_(*or_conditions))

    return filter_query


def apply_pagination_to_query[T](query: Select[T], pagination: PaginationConditions) -> Select[T]:
    """
    Applies pagination to a SQLAlchemy Select query based on the provided pagination conditions.

    Args:
        query (Select[T]): The SQLAlchemy Select query to paginate.
        pagination (PaginationConditions): An object containing pagination parameters such as page number and page size.

    Returns:
        Select[T]: The query with pagination (limit and offset) applied if valid pagination conditions are provided; otherwise, returns the original query.
    """

    paginated_query = query

    if pagination and pagination.page_size and pagination.page:
        paginated_query = query.limit(pagination.page_size).offset((pagination.page - 1) * pagination.page_size)
    return paginated_query
