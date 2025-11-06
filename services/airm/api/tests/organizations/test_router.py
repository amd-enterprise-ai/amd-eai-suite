# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from keycloak.exceptions import KeycloakGetError
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.organizations.models import Organization as OrganizationModel
from app.organizations.schemas import OrganizationCreate, OrganizationResponse
from app.projects.schemas import ProjectResponse
from app.users.schemas import InviteUser, UserRoleEnum
from app.utilities.database import get_session
from app.utilities.exceptions import ConflictException
from app.utilities.security import (
    ensure_platform_administrator,
    ensure_super_administrator,
    get_user_email,
    get_user_organization,
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
    "app.organizations.router.create_organization_in_system",
    return_value=OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb02779741",
        name="Org1",
        domains=["domain1"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_create_organization_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    organization_create = OrganizationCreate(name="Org1", domains=["domain1"])

    with TestClient(app) as client:
        response = client.post("/v1/organizations", json=organization_create.dict())

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "id": "0aa18e92-002c-45b7-a06e-dcdb02779741",
        "name": "Org1",
        "domains": ["domain1"],
        "idp_linked": False,
        "smtp_enabled": False,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }


@pytest.mark.asyncio
async def test_create_organization_not_in_role():
    mock_ensure_super_administrator = MagicMock()
    mock_ensure_super_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_super_administrator] = lambda: mock_ensure_super_administrator()
    organization_create = OrganizationCreate(name="Org1", domains=["domain1"])

    with TestClient(app) as client:
        response = client.post("/v1/organizations", json=organization_create.dict())

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.organizations.router.create_organization_in_system")
async def test_create_organization_duplicate_name(create_organization_in_system):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    create_organization_in_system.side_effect = ConflictException("An organization with name 'Org1' already exists")

    organization_create = OrganizationCreate(name="Org1", domains=["domain1"])

    with TestClient(app) as client:
        response = client.post("/v1/organizations", json=organization_create.dict())

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "An organization with name 'Org1' already exists"}


@pytest.mark.asyncio
@patch("app.organizations.router.create_organization_in_system")
async def test_create_organization_keycloak_error(create_organization_in_system):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)
    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    create_organization_in_system.side_effect = KeycloakGetError("", "", Exception())

    organization_create = OrganizationCreate(name="Org1", domains=["domain1"])

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/v1/organizations", json=organization_create.dict())

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_create_organization_invalid_input():
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.post("/v1/organizations", json={"name": "Org" + "*" * 64, "domains": ["domain1"]})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch("app.organizations.router.create_user_in_organization")
@patch(
    "app.organizations.router.get_organization_by_id",
    return_value=OrganizationModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    ),
)
async def test_invite_user_to_organization_success(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_user_email] = lambda: "test_user"
    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/organizations/0aa18e92-002c-45b7-a06e-dcdb02779741/users", json=user_create.dict())

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_invite_user_to_organization_not_in_role():
    mock_ensure_super_administrator = MagicMock()
    mock_ensure_super_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_super_administrator] = lambda: mock_ensure_super_administrator()
    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/organizations/0aa18e92-002c-45b7-a06e-dcdb02779741/users", json=user_create.dict())

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.organizations.router.create_user_in_organization")
@patch("app.organizations.router.get_organization_by_id", return_value=None)
async def test_invite_user_to_organization_org_not_found(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_user_email] = lambda: "test_user"
    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/organizations/0aa18e92-002c-45b7-a06e-dcdb02779741/users", json=user_create.dict())

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Organization not found"}


@pytest.mark.asyncio
@patch("app.organizations.router.create_user_in_organization")
@patch(
    "app.organizations.router.get_organization_by_id",
    return_value=OrganizationModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    ),
)
async def test_invite_user_to_organization_duplicate_email(_, create_user_in_organization):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    create_user_in_organization.side_effect = ConflictException("A user with email 'test1@example.com' already exists")

    user_create = InviteUser(email="test1@example.com", roles=[UserRoleEnum.PLATFORM_ADMIN])

    with TestClient(app) as client:
        response = client.post("/v1/organizations/0aa18e92-002c-45b7-a06e-dcdb02779741/users", json=user_create.dict())

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "A user with email 'test1@example.com' already exists"}


@pytest.mark.asyncio
async def test_get_organizations_not_in_role():
    mock_ensure_super_administrator = MagicMock()
    mock_ensure_super_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_super_administrator] = lambda: mock_ensure_super_administrator()

    with TestClient(app) as client:
        response = client.get("/v1/organizations")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch(
    "app.organizations.router.get_all_organizations",
    return_value=[
        OrganizationResponse(
            id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
            name="organization_1",
            domains=["test1.com", "test2.com"],
            idp_linked=False,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
        OrganizationResponse(
            id="0aa18e92-002c-45b7-a06e-dcdb0277974d",
            name="organization_2",
            domains=["amd.com"],
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            created_by="test@example.com",
            updated_by="test@example.com",
            idp_linked=False,
        ),
        OrganizationResponse(
            id="0aa18e92-002c-45b7-a06e-dcdb0277974e",
            name="organization_3",
            domains=[],
            idp_linked=True,
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            created_by="test@example.com",
            updated_by="test@example.com",
        ),
    ],
)
async def test_get_organizations_success(_):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/organizations")

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == {
        "organizations": [
            {
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
                "name": "organization_1",
                "domains": ["test1.com", "test2.com"],
                "idp_linked": False,
                "smtp_enabled": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
            {
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974d",
                "name": "organization_2",
                "domains": ["amd.com"],
                "idp_linked": False,
                "smtp_enabled": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
            {
                "id": "0aa18e92-002c-45b7-a06e-dcdb0277974e",
                "name": "organization_3",
                "domains": [],
                "idp_linked": True,
                "smtp_enabled": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            },
        ]
    }


@pytest.mark.asyncio
@patch("app.organizations.router.get_all_organizations", return_value=[])
async def test_get_organizations_empty_list(_):
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=AsyncSession)

    mock_get_user = MagicMock(spec_set=str)
    mock_get_user.return_value = "test_user"

    app.dependency_overrides[get_user_email] = lambda: mock_get_user()
    app.dependency_overrides[ensure_super_administrator] = lambda: MagicMock(spec_set=[])

    with TestClient(app) as client:
        response = client.get("/v1/organizations")

    assert response.status_code == status.HTTP_200_OK

    assert response.json() == {"organizations": []}


@pytest.mark.asyncio
@patch(
    "app.organizations.router.enrich_organization_details",
    return_value=OrganizationResponse(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c",
        name="organization_1",
        domains=["test1.com", "test2.com"],
        idp_linked=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_get_user_organization(_):
    app.dependency_overrides[get_user_organization] = lambda: OrganizationModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/organization")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": "0aa18e92-002c-45b7-a06e-dcdb0277974c",
        "name": "organization_1",
        "domains": ["test1.com", "test2.com"],
        "idp_linked": False,
        "smtp_enabled": False,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }


@pytest.mark.asyncio
async def test_get_user_organization_non_platform_admin():
    app.dependency_overrides[get_user_organization] = lambda: OrganizationModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization1", keycloak_organization_id="123"
    )

    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get("/v1/organization")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@patch("app.organizations.router.validate_datetime_range", autospec=True)
@patch(
    "app.organizations.router.get_gpu_memory_utilization_timeseries_from_ds",
    return_value=default_timeseries_metrics,
    autospec=True,
)
async def test_get_gpu_memory_utilization_timeseries_success(_, __):
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = OrganizationModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

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
async def test_get_gpu_memory_utilization_timeseries_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_gpu_memory_utilization_timeseries_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_memory_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.organizations.router.validate_datetime_range", autospec=True)
@patch(
    "app.organizations.router.get_gpu_device_utilization_timeseries_from_ds",
    return_value=default_timeseries_metrics,
    autospec=True,
)
async def test_get_gpu_device_utilization_timeseries_success(_, __):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = OrganizationModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

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
async def test_gpu_device_utilization_timeseries_not_in_role():
    mock_ensure_platform_administrator = MagicMock()
    mock_ensure_platform_administrator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    app.dependency_overrides[ensure_platform_administrator] = lambda: mock_ensure_platform_administrator()

    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_gpu_device_utilization_timeseries_no_organization():
    app.dependency_overrides[get_session] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/metrics/gpu_device_utilization?start=2025-03-10T12:00:00Z&end=2025-03-11T12:00:00Z")

    assert response.status_code == status.HTTP_404_NOT_FOUND


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
async def test_get_current_utilization(_):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = OrganizationModel(
        id="0aa18e92-002c-45b7-a06e-dcdb0277974c", name="Organization 1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()

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
