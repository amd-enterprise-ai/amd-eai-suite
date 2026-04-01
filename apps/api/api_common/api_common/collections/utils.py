# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Utilities for collection operations (pagination, sorting, etc.)."""

from dataclasses import dataclass
from typing import Any

from .schemas import SortDirection


@dataclass
class PaginatedResult[T]:
    """Result of paginating a list."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def sort_list[T](
    items: list[T],
    sort_by: str | None = None,
    sort_order: SortDirection = SortDirection.desc,
) -> list[T]:
    """Sort a list of items by a field.

    Args:
        items: The list of items to sort
        sort_by: Field name to sort by. If None, returns items unchanged.
        sort_order: Sort direction (asc or desc). Defaults to desc.

    Returns:
        Sorted list of items. None values are placed at the end.
    """
    if not sort_by or not items:
        return items

    def get_sort_key(item: T) -> tuple[int, Any]:
        if hasattr(item, sort_by):
            value = getattr(item, sort_by)
        elif isinstance(item, dict):
            value = item.get(sort_by)
        else:
            value = None
        # Handle None/missing values by putting them at the end
        if value is None:
            return (1, "")
        return (0, value)

    return sorted(items, key=get_sort_key, reverse=(sort_order == SortDirection.desc))


def paginate_list[T](items: list[T], page: int = 1, page_size: int = 20) -> PaginatedResult[T]:
    """Paginate a list of items.

    Args:
        items: The full list of items to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PaginatedResult with the paginated items and metadata
    """
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    return PaginatedResult(
        items=items[start_idx:end_idx],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
