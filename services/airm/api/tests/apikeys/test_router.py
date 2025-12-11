# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.apikeys.cluster_auth_client import get_cluster_auth_client
from app.apikeys.schemas import ApiKeyDetails, ApiKeyResponse, ApiKeyWithFullKey, GroupResponse
from app.utilities.database import get_session
from app.utilities.security import (
    create_logged_in_user_in_system,
    get_user_email,
    get_user_organization,
    track_user_activity_from_token,
    validate_and_get_project_from_query,
)


def _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_user_organization] = lambda: mock_organization
    app.dependency_overrides[get_user_email] = lambda: "test@example.com"
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: mock_project
    app.dependency_overrides[create_logged_in_user_in_system] = lambda: None
    app.dependency_overrides[track_user_activity_from_token] = lambda: None
    app.dependency_overrides[get_cluster_auth_client] = lambda: mock_cluster_auth_client


def test_get_api_keys_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    expected_keys = [
        ApiKeyResponse(
            id=uuid4(),
            name="Production Key",
            truncated_key="amd_aim_api_key_••••••••1234",
            project_id=mock_project.id,
            expires_at=None,
            renewable=True,
            num_uses=0,
            ttl="1h",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            created_by="test@example.com",
            updated_by="test@example.com",
        )
    ]

    with patch("app.apikeys.router.list_api_keys_for_project") as mock_service:
        mock_service.return_value = expected_keys

        with TestClient(app) as client:
            response = client.get(f"/v1/api-keys?project_id={mock_project.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Production Key"
    assert data["data"][0]["truncated_key"] == "amd_aim_api_key_••••••••1234"


def test_create_api_key_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    api_key_id = uuid4()
    expected_response = ApiKeyWithFullKey(
        id=api_key_id,
        name="New Key",
        truncated_key="amd_aim_api_key_••••••••5678",
        project_id=mock_project.id,
        expires_at=None,
        renewable=True,
        num_uses=0,
        ttl="24h",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
        full_key="amd_aim_api_key_7a3f9b2e1d4c8a6f5e9b2d1c3a7f5678",
    )

    with patch("app.apikeys.router.create_api_key_with_cluster_auth") as mock_service:
        mock_service.return_value = expected_response

        with TestClient(app) as client:
            response = client.post(
                f"/v1/api-keys?project_id={mock_project.id}",
                json={
                    "name": "New Key",
                    "ttl": "24h",
                    "renewable": True,
                    "num_uses": 0,
                    "meta": {},
                },
            )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "New Key"
    assert data["full_key"] == "amd_aim_api_key_7a3f9b2e1d4c8a6f5e9b2d1c3a7f5678"
    assert data["truncated_key"] == "amd_aim_api_key_••••••••5678"


def test_get_api_key_details_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()
    api_key_id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    expected_details = ApiKeyDetails(
        id=api_key_id,
        name="Detailed Key",
        truncated_key="amd_aim_api_key_••••••••9999",
        project_id=mock_project.id,
        expires_at=None,
        renewable=True,
        num_uses=0,
        ttl="1h",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
        groups=["group-1", "group-2"],
        entity_id="entity-123",
        meta={"environment": "production"},
    )

    with patch("app.apikeys.router.get_api_key_details_from_cluster_auth") as mock_service:
        mock_service.return_value = expected_details

        with TestClient(app) as client:
            response = client.get(f"/v1/api-keys/{api_key_id}?project_id={mock_project.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Detailed Key"
    assert len(data["groups"]) == 2
    assert data["entity_id"] == "entity-123"
    assert data["meta"]["environment"] == "production"


def test_delete_api_key_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()
    api_key_id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    with patch("app.apikeys.router.delete_api_key_from_cluster_auth") as mock_service:
        mock_service.return_value = None

        with TestClient(app) as client:
            response = client.delete(f"/v1/api-keys/{api_key_id}?project_id={mock_project.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_renew_api_key_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()
    api_key_id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    with patch("app.apikeys.router.renew_api_key_in_cluster_auth") as mock_service:
        mock_service.return_value = {"lease_duration": 3600}

        with TestClient(app) as client:
            response = client.post(f"/v1/api-keys/{api_key_id}/renew?project_id={mock_project.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["lease_duration"] == 3600


def test_bind_api_key_to_group_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()
    api_key_id = uuid4()
    group_id = "test-group-123"

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    with patch("app.apikeys.router.bind_api_key_to_group_in_cluster_auth") as mock_service:
        mock_service.return_value = {"groups": [group_id]}

        with TestClient(app) as client:
            response = client.post(
                f"/v1/api-keys/{api_key_id}/bind-group?project_id={mock_project.id}",
                json={"group_id": group_id},
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert group_id in data["groups"]


def test_unbind_api_key_from_group_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()
    api_key_id = uuid4()
    group_id = "test-group-123"

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    with patch("app.apikeys.router.unbind_api_key_from_group_in_cluster_auth") as mock_service:
        mock_service.return_value = {"groups": []}

        with TestClient(app) as client:
            response = client.post(
                f"/v1/api-keys/{api_key_id}/unbind-group?project_id={mock_project.id}",
                json={"group_id": group_id},
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["groups"]) == 0


def test_create_group_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    expected_group = GroupResponse(id="group-123", name="Test Group")

    with patch("app.apikeys.router.create_group_in_cluster_auth") as mock_service:
        mock_service.return_value = expected_group

        with TestClient(app) as client:
            response = client.post(
                f"/v1/api-keys/groups?project_id={mock_project.id}",
                json={"name": "Test Group", "id": "group-123"},
            )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == "group-123"
    assert data["name"] == "Test Group"


def test_create_group_auto_generated(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    expected_group = GroupResponse(id="auto-generated-uuid", name="group_abc123")

    with patch("app.apikeys.router.create_group_in_cluster_auth") as mock_service:
        mock_service.return_value = expected_group

        with TestClient(app) as client:
            response = client.post(
                f"/v1/api-keys/groups?project_id={mock_project.id}",
                json={"name": "group_abc123"},
            )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == "auto-generated-uuid"
    assert data["name"] == "group_abc123"


def test_delete_group_success(mock_cluster_auth_client):
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()
    group_id = "test-group-456"

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    with patch("app.apikeys.router.delete_group_from_cluster_auth") as mock_service:
        mock_service.return_value = None

        with TestClient(app) as client:
            response = client.delete(f"/v1/api-keys/groups/{group_id}?project_id={mock_project.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_update_api_key_bindings_success(mock_cluster_auth_client):
    """Test updating API key bindings via PATCH endpoint"""
    from app.apikeys.schemas import ApiKeyDetails

    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    mock_project = MagicMock()
    mock_project.id = uuid4()
    api_key_id = uuid4()

    _apply_common_overrides(mock_organization, mock_project, mock_cluster_auth_client)

    mock_updated_key = ApiKeyDetails(
        id=api_key_id,
        name="Updated Key",
        truncated_key="••••••••abcd",
        project_id=mock_project.id,
        renewable=True,
        num_uses=0,
        ttl="1h",
        expires_at=None,
        groups=["aim-group-1", "aim-group-2"],
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T01:00:00Z",
        created_by="user@example.com",
        updated_by="user@example.com",
    )

    with patch("app.apikeys.router.update_api_key_bindings_with_cluster_auth") as mock_service:
        mock_service.return_value = mock_updated_key

        aim_id_1 = uuid4()
        aim_id_2 = uuid4()

        with TestClient(app) as client:
            response = client.patch(
                f"/v1/api-keys/{api_key_id}?project_id={mock_project.id}",
                json={"aim_ids": [str(aim_id_1), str(aim_id_2)]},
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(api_key_id)
    assert len(data["groups"]) == 2
    assert "aim-group-1" in data["groups"]
    assert "aim-group-2" in data["groups"]
