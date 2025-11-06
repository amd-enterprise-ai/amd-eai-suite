# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus
from app.clusters.models import Cluster
from app.metrics.constants import (
    PROJECT_ID_METRIC_LABEL,
    VLLM_END_TO_END_LATENCY_LABEL,
    VLLM_INTER_TOKEN_LATENCY_LABEL,
    VLLM_TIME_TO_FIRST_TOKEN_LABEL,
)
from app.metrics.schemas import (
    Datapoint,
    DatapointMetadataBase,
    DatapointsWithMetadata,
    DateRange,
    MetricsScalarWithRange,
    MetricsTimeseries,
    ProjectDatapointMetadata,
    TimeseriesRange,
    WorkloadsWithMetrics,
)
from app.metrics.service import (
    __get_utilized_gpu_count_by_project,
    get_average_wait_time_for_project,
    get_avg_gpu_idle_time_for_project,
    get_current_utilization,
    get_end_to_end_latency_metrics,
    get_gpu_device_utilization_for_project_by_workload_id,
    get_gpu_device_utilization_timeseries,
    get_gpu_device_utilization_timeseries_for_cluster,
    get_gpu_device_utilization_timeseries_for_project,
    get_gpu_memory_utilization_for_project_by_workload_id,
    get_gpu_memory_utilization_timeseries,
    get_gpu_memory_utilization_timeseries_for_project,
    get_inter_token_latency_metrics,
    get_kv_cache_usage_metric,
    get_time_to_first_token_metrics,
    get_total_tokens_metric,
    get_workload_request_metrics,
    get_workloads_metrics_by_project,
)
from app.organizations.models import Organization
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.projects.schemas import ProjectResponse
from app.quotas.models import Quota
from app.utilities.collections.schemas import PaginationConditions
from app.workloads.models import Workload


@patch("app.metrics.service.get_step_for_range_query", return_value=300)
@patch("app.metrics.service.get_aggregation_lookback_for_metrics", return_value="5m")
@patch(
    "app.metrics.service.get_projects_in_organization",
    return_value=[
        Project(
            id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
            name="Group1",
            description="Test Group 1",
            status=ProjectStatus.READY,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        Project(
            id=UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"),
            name="Group2",
            description="Test Group 2",
            status=ProjectStatus.READY,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ],
)
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_timeseries_split_by_project", return_value=AsyncMock())
async def test_get_gpu_memory_utilization_timeseries(
    mock_map_timeseries, mock_query, mock_get_projects, mock_get_lookback, mock_get_step
):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    await get_gpu_memory_utilization_timeseries(
        session=AsyncMock(spec=AsyncSession),
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 2),
        organization=Organization(
            id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"), name="ORG1", keycloak_organization_id="123"
        ),
        prometheus_client=prometheus_client_mock,
    )

    assert mock_query.call_count == 1
    assert (
        mock_query.call_args[1]["query"]
        == """
(
sum by(project_id) (
    avg_over_time(
        gpu_used_vram{org_name="ORG1"}[5m]
    )
) * 100
 /
scalar(
    sum(
        max by (gpu_uuid, hostname) (
            gpu_total_vram{org_name="ORG1"}
        )
    )
)
)
or
(vector(0) /
scalar(
    sum(
        max by (gpu_uuid, hostname) (
            gpu_total_vram{org_name="ORG1"}
        )
    )
)
)
"""
    )


@patch("app.metrics.service.get_step_for_range_query", return_value=300)
@patch("app.metrics.service.get_aggregation_lookback_for_metrics", return_value="5m")
@patch(
    "app.metrics.service.get_projects_in_organization",
    return_value=[
        Project(
            id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
            name="Group1",
            description="Test Group 1",
            status=ProjectStatus.READY,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        Project(
            id=UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"),
            name="Group2",
            description="Test Group 2",
            status=ProjectStatus.READY,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ],
)
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_timeseries_split_by_project", return_value=AsyncMock())
async def test_get_gpu_device_utilization_timeseries(
    mock_map_timeseries, mock_query, mock_get_projects, mock_get_lookback, mock_get_step
):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    await get_gpu_device_utilization_timeseries(
        session=AsyncMock(spec=AsyncSession),
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 2),
        organization=Organization(
            id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"), name="ORG1", keycloak_organization_id="123"
        ),
        prometheus_client=prometheus_client_mock,
    )

    assert mock_query.call_count == 1
    assert (
        mock_query.call_args[1]["query"]
        == """
(
avg_over_time(
    count by (project_id) (
        gpu_gfx_activity{org_name="ORG1"}
    )
    [5m:]
) * 100
 /
scalar(
    count(
        count by (gpu_uuid, hostname) (
            gpu_total_vram{org_name="ORG1"}
        )
    )
)
)
or
(vector(0) /
scalar(
    count(
        count by (gpu_uuid, hostname) (
            gpu_total_vram{org_name="ORG1"}
        )
    )
)
)
"""
    )


@patch("app.metrics.service.get_step_for_range_query", return_value=300)
@patch("app.metrics.service.get_aggregation_lookback_for_metrics", return_value="5m")
@patch(
    "app.metrics.service.get_projects_in_organization",
    return_value=[
        Project(
            id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
            name="Group1",
            description="Test Group 1",
            status=ProjectStatus.READY,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        Project(
            id=UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"),
            name="Group2",
            description="Test Group 2",
            status=ProjectStatus.READY,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ],
)
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_timeseries_split_by_project", return_value=AsyncMock())
async def test_get_gpu_device_utilization_timeseries_for_cluster(
    mock_map_timeseries, mock_query, mock_get_projects, mock_get_lookback, mock_get_step
):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    await get_gpu_device_utilization_timeseries_for_cluster(
        session=AsyncMock(spec=AsyncSession),
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 2),
        cluster_name="CLUSTER1",
        organization_id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
        prometheus_client=prometheus_client_mock,
    )

    assert mock_query.call_count == 1
    assert (
        mock_query.call_args[1]["query"]
        == """
(
avg_over_time(
    count by (project_id) (
        gpu_gfx_activity{kube_cluster_name="CLUSTER1"}
    )
    [5m:]
) * 100
 /
scalar(
    count(
        count by (gpu_uuid, hostname) (
            gpu_total_vram{kube_cluster_name="CLUSTER1"}
        )
    )
)
)
or
(vector(0) /
scalar(
    count(
        count by (gpu_uuid, hostname) (
            gpu_total_vram{kube_cluster_name="CLUSTER1"}
        )
    )
)
)
"""
    )


@patch("app.metrics.service.get_aggregation_lookback_for_metrics", return_value="5m")
@patch(
    "app.metrics.service.get_workload_counts_with_status_by_project_id",
    return_value={
        (UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"), WorkloadStatus.RUNNING): 5,
        (UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"), WorkloadStatus.RUNNING): 3,
        (UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"), WorkloadStatus.PENDING): 1,
        (UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"), WorkloadStatus.PENDING): 0,
    },
)
@patch(
    "app.metrics.service.get_quotas_for_organization",
    return_value=[
        Quota(
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            gpu_count=8,
            cpu_milli_cores=1000,
            memory_bytes=1000,
            ephemeral_storage_bytes=1000,
            status="pending",
            project_id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
            project=Project(
                id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
                name="Test Project",
                description="Test Description",
                status=ProjectStatus.READY,
                cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                updated_at=datetime(2023, 1, 1, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
            ),
        ),
        Quota(
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            gpu_count=0,
            cpu_milli_cores=500,
            memory_bytes=1000,
            ephemeral_storage_bytes=1000,
            status="deleting",
            project_id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
            project=Project(
                id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
                name="Test Project",
                description="Test Description",
                status=ProjectStatus.READY,
                cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                updated_at=datetime(2023, 1, 1, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
            ),
        ),
        Quota(
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            gpu_count=1,
            cpu_milli_cores=500,
            memory_bytes=1000,
            ephemeral_storage_bytes=1000,
            status="deleting",
            project_id=UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"),
            project=Project(
                id=UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"),
                name="Test Project",
                description="Test Description",
                status=ProjectStatus.READY,
                cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                updated_at=datetime(2023, 1, 1, tzinfo=UTC),
                created_by="test@example.com",
                updated_by="test@example.com",
            ),
        ),
    ],
)
@patch(
    "app.metrics.service.get_projects_in_organization",
    return_value=[
        Project(
            id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"),
            name="group1",
            description="Test Group 1",
            status=ProjectStatus.READY,
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        Project(
            id=UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792"),
            name="group2",
            description="Test Group 2",
            status=ProjectStatus.READY,
            cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ],
)
@patch(
    "app.metrics.service.__get_utilized_gpu_count_by_project",
    return_value={"a24c9e53-5532-419e-8dec-cf8b29d63812": 5, "3d8e02e4-caf3-48ff-8342-63cb5db19792": 3, None: 2},
)
async def test_get_current_utilization(
    mock_get_utilized_gpu_count, mock_get_projects, mock_get_quotas, mock_get_workload_counts, mock_get_lookback
):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    utilization = await get_current_utilization(
        session=AsyncMock(spec=AsyncSession),
        organization=Organization(
            id=UUID("a24c9e53-5532-419e-8dec-cf8b29d63812"), name="ORG1", keycloak_organization_id="123"
        ),
        prometheus_client=prometheus_client_mock,
    )

    assert utilization.total_utilized_gpus_count == 8
    assert utilization.total_running_workloads_count == 8
    assert utilization.total_pending_workloads_count == 1
    assert len(utilization.utilization_by_project) == 2
    assert utilization.utilization_by_project[0].project.id == UUID("a24c9e53-5532-419e-8dec-cf8b29d63812")
    assert utilization.utilization_by_project[0].allocated_gpus_count == 8
    assert utilization.utilization_by_project[0].utilized_gpus_count == 5
    assert utilization.utilization_by_project[0].pending_workloads_count == 1
    assert utilization.utilization_by_project[0].running_workloads_count == 5

    assert utilization.utilization_by_project[1].project.id == UUID("3d8e02e4-caf3-48ff-8342-63cb5db19792")
    assert utilization.utilization_by_project[1].allocated_gpus_count == 1
    assert utilization.utilization_by_project[1].utilized_gpus_count == 3
    assert utilization.utilization_by_project[1].pending_workloads_count == 0
    assert utilization.utilization_by_project[1].running_workloads_count == 3


@patch("app.metrics.service.get_aggregation_lookback_for_metrics", return_value="1m")
@patch(
    "app.metrics.service.a_custom_query",
    return_value=[
        {
            "metric": {
                PROJECT_ID_METRIC_LABEL: "123",
            },
            "value": [1672531199, "1"],
        },
        {
            "metric": {
                PROJECT_ID_METRIC_LABEL: "345",
            },
            "value": [1672531199, "2"],
        },
        {"metric": {}, "value": [1672531199, "5"]},
    ],
)
async def test__get_utilized_gpu_count_by_project(mock_query, mock_get_lookback):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    org_name = "ORG1"
    results = await __get_utilized_gpu_count_by_project(org_name, prometheus_client=prometheus_client_mock)
    assert results == {"123": 1, "345": 2, None: 5}
    assert mock_query.call_count == 1
    assert (
        mock_query.call_args[1]["query"]
        == """
count by (project_id) (
  max_over_time(gpu_gfx_activity{org_name="ORG1"}[1m])
)
"""
    )


@pytest.mark.asyncio
async def test_get_metrics_for_workloads_in_project():
    mock_session = AsyncMock(spec=AsyncSession)
    project = Project(
        id=uuid4(),
        name="Test Project",
        organization_id=uuid4(),
        status=ProjectStatus.READY,
        cluster_id="b4884301-b87c-4e4a-89bc-e60f458f176d",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    workload = Workload(
        id=uuid4(),
        project_id=project.id,
        cluster_id=uuid4(),
        status=WorkloadStatus.RUNNING,
        created_by="tester",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        updated_by="tester",
    )
    gpus = {}
    vram = {}
    gpus[str(workload.id)] = 1
    vram[str(workload.id)] = 1024

    pagination_params = PaginationConditions(page=1, page_size=10)
    sort_params = []
    filter_params = []

    with (
        patch("app.metrics.service.get_workloads_with_running_time_in_project", return_value=([(workload, 300)], 1)),
        patch("app.metrics.service.get_gpu_device_utilization_for_project_by_workload_id", return_value=gpus),
        patch("app.metrics.service.get_gpu_memory_utilization_for_project_by_workload_id", return_value=vram),
    ):
        prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
        result = await get_workloads_metrics_by_project(
            mock_session,
            project=project,
            prometheus_client=prometheus_client_mock,
            pagination_params=pagination_params,
            sort_params=sort_params,
            filter_params=filter_params,
        )

    assert isinstance(result, WorkloadsWithMetrics)
    assert len(result.workloads) == 1
    workload = result.workloads[0]
    assert workload.gpu_count == 1
    assert workload.vram == 1024
    assert workload.run_time == 300
    assert workload.status == WorkloadStatus.RUNNING
    assert workload.created_by == "tester"


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query", autospec=True)
@patch("app.metrics.service.get_aggregation_lookback_for_metrics", return_value="5m")
async def test_get_gpu_device_utilization_for_project_by_workload_id(mock_lookback, mock_query):
    project_id = uuid4()
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    mock_query.return_value = [
        {"metric": {"workload_id": "w1"}, "value": [1672531199, "2"]},
        {"metric": {"workload_id": "w2"}, "value": [1672531199, "4"]},
        {"metric": {}, "value": [1672531199, "1"]},
    ]

    result = await get_gpu_device_utilization_for_project_by_workload_id(
        project_id, prometheus_client=prometheus_client_mock
    )
    assert result == {"w1": 2, "w2": 4, None: 1}
    assert mock_query.call_count == 1
    assert (
        "count by (workload_id)" in mock_query.call_args[1]["query"]
        and f'gpu_gfx_activity{{project_id="{project_id}"}}' in mock_query.call_args[1]["query"]
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query", autospec=True)
@patch("app.metrics.service.get_aggregation_lookback_for_metrics", return_value="5m")
async def test_get_gpu_memory_utilization_for_project_by_workload_id(mock_lookback, mock_query):
    project_id = uuid4()
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    mock_query.return_value = [
        {"metric": {"workload_id": "w1"}, "value": [1672531199, "1024"]},
        {"metric": {"workload_id": "w2"}, "value": [1672531199, "2048"]},
        {"metric": {}, "value": [1672531199, "512"]},
    ]

    result = await get_gpu_memory_utilization_for_project_by_workload_id(
        project_id, prometheus_client=prometheus_client_mock
    )
    assert result == {"w1": 1024, "w2": 2048, None: 512}
    assert mock_query.call_count == 1
    assert (
        "sum by (workload_id)" in mock_query.call_args[1]["query"]
        and f'gpu_used_vram{{project_id="{project_id}"}}' in mock_query.call_args[1]["query"]
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_metrics_timeseries", autospec=True)
async def test_get_gpu_device_utilization_timeseries_for_project(mock_map_timeseries, mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)
    project = Project(
        id=uuid4(),
        name="test-project",
        description="Test description",
        cluster_id="b4884301-b87c-4e4a-89bc-e60f458f176d",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        status=ProjectStatus.READY,
        updated_by="test@example.com",
        cluster=Cluster(
            id="b4884301-b87c-4e4a-89bc-e60f458f176d",
            name="Test Cluster",
            organization_id=uuid4(),
        ),
    )

    utilized_gpus_mock = [{"metric": {}, "values": [(start.timestamp(), "5"), (end.timestamp(), "10")]}]
    allocated_gpus_mock = [{"metric": {}, "values": [(start.timestamp(), "15"), (end.timestamp(), "20")]}]
    mock_custom_query.side_effect = [utilized_gpus_mock, allocated_gpus_mock]

    mock_map_timeseries.side_effect = [
        MetricsTimeseries(
            data=[
                DatapointsWithMetadata(
                    metadata=ProjectDatapointMetadata(
                        label="utilized_gpus", project=ProjectResponse.model_validate(project)
                    ),
                    values=[Datapoint(value=5.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
                )
            ],
            range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
        ),
        MetricsTimeseries(
            data=[
                DatapointsWithMetadata(
                    metadata=ProjectDatapointMetadata(
                        label="allocated_gpus", project=ProjectResponse.model_validate(project)
                    ),
                    values=[Datapoint(value=8.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
                )
            ],
            range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
        ),
    ]

    result = await get_gpu_device_utilization_timeseries_for_project(
        start, end, project, prometheus_client=prometheus_client_mock
    )

    assert len(result.data) == 2
    assert result.data[0].values[0].value == 5.0
    assert result.data[1].values[0].value == 8.0

    assert mock_custom_query.call_count == 2

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f"""
avg_over_time(
    count(
        gpu_gfx_activity{{project_id="{project.id}"}}
    )
    [1m:]
)
OR (0 * max(gpu_total_vram{{kube_cluster_name="Test Cluster"}}))
"""
    )
    assert (
        mock_custom_query.call_args_list[1][1]["query"]
        == f"""
avg_over_time(
    max(
        allocated_gpus{{project_id="{project.id}"}}
    )
    [1m:]
)
"""
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_metrics_timeseries", autospec=True)
async def test_get_gpu_memory_utilization_timeseries_for_project(mock_map_timeseries, mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)
    project = Project(
        id=uuid4(),
        name="test-project",
        description="Test description",
        status=ProjectStatus.READY,
        cluster_id="b4884301-b87c-4e4a-89bc-e60f458f176d",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
        cluster=Cluster(
            id="b4884301-b87c-4e4a-89bc-e60f458f176d",
            name="Test Cluster",
            organization_id=uuid4(),
        ),
    )

    utilized_gpus_mock = [{"metric": {}, "values": [(start.timestamp(), "5"), (end.timestamp(), "10")]}]
    allocated_gpus_mock = [{"metric": {}, "values": [(start.timestamp(), "15"), (end.timestamp(), "20")]}]
    mock_custom_query.side_effect = [utilized_gpus_mock, allocated_gpus_mock]

    mock_map_timeseries.side_effect = [
        MetricsTimeseries(
            data=[
                DatapointsWithMetadata(
                    metadata=ProjectDatapointMetadata(
                        label="utilized_gpu_vram", project=ProjectResponse.model_validate(project)
                    ),
                    values=[Datapoint(value=5.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
                )
            ],
            range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
        ),
        MetricsTimeseries(
            data=[
                DatapointsWithMetadata(
                    metadata=ProjectDatapointMetadata(
                        label="allocated_gpu_vram", project=ProjectResponse.model_validate(project)
                    ),
                    values=[Datapoint(value=8.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
                )
            ],
            range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
        ),
    ]

    result = await get_gpu_memory_utilization_timeseries_for_project(
        start, end, project, prometheus_client=prometheus_client_mock
    )

    assert len(result.data) == 2
    assert result.data[0].values[0].value == 5.0
    assert result.data[1].values[0].value == 8.0

    assert mock_custom_query.call_count == 2

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f"""
avg_over_time(
    sum(
        gpu_used_vram{{project_id="{project.id}"}}
    )
    [1m:]
)
OR (0 * max(gpu_total_vram{{kube_cluster_name="Test Cluster"}}))
"""
    )
    assert (
        mock_custom_query.call_args_list[1][1]["query"]
        == f"""
avg_over_time(
    max(
        allocated_gpu_vram{{project_id="{project.id}"}}
    )
    [1m:]
)
"""
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
async def test_get_avg_gpu_idle_time_for_project(mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="Test description",
        status=ProjectStatus.READY,
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    average_idle_time_mock = [
        {
            "metric": {},
            "values": [
                (start.timestamp(), "5"),
                ((start + timedelta(minutes=1)).timestamp(), "6"),
                ((start + timedelta(minutes=2)).timestamp(), "NaN"),
                ((start + timedelta(minutes=3)).timestamp(), "Inf"),
                ((start + timedelta(minutes=4)).timestamp(), "-Inf"),
                (end.timestamp(), "10"),
            ],
        }
    ]
    mock_custom_query.return_value = average_idle_time_mock

    result = await get_avg_gpu_idle_time_for_project(start, end, project, prometheus_client=prometheus_client_mock)

    assert result.data == 21.0

    assert mock_custom_query.call_count == 1

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f"""
(
    avg_over_time(
        avg(
            allocated_gpus{{project_id="{project.id}"}}
        )
        [1m:]
    ) -
    on() avg_over_time(
        count(
            gpu_gfx_activity{{project_id="{project.id}"}}
        )
        [1m:]
    )
) * 60.0
/
on() avg_over_time(
        avg(
            allocated_gpus{{project_id="{project.id}"}}
        )
        [1m:]
)
"""
    )


@pytest.mark.asyncio
@patch("app.metrics.service.get_average_pending_time_for_workloads_in_project_created_between", autospec=True)
async def test_get_average_pending_time_for_workloads_in_project_created_between_returns_valid_average(
    mock_get_avg,
):
    mock_get_avg.return_value = 123.45

    project = Project(
        id=uuid4(),
        status=ProjectStatus.READY,
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC)

    session = AsyncMock(spec=AsyncSession)

    result = await get_average_wait_time_for_project(session, start, end, project)

    assert isinstance(result, MetricsScalarWithRange)
    assert result.data == 123.45
    assert result.range == DateRange(start=start, end=end)


@pytest.mark.asyncio
@patch("app.metrics.service.get_average_pending_time_for_workloads_in_project_created_between", autospec=True)
async def test_get_average_pending_time_for_workloads_in_project_created_between_returns_zero_if_none(mock_get_avg):
    mock_get_avg.return_value = None

    project = Project(
        id=uuid4(),
        status=ProjectStatus.READY,
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC)

    session = AsyncMock(spec=AsyncSession)

    result = await get_average_wait_time_for_project(session, start, end, project)

    assert result.data == 0
    assert result.range == DateRange(start=start, end=end)


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_metrics_timeseries", autospec=True)
async def test_get_workload_request_metrics(mock_map_timeseries, mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)

    running_requests = [{"metric": {}, "values": [(start.timestamp(), "5"), (end.timestamp(), "10")]}]
    pending_requests = [{"metric": {}, "values": [(start.timestamp(), "15"), (end.timestamp(), "20")]}]
    mock_custom_query.side_effect = [running_requests, pending_requests]

    mock_map_timeseries.side_effect = [
        MetricsTimeseries(
            data=[
                DatapointsWithMetadata(
                    metadata=DatapointMetadataBase(label="running_requests"),
                    values=[Datapoint(value=5.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
                )
            ],
            range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
        ),
        MetricsTimeseries(
            data=[
                DatapointsWithMetadata(
                    metadata=DatapointMetadataBase(label="waiting_requests"),
                    values=[Datapoint(value=8.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
                )
            ],
            range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
        ),
    ]

    workload_id = uuid4()

    result = await get_workload_request_metrics(start, end, workload_id, prometheus_client=prometheus_client_mock)

    assert len(result.data) == 2
    assert result.data[0].values[0].value == 5.0
    assert result.data[1].values[0].value == 8.0

    assert mock_custom_query.call_count == 2

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f'max_over_time(vllm:num_requests_running{{workload_id="{workload_id}"}}[1m])'
    )
    assert (
        mock_custom_query.call_args_list[1][1]["query"]
        == f'max_over_time(vllm:num_requests_waiting{{workload_id="{workload_id}"}}[1m])'
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_metrics_timeseries", autospec=True)
async def test_get_time_to_first_token_metrics(mock_map_timeseries, mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)

    mock_custom_query.side_effect = [{"metric": {}, "values": [(start.timestamp(), "0.1"), (end.timestamp(), "1")]}]

    mock_map_timeseries.return_value = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_TIME_TO_FIRST_TOKEN_LABEL),
                values=[Datapoint(value=0.1, timestamp=start), Datapoint(value=1, timestamp=end)],
            )
        ],
        range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    workload_id = uuid4()
    result = await get_time_to_first_token_metrics(start, end, workload_id, prometheus_client=prometheus_client_mock)

    assert result.data[0].values[0].value == 0.1

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f"""rate(vllm:time_to_first_token_seconds_sum{{workload_id="{workload_id}"}}[1m])
/
rate(vllm:time_to_first_token_seconds_count{{workload_id="{workload_id}"}}[1m])"""
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_metrics_timeseries", autospec=True)
async def test_get_inter_token_latency_metrics(mock_map_timeseries, mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)

    mock_custom_query.side_effect = [{"metric": {}, "values": [(start.timestamp(), "0.1"), (end.timestamp(), "1")]}]

    mock_map_timeseries.return_value = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_INTER_TOKEN_LATENCY_LABEL),
                values=[Datapoint(value=0.1, timestamp=start), Datapoint(value=1, timestamp=end)],
            )
        ],
        range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    workload_id = uuid4()
    result = await get_inter_token_latency_metrics(start, end, workload_id, prometheus_client=prometheus_client_mock)

    assert result.data[0].values[0].value == 0.1

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f"""rate(vllm:time_per_output_token_seconds_sum{{workload_id="{workload_id}"}}[1m])
/
rate(vllm:time_per_output_token_seconds_count{{workload_id="{workload_id}"}}[1m])"""
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query_range", return_value=AsyncMock())
@patch("app.metrics.service.map_metrics_timeseries", autospec=True)
async def test_get_end_to_end_latency_metrics(mock_map_timeseries, mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)

    mock_custom_query.side_effect = [{"metric": {}, "values": [(start.timestamp(), "0.1"), (end.timestamp(), "1")]}]

    mock_map_timeseries.return_value = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_END_TO_END_LATENCY_LABEL),
                values=[Datapoint(value=0.1, timestamp=start), Datapoint(value=1, timestamp=end)],
            )
        ],
        range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    workload_id = uuid4()
    result = await get_end_to_end_latency_metrics(start, end, workload_id, prometheus_client=prometheus_client_mock)

    assert result.data[0].values[0].value == 0.1

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f"""rate(vllm:e2e_request_latency_seconds_sum{{workload_id="{workload_id}"}}[1m])
/
rate(vllm:e2e_request_latency_seconds_count{{workload_id="{workload_id}"}}[1m])"""
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query", return_value=AsyncMock())
async def test_get_kv_cache_usage_metric(mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)

    mock_custom_query.return_value = [{"metric": {}, "value": [end, "20"]}]

    workload_id = uuid4()
    result = await get_kv_cache_usage_metric(start, end, workload_id, prometheus_client=prometheus_client_mock)

    assert result.data == 20

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f'avg_over_time(vllm:kv_cache_usage_perc{{workload_id="{workload_id}"}}[600s])'
    )


@pytest.mark.asyncio
@patch("app.metrics.service.a_custom_query", return_value=AsyncMock())
async def test_get_total_tokens_metric(mock_custom_query):
    prometheus_client_mock = AsyncMock(spec=PrometheusConnect)
    start = datetime.now(UTC)
    end = start + timedelta(minutes=10)

    mock_custom_query.return_value = [{"metric": {}, "value": [end, "42334"]}]

    workload_id = uuid4()
    result = await get_total_tokens_metric(workload_id, prometheus_client=prometheus_client_mock)

    assert result.data == 42334

    assert (
        mock_custom_query.call_args_list[0][1]["query"]
        == f'vllm:generation_tokens_total{{workload_id="{workload_id}"}}'
    )
