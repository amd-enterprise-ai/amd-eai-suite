# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import json

from fastapi import Query
from loguru import logger
from pydantic.alias_generators import to_camel

from .schemas import FilterCondition, PaginationConditions, SortCondition


def get_pagination_query_params(
    page: int = 1,
    # Explicit alias needed because QueryParam[PaginationConditions] doesn't flatten
    # when the endpoint also has Depends() with Query() params (FastAPI limitation).
    # Tracked in: https://github.com/fastapi/fastapi/pull/12944
    page_size: int = Query(default=10, alias=to_camel("page_size")),
) -> PaginationConditions:
    """
    Dependency function to parse collection pagination query parameters with default pagination.
    """
    return PaginationConditions(page=page, page_size=page_size)


def get_sort_query_params(
    sort: str | None = Query(default=None),
) -> list[SortCondition]:
    """Dependency function to parse collection sort query parameter."""
    sort_spec: list[SortCondition] = []
    if sort:
        try:
            sort_spec = [SortCondition(**item) for item in json.loads(sort)]
        except Exception as e:
            logger.warning("Warning - Failed to parse sort query parameter", e)
            sort_spec = []
    return sort_spec


def get_filter_query_params(
    filter: str | None = Query(default=None),
) -> list[FilterCondition]:
    """Dependency function to parse collection filter query parameters."""
    filter_spec: list[FilterCondition] = []
    if filter:
        try:
            filter_spec = [FilterCondition(**item) for item in json.loads(filter)]
        except Exception:
            filter_spec = []
    return filter_spec
