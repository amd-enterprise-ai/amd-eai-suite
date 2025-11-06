# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.managed_workloads.enums import WorkloadStatus
from app.managed_workloads.schemas import AllocatedResources, ChartWorkloadResponse
from app.metrics.constants import (
    VLLM_END_TO_END_LATENCY_LABEL,
    VLLM_INTER_TOKEN_LATENCY_LABEL,
    VLLM_RUNNING_REQUESTS_LABEL,
    VLLM_TIME_TO_FIRST_TOKEN_LABEL,
    VLLM_WAITING_REQUESTS_LABEL,
)
from app.metrics.schemas import (
    Datapoint,
    DatapointMetadataBase,
    DatapointsWithMetadata,
    DateRange,
    MetricsScalar,
    MetricsScalarWithRange,
    MetricsTimeseries,
    TimeseriesRange,
)
from app.metrics.service import get_prometheus_client
from app.utilities.database import get_session
from app.utilities.exceptions import NotFoundException
from app.utilities.security import (
    BearerToken,
    auth_token_claimset,
    get_projects_accessible_to_user,
    get_user_organization,
    validate_and_get_project_from_query,
)
from tests import factory
from tests.conftest import get_test_client

from ..test_utils.date_utils import datetime_to_iso_format


def setup_test_dependencies(env, db_session, mock_claimset):
    """Set up common test dependencies."""
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: env.project
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]
    app.dependency_overrides[get_user_organization] = lambda: MagicMock(id=uuid4())
    app.dependency_overrides[BearerToken] = lambda: "test-token"
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()


@patch("app.managed_workloads.router.list_workloads")
async def test_get_workloads(mock_list_workloads, db_session: AsyncSession, mock_claimset):
    """Test list managed workloads endpoint returns 200."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    # Create a managed workload using the existing model
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
    )

    workload_response = ChartWorkloadResponse.model_validate(managed_workload)
    mock_list_workloads.return_value = [workload_response]

    setup_test_dependencies(env, db_session, mock_claimset)

    with get_test_client() as client:
        response = client.get(f"/v1/managed-workloads?project={env.project.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == str(workload_response.id)


@patch("app.managed_workloads.router.list_workloads")
async def test_get_workloads_with_resources(mock_list_workloads, db_session: AsyncSession, mock_claimset):
    """Test list managed workloads with resources returns 200."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
    )

    workload_response = ChartWorkloadResponse.model_validate(managed_workload)
    mock_list_workloads.return_value = [workload_response]

    setup_test_dependencies(env, db_session, mock_claimset)

    with (
        patch("app.managed_workloads.router.enrich_with_resource_utilization") as mock_enrich,
        get_test_client() as client,
    ):
        # Mock the enrichment function to return response with allocated resources
        enriched_response = ChartWorkloadResponse.model_validate(managed_workload)
        enriched_response.allocated_resources = AllocatedResources(gpu_count=2, vram=32000.0)
        mock_enrich.return_value = [enriched_response]

        response = client.get(f"/v1/managed-workloads?project={env.project.id}&with_resources=true")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        mock_enrich.assert_called_once()


@patch("app.managed_workloads.router.get_workload")
async def test_get_workload(mock_get_workload, db_session: AsyncSession, mock_claimset):
    """Test get workload details endpoint returns 200."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        manifest="apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service",
    )

    workload_response = ChartWorkloadResponse.model_validate(managed_workload)
    mock_get_workload.return_value = workload_response

    setup_test_dependencies(env, db_session, mock_claimset)

    with get_test_client() as client:
        response = client.get(f"/v1/managed-workloads/{managed_workload.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(managed_workload.id)


@patch("app.managed_workloads.router.get_workload")
async def test_get_workload_with_resources(mock_get_workload, db_session: AsyncSession, mock_claimset):
    """Test get workload details with resources returns 200."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        manifest="apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service",
    )

    workload_response = ChartWorkloadResponse.model_validate(managed_workload)
    mock_get_workload.return_value = workload_response

    setup_test_dependencies(env, db_session, mock_claimset)

    with (
        patch("app.managed_workloads.router.enrich_with_resource_utilization") as mock_enrich,
        get_test_client() as client,
    ):
        # Mock the enrichment function to return response with allocated resources
        enriched_response = ChartWorkloadResponse.model_validate(managed_workload)
        enriched_response.allocated_resources = AllocatedResources(gpu_count=2, vram=32000.0)
        mock_enrich.return_value = [enriched_response]

        response = client.get(f"/v1/managed-workloads/{managed_workload.id}?with_resources=true")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(managed_workload.id)
        mock_enrich.assert_called_once()


@patch("app.managed_workloads.router.get_workload")
async def test_get_workload_not_found(mock_get_workload, db_session: AsyncSession, mock_claimset):
    """Test get workload details with non-existent ID returns 404."""
    env = await factory.create_basic_test_environment(db_session)
    workload_id = uuid4()
    mock_get_workload.side_effect = NotFoundException(f"Workload {workload_id} not found")

    setup_test_dependencies(env, db_session, mock_claimset)

    with get_test_client() as client:
        response = client.get(f"/v1/managed-workloads/{workload_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@patch("app.managed_workloads.router.select_workload")
@patch("app.managed_workloads.router.stream_downstream")
async def test_chat_with_model(mock_stream, mock_select_workload, db_session: AsyncSession, mock_claimset):
    """Test chat with model endpoint returns streaming response."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={"internal_host": "http://test-host:8080"},
    )

    workload_response = ChartWorkloadResponse.model_validate(managed_workload)
    mock_select_workload.return_value = workload_response
    mock_stream.return_value = MagicMock()

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(
            f"/v1/chat/{managed_workload.id}",
            json={"messages": [{"content": "Hello", "role": "user"}], "stream": False},
        )
        assert response.status_code == status.HTTP_200_OK
        mock_stream.assert_called_once()


@patch("app.managed_workloads.router.select_workload")
async def test_chat_with_model_not_found(mock_select_workload, db_session: AsyncSession, mock_claimset):
    """Test chat with non-existent model returns 404."""
    env = await factory.create_basic_test_environment(db_session)
    workload_id = uuid4()
    mock_select_workload.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(f"/v1/chat/{workload_id}", json={"messages": [{"content": "Hello", "role": "user"}]})
        assert response.status_code == status.HTTP_404_NOT_FOUND


@patch("app.managed_workloads.router.select_workload")
async def test_chat_with_model_not_running(mock_select_workload, db_session: AsyncSession, mock_claimset):
    """Test chat with non-running model returns 422."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.PENDING.value,
        name="Test-Workload",
        display_name="Test Workload",
    )

    workload_response = ChartWorkloadResponse.model_validate(managed_workload)
    mock_select_workload.return_value = workload_response

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(
            f"/v1/chat/{managed_workload.id}", json={"messages": [{"content": "Hello", "role": "user"}]}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@patch("app.managed_workloads.router.select_workload")
async def test_chat_with_model_no_host(mock_select_workload, db_session: AsyncSession, mock_claimset):
    """Test chat with model that has no host returns 422."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={},  # No internal_host
    )

    workload_response = ChartWorkloadResponse.model_validate(managed_workload)
    mock_select_workload.return_value = workload_response

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(
            f"/v1/chat/{managed_workload.id}", json={"messages": [{"content": "Hello", "role": "user"}]}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
@patch("app.managed_workloads.router.validate_datetime_range")
@patch("app.managed_workloads.router.get_workload_request_metrics")
async def test_get_aim_workload_request_metrics_success(
    mock_get_workload_metrics, mock_validate, __, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={},  # No internal_host
    )

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    expected_metrics = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_RUNNING_REQUESTS_LABEL),
                values=[Datapoint(value=5.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
            ),
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_WAITING_REQUESTS_LABEL),
                values=[Datapoint(value=8.0, timestamp=start), Datapoint(value=10.0, timestamp=end)],
            ),
        ],
        range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    mock_get_workload_metrics.return_value = expected_metrics

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{managed_workload.id}/metrics/requests?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert MetricsTimeseries.model_validate(response.json()) == expected_metrics
        mock_validate.assert_called_once()


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
async def test_get_aim_workload_request_metrics_workload_not_found(
    mock_get_workload, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    mock_get_workload.side_effect = NotFoundException("Not found")

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{uuid4()}/metrics/requests?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
@patch("app.managed_workloads.router.validate_datetime_range")
@patch("app.managed_workloads.router.get_time_to_first_token_metrics")
async def test_get_aim_time_to_first_token_metrics_success(
    mock_get_metrics, mock_validate, __, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={},
    )

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    expected_metrics = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_TIME_TO_FIRST_TOKEN_LABEL),
                values=[Datapoint(value=150.0, timestamp=start), Datapoint(value=180.0, timestamp=end)],
            ),
        ],
        range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    mock_get_metrics.return_value = expected_metrics

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{managed_workload.id}/metrics/time_to_first_token?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert MetricsTimeseries.model_validate(response.json()) == expected_metrics
        mock_validate.assert_called_once()


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
async def test_get_aim_time_to_first_token_metrics_workload_not_found(
    mock_get_aim, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    mock_get_aim.side_effect = NotFoundException("Not found")

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{uuid4()}/metrics/time_to_first_token?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
@patch("app.managed_workloads.router.validate_datetime_range")
@patch("app.managed_workloads.router.get_inter_token_latency_metrics")
async def test_get_aim_inter_token_latency_metrics_success(
    mock_get_metrics, mock_validate, __, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={},
    )

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    expected_metrics = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_INTER_TOKEN_LATENCY_LABEL),
                values=[Datapoint(value=25.0, timestamp=start), Datapoint(value=30.0, timestamp=end)],
            ),
        ],
        range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    mock_get_metrics.return_value = expected_metrics

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{managed_workload.id}/metrics/inter_token_latency?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert MetricsTimeseries.model_validate(response.json()) == expected_metrics
        mock_validate.assert_called_once()


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
async def test_get_aim_inter_token_latency_metrics_workload_not_found(
    mock_get_aim, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    mock_get_aim.side_effect = NotFoundException("Not found")

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{uuid4()}/metrics/inter_token_latency?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
@patch("app.managed_workloads.router.validate_datetime_range")
@patch("app.managed_workloads.router.get_end_to_end_latency_metrics")
async def test_get_aim_end_to_end_latency_metrics_success(
    mock_get_metrics, mock_validate, __, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={},
    )

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    expected_metrics = MetricsTimeseries(
        data=[
            DatapointsWithMetadata(
                metadata=DatapointMetadataBase(label=VLLM_END_TO_END_LATENCY_LABEL),
                values=[Datapoint(value=500.0, timestamp=start), Datapoint(value=550.0, timestamp=end)],
            ),
        ],
        range=TimeseriesRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    mock_get_metrics.return_value = expected_metrics

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{managed_workload.id}/metrics/end_to_end_latency?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert MetricsTimeseries.model_validate(response.json()) == expected_metrics
        mock_validate.assert_called_once()


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
async def test_get_aim_end_to_end_latency_metrics_workload_not_found(
    mock_get_aim, db_session: AsyncSession, mock_claimset
):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    mock_get_aim.side_effect = NotFoundException("Not found")

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{uuid4()}/metrics/end_to_end_latency?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
@patch("app.managed_workloads.router.validate_datetime_range")
@patch("app.managed_workloads.router.get_kv_cache_usage_metric")
async def test_get_aim_kv_cache_usage_metric_success(mock_get_metrics, _, __, db_session: AsyncSession, mock_claimset):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={},
    )

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    expected_metrics = MetricsScalarWithRange(
        data=45.5,
        range=DateRange(start=start, end=end, interval_seconds=300, timestamps=[start, end]),
    )

    mock_get_metrics.return_value = expected_metrics

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{managed_workload.id}/metrics/kv_cache_usage?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert MetricsScalarWithRange.model_validate(response.json()) == expected_metrics


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
async def test_get_aim_kv_cache_usage_metric_workload_not_found(mock_get_aim, db_session: AsyncSession, mock_claimset):
    start = datetime.now(UTC).replace(microsecond=0)
    end = start + timedelta(minutes=10)

    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    mock_get_aim.side_effect = NotFoundException("Not found")

    with get_test_client() as client:
        response = client.get(
            f"/v1/managed-workloads/{uuid4()}/metrics/kv_cache_usage?start={datetime_to_iso_format(start)}&end={datetime_to_iso_format(end)}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
@patch("app.managed_workloads.router.get_total_tokens_metric")
async def test_get_aim_total_tokens_metric_success(mock_get_metrics, _, db_session: AsyncSession, mock_claimset):
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    managed_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="Test-Workload",
        display_name="Test Workload",
        output={},
    )

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    expected_metrics = MetricsScalar(data=12345.0)

    mock_get_metrics.return_value = expected_metrics

    with get_test_client() as client:
        response = client.get(f"/v1/managed-workloads/{managed_workload.id}/metrics/total_tokens")
        assert response.status_code == status.HTTP_200_OK
        assert MetricsScalar.model_validate(response.json()) == expected_metrics


@pytest.mark.asyncio
@patch("app.managed_workloads.router.get_workload")
async def test_get_aim_total_tokens_metric_workload_not_found(mock_get_aim, db_session: AsyncSession, mock_claimset):
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    setup_test_dependencies(env, db_session, mock_claimset)
    app.dependency_overrides[get_prometheus_client] = lambda: MagicMock()
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: [env.project]

    mock_get_aim.side_effect = NotFoundException("Not found")

    with get_test_client() as client:
        response = client.get(f"/v1/managed-workloads/{uuid4()}/metrics/total_tokens")
        assert response.status_code == status.HTTP_404_NOT_FOUND
