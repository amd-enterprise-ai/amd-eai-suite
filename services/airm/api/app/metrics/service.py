# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
from collections import defaultdict
from datetime import datetime
from uuid import UUID

from fastapi import Request
from loguru import logger
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus

from ..organizations.models import Organization
from ..projects.models import Project
from ..projects.models import Project as ProjectModel
from ..projects.repository import get_projects_in_organization
from ..projects.schemas import ProjectResponse
from ..quotas.repository import get_quotas_for_organization
from ..utilities.collections.schemas import FilterCondition, PaginationConditions, SortCondition
from ..utilities.prometheus_instrumentation import ALLOCATED_GPU_VRAM_METRIC_LABEL, ALLOCATED_GPUS_METRIC_LABEL
from ..workloads.repository import (
    get_average_pending_time_for_workloads_in_project_created_between,
    get_workload_counts_with_status_by_project_id,
    get_workloads_with_running_time_in_project,
)
from .config import PROMETHEUS_URL
from .constants import (
    ALLOCATED_GPU_VRAM_SERIES_LABEL,
    ALLOCATED_GPUS_SERIES_LABEL,
    PROMETHEUS_INF_STRING,
    PROMETHEUS_MINUS_INF_STRING,
    PROMETHEUS_NAN_STRING,
    UTILIZED_GPU_VRAM_SERIES_LABEL,
    UTILIZED_GPUS_SERIES_LABEL,
    VLLM_END_TO_END_LATENCY_LABEL,
    VLLM_INTER_TOKEN_LATENCY_LABEL,
    VLLM_RUNNING_REQUESTS_LABEL,
    VLLM_TIME_TO_FIRST_TOKEN_LABEL,
    VLLM_WAITING_REQUESTS_LABEL,
    WORKLOAD_ID_METRIC_LABEL,
)
from .constants import CLUSTER_NAME_METRIC_LABEL as CLUSTER_NAME
from .constants import ORGANIZATION_NAME_METRIC_LABEL as ORGANIZATION_NAME
from .constants import PROJECT_ID_METRIC_LABEL as PROJECT_ID
from .constants import WORKLOAD_ID_METRIC_LABEL as WORKLOAD_ID
from .schemas import (
    CurrentUtilization,
    DateRange,
    MetricsScalar,
    MetricsScalarWithRange,
    MetricsTimeseries,
    UtilizationByProject,
    WorkloadsWithMetrics,
    WorkloadWithMetrics,
)
from .utils import (
    a_custom_query,
    a_custom_query_range,
    construct_timeseries_query_with_fallback_for_default_series,
    convert_prometheus_string_to_float,
    get_aggregation_lookback_for_metrics,
    get_step_for_range_query,
    map_metrics_timeseries,
    map_timeseries_split_by_project,
)


def init_prometheus_client() -> PrometheusConnect:
    """Initialize Prometheus client. This will be called at application startup."""
    if not PROMETHEUS_URL:
        raise ValueError("PROMETHEUS_URL environment variable must be set")
    client = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    logger.info("Connected to Prometheus server at {}", PROMETHEUS_URL)
    return client


def get_prometheus_client(request: Request) -> PrometheusConnect:
    """FastAPI dependency to get the initialized PrometheusConnect client from app.state."""
    if not hasattr(request.app.state, "prometheus_client") or request.app.state.prometheus_client is None:
        logger.error("Prometheus client not initialized in app.state.")
        raise RuntimeError("Prometheus client not available.")
    return request.app.state.prometheus_client


async def get_gpu_memory_utilization_timeseries(
    session: AsyncSession,
    start: datetime,
    end: datetime,
    organization: Organization,
    prometheus_client: PrometheusConnect,
) -> MetricsTimeseries:
    """
    Returns a timeseries of GPU memory utilization for the given organization, grouped by Project.

    This corresponds to (GPU Used VRAM (grouped by project) / GPU Total VRAM) or (0 / GPU Total VRAM).
    The second part of the query ensures that if there is data available for GPU Total VRAM, we receive 0 utilization
    but if it doesn't have values, we receive NaN. This is to account for cases where there was a network error and we
    don't have values to display.
    """
    projects = await get_projects_in_organization(session, organization.id)

    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)

    numerator = f"""
sum by({PROJECT_ID}) (
    avg_over_time(
        gpu_used_vram{{{ORGANIZATION_NAME}="{organization.name}"}}[{lookback}]
    )
) * 100
"""
    denominator = f"""
scalar(
    sum(
        max by (gpu_uuid, hostname) (
            gpu_total_vram{{{ORGANIZATION_NAME}="{organization.name}"}}
        )
    )
)
"""

    query = construct_timeseries_query_with_fallback_for_default_series(numerator, denominator)

    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(step)
    )
    return map_timeseries_split_by_project(
        results=results, projects=projects, start=start, end=end, step=step, series_label=UTILIZED_GPU_VRAM_SERIES_LABEL
    )


async def get_gpu_device_utilization_timeseries(
    session: AsyncSession,
    start: datetime,
    end: datetime,
    organization: Organization,
    prometheus_client: PrometheusConnect,
) -> MetricsTimeseries:
    """
    Returns a timeseries of GPU device utilization for the given organization, grouped by Project.

    This corresponds to (Number of GPUs used (grouped by project) / Total number of GPUs) or (0 / Total number of GPUs).
    The second part of the query ensures that if there is data available for Total number of GPUs, we receive 0 utilization
    but if it doesn't have values, we receive NaN. This is to account for cases where there was a network error and we
    don't have values to display.
    """
    projects = await get_projects_in_organization(session, organization.id)

    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)

    numerator = f"""
avg_over_time(
    count by ({PROJECT_ID}) (
        gpu_gfx_activity{{{ORGANIZATION_NAME}="{organization.name}"}}
    )
    [{lookback}:]
) * 100
"""
    denominator = f"""
scalar(
    count(
        count by (gpu_uuid, hostname) (
            gpu_total_vram{{{ORGANIZATION_NAME}="{organization.name}"}}
        )
    )
)
"""

    query = construct_timeseries_query_with_fallback_for_default_series(numerator, denominator)
    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(step)
    )
    return map_timeseries_split_by_project(
        results=results, projects=projects, start=start, end=end, step=step, series_label=UTILIZED_GPUS_SERIES_LABEL
    )


async def get_gpu_device_utilization_timeseries_for_cluster(
    session: AsyncSession,
    start: datetime,
    end: datetime,
    cluster_name: str,
    organization_id: UUID,
    prometheus_client: PrometheusConnect,
) -> MetricsTimeseries:
    """
    Returns a timeseries of GPU device utilization for the given cluster, grouped by Project.

    This corresponds to (Number of GPUs used (grouped by project) / Total number of GPUs) or (0 / Total number of GPUs).
    The second part of the query ensures that if there is data available for Total number of GPUs, we receive 0 utilization
    but if it doesn't have values, we receive NaN. This is to account for cases where there was a network error and we
    don't have values to display.
    """
    projects = await get_projects_in_organization(session, organization_id)
    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)
    numerator = f"""
avg_over_time(
    count by ({PROJECT_ID}) (
        gpu_gfx_activity{{{CLUSTER_NAME}="{cluster_name}"}}
    )
    [{lookback}:]
) * 100
"""
    denominator = f"""
scalar(
    count(
        count by (gpu_uuid, hostname) (
            gpu_total_vram{{{CLUSTER_NAME}="{cluster_name}"}}
        )
    )
)
"""

    query = construct_timeseries_query_with_fallback_for_default_series(numerator, denominator)
    results = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(step)
    )
    return map_timeseries_split_by_project(
        results=results, projects=projects, start=start, end=end, step=step, series_label=UTILIZED_GPUS_SERIES_LABEL
    )


async def get_current_utilization(
    session: AsyncSession, organization: Organization, prometheus_client: PrometheusConnect
) -> CurrentUtilization:
    """
    Returns a snapshot of GPU device utilization for the given cluster, grouped by Project, along with some workload stats.
    """
    workload_counts_by_project, quotas, projects = await asyncio.gather(
        get_workload_counts_with_status_by_project_id(
            session, organization.id, [WorkloadStatus.RUNNING, WorkloadStatus.PENDING]
        ),
        get_quotas_for_organization(session, organization.id),
        get_projects_in_organization(session, organization.id),
    )

    allocated_gpu_counts_by_project: dict[UUID, int] = defaultdict(int)
    for quota in quotas:
        allocated_gpu_counts_by_project[quota.project_id] += quota.gpu_count

    utilization_by_project_id = await __get_utilized_gpu_count_by_project(
        organization_name=organization.name,
        prometheus_client=prometheus_client,
    )
    total_running_workloads_count = sum(
        count for (_, status), count in workload_counts_by_project.items() if status == WorkloadStatus.RUNNING
    )
    total_pending_workloads_count = sum(
        count for (_, status), count in workload_counts_by_project.items() if status == WorkloadStatus.PENDING
    )

    return CurrentUtilization(
        total_utilized_gpus_count=sum([utilization_by_project_id.get(str(project.id), 0) for project in projects]),
        total_running_workloads_count=total_running_workloads_count,
        total_pending_workloads_count=total_pending_workloads_count,
        utilization_by_project=[
            UtilizationByProject(
                project=ProjectResponse.model_validate(project),
                allocated_gpus_count=allocated_gpu_counts_by_project.get(project.id, 0),
                utilized_gpus_count=utilization_by_project_id.get(str(project.id), 0),
                running_workloads_count=workload_counts_by_project.get((project.id, WorkloadStatus.RUNNING), 0),
                pending_workloads_count=workload_counts_by_project.get((project.id, WorkloadStatus.PENDING), 0),
            )
            for project in projects
        ],
    )


async def __get_utilized_gpu_count_by_project(
    organization_name: str, prometheus_client: PrometheusConnect
) -> dict[str, int]:
    lookback = get_aggregation_lookback_for_metrics()
    results = await a_custom_query(
        client=prometheus_client,
        query=f"""
count by ({PROJECT_ID}) (
  max_over_time(gpu_gfx_activity{{{ORGANIZATION_NAME}="{organization_name}"}}[{lookback}])
)
""",
    )
    project_gpu_counts: dict[str, int] = {}
    for result in results:
        project_id = result["metric"].get(PROJECT_ID, None)
        value = int(result["value"][1])
        project_gpu_counts[project_id] = value
    return project_gpu_counts


async def get_gpu_device_utilization_timeseries_for_project(
    start: datetime, end: datetime, project: ProjectModel, prometheus_client: PrometheusConnect
) -> MetricsTimeseries:
    """
    Returns two timeseries of GPU device utilization for the given project:
    Count of utilized GPUs vs count of allocated GPUs.

    For count of utilized GPUs, the data is "or-ed" with a fallback to 0 * a guaranteed-available metric,
    (max(gpu_total_vram)), that is always expected to exist - Absence of this metric implies error collecting data,
    and will result in null value for that datapoint. This is needed because gpu_gfx_activity{project_id="..."}
    only exists when the GPU is being utilized by a workload of the project, else it returns a null.

    gpu_total_vram was chosen instead of allocated_gpus since the source of gpu_total_vram (GPU metrics exporter)
    is the same as that of gpu_gfx_activity
    """
    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)
    utilized_gpus = f"""
avg_over_time(
    count(
        gpu_gfx_activity{{{PROJECT_ID}="{project.id}"}}
    )
    [{lookback}:]
)
OR (0 * max(gpu_total_vram{{{CLUSTER_NAME}="{project.cluster.name}"}}))
"""
    allocated_gpus = f"""
avg_over_time(
    max(
        {ALLOCATED_GPUS_METRIC_LABEL}{{{PROJECT_ID}="{project.id}"}}
    )
    [{lookback}:]
)
"""
    utilized_gpus_res, allocated_gpus_res = await asyncio.gather(
        a_custom_query_range(
            client=prometheus_client, query=utilized_gpus, start_time=start, end_time=end, step=str(step)
        ),
        a_custom_query_range(
            client=prometheus_client, query=allocated_gpus, start_time=start, end_time=end, step=str(step)
        ),
    )
    utilized_gpus_timeseries = map_metrics_timeseries(
        results=utilized_gpus_res,
        project=project,
        start=start,
        end=end,
        step=step,
        series_label=UTILIZED_GPUS_SERIES_LABEL,
    )
    allocated_gpus_timeseries = map_metrics_timeseries(
        results=allocated_gpus_res,
        project=project,
        start=start,
        end=end,
        step=step,
        series_label=ALLOCATED_GPUS_SERIES_LABEL,
    )

    return MetricsTimeseries(
        data=utilized_gpus_timeseries.data + allocated_gpus_timeseries.data, range=utilized_gpus_timeseries.range
    )


async def get_gpu_memory_utilization_timeseries_for_project(
    start: datetime, end: datetime, project: ProjectModel, prometheus_client: PrometheusConnect
) -> MetricsTimeseries:
    """
    Returns two timeseries of GPU device utilization for the given project:
    Utilized GPU VRAM vs (count of allocated GPUs * VRAM per GPU)

    For utilized GPU VRAM, the data is "or-ed" with a fallback to 0 * a guaranteed-available metric,
    (max(gpu_total_vram)), that is always expected to exist. Absence of this metric implies error collecting data,
    and will result in null value for that datapoint. This is needed because gpu_used_vram{project_id="..."}
    only exists when the GPU is being utilized by a workload of the project, else it returns a null.

    gpu_total_vram was chosen instead of allocated_gpus since the source of gpu_total_vram (GPU metrics exporter)
    is the same as that of gpu_used_vram

    """
    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)
    utilized_vram = f"""
avg_over_time(
    sum(
        gpu_used_vram{{{PROJECT_ID}="{project.id}"}}
    )
    [{lookback}:]
)
OR (0 * max(gpu_total_vram{{{CLUSTER_NAME}="{project.cluster.name}"}}))
"""
    allocated_vram = f"""
avg_over_time(
    max(
        {ALLOCATED_GPU_VRAM_METRIC_LABEL}{{{PROJECT_ID}="{project.id}"}}
    )
    [{lookback}:]
)
"""
    utilized_vram_res, allocated_vram_res = await asyncio.gather(
        a_custom_query_range(
            client=prometheus_client, query=utilized_vram, start_time=start, end_time=end, step=str(step)
        ),
        a_custom_query_range(
            client=prometheus_client, query=allocated_vram, start_time=start, end_time=end, step=str(step)
        ),
    )
    utilized_vram_timeseries = map_metrics_timeseries(
        results=utilized_vram_res,
        project=project,
        start=start,
        end=end,
        step=step,
        series_label=UTILIZED_GPU_VRAM_SERIES_LABEL,
    )
    allocated_vram_timeseries = map_metrics_timeseries(
        results=allocated_vram_res,
        project=project,
        start=start,
        end=end,
        step=step,
        series_label=ALLOCATED_GPU_VRAM_SERIES_LABEL,
    )

    return MetricsTimeseries(
        data=utilized_vram_timeseries.data + allocated_vram_timeseries.data, range=utilized_vram_timeseries.range
    )


async def get_gpu_device_utilization_for_project_by_workload_id(
    project_id: UUID, prometheus_client: PrometheusConnect
) -> dict[str, int]:
    """
    Returns a snapshot of the count of utilized GPUs for each workload in the given project.
    """
    lookback = get_aggregation_lookback_for_metrics()
    results = await a_custom_query(
        client=prometheus_client,
        query=f"""
count by ({WORKLOAD_ID}) (
  max_over_time(gpu_gfx_activity{{{PROJECT_ID}="{project_id}"}}[{lookback}:])
)
""",
    )
    workload_gpu_counts: dict[str, int] = {}
    for result in results:
        workload_id = result["metric"].get(WORKLOAD_ID, None)
        value = int(result["value"][1])
        workload_gpu_counts[workload_id] = value
    return workload_gpu_counts


async def get_gpu_memory_utilization_for_project_by_workload_id(
    project_id: UUID, prometheus_client: PrometheusConnect
) -> dict[str, float]:
    """
    Returns a snapshot of the average utilized VRAM for each workload in the given project.
    """
    lookback = get_aggregation_lookback_for_metrics()
    results = await a_custom_query(
        client=prometheus_client,
        query=f"""
sum by ({WORKLOAD_ID}) (
  avg_over_time(gpu_used_vram{{{PROJECT_ID}="{project_id}"}}[{lookback}:])
)
""",
    )
    workload_vram_usage: dict[str, float] = {}
    for result in results:
        workload_id = result["metric"].get(WORKLOAD_ID, None)
        value = convert_prometheus_string_to_float(result["value"][1])
        workload_vram_usage[workload_id] = value
    return workload_vram_usage


async def get_workloads_metrics_by_project(
    session: AsyncSession,
    project: Project,
    prometheus_client: PrometheusConnect,
    pagination_params: PaginationConditions,
    sort_params: list[SortCondition],
    filter_params: list[FilterCondition],
) -> WorkloadsWithMetrics:
    """
    Returns a snapshot of workloads with their corresponding metrics for the given project.

    This includes the:
    - GPUs currently allocated to the workload
    - VRAM currently utilized by the workload
    - Aggregated run time of the workload in seconds (Elapsed run time + (now - last status change if current status = RUNNING)
    """
    [workloads_with_running_time, count], workload_gpu_counts, workload_vram_usage = await asyncio.gather(
        get_workloads_with_running_time_in_project(session, project.id, pagination_params, sort_params, filter_params),
        get_gpu_device_utilization_for_project_by_workload_id(project.id, prometheus_client),
        get_gpu_memory_utilization_for_project_by_workload_id(project.id, prometheus_client),
    )
    workload_metrics = []
    for workload, running_time in workloads_with_running_time:
        workload_dict = {
            **workload.__dict__,
            "gpu_count": workload_gpu_counts.get(str(workload.id), 0),
            "vram": workload_vram_usage.get(str(workload.id), 0),
            "run_time": int(running_time),
        }
        workload_metrics.append(WorkloadWithMetrics.model_validate(workload_dict))

    return WorkloadsWithMetrics(
        workloads=workload_metrics, total=count, page=pagination_params.page, page_size=pagination_params.page_size
    )


async def get_average_wait_time_for_project(
    session: AsyncSession, start: datetime, end: datetime, project: ProjectModel
) -> MetricsScalarWithRange:
    """
    Returns the average wait time for workloads in the given project that were created between the start and end dates.
    Average wait time corresponds to avg(Elapsed pending time + (now - last status change if current status = PENDING))

    """
    average_wait_time = await get_average_pending_time_for_workloads_in_project_created_between(
        session, project.id, start, end
    )

    return MetricsScalarWithRange(
        data=average_wait_time or 0,
        range=DateRange(start=start, end=end),
    )


async def get_avg_gpu_idle_time_for_project(
    start: datetime, end: datetime, project: ProjectModel, prometheus_client: PrometheusConnect
) -> MetricsScalarWithRange:
    """
    Returns the average GPU idle time for the given project within the specified date range.

    The idle time is calculated as:
    sum((Average allocated GPUs - Average utilized GPUs) * step / Average allocated GPU)

    For each datapoint, it computes the average allocated GPUs and average utilized GPUs over a lookback period,
    This is then multiplied by the step size to get the idle time in seconds, for that time range.
    These are then summed up, to get the total idle time for the range.
    """
    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)

    idle_time_query = f"""
(
    avg_over_time(
        avg(
            {ALLOCATED_GPUS_METRIC_LABEL}{{{PROJECT_ID}="{project.id}"}}
        )
        [{lookback}:]
    ) -
    on() avg_over_time(
        count(
            gpu_gfx_activity{{{PROJECT_ID}="{project.id}"}}
        )
        [{lookback}:]
    )
) * {step}
/
on() avg_over_time(
        avg(
            {ALLOCATED_GPUS_METRIC_LABEL}{{{PROJECT_ID}="{project.id}"}}
        )
        [{lookback}:]
)
"""
    results = await a_custom_query_range(
        client=prometheus_client, query=idle_time_query, start_time=start, end_time=end, step=str(step)
    )

    idle_time = (
        sum(
            [
                float(v[1])
                for v in results[0]["values"]
                if v[1] and v[1] not in [PROMETHEUS_NAN_STRING, PROMETHEUS_INF_STRING, PROMETHEUS_MINUS_INF_STRING]
            ]
            if results
            else []
        )
        or 0
    )

    return MetricsScalarWithRange(
        data=max(idle_time, 0),
        range=DateRange(start=start, end=end),
    )


async def get_workload_request_metrics(
    start: datetime, end: datetime, workload_id: UUID, prometheus_client: PrometheusConnect
) -> MetricsTimeseries:
    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)
    running_requests_query = (
        f'max_over_time(vllm:num_requests_running{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"}}[{lookback}])'
    )
    waiting_requests_query = (
        f'max_over_time(vllm:num_requests_waiting{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"}}[{lookback}])'
    )

    running_requests_res, waiting_requests_res = await asyncio.gather(
        a_custom_query_range(
            client=prometheus_client, query=running_requests_query, start_time=start, end_time=end, step=str(step)
        ),
        a_custom_query_range(
            client=prometheus_client, query=waiting_requests_query, start_time=start, end_time=end, step=str(step)
        ),
    )

    running_requests = map_metrics_timeseries(running_requests_res, None, start, end, step, VLLM_RUNNING_REQUESTS_LABEL)
    waiting_requests = map_metrics_timeseries(waiting_requests_res, None, start, end, step, VLLM_WAITING_REQUESTS_LABEL)

    return MetricsTimeseries(data=running_requests.data + waiting_requests.data, range=running_requests.range)


async def get_time_to_first_token_metrics(
    start: datetime, end: datetime, workload_id: UUID, prometheus_client: PrometheusConnect
) -> MetricsTimeseries:
    return await __get_vllm_timeseries_for_rate_metric(
        start, end, workload_id, "time_to_first_token_seconds", prometheus_client, VLLM_TIME_TO_FIRST_TOKEN_LABEL
    )


async def get_inter_token_latency_metrics(
    start: datetime, end: datetime, workload_id: UUID, prometheus_client: PrometheusConnect
) -> MetricsTimeseries:
    return await __get_vllm_timeseries_for_rate_metric(
        start, end, workload_id, "time_per_output_token_seconds", prometheus_client, VLLM_INTER_TOKEN_LATENCY_LABEL
    )


async def get_end_to_end_latency_metrics(
    start: datetime, end: datetime, workload_id: UUID, prometheus_client: PrometheusConnect
) -> MetricsTimeseries:
    return await __get_vllm_timeseries_for_rate_metric(
        start, end, workload_id, "e2e_request_latency_seconds", prometheus_client, VLLM_END_TO_END_LATENCY_LABEL
    )


async def __get_vllm_timeseries_for_rate_metric(
    start: datetime,
    end: datetime,
    workload_id: UUID,
    metric_name: str,
    prometheus_client: PrometheusConnect,
    response_label: str,
) -> MetricsTimeseries:
    step = get_step_for_range_query(start, end)
    lookback = get_aggregation_lookback_for_metrics(step)
    # Adapted from https://docs.vllm.ai/en/latest/examples/online_serving/prometheus_grafana.html#example-materials
    query = f"""rate(vllm:{metric_name}_sum{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"}}[{lookback}])
/
rate(vllm:{metric_name}_count{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"}}[{lookback}])"""
    response = await a_custom_query_range(
        client=prometheus_client, query=query, start_time=start, end_time=end, step=str(step)
    )
    return map_metrics_timeseries(response, None, start, end, step, response_label)


async def get_kv_cache_usage_metric(
    start: datetime, end: datetime, workload_id: UUID, prometheus_client: PrometheusConnect
) -> MetricsScalarWithRange:
    seconds = int((end - start).total_seconds())
    query = f'avg_over_time(vllm:kv_cache_usage_perc{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"}}[{seconds}s])'
    results = await a_custom_query(
        client=prometheus_client,
        query=query,
    )
    value = convert_prometheus_string_to_float(results[0]["value"][1]) if results else 0

    return MetricsScalarWithRange(
        data=max(value, 0),
        range=DateRange(start=start, end=end),
    )


async def get_total_tokens_metric(workload_id: UUID, prometheus_client: PrometheusConnect) -> MetricsScalar:
    results = await a_custom_query(
        client=prometheus_client,
        query=f'vllm:generation_tokens_total{{{WORKLOAD_ID_METRIC_LABEL}="{workload_id}"}}',
    )
    value = convert_prometheus_string_to_float(results[0]["value"][1]) if results else 0

    return MetricsScalar(
        data=max(value, 0),
    )
