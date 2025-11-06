# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from pydantic import AwareDatetime

from ..metrics.schemas import CurrentUtilization, MetricsTimeseries
from ..metrics.service import get_current_utilization as get_current_utilization_from_ds
from ..metrics.service import get_gpu_device_utilization_timeseries as get_gpu_device_utilization_timeseries_from_ds
from ..metrics.service import get_gpu_memory_utilization_timeseries as get_gpu_memory_utilization_timeseries_from_ds
from ..metrics.service import (
    get_prometheus_client,
)
from ..metrics.utils import validate_datetime_range
from ..users.schemas import InviteUser
from ..users.service import create_user_in_organization
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException
from ..utilities.keycloak_admin import get_kc_admin
from ..utilities.security import (
    ensure_platform_administrator,
    ensure_super_administrator,
    get_user_email,
    get_user_organization,
)
from .repository import get_organization_by_id
from .schemas import OrganizationCreate, OrganizationResponse, Organizations
from .service import create_organization as create_organization_in_system
from .service import enrich_organization_details, get_all_organizations

router = APIRouter(tags=["Organizations"])


@router.get(
    "/organizations",
    operation_id="get_organizations",
    summary="List all organizations",
    description="""
        List all organizations in the system with detailed metadata. Requires
        super administrator role. Used for system-wide organization management
        and multi-tenant administration workflows.
    """,
    status_code=status.HTTP_200_OK,
    response_model=Organizations,
)
async def get_organizations(
    _=Depends(ensure_super_administrator),
    session=Depends(get_session),
    kc_admin=Depends(get_kc_admin),
) -> Organizations:
    organizations = await get_all_organizations(kc_admin, session)
    return Organizations(organizations=organizations)


@router.post(
    "/organizations",
    operation_id="create_organization",
    summary="Create organization",
    description="""
        Create new organization for multi-tenant AI/ML resource management.
        Requires super administrator role. Sets up organization in both Keycloak
        and database for isolated resource management and user access control.
    """,
    status_code=status.HTTP_201_CREATED,
    response_model=OrganizationResponse,
)
async def create_organization(
    organization: OrganizationCreate,
    _=Depends(ensure_super_administrator),
    session=Depends(get_session),
    kc_admin=Depends(get_kc_admin),
):
    return await create_organization_in_system(kc_admin, session, organization)


@router.post(
    "/organizations/{organization_id}/users",
    operation_id="invite_user_to_organization",
    summary="Add user to organization",
    description="""
        Add user to organization with initial access setup. Requires super
        administrator role. Creates user account and establishes organization
        membership for multi-tenant resource access.
    """,
    status_code=status.HTTP_201_CREATED,
)
async def invite_user_to_organization(
    _=Depends(ensure_super_administrator),
    user=Depends(get_user_email),
    session=Depends(get_session),
    kc_admin=Depends(get_kc_admin),
    organization_id: UUID = Path(description="The ID of the organization to be retrieved"),
    invite_user: InviteUser = Body(description="The user to be invited in the organization"),
):
    organization = await get_organization_by_id(session, organization_id)

    if not organization:
        raise NotFoundException("Organization not found")

    await create_user_in_organization(kc_admin, session, organization, invite_user, user)


@router.get(
    "/organization",
    operation_id="get_current_user_organization",
    summary="Get current organization details",
    description="""
        Retrieve detailed information about the authenticated platform administrator's
        organization including member count and configuration. Requires platform
        administrator role. Essential for organization management and user workflows.
    """,
    status_code=status.HTTP_200_OK,
    response_model=OrganizationResponse,
)
async def get_current_user_organization(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    kc_admin=Depends(get_kc_admin),
):
    if not organization:
        raise NotFoundException("Organization not found for user")

    return await enrich_organization_details(kc_admin=kc_admin, organization=organization)


@router.get(
    "/metrics/gpu_memory_utilization",
    operation_id="get_gpu_memory_utilization_timeseries",
    summary="Get GPU memory utilization timeseries",
    description="""
        Retrieve GPU memory usage metrics across all organization clusters over time.
        Shows memory allocation patterns and utilization trends across the entire
        organization infrastructure. Critical for capacity planning and cost management.
    """,
    status_code=status.HTTP_200_OK,
    response_model=MetricsTimeseries,
)
async def get_gpu_memory_utilization_timeseries(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsTimeseries:
    validate_datetime_range(start, end)

    return await get_gpu_memory_utilization_timeseries_from_ds(
        session=session, start=start, end=end, organization=organization, prometheus_client=prometheus_client
    )


@router.get(
    "/metrics/gpu_device_utilization",
    operation_id="get_gpu_device_utilization_timeseries",
    summary="Get GPU device utilization timeseries",
    description="""
        Retrieve GPU compute utilization metrics across all organization clusters.
        Shows percentage of GPU compute capacity used across the entire organization
        infrastructure. Essential for resource optimization and capacity planning.
    """,
    status_code=status.HTTP_200_OK,
    response_model=MetricsTimeseries,
)
async def get_gpu_device_utilization_timeseries(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    start: datetime = Query(..., description="The start timestamp for the timeseries"),
    end: datetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsTimeseries:
    validate_datetime_range(start, end)

    return await get_gpu_device_utilization_timeseries_from_ds(
        session=session, start=start, end=end, organization=organization, prometheus_client=prometheus_client
    )


@router.get(
    "/metrics/utilization",
    operation_id="get_current_utilization",
    summary="Get current cluster utilization",
    description="""
        Get real-time GPU utilization and workload statistics across organization clusters.
        Provides immediate insights into resource usage, active workloads, and cluster
        health. Critical for operational monitoring and resource allocation decisions.
    """,
    status_code=status.HTTP_200_OK,
    response_model=CurrentUtilization,
)
async def get_current_utilization(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> CurrentUtilization:
    return await get_current_utilization_from_ds(
        session=session, organization=organization, prometheus_client=prometheus_client
    )
