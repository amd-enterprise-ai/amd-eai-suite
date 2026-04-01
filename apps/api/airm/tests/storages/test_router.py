# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app import app  # type: ignore
from app.storages.enums import StorageScope, StorageStatus, StorageType
from app.storages.schemas import Storages, StorageWithProjects
from app.utilities.exceptions import ConflictException, NotFoundException
from tests.dependency_overrides import ADMIN_OVERRIDES, override_dependencies


@override_dependencies(ADMIN_OVERRIDES)
def test_get_storage_success():
    """Test successful retrieval of storages via API."""
    # Create expected response with mock data
    expected_response = Storages(
        data=[
            StorageWithProjects(
                id=uuid4(),
                name="storage1",
                secret_id=uuid4(),
                type=StorageType.S3,
                scope=StorageScope.ORGANIZATION,
                status=StorageStatus.SYNCED,
                status_reason=None,
                project_storages=[],
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                created_by="test@example.com",
                updated_by="test@example.com",
            )
        ]
    )

    with patch("app.storages.router.get_storages_with_assigned_project_storages") as mock_service:
        mock_service.return_value = expected_response

        with TestClient(app) as client:
            response = client.get("/v1/storages")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "storage1"
    assert data["data"][0]["type"] == StorageType.S3.value
    assert data["data"][0]["status"] == StorageStatus.SYNCED.value
    mock_service.assert_called_once()


@override_dependencies(ADMIN_OVERRIDES)
def test_create_storage_success():
    """Test successful storage creation via API."""
    mock_project_id = uuid4()
    mock_secret_id = uuid4()

    storage_in = {
        "name": "my-storage",
        "secret_id": str(mock_secret_id),
        "type": StorageType.S3.value,
        "scope": StorageScope.ORGANIZATION.value,
        "project_ids": [str(mock_project_id)],
        "spec": {
            "bucket_url": "https://some-bucket-name.s3.amazonaws.com/path/",
            "access_key_name": "accessKeyName",
            "secret_key_name": "secretKeyName",
        },
    }

    # Expected response from service
    expected_storage = StorageWithProjects(
        id=uuid4(),
        name="my-storage",
        secret_id=mock_secret_id,
        type=StorageType.S3,
        scope=StorageScope.ORGANIZATION,
        status=StorageStatus.PENDING,
        status_reason=None,
        project_storages=[],
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    with patch("app.storages.router.create_storage_in_db", return_value=expected_storage) as mock_service:
        with TestClient(app) as client:
            response = client.post("/v1/storages", json=storage_in)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "my-storage"
    assert data["type"] == StorageType.S3.value
    assert data["status"] == StorageStatus.PENDING.value
    mock_service.assert_awaited_once()


@override_dependencies(ADMIN_OVERRIDES)
def test_create_storage_conflict():
    """Test creating storage with duplicate name returns conflict."""
    mock_secret_id = uuid4()

    secret_in = {
        "name": "duplicate-storage",
        "secret_id": str(mock_secret_id),
        "type": StorageType.S3.value,
        "scope": StorageScope.ORGANIZATION.value,
        "project_ids": [],
        "spec": {
            "bucket_url": "https://some-bucket-name.s3.amazonaws.com/path/",
            "access_key_name": "accessKeyName",
            "secret_key_name": "secretKeyName",
        },
    }

    with patch("app.storages.router.create_storage_in_db") as mock_service:
        mock_service.side_effect = ConflictException(
            "A storage with the name 'duplicate-storage' already exists in the organization"
        )

        with TestClient(app) as client:
            response = client.post("/v1/storages", json=secret_in)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]


@override_dependencies(ADMIN_OVERRIDES)
def test_create_storage_secret_not_found():
    """Test creating storage with the secret id not valid."""
    non_existent_secret_id = uuid4()

    secret_in = {
        "name": "not-found-storage",
        "secret_id": str(non_existent_secret_id),
        "type": StorageType.S3.value,
        "scope": StorageScope.ORGANIZATION.value,
        "project_ids": [],
        "spec": {
            "bucket_url": "https://some-bucket-name.s3.amazonaws.com/path/",
            "access_key_name": "accessKeyName",
            "secret_key_name": "secretKeyName",
        },
    }

    # Mock the service layer to raise NotFoundException
    with patch("app.storages.router.create_storage_in_db") as mock_service:
        mock_service.side_effect = NotFoundException(f"Secret with ID {non_existent_secret_id} not found")

        with TestClient(app) as client:
            response = client.post("/v1/storages", json=secret_in)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@override_dependencies(ADMIN_OVERRIDES)
def test_delete_secret_success():
    """Test successful storage deletion via API."""
    storage_id = uuid4()

    mock_storage = MagicMock()
    mock_storage.id = storage_id

    with (
        patch("app.storages.router.get_storage_by_id") as mock_get,
        patch("app.storages.router.submit_delete_storage") as mock_delete,
    ):
        mock_get.return_value = mock_storage

        with TestClient(app) as client:
            response = client.delete(f"/v1/storages/{storage_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_get.assert_called_once()
    mock_delete.assert_called_once()


@override_dependencies(ADMIN_OVERRIDES)
def test_delete_storage_not_found():
    """Test deleting non-existent storage returns 404."""
    non_existent_id = uuid4()

    with patch("app.storages.router.get_storage_by_id") as mock_get:
        mock_get.return_value = None

        with TestClient(app) as client:
            response = client.delete(f"/v1/storages/{non_existent_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@override_dependencies(ADMIN_OVERRIDES)
def test_delete_storage_conflict():
    """Test deleting storage in conflicting state returns 409."""
    storage_id = uuid4()

    mock_storage = MagicMock()
    mock_storage.id = storage_id

    with (
        patch("app.storages.router.get_storage_by_id") as mock_get,
        patch("app.storages.router.submit_delete_storage") as mock_delete,
    ):
        mock_get.return_value = mock_storage
        mock_delete.side_effect = ConflictException("Storage is in PENDING state and cannot be deleted")

        with TestClient(app) as client:
            response = client.delete(f"/v1/storages/{storage_id}")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "PENDING state" in response.json()["detail"]


@override_dependencies(ADMIN_OVERRIDES)
def test_assign_storage_success():
    """Test successful project storage assignment via API."""
    storage_id = uuid4()
    project_id = uuid4()

    mock_storage = MagicMock()
    mock_storage.id = storage_id

    with (
        patch("app.storages.router.get_storage_by_id") as mock_get,
        patch("app.storages.router.update_project_storage_assignments") as mock_update,
    ):
        mock_get.return_value = mock_storage

        with TestClient(app) as client:
            response = client.put(f"/v1/storages/{storage_id}/assign", json={"project_ids": [str(project_id)]})

    assert response.status_code == status.HTTP_200_OK
    mock_get.assert_called_once()
    mock_update.assert_called_once()


@override_dependencies(ADMIN_OVERRIDES)
def test_assign_storage_not_found():
    """Test assigning non-existent secret returns 404."""
    non_existent_id = uuid4()
    project_id = uuid4()

    with patch("app.storages.router.get_storage_by_id") as mock_get:
        mock_get.return_value = None

        with TestClient(app) as client:
            response = client.put(f"/v1/storages/{non_existent_id}/assign", json={"project_ids": [str(project_id)]})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@override_dependencies(ADMIN_OVERRIDES)
def test_assign_storage_validation_error():
    """Test assigning projects with validation error returns 422."""
    storage_id = uuid4()
    project_id = uuid4()

    mock_storage = MagicMock()
    mock_storage.id = storage_id

    with (
        patch("app.storages.router.get_storage_by_id") as mock_get,
        patch("app.storages.router.update_project_storage_assignments") as mock_update,
    ):
        mock_get.return_value = mock_storage
        mock_update.side_effect = ValueError("No changes in project assignments")

        with TestClient(app) as client:
            response = client.put(f"/v1/storages/{storage_id}/assign", json={"project_ids": [str(project_id)]})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "No changes" in response.json()["detail"]
