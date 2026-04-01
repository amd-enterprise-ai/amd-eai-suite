# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import app  # type: ignore
from app.metrics.schemas import (
    CurrentUtilization,
    Datapoint,
    DatapointsWithMetadata,
    MetricsTimeseries,
    ProjectDatapointMetadata,
    TimeseriesRange,
    UtilizationByProject,
)
from app.organizations.schemas import OrganizationResponse
from app.projects.schemas import ProjectResponse
from tests.dependency_overrides import (
    ADMIN_FORBIDDEN_OVERRIDES,
    ADMIN_SESSION_OVERRIDES,
    override_dependencies,
)

default_timeseries_metrics = MetricsTimeseries(
    data=[
        DatapointsWithMetadata(
            metadata=ProjectDatapointMetadata(
                label="default_label",
                project=ProjectResponse(
                    id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
                    name="project1",
                    description="project 1",
                    cluster_id=UUID("0aa22e92-002c-41b7-a06e-dcdb0244974c"),
                    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    status="Pending",
                    status_reason="Creating",
                ),
            ),
            values=[
                Datapoint(
                    value=0.1,
                    timestamp=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                ),
                Datapoint(
                    value=0.3,
                    timestamp=datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC),
                ),
            ],
        ),
        DatapointsWithMetadata(
            metadata=ProjectDatapointMetadata(
                label="default_label",
                project=ProjectResponse(
                    id=UUID("19465a28-1649-4f55-887f-536dd36a47f8"),
                    name="project2",
                    description="project 2",
                    cluster_id=UUID("1ab22e52-102c-31b7-a06e-dcdb0244974c"),
                    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    status="Pending",
                    status_reason="Creating",
                ),
            ),
            values=[
                Datapoint(
                    value=0.2,
                    timestamp=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
                ),
                Datapoint(
                    value=0.4,
                    timestamp=datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC),
                ),
            ],
        ),
    ],
    range=TimeseriesRange(
        start=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        end=datetime(2025, 3, 11, 12, 0, 0, tzinfo=UTC),
        interval_seconds=60,
        timestamps=[
            datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
            datetime(2025, 3, 10, 12, 1, 0, tzinfo=UTC),
        ],
    ),
)


@pytest.mark.asyncio
@patch(
    "app.organizations.router.get_realm_details",
    return_value=OrganizationResponse(
        idp_linked=False,
    ),
)
async def test_get_user_organization(_: AsyncMock) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/organization")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "idp_linked": False,
        "smtp_enabled": False,
    }


@pytest.mark.asyncio
@patch(
    "app.organizations.router.get_gpu_memory_utilization_timeseries_from_ds",
    return_value=default_timeseries_metrics,
    autospec=True,
)
@patch("app.metrics.schemas.datetime")
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_get_gpu_memory_utilization_timeseries_success(mock_dt: MagicMock, _: AsyncMock) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": [
            {
                "metadata": {
                    "label": "default_label",
                    "project": {
                        "description": "project 1",
                        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                        "name": "project1",
                        "cluster_id": "0aa22e92-002c-41b7-a06e-dcdb0244974c",
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
                    },
                },
                "values": [
                    {"timestamp": "2025-03-10T12:00:00Z", "value": 0.1},
                    {"timestamp": "2025-03-10T12:01:00Z", "value": 0.3},
                ],
            },
            {
                "metadata": {
                    "label": "default_label",
                    "project": {
                        "description": "project 2",
                        "id": "19465a28-1649-4f55-887f-536dd36a47f8",
                        "name": "project2",
                        "cluster_id": "1ab22e52-102c-31b7-a06e-dcdb0244974c",
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
                    },
                },
                "values": [
                    {"timestamp": "2025-03-10T12:00:00Z", "value": 0.2},
                    {"timestamp": "2025-03-10T12:01:00Z", "value": 0.4},
                ],
            },
        ],
        "range": {
            "end": "2025-03-11T12:00:00Z",
            "interval_seconds": 60,
            "start": "2025-03-10T12:00:00Z",
            "timestamps": ["2025-03-10T12:00:00Z", "2025-03-10T12:01:00Z"],
        },
    }


@pytest.mark.asyncio
@override_dependencies(ADMIN_FORBIDDEN_OVERRIDES)
async def test_get_gpu_memory_utilization_timeseries_not_in_role() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.organizations.router.get_gpu_device_utilization_timeseries_from_ds",
    return_value=default_timeseries_metrics,
    autospec=True,
)
@patch("app.metrics.schemas.datetime")
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_get_gpu_device_utilization_timeseries_success(mock_dt: MagicMock, _: AsyncMock) -> None:
    mock_dt.now.return_value = datetime(2025, 3, 11, 12, 1, 0, tzinfo=UTC)
    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "data": [
            {
                "metadata": {
                    "label": "default_label",
                    "project": {
                        "description": "project 1",
                        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                        "name": "project1",
                        "cluster_id": "0aa22e92-002c-41b7-a06e-dcdb0244974c",
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
                    },
                },
                "values": [
                    {"timestamp": "2025-03-10T12:00:00Z", "value": 0.1},
                    {"timestamp": "2025-03-10T12:01:00Z", "value": 0.3},
                ],
            },
            {
                "metadata": {
                    "label": "default_label",
                    "project": {
                        "description": "project 2",
                        "id": "19465a28-1649-4f55-887f-536dd36a47f8",
                        "name": "project2",
                        "cluster_id": "1ab22e52-102c-31b7-a06e-dcdb0244974c",
                        "created_at": "2025-03-10T10:00:00Z",
                        "updated_at": "2025-03-10T10:00:00Z",
                        "created_by": "test@example.com",
                        "updated_by": "test@example.com",
                        "status": "Pending",
                        "status_reason": "Creating",
                    },
                },
                "values": [
                    {"timestamp": "2025-03-10T12:00:00Z", "value": 0.2},
                    {"timestamp": "2025-03-10T12:01:00Z", "value": 0.4},
                ],
            },
        ],
        "range": {
            "end": "2025-03-11T12:00:00Z",
            "interval_seconds": 60,
            "start": "2025-03-10T12:00:00Z",
            "timestamps": ["2025-03-10T12:00:00Z", "2025-03-10T12:01:00Z"],
        },
    }


@pytest.mark.asyncio
@override_dependencies(ADMIN_FORBIDDEN_OVERRIDES)
async def test_gpu_device_utilization_timeseries_not_in_role() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.organizations.router.get_current_utilization_from_ds",
    return_value=CurrentUtilization(
        timestamp=datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC),
        total_utilized_gpus_count=10,
        total_running_workloads_count=5,
        total_pending_workloads_count=2,
        utilization_by_project=[
            UtilizationByProject(
                project=ProjectResponse(
                    id=UUID("0aa18e92-002c-45b7-a06e-dcdb0277974c"),
                    name="project1",
                    description="project 1",
                    cluster_id=UUID("0aa22e92-002c-41b7-a06e-dcdb0244974c"),
                    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    status="Pending",
                    status_reason="Creating",
                ),
                allocated_gpus_count=3,
                utilized_gpus_count=2,
                running_workloads_count=2,
                pending_workloads_count=1,
            ),
            UtilizationByProject(
                project=ProjectResponse(
                    id=UUID("1aa18e92-002c-45b7-a06e-dcdb0277974c"),
                    name="project2",
                    description="project 2",
                    cluster_id=UUID("1ab22e52-102c-31b7-a06e-dcdb0244974c"),
                    created_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    updated_at=datetime(2025, 3, 10, 10, 0, 0, tzinfo=UTC),
                    created_by="test@example.com",
                    updated_by="test@example.com",
                    status="Pending",
                    status_reason="Creating",
                ),
                allocated_gpus_count=1,
                utilized_gpus_count=0,
                running_workloads_count=0,
                pending_workloads_count=0,
            ),
        ],
    ),
)
@pytest.mark.asyncio
@override_dependencies(ADMIN_SESSION_OVERRIDES)
async def test_get_current_utilization(_: AsyncMock) -> None:
    with TestClient(app) as client:
        response = client.get("/v1/metrics/utilization")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "timestamp": "2025-03-10T12:00:00Z",
        "total_utilized_gpus_count": 10,
        "total_running_workloads_count": 5,
        "total_pending_workloads_count": 2,
        "utilization_by_project": [
            {
                "allocated_gpus_count": 3,
                "pending_workloads_count": 1,
                "running_workloads_count": 2,
                "project": {
                    "description": "project 1",
                    "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                    "name": "project1",
                    "cluster_id": "0aa22e92-002c-41b7-a06e-dcdb0244974c",
                    "created_at": "2025-03-10T10:00:00Z",
                    "updated_at": "2025-03-10T10:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "status": "Pending",
                    "status_reason": "Creating",
                },
                "utilized_gpus_count": 2,
            },
            {
                "allocated_gpus_count": 1,
                "pending_workloads_count": 0,
                "running_workloads_count": 0,
                "project": {
                    "description": "project 2",
                    "id": "1aa18e92-002c-45b7-a06e-dcdb0277974c",
                    "name": "project2",
                    "cluster_id": "1ab22e52-102c-31b7-a06e-dcdb0244974c",
                    "created_at": "2025-03-10T10:00:00Z",
                    "updated_at": "2025-03-10T10:00:00Z",
                    "created_by": "test@example.com",
                    "updated_by": "test@example.com",
                    "status": "Pending",
                    "status_reason": "Creating",
                },
                "utilized_gpus_count": 0,
            },
        ],
    }
