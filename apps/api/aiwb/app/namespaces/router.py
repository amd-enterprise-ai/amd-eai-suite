# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent

from fastapi import APIRouter, Depends, Path, Query, status
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_groups
from api_common.collections import SortDirection
from api_common.database import get_session
from api_common.schemas import ListResponse

from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..metrics.client import get_prometheus_client
from ..metrics.enums import NamespaceMetricName
from ..metrics.schemas import MetricsTimeRange, MetricsTimeseries
from ..metrics.service import get_metric_by_namespace
from ..workloads.enums import WorkloadStatus, WorkloadType
from .crds import Namespace
from .schemas import (
    ChattableResponse,
    NamespaceStatsCounts,
    NamespaceWorkloadMetricsListPaginated,
)
from .security import ensure_access_to_workbench_namespace, get_workbench_namespace
from .service import (
    get_accessible_namespaces,
    get_chattable_resources,
    get_namespace_stats_counts,
    get_namespace_workload_metrics_paginated,
)

router = APIRouter(prefix="/namespaces", tags=["Namespaces"])


@router.get(
    "",
    response_model=ListResponse[str],
    status_code=status.HTTP_200_OK,
    summary="List accessible namespaces",
    description="List namespaces accessible to the user based on JWT groups.",
)
async def list_namespaces(
    user_groups: list[str] = Depends(get_user_groups),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ListResponse[str]:
    namespaces = await get_accessible_namespaces(kube_client, user_groups)
    return ListResponse(data=[ns.name for ns in namespaces])


@router.get(
    "/{namespace}/metrics",
    response_model=NamespaceWorkloadMetricsListPaginated,
    status_code=status.HTTP_200_OK,
    summary="Get namespace resource metrics (paginated)",
    description=dedent("""
        Retrieve paginated metrics for all resources (AIM services and workloads) in a namespace.
        Includes GPU usage and VRAM for dashboard visualization.
        Supports filtering by workload type(s) and/or status(es), and sorting by any field.
    """),
)
async def get_namespace_metrics_endpoint(
    namespace: Namespace = Depends(get_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize", description="Number of items per page"),
    workload_type: list[WorkloadType] | None = Query(None, description="Filter by workload type(s)"),
    status_filter: list[WorkloadStatus] | None = Query(None, description="Filter by workload status(es)"),
    sort_by: str | None = Query(
        None, alias="sortBy", description="Field to sort by (e.g., 'created_at', 'name', 'status')"
    ),
    sort_order: SortDirection = Query(SortDirection.desc, alias="sortOrder", description="Sort order: 'asc' or 'desc'"),
) -> NamespaceWorkloadMetricsListPaginated:
    """Get paginated resources and their metrics in a namespace."""
    return await get_namespace_workload_metrics_paginated(
        kube_client=kube_client,
        session=session,
        namespace=namespace,
        prometheus_client=prometheus_client,
        page=page,
        page_size=page_size,
        workload_types=workload_type,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{namespace}/stats",
    response_model=NamespaceStatsCounts,
    status_code=status.HTTP_200_OK,
    summary="Get namespace resource statistics",
    description=dedent("""
        Retrieve aggregated statistics for all resources (AIM services and workloads) in a namespace.
        Returns counts of resources grouped by status (failed, pending, running, completed).

        This is a lightweight endpoint that provides summary statistics without detailed metrics.
    """),
)
async def get_namespace_stats_endpoint(
    namespace: Namespace = Depends(get_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> NamespaceStatsCounts:
    """Get resource statistics for a namespace."""
    return await get_namespace_stats_counts(
        kube_client=kube_client,
        session=session,
        namespace=namespace,
    )


@router.get(
    "/{namespace}/metrics/{metric}",
    response_model=MetricsTimeseries,
    status_code=status.HTTP_200_OK,
    summary="Get namespace metric",
    description="Retrieve aggregated metrics for a namespace by querying Prometheus using the namespace name.",
)
async def get_namespace_metric(
    namespace: Namespace = Depends(get_workbench_namespace),
    metric: NamespaceMetricName = Path(description="Metric name to retrieve"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries:
    return await get_metric_by_namespace(
        namespace=namespace,
        metric=metric,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
    )


@router.get(
    "/{namespace}/chattable",
    response_model=ChattableResponse,
    status_code=status.HTTP_200_OK,
    summary="List all chattable resources",
    description=dedent("""
        List all RUNNING resources that support chat functionality in the namespace.
        Returns both AIM services and workloads (finetuned models) that are available for chat.
        This unified endpoint provides all models that can be used in the Chat interface.
    """),
)
async def get_chattable_resources_endpoint(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> ChattableResponse:
    """Get all chattable AIM services and workloads in a namespace."""
    return await get_chattable_resources(
        kube_client=kube_client,
        session=session,
        namespace=namespace,
    )
