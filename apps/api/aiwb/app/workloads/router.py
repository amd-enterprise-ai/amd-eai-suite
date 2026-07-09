# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""HTTP interface for the workloads polymorphic read-only view.

The workloads router exposes a cross-cutting view over every workload type
(inference, fine-tuning, workspaces) for shared concerns: listing, fetching,
logs, and metrics. Capability-specific mutations live on their own routers
(``/v1/projects/{project}/inference``, ``/fine-tuning``, ``/workspaces``).

Path-keying choice
------------------
URLs use ``/v1/projects/{project}/workloads/...`` per the convention
established by the capability routers (EAI-6354/6357/6359/6311/6312).
``ensure_access_to_project`` maps the project identifier 1:1 to the
underlying workbench namespace.
"""

from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import StreamingResponse
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.collections import PaginationMetadata, SortCondition, paginate_list
from api_common.database import get_session
from api_common.exceptions import NotFoundException
from api_common.schemas import QueryParam

from ..common_responses import PROJECT_ACCESS_RESPONSES
from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..logs.client import get_loki_client
from ..logs.schemas import LogsQuery, WorkloadLogsResponse
from ..logs.service import get_logs_by_workload_id, stream_workload_logs_sse
from ..metrics.client import get_prometheus_client
from ..metrics.enums import MetricName, NamespaceMetricName
from ..metrics.schemas import MetricsScalar, MetricsScalarWithRange, MetricsTimeRange, MetricsTimeseries
from ..metrics.service import get_metric_by_namespace, get_metric_by_workload_id
from ..projects.crds import Namespace
from ..projects.security import ensure_access_to_project, get_project_namespace
from .repository import get_workload_by_id, get_workloads
from .schemas import (
    WorkloadListQuery,
    WorkloadMetricsListPaginated,
    WorkloadMetricsQuery,
    WorkloadResponse,
    WorkloadsList,
    WorkloadStatsCounts,
    WorkloadStreamQuery,
)
from .service import (
    ensure_workload_or_aim_service_exists,
    get_workload_metrics_paginated,
    get_workload_stats_counts,
)

router = APIRouter(tags=["Workloads"])


@router.get(
    "/projects/{project}/workloads",
    response_model=WorkloadsList,
    status_code=status.HTTP_200_OK,
    summary="List workloads in project",
    description=dedent("""
        List all workloads deployed in a project as a single polymorphic view
        across inference deployments, fine-tuning jobs, and workspaces, as a
        paginated envelope (default page size 10, max 100). Use `?page=` and
        `?pageSize=` to navigate; the response includes a `pagination` object
        with `page`, `pageSize`, and `total` alongside `data`.

        Use `?workloadType=` (repeatable) to restrict the result to one or more
        workload kinds and `?statusFilter=` (repeatable) to restrict by status.
        Both filters compose; pagination applies after filtering so `total`
        reflects the filtered count. This endpoint is a read-only cross-cutting
        view; capability-specific mutations live on the dedicated routers
        (`/inference`, `/fine-tuning`, `/workspaces`).
    """),
    responses={**PROJECT_ACCESS_RESPONSES},
)
async def list_project_workloads(
    query: QueryParam[WorkloadListQuery],
    project: str = Depends(ensure_access_to_project),
    session: AsyncSession = Depends(get_session),
) -> WorkloadsList:
    workloads = await get_workloads(
        session=session,
        namespace=project,
        workload_types=query.workload_type if query.workload_type else None,
        status_filter=query.status_filter if query.status_filter else None,
    )
    paginated = paginate_list(workloads, page=query.page, page_size=query.page_size)
    return WorkloadsList(
        data=[WorkloadResponse.model_validate(workload) for workload in paginated.items],
        pagination=PaginationMetadata(
            page=paginated.page,
            page_size=paginated.page_size,
            total=paginated.total,
        ),
    )


@router.get(
    "/projects/{project}/workloads/stats",
    response_model=WorkloadStatsCounts,
    status_code=status.HTTP_200_OK,
    summary="Get project workload statistics",
    description=dedent("""
        Retrieve aggregated statistics for all resources (AIM services and workloads) in a project.
        Returns counts of resources grouped by status (failed, pending, running, completed).

        This is a lightweight endpoint that provides summary statistics without detailed metrics.
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
    },
)
async def get_project_workload_stats(
    project: Namespace = Depends(get_project_namespace),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> WorkloadStatsCounts:
    """Get resource statistics for a project."""
    return await get_workload_stats_counts(
        kube_client=kube_client,
        session=session,
        namespace=project,
    )


@router.get(
    "/projects/{project}/workloads/metrics",
    response_model=WorkloadMetricsListPaginated,
    status_code=status.HTTP_200_OK,
    summary="Get project workload metrics (paginated)",
    description=dedent("""
        Retrieve metrics for all resources (AIM services and workloads) in a project as a
        paginated envelope (default page size 10, max 100). Use `?page=` and `?pageSize=`
        to navigate; the response includes a `pagination` object with `page`, `pageSize`,
        and `total` alongside `data`. Includes GPU usage and VRAM for dashboard visualization.

        Supports filtering by `workloadType` and `statusFilter` (both repeatable),
        and sorting via `sortBy` with `sortOrder`. Common `sortBy` values are
        `createdAt`, `name`, and `status`; unknown fields are silently ignored
        (ordering unchanged).
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
    },
)
async def get_project_workload_metrics(
    query: QueryParam[WorkloadMetricsQuery],
    project: Namespace = Depends(get_project_namespace),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> WorkloadMetricsListPaginated:
    """Get paginated resources and their metrics in a project."""
    sort = [SortCondition(field=query.sort_by, direction=query.sort_order)] if query.sort_by else None
    return await get_workload_metrics_paginated(
        kube_client=kube_client,
        session=session,
        namespace=project,
        prometheus_client=prometheus_client,
        page=query.page,
        page_size=query.page_size,
        workload_types=query.workload_type,
        status_filter=query.status_filter,
        sort=sort,
    )


@router.get(
    "/projects/{project}/workloads/metrics/{metric}",
    response_model=MetricsTimeseries,
    status_code=status.HTTP_200_OK,
    summary="Get project metric",
    description=dedent("""
        Retrieve a single aggregated metric for a project by querying
        Prometheus keyed on the project namespace.

        The metric path parameter must be one of the namespace-scoped metric
        names. Use the `start` and `end` query parameters to bound the time
        window; omitted bounds default to the metric's standard window.
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        422: {
            "description": (
                "Invalid metric name (not in the supported enum), "
                "or invalid time range (e.g., start >= end, or start older than the lookback window)."
            )
        },
    },
)
async def get_project_metric(
    project: Namespace = Depends(get_project_namespace),
    metric: NamespaceMetricName = Path(description="Metric name to retrieve"),
    time_range: MetricsTimeRange = Depends(),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries:
    return await get_metric_by_namespace(
        namespace=project,
        metric=metric,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
    )


@router.get(
    "/projects/{project}/workloads/{workload_id}",
    response_model=WorkloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workload details",
    description="Retrieve detailed information about a specific workload in a project.",
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "Project or namespace not found, or workload not found in the project."},
    },
)
async def get_workload(
    project: str = Depends(ensure_access_to_project),
    workload_id: UUID = Path(description="The UUID of the workload to get"),
    session: AsyncSession = Depends(get_session),
) -> WorkloadResponse:
    workload = await get_workload_by_id(session=session, namespace=project, workload_id=workload_id)
    if not workload:
        raise NotFoundException(f"Workload {workload_id} not found")

    return WorkloadResponse.model_validate(workload)


@router.get(
    "/projects/{project}/workloads/{workload_id}/metrics/{metric}",
    response_model=MetricsTimeseries | MetricsScalar | MetricsScalarWithRange,
    status_code=status.HTTP_200_OK,
    summary="Get workload metric",
    description="Retrieve a metric for a workload by querying Prometheus with workload_id.",
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "Project or namespace not found, or workload not found."},
        422: {
            "description": (
                "Invalid metric name (not in the supported enum), "
                "or invalid time range (e.g., start >= end, or start older than the lookback window)."
            )
        },
    },
)
async def get_workload_metric(
    project: str = Depends(ensure_access_to_project),
    time_range: MetricsTimeRange = Depends(),
    workload_id: UUID = Path(description="The UUID of the workload"),
    metric: MetricName = Path(description="Metric name to retrieve"),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries | MetricsScalar | MetricsScalarWithRange:
    await ensure_workload_or_aim_service_exists(
        session=session, kube_client=kube_client, project=project, workload_id=workload_id
    )

    return await get_metric_by_workload_id(
        workload_id=str(workload_id),
        metric=metric,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
    )


@router.get(
    "/projects/{project}/workloads/{workload_id}/logs",
    response_model=WorkloadLogsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workload logs",
    description="Retrieve logs for a specific workload from Loki, with pagination and filtering support.",
    responses={
        **PROJECT_ACCESS_RESPONSES,
        404: {"description": "Project or namespace not found, or workload not found."},
    },
)
async def get_workload_logs_endpoint(
    params: QueryParam[LogsQuery],
    project: str = Depends(ensure_access_to_project),
    workload_id: UUID = Path(description="The UUID of the workload"),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
    loki_client: object = Depends(get_loki_client),
) -> WorkloadLogsResponse:
    """Get logs for a workload with optional filtering and pagination."""
    await ensure_workload_or_aim_service_exists(
        session=session, kube_client=kube_client, project=project, workload_id=workload_id
    )

    return await get_logs_by_workload_id(
        workload_id=str(workload_id),
        loki_client=loki_client,
        start_date=params.start,
        end_date=params.end,
        page_token=params.page_token,
        limit=params.limit,
        level_filter=params.level,
        log_type=params.log_type,
        direction=params.direction,
    )


@router.get(
    "/projects/{project}/workloads/{workload_id}/logs/stream",
    operation_id="stream_workload_logs",
    summary="Stream logs for a workload in real-time",
    description=dedent("""
        Stream workload logs in real-time using Server-Sent Events (SSE).

        **Event Format:**
        ```
        data: {"timestamp": "2025-01-01T10:00:00Z", "level": "INFO", "message": "Log message"}

        ```

        **Connection Details:**
        - Media type: `text/event-stream`
        - Events sent every 1-30 seconds based on `delay` parameter
        - Connection stays open until client disconnects or error occurs
        - Errors are sent as JSON events with `error` field

        **Client Implementation:**
        Use EventSource API or equivalent SSE client library to consume the stream.
    """),
    responses={
        **PROJECT_ACCESS_RESPONSES,
        200: {
            "description": "SSE stream established successfully",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"timestamp": "2025-01-01T10:00:00Z", "level": "INFO", "message": "Application started"}\n\n'
                }
            },
        },
        404: {"description": "Project or namespace not found, or workload not found."},
        422: {"description": "Invalid parameters (e.g., delay out of range)"},
    },
)
async def workload_logs_stream(
    query: QueryParam[WorkloadStreamQuery],
    project: str = Depends(ensure_access_to_project),
    workload_id: UUID = Path(description="The ID of the workload"),
    session: AsyncSession = Depends(get_session),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> StreamingResponse:
    """Stream workload logs in real-time via SSE."""
    await ensure_workload_or_aim_service_exists(
        session=session, kube_client=kube_client, project=project, workload_id=workload_id
    )

    return StreamingResponse(
        stream_workload_logs_sse(
            workload_id=str(workload_id),
            start_time=query.start_time,
            level_filter=query.level,
            log_type=query.log_type,
            delay_seconds=query.delay,
        ),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
