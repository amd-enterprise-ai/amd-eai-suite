# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from fastapi import APIRouter, Depends, status
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..metrics.schemas import CurrentUtilization, MetricsTimeRange, MetricsTimeseries
from ..metrics.service import get_current_utilization as get_current_utilization_from_ds
from ..metrics.service import get_gpu_device_utilization_timeseries as get_gpu_device_utilization_timeseries_from_ds
from ..metrics.service import get_gpu_memory_utilization_timeseries as get_gpu_memory_utilization_timeseries_from_ds
from ..metrics.service import (
    get_prometheus_client,
)
from ..utilities.database import get_session
from ..utilities.keycloak_admin import KeycloakAdmin, get_kc_admin
from ..utilities.security import (
    ensure_platform_administrator,
)
from .schemas import OrganizationResponse
from .utils import get_realm_details

router = APIRouter(tags=["Organizations"])


@router.get(
    "/organization",
    operation_id="get_current_user_organization",
    summary="Get current organization details",
    description="""
    Retrieves information about the current user's organization.
    """,
    status_code=status.HTTP_200_OK,
    response_model=OrganizationResponse,
)
async def get_current_user_organization(
    kc_admin: KeycloakAdmin = Depends(get_kc_admin),
) -> OrganizationResponse:
    return await get_realm_details(kc_admin=kc_admin)


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
    _: None = Depends(ensure_platform_administrator),
    time_range: MetricsTimeRange = Depends(),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries:
    return await get_gpu_memory_utilization_timeseries_from_ds(
        session=session,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
        step=time_range.step,
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
    _: None = Depends(ensure_platform_administrator),
    time_range: MetricsTimeRange = Depends(),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries:
    return await get_gpu_device_utilization_timeseries_from_ds(
        session=session,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
        step=time_range.step,
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
    _: None = Depends(ensure_platform_administrator),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> CurrentUtilization:
    return await get_current_utilization_from_ds(session=session, prometheus_client=prometheus_client)
