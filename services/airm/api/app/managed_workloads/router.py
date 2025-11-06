# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.responses import StreamingResponse
from loguru import logger
from prometheus_api_client import PrometheusConnect
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..metrics.schemas import MetricsScalar, MetricsScalarWithRange, MetricsTimeseries
from ..metrics.service import (
    get_end_to_end_latency_metrics,
    get_inter_token_latency_metrics,
    get_kv_cache_usage_metric,
    get_prometheus_client,
    get_time_to_first_token_metrics,
    get_total_tokens_metric,
    get_workload_request_metrics,
)
from ..metrics.utils import validate_datetime_range
from ..projects.models import Project
from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException, ValidationException
from ..utilities.security import get_projects_accessible_to_user, validate_and_get_project_from_query
from ..workloads.enums import WorkloadType
from .enums import WorkloadStatus
from .repository import select_workload
from .schemas import AIMWorkloadResponse, ChartWorkloadResponse
from .service import (
    get_workload,
    list_workloads,
    stream_downstream,
)
from .utils import enrich_with_resource_utilization

router = APIRouter(tags=["Managed Workloads"])


@router.get(
    "/managed-workloads",
    response_model=list[ChartWorkloadResponse | AIMWorkloadResponse],
    status_code=status.HTTP_200_OK,
    summary="List managed workloads",
    description="""
        List active managed workloads with status updates from cluster dispatcher.
        Requires project membership. Supports filtering by type and status.
        Can be enriched with allocated resources.
        Essential for monitoring running inference and training workloads.
    """,
)
async def get_workloads(
    type: list[WorkloadType] | None = Query(None, description="Filter by workload type(s)"),
    status: list[WorkloadStatus] | None = Query(None, description="Filter by workload status(es)"),
    with_resources: bool = Query(False, description="Whether to include allocated resources in the response"),
    project=Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> list[ChartWorkloadResponse | AIMWorkloadResponse]:
    result_workloads = await list_workloads(
        session=session,
        project_id=project.id,
        type=type,
        status=status,
    )

    try:
        if with_resources:
            return await enrich_with_resource_utilization(project.id, result_workloads, prometheus_client)
    except Exception as e:
        logger.exception("Error enriching workloads with resource utilization")

    return result_workloads


@router.get(
    "/managed-workloads/{workload_id}",
    response_model=ChartWorkloadResponse | AIMWorkloadResponse,
    summary="Get workload details",
    description="""
        Retrieve detailed information about a specific managed workload with
        real-time status from cluster dispatcher. Requires project membership
        and workload access. Used for workload monitoring and troubleshooting.
    """,
)
async def get_workload_endpoint(
    workload_id: UUID = Path(description="The ID of the job to get the status of"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    with_resources: bool = Query(False, description="Whether to include allocated resources in the response"),
    session: AsyncSession = Depends(get_session),
    prometheus_client: PrometheusConnect = Depends(get_prometheus_client),
) -> ChartWorkloadResponse | AIMWorkloadResponse:
    workload = await get_workload(
        session=session,
        workload_id=workload_id,
        accessible_projects=accessible_projects,
    )
    try:
        if with_resources:
            return (await enrich_with_resource_utilization(workload.project.id, [workload], prometheus_client))[0]
    except Exception as e:
        logger.exception(f"Error enriching workload {workload_id} with resource utilization")
    return workload


@router.post(
    "/chat/{workload_id}",
    summary="Chat with deployed AI model",
    description="""
        Send chat messages to deployed AI model for interactive conversations.
        Requires project membership and running model workload. Streams responses
        for real-time chat experience with deployed language models.
    """,
    response_class=StreamingResponse,
    include_in_schema=False,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {"messages": [{"content": "Hello", "role": "user"}], "stream": False, "temperature": 0.5}
                }
            }
        }
    },
)
async def chat_with_model(
    request: Request,
    workload_id: UUID = Path(description="The ID of the deployed model workload to chat with"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    session: AsyncSession = Depends(get_session),
):
    # Get workload with latest status
    workload = await select_workload(session, workload_id, accessible_projects)
    if workload is None:
        raise NotFoundException(f"Workload {workload_id} not found")

    # Check if workload is ready
    if workload.status != WorkloadStatus.RUNNING:
        raise ValidationException(f"Workload {workload_id} is not running (status: {workload.status})")

    # Check if workload has a host
    if not workload.output or workload.output.get("internal_host") is None:
        raise ValidationException(f"Workload {workload_id} does not have a host")

    # Get the endpoint URL
    host = workload.output["internal_host"]
    if not host.startswith(("http://", "https://")):
        base_url = f"http://{host}"
    else:
        base_url = host

    # Stream the response from the model endpoint
    try:
        # Pass through the raw request body without validation
        return await stream_downstream(base_url=base_url, url_path="/v1/chat/completions", request=request)
    except Exception as e:
        logger.error(f"Error streaming from endpoint {base_url}: {e}")
        raise ValidationException(f"Error connecting to model endpoint: {str(e)}")


@router.get(
    "/managed-workloads/{workload_id}/metrics/requests",
    response_model=MetricsTimeseries,
    summary="Get metrics for requests to AIM deployments",
    description="""
        Retrieve metrics about requests made to AIM deployments, including
        running requests and waiting requests.
    """,
)
async def get_aim_workload_request_metrics(
    workload_id: UUID = Path(description="The ID of the workload to get the status of"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsTimeseries:
    workload = await get_workload(
        session=session,
        workload_id=workload_id,
        accessible_projects=accessible_projects,
        require_aim=True,
    )

    validate_datetime_range(start, end)

    return await get_workload_request_metrics(
        start=start, end=end, workload_id=workload.id, prometheus_client=prometheus_client
    )


@router.get(
    "/managed-workloads/{workload_id}/metrics/time_to_first_token",
    response_model=MetricsTimeseries,
    summary="Get metrics for time to first token for AIM deployments",
    description="Retrieve timeseries details about the time to first token for an AIM deployment.",
)
async def get_aim_time_to_first_token_metrics(
    workload_id: UUID = Path(description="The ID of the workload to get the status of"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsTimeseries:
    workload = await get_workload(
        session=session,
        workload_id=workload_id,
        accessible_projects=accessible_projects,
        require_aim=True,
    )

    validate_datetime_range(start, end)

    return await get_time_to_first_token_metrics(
        start=start, end=end, workload_id=workload.id, prometheus_client=prometheus_client
    )


@router.get(
    "/managed-workloads/{workload_id}/metrics/inter_token_latency",
    response_model=MetricsTimeseries,
    summary="Get metrics for inter token latency for AIM deployments",
    description="Retrieve timeseries details about the inter token latency for an AIM deployment.",
)
async def get_aim_inter_token_latency_metrics(
    workload_id: UUID = Path(description="The ID of the workload to get the status of"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsTimeseries:
    workload = await get_workload(
        session=session,
        workload_id=workload_id,
        accessible_projects=accessible_projects,
        require_aim=True,
    )

    validate_datetime_range(start, end)

    return await get_inter_token_latency_metrics(
        start=start, end=end, workload_id=workload.id, prometheus_client=prometheus_client
    )


@router.get(
    "/managed-workloads/{workload_id}/metrics/end_to_end_latency",
    response_model=MetricsTimeseries,
    summary="Get metrics for end to end latency for AIM deployments",
    description="Retrieve timeseries details about the end to end latency for an AIM deployment.",
)
async def get_aim_end_to_end_latency_metrics(
    workload_id: UUID = Path(description="The ID of the workload to get the status of"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsTimeseries:
    workload = await get_workload(
        session=session,
        workload_id=workload_id,
        accessible_projects=accessible_projects,
        require_aim=True,
    )

    validate_datetime_range(start, end)

    return await get_end_to_end_latency_metrics(
        start=start, end=end, workload_id=workload.id, prometheus_client=prometheus_client
    )


@router.get(
    "/managed-workloads/{workload_id}/metrics/kv_cache_usage",
    response_model=MetricsScalarWithRange,
    summary="Get the metric for avg KV Cache usage in the provided timeframe",
    description="Retrieve the average KV Cache for an AIM deployment, in the requested timeframe.",
)
async def get_aim_kv_cache_usage_metric(
    workload_id: UUID = Path(description="The ID of the workload to get the status of"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    start: AwareDatetime = Query(..., description="The start timestamp for the timeseries"),
    end: AwareDatetime = Query(..., description="The end timestamp for the timeseries"),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsScalarWithRange:
    workload = await get_workload(
        session=session,
        workload_id=workload_id,
        accessible_projects=accessible_projects,
        require_aim=True,
    )

    validate_datetime_range(start, end)

    return await get_kv_cache_usage_metric(
        start=start, end=end, workload_id=workload.id, prometheus_client=prometheus_client
    )


@router.get(
    "/managed-workloads/{workload_id}/metrics/total_tokens",
    response_model=MetricsScalar,
    summary="Get the total tokens produced for an AIM deployment",
    description="Retrieve the total tokens produced for an AIM deployment. This metric resets to 0 upon restart of the pod.",
)
async def get_aim_total_tokens_metric(
    workload_id: UUID = Path(description="The ID of the workload to get the status of"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    session=Depends(get_session),
    prometheus_client=Depends(get_prometheus_client),
) -> MetricsScalar:
    workload = await get_workload(
        session=session,
        workload_id=workload_id,
        accessible_projects=accessible_projects,
        require_aim=True,
    )

    return await get_total_tokens_metric(workload_id=workload.id, prometheus_client=prometheus_client)
