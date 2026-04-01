# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from textwrap import dedent
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.responses import StreamingResponse
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.database import get_session
from api_common.exceptions import NotFoundException
from api_common.schemas import ListResponse

from ..logs.client import get_loki_client
from ..logs.schemas import LogLevel, LogsQueryRequest, LogType, WorkloadLogsResponse
from ..logs.service import get_logs_by_workload_id, stream_workload_logs_sse
from ..metrics.client import get_prometheus_client
from ..metrics.enums import MetricName
from ..metrics.schemas import MetricsScalar, MetricsScalarWithRange, MetricsTimeRange, MetricsTimeseries
from ..metrics.service import get_metric_by_workload_id
from ..namespaces.security import ensure_access_to_workbench_namespace
from .enums import WorkloadStatus, WorkloadType
from .repository import get_workload_by_id, get_workloads
from .schemas import WorkloadResponse
from .service import chat_with_workload, delete_workload_components, list_chattable_workloads

router = APIRouter(tags=["Workloads"])


@router.get(
    "/namespaces/{namespace}/workloads",
    response_model=ListResponse[WorkloadResponse],
    status_code=status.HTTP_200_OK,
    summary="List workloads in namespace",
    description="Retrieve all workloads deployed in a specific namespace, optionally filtered by workload type and status.",
)
async def list_namespace_workloads(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    workload_type: list[WorkloadType] = Query(default=[], description="Filter by workload type(s)"),
    status_filter: list[WorkloadStatus] = Query(default=[], description="Filter by workload status"),
) -> ListResponse[WorkloadResponse]:
    workloads = await get_workloads(
        session=session,
        namespace=namespace,
        workload_types=workload_type if workload_type else None,
        status_filter=status_filter if status_filter else None,
    )
    return ListResponse(data=[WorkloadResponse.model_validate(workload) for workload in workloads])


@router.get(
    "/namespaces/{namespace}/workloads/chattable",
    response_model=ListResponse[WorkloadResponse],
    status_code=status.HTTP_200_OK,
    summary="List chattable workloads",
    description="List RUNNING inference workloads that support chat functionality.",
)
async def get_chattable_workloads(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
) -> ListResponse[WorkloadResponse]:
    workloads = await list_chattable_workloads(session=session, namespace=namespace)
    return ListResponse(data=workloads)


@router.post(
    "/namespaces/{namespace}/workloads/{workload_id}/chat",
    summary="Chat with deployed workload",
    description=dedent("""
        Send chat messages to a deployed AI model workload for interactive conversations.
        Requires namespace access and a running inference workload with chat capability.
        Streams responses for real-time chat experience.
    """),
    response_class=StreamingResponse,
    responses={
        200: {"description": "Streaming chat response from the model"},
        404: {"description": "Workload not found"},
        422: {"description": "Workload is not running or does not support chat"},
    },
)
async def chat_with_workload_endpoint(
    request: Request,
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    workload_id: UUID = Path(description="The UUID of the workload to chat with"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    return await chat_with_workload(
        session=session,
        namespace=namespace,
        workload_id=workload_id,
        request=request,
    )


@router.get(
    "/namespaces/{namespace}/workloads/{workload_id}",
    response_model=WorkloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workload details",
    description="Retrieve detailed information about a specific workload in a namespace.",
)
async def get_workload(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    workload_id: UUID = Path(description="The UUID of the workload to get"),
    session: AsyncSession = Depends(get_session),
) -> WorkloadResponse:
    workload = await get_workload_by_id(session=session, namespace=namespace, workload_id=workload_id)
    if not workload:
        raise NotFoundException(f"Workload {workload_id} not found")

    return WorkloadResponse.model_validate(workload)


@router.delete(
    "/namespaces/{namespace}/workloads/{workload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workload",
    description=dedent("""
        Delete a workload and all its Kubernetes components. This will remove all resources
        (Deployments, Services, ConfigMaps, Jobs, Pods, etc.) associated with the workload
        using the workload-id label selector. Adapted from AIRM dispatcher pattern.
    """),
)
async def delete_workload(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    workload_id: UUID = Path(description="The UUID of the workload to delete"),
    session: AsyncSession = Depends(get_session),
) -> None:
    workload = await get_workload_by_id(session=session, workload_id=workload_id, namespace=namespace)
    if not workload:
        raise NotFoundException(f"Workload {workload_id} not found")

    # Delete all workload components from Kubernetes and update status in DB
    await delete_workload_components(namespace, workload_id, session)


@router.get(
    "/namespaces/{namespace}/workloads/{workload_id}/metrics/{metric}",
    response_model=MetricsTimeseries | MetricsScalar | MetricsScalarWithRange,
    status_code=status.HTTP_200_OK,
    summary="Get workload metric",
    description="Retrieve a metric for a workload by querying Prometheus with workload_id.",
)
async def get_workload_metric(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    time_range: MetricsTimeRange = Depends(),
    workload_id: UUID = Path(description="The UUID of the workload"),
    metric: MetricName = Path(description="Metric name to retrieve"),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> MetricsTimeseries | MetricsScalar | MetricsScalarWithRange:
    workload = await get_workload_by_id(session=session, workload_id=workload_id, namespace=namespace)
    if not workload:
        raise NotFoundException(f"Workload {workload_id} not found")

    return await get_metric_by_workload_id(
        workload_id=str(workload_id),
        metric=metric,
        start=time_range.start,
        end=time_range.end,
        prometheus_client=prometheus_client,
    )


@router.get(
    "/namespaces/{namespace}/workloads/{workload_id}/logs",
    response_model=WorkloadLogsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workload logs",
    description="Retrieve logs for a specific workload from Loki, with pagination and filtering support.",
)
async def get_workload_logs_endpoint(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    workload_id: UUID = Path(description="The UUID of the workload"),
    session: AsyncSession = Depends(get_session),
    params: LogsQueryRequest = Depends(),
    loki_client: object = Depends(get_loki_client),
) -> WorkloadLogsResponse:
    """Get logs for a workload with optional filtering and pagination."""
    workload = await get_workload_by_id(session=session, workload_id=workload_id, namespace=namespace)
    if not workload:
        raise NotFoundException(f"Workload {workload_id} not found")

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
    "/namespaces/{namespace}/workloads/{workload_id}/logs/stream",
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
        200: {
            "description": "SSE stream established successfully",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"timestamp": "2025-01-01T10:00:00Z", "level": "INFO", "message": "Application started"}\n\n'
                }
            },
        },
        404: {"description": "Workload not found or access denied"},
        422: {"description": "Invalid parameters (e.g., delay out of range)"},
    },
)
async def workload_logs_stream(
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    workload_id: UUID = Path(description="The ID of the workload"),
    start_time: datetime | None = Query(default=None, description="Start time for streaming (ISO format)"),
    level: LogLevel | None = Query(default=None, description="Filter logs at this level and above"),
    log_type: LogType = Query(default=LogType.WORKLOAD, description="Type of logs: 'workload' or 'event'"),
    delay: int = Query(default=1, ge=1, le=30, description="Delay between polls (1-30 seconds)"),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Stream workload logs in real-time via SSE."""
    workload = await get_workload_by_id(session=session, workload_id=workload_id, namespace=namespace)
    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found")

    return StreamingResponse(
        stream_workload_logs_sse(
            workload_id=str(workload_id),
            start_time=start_time,
            level_filter=level,
            log_type=log_type,
            delay_seconds=delay,
        ),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
