# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_email
from api_common.database import get_session
from api_common.exceptions import NotFoundException, ValidationException
from api_common.schemas import ListResponse

from ..workloads.enums import WorkloadType
from .repository import (
    create_chart,
    delete_chart,
    list_charts,
    update_chart,
)
from .schemas import ChartCreate, ChartListResponse, ChartResponse, ChartUpdate
from .service import get_chart

router = APIRouter(tags=["Charts"])


@router.post(
    "/charts",
    operation_id="create_chart",
    summary="Create workload template",
    description=dedent("""
        Create reusable Helm chart template for standardized AI/ML workload deployment.
        Requires super administrator role. Defines container specifications, resource
        requirements, and configuration patterns for consistent workload management.
    """),
    status_code=status.HTTP_201_CREATED,
    response_model=ChartResponse,
)
async def create_chart_endpoint(
    chart: ChartCreate = Form(), session: AsyncSession = Depends(get_session), user: str = Depends(get_user_email)
) -> ChartResponse:
    try:
        chart_obj = await create_chart(session, chart, user)
        return chart_obj
    except ValueError as e:
        raise ValidationException(str(e))


@router.put(
    "/charts/{chart_id}",
    operation_id="update_chart",
    summary="Update workload template",
    description=dedent("""
        Modify existing Helm chart template including configuration files and resource
        specifications. Requires super administrator role. Updates template definitions
        for improved workload deployment patterns and configurations.
    """),
    status_code=status.HTTP_200_OK,
    response_model=ChartResponse,
)
async def update_chart_endpoint(
    chart_id: UUID,
    chart_update: ChartUpdate = Form(),
    session: AsyncSession = Depends(get_session),
    user: str = Depends(get_user_email),
) -> ChartResponse:
    try:
        chart = await update_chart(session, chart_id, chart_update, user)
        return chart
    except ValueError as e:
        raise ValidationException(str(e))


@router.get(
    "/charts",
    response_model=ListResponse[ChartListResponse],
    status_code=status.HTTP_200_OK,
    summary="List workload templates",
    description=dedent("""
        List all available Helm chart templates for AI/ML workload deployment.
        Requires authentication. Used for discovering available workload patterns
        and standardized deployment configurations.
    """),
)
async def get_charts(
    session: AsyncSession = Depends(get_session),
    chart_type: WorkloadType | None = Query(default=None, alias="type"),
) -> ListResponse[ChartListResponse]:
    charts = await list_charts(session, chart_type)
    return ListResponse(data=charts)


@router.get(
    "/charts/{chart_id}",
    operation_id="get_chart",
    summary="Get workload template details",
    description=dedent("""
        Retrieve detailed information about a specific Helm chart template including
        configuration files and user input definitions. Used for understanding
        template specifications before workload deployment.
    """),
    response_model=ChartResponse,
)
async def get_chart_endpoint(
    chart_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ChartResponse:
    chart = await get_chart(session, chart_id=chart_id)
    return chart


@router.delete(
    "/charts/{chart_id}",
    operation_id="delete_chart",
    summary="Delete workload template",
    description=dedent("""
        Remove Helm chart template from system. Requires super administrator role.
        Permanently deletes template and associated configuration files. Use with
        caution as this affects workload deployment capabilities.
    """),
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_chart_endpoint(chart_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    deleted = await delete_chart(session, chart_id)
    if not deleted:
        raise NotFoundException("Chart not found")
