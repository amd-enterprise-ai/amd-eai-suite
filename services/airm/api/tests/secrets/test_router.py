# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.secrets.enums import SecretScope, SecretStatus, SecretType
from app.secrets.schemas import Secrets, SecretWithProjects
from app.utilities.database import get_session
from app.utilities.exceptions import ConflictException
from app.utilities.security import (
    create_logged_in_user_in_system,
    ensure_platform_administrator,
    get_projects_accessible_to_user,
    get_user_email,
    get_user_organization,
    track_user_activity_from_token,
    validate_and_get_project_from_query,
)


def _apply_common_overrides(mock_organization):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_user_organization] = lambda: mock_organization
    app.dependency_overrides[ensure_platform_administrator] = lambda: None
    app.dependency_overrides[get_user_email] = lambda: "test@example.com"
    app.dependency_overrides[get_projects_accessible_to_user] = lambda: []
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: []
    app.dependency_overrides[create_logged_in_user_in_system] = lambda: None
    app.dependency_overrides[track_user_activity_from_token] = lambda: None


def test_get_secrets_success():
    """Test successful retrieval of secrets via API."""
    # Mock organization for dependencies
    mock_organization = MagicMock()
    mock_organization.id = uuid4()

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    # Create expected response with mock data
    expected_response = Secrets(
        secrets=[
            SecretWithProjects(
                id=uuid4(),
                name="secret1",
                type=SecretType.EXTERNAL,
                scope=SecretScope.ORGANIZATION,
                status=SecretStatus.SYNCED,
                status_reason=None,
                manifest="apiVersion: v1\nkind: Secret",
                project_secrets=[],
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                created_by="test@example.com",
                updated_by="test@example.com",
            )
        ]
    )

    with patch("app.secrets.router.get_secrets_with_assigned_project_secrets") as mock_service:
        mock_service.return_value = expected_response

        with TestClient(app) as client:
            response = client.get("/v1/secrets")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["secrets"]) == 1
    assert data["secrets"][0]["name"] == "secret1"
    assert data["secrets"][0]["type"] == SecretType.EXTERNAL.value
    assert data["secrets"][0]["status"] == SecretStatus.SYNCED.value
    mock_service.assert_called_once()
    _, kwargs = mock_service.call_args
    assert kwargs.get("project") is None
    assert kwargs.get("secret_type") is None
    assert kwargs.get("use_case") is None


def test_create_secret_success():
    """Test successful secret creation via API."""
    mock_project_id = uuid4()
    mock_organization = MagicMock()
    mock_organization.id = uuid4()

    secret_in = {
        "name": "my-secret",
        "type": SecretType.KUBERNETES_SECRET.value,
        "scope": SecretScope.ORGANIZATION.value,
        "project_ids": [str(mock_project_id)],
        "manifest": "apiVersion: v1",
    }

    # Expected response from service
    expected_secret = SecretWithProjects(
        id=uuid4(),
        name="my-secret",
        type=SecretType.KUBERNETES_SECRET,
        scope=SecretScope.ORGANIZATION,
        status=SecretStatus.PENDING,
        status_reason=None,
        manifest="apiVersion: v1\nkind: Secret\nmetadata:\n  name: my-secret",
        project_secrets=[],
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with patch("app.secrets.router.create_secret_in_organization") as mock_service:
        mock_service.return_value = expected_secret

        with TestClient(app) as client:
            response = client.post("/v1/secrets", json=secret_in)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "my-secret"
    assert data["type"] == SecretType.KUBERNETES_SECRET.value
    assert data["status"] == SecretStatus.PENDING.value
    mock_service.assert_called_once()


def test_create_secret_conflict():
    """Test creating secret with duplicate name returns conflict."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()

    secret_in = {
        "name": "duplicate-secret",
        "type": SecretType.KUBERNETES_SECRET.value,
        "scope": SecretScope.ORGANIZATION.value,
        "project_ids": [],
        "manifest": "apiVersion: v1",
    }

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with patch("app.secrets.router.create_secret_in_organization") as mock_service:
        mock_service.side_effect = ConflictException(
            "A secret with the name 'duplicate-secret' already exists in the organization"
        )

        with TestClient(app) as client:
            response = client.post("/v1/secrets", json=secret_in)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    "secret_type,use_case,scope,expected_message_fragment",
    [
        (SecretType.EXTERNAL, None, SecretScope.ORGANIZATION, "not found in your organization"),
        (SecretType.KUBERNETES_SECRET, "HuggingFace", SecretScope.PROJECT, "Secret with ID"),
    ],
)
def test_delete_secret_success(secret_type, use_case, scope, expected_message_fragment):
    """Test successful secret deletion via API."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    secret_id = uuid4()

    mock_secret = MagicMock()
    mock_secret.id = secret_id
    mock_secret.use_case = use_case
    mock_secret.type = secret_type
    mock_secret.scope = scope
    mock_secret.project_secrets = []

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with (
        patch("app.secrets.router.get_secret_in_organization") as mock_get,
        patch("app.secrets.router.get_storage_by_secret_id") as mock_get_storage,
        patch("app.secrets.router.submit_delete_secret") as mock_delete,
    ):
        mock_get.return_value = mock_secret
        mock_get_storage.return_value = None

        with TestClient(app) as client:
            response = client.delete(f"/v1/secrets/{secret_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_get.assert_called_once()
    mock_get_storage.assert_called_once()
    mock_delete.assert_called_once()
    # Verify the correct arguments were passed (session object will be different instance)
    args, kwargs = mock_delete.call_args
    assert args[1] == mock_secret  # second arg should be the secret
    assert args[2] == "test@example.com"  # third arg should be the user email


@pytest.mark.parametrize(
    "secret_type,use_case,scope,expected_message_fragment",
    [
        (SecretType.EXTERNAL, None, SecretScope.ORGANIZATION, "not found in your organization"),
        (SecretType.KUBERNETES_SECRET, "HuggingFace", SecretScope.PROJECT, "Secret with ID"),
    ],
)
def test_delete_secret_not_found(secret_type, use_case, scope, expected_message_fragment):
    """Test deleting non-existent secret returns 404."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    secret_id = uuid4()

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with patch("app.secrets.router.get_secret_in_organization") as mock_get:
        mock_get.return_value = None

        with TestClient(app) as client:
            response = client.delete(f"/v1/secrets/{secret_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert expected_message_fragment in response.json()["detail"]


@pytest.mark.parametrize(
    "secret_type,use_case,scope,conflict_message",
    [
        (SecretType.EXTERNAL, None, SecretScope.ORGANIZATION, "Secret is in PENDING state and cannot be deleted"),
        (
            SecretType.KUBERNETES_SECRET,
            "HuggingFace",
            SecretScope.PROJECT,
            "Secret is in PENDING state and cannot be deleted",
        ),
    ],
)
def test_delete_secret_conflict(secret_type, use_case, scope, conflict_message):
    """Test deleting secret in conflicting state returns 409."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    secret_id = uuid4()

    mock_secret = MagicMock()
    mock_secret.id = secret_id
    mock_secret.use_case = use_case
    mock_secret.type = secret_type
    mock_secret.scope = scope
    mock_secret.project_secrets = []

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with (
        patch("app.secrets.router.get_secret_in_organization") as mock_get,
        patch("app.secrets.router.get_storage_by_secret_id") as mock_get_storage,
        patch("app.secrets.router.submit_delete_secret") as mock_delete,
    ):
        mock_get.return_value = mock_secret
        mock_get_storage.return_value = None
        mock_delete.side_effect = ConflictException(conflict_message)

        with TestClient(app) as client:
            response = client.delete(f"/v1/secrets/{secret_id}")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "PENDING state" in response.json()["detail"]


def test_delete_secret_storage_found_raises_validation():
    """Test deleting secret assigned to storage returns validation exception."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    secret_id = uuid4()

    mock_secret = MagicMock()
    mock_secret.id = secret_id
    mock_secret.name = "secret-1"

    mock_storage = MagicMock()
    mock_storage.id = uuid4()
    mock_storage.name = "linked-storage"
    mock_storage.secret_id = secret_id

    # Mock dependencies for TestClient
    app.dependency_overrides[get_session] = lambda: AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_user_organization] = lambda: mock_organization
    app.dependency_overrides[ensure_platform_administrator] = lambda: None
    app.dependency_overrides[get_user_email] = lambda: "test@example.com"

    with (
        patch("app.secrets.router.get_secret_in_organization") as mock_get,
        patch("app.secrets.router.get_storage_by_secret_id") as mock_get_storage,
        patch("app.secrets.router.submit_delete_secret") as mock_delete,
    ):
        mock_get.return_value = mock_secret
        mock_get_storage.return_value = mock_storage

        with TestClient(app) as client:
            response = client.delete(f"/v1/secrets/{secret_id}")

    mock_get.assert_called_once()
    mock_get_storage.assert_called_once()
    mock_delete.assert_not_awaited()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        f"Cannot delete secret '{mock_secret.name}' because it is currently linked to storage '{mock_storage.name}' (ID: {mock_storage.id})."
        in response.json()["detail"]
    )


def test_assign_secret_success():
    """Test successful secret project assignment via API."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    secret_id = uuid4()
    project_id = uuid4()

    mock_secret = MagicMock()
    mock_secret.id = secret_id
    mock_secret.type = SecretType.KUBERNETES_SECRET
    mock_secret.project_secrets = []
    mock_secret.project_secrets = []

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with (
        patch("app.secrets.router.get_secret_in_organization") as mock_get,
        patch("app.secrets.router.update_project_secret_assignments") as mock_update,
    ):
        mock_get.return_value = mock_secret

        with TestClient(app) as client:
            response = client.put(f"/v1/secrets/{secret_id}/assign", json={"project_ids": [str(project_id)]})

    assert response.status_code == status.HTTP_200_OK
    mock_get.assert_called_once()
    mock_update.assert_called_once()


def test_assign_secret_not_found():
    """Test assigning non-existent secret returns 404."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    non_existent_id = uuid4()
    project_id = uuid4()

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with patch("app.secrets.router.get_secret_in_organization") as mock_get:
        mock_get.return_value = None

        with TestClient(app) as client:
            response = client.put(f"/v1/secrets/{non_existent_id}/assign", json={"project_ids": [str(project_id)]})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found in your organization" in response.json()["detail"]


def test_assign_secret_validation_error():
    """Test assigning projects with validation error returns 422."""
    mock_organization = MagicMock()
    mock_organization.id = uuid4()
    secret_id = uuid4()
    project_id = uuid4()

    mock_secret = MagicMock()
    mock_secret.id = secret_id
    mock_secret.type = SecretType.KUBERNETES_SECRET

    # Mock dependencies for TestClient
    _apply_common_overrides(mock_organization)

    with (
        patch("app.secrets.router.get_secret_in_organization") as mock_get,
        patch("app.secrets.router.update_project_secret_assignments") as mock_update,
    ):
        mock_get.return_value = mock_secret
        mock_update.side_effect = ValueError("No changes in project assignments")

        with TestClient(app) as client:
            response = client.put(f"/v1/secrets/{secret_id}/assign", json={"project_ids": [str(project_id)]})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "No changes" in response.json()["detail"]
