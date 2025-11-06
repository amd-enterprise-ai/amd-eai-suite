# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Response, status

from airm.messaging.schemas import QuotaStatus
from app import app  # type: ignore
from app.datasets.models import DatasetType
from app.datasets.schemas import DatasetCreate, DatasetEdit, DatasetResponse
from app.projects.models import Project
from app.quotas.models import Quota
from app.utilities.database import get_session
from app.utilities.exceptions import NotFoundException
from app.utilities.minio import MinioClient, get_minio_client
from app.utilities.security import (
    auth_token_claimset,
    get_user,
    get_user_organization,
    validate_and_get_project_from_query,
)

from ..conftest import get_test_client


@pytest.fixture(autouse=True)
def setup_app_depends(mock_claimset, db_session, project):
    """Set up common dependency overrides for dataset tests.

    This fixture configures the common dependency overrides needed for dataset tests
    and cleans them up after the test is complete.
    """
    # Set up common dependency overrides
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: MagicMock(spec_set=Project)
    app.dependency_overrides[get_user] = lambda: "test@example.com"
    app.dependency_overrides[get_user_organization] = lambda: MagicMock(spec_set=["id"], id=uuid4())
    app.dependency_overrides[get_minio_client] = lambda: MagicMock(spec=MinioClient)

    yield

    # Clean up after the test
    app.dependency_overrides.clear()


@pytest.fixture
def cluster_id():
    return uuid4()


@pytest.fixture
def project(cluster_id):
    project_id = uuid4()
    return Project(
        id=project_id,
        name="Test Project",
        cluster_id=cluster_id,
        organization_id=uuid4(),
        quota=Quota(
            cluster_id=cluster_id,
            project_id=project_id,
            gpu_count=1,
            cpu_milli_cores=1000,
            memory_bytes=1000,
            ephemeral_storage_bytes=1000,
            status=QuotaStatus.PENDING,
            id=uuid4(),
        ),
    )


@pytest.fixture
def dataset_id():
    return uuid4()


@pytest.fixture
def dataset_response():
    return DatasetResponse(
        id=uuid4(),
        name="Test Dataset",
        description="Test Description",
        path="s3://bucket/datasets/test",
        type=DatasetType.FINETUNING,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )


@pytest.fixture
def dataset_create():
    return DatasetCreate(
        name="Test Dataset",
        description="Test Description",
        path="s3://bucket/datasets/test",
        type=DatasetType.FINETUNING,
    )


@pytest.fixture
def dataset_edit():
    return DatasetEdit(
        name="Updated Dataset",
        description="Updated Description",
        type=DatasetType.FINETUNING,
    )


@patch("app.datasets.router.insert_dataset")
def test_create_dataset(
    mock_insert_dataset,
    cluster_id,
    project_id,
    dataset_response,
    dataset_create,
):
    mock_insert_dataset.return_value = dataset_response

    with get_test_client() as client:
        response = client.post(
            f"/v1/datasets?project_id={project_id}",
            json=dataset_create.model_dump(),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == dataset_response.name
        assert response.json()["description"] == dataset_response.description
        assert response.json()["path"] == dataset_response.path
        assert response.json()["type"] == dataset_response.type


@patch("app.datasets.router.create_and_upload_dataset")
@patch("app.datasets.router.ensure_cluster_healthy")
def test_upload_dataset(
    mock_ensure_healthy,
    mock_upload_dataset,
    project_id,
    dataset_response,
):
    mock_upload_dataset.return_value = dataset_response
    mock_ensure_healthy.return_value = None

    # Create a test file
    test_file_content = b'{"text": "test"}\n{"text": "test2"}'
    files = {"jsonl": ("test.jsonl", test_file_content, "application/jsonlines")}
    data = {
        "name": "Test Dataset",
        "description": "Test Description",
        "type": DatasetType.FINETUNING.value,
    }

    with get_test_client() as client:
        response = client.post(
            f"/v1/datasets/upload?project_id={project_id}",
            files=files,
            data=data,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == dataset_response.name
        assert response.json()["description"] == dataset_response.description
        assert response.json()["path"] == dataset_response.path
        assert response.json()["type"] == dataset_response.type


@patch("app.datasets.router.list_datasets")
def test_get_datasets(mock_list_datasets, project_id, dataset_response):
    mock_list_datasets.return_value = [dataset_response]

    with get_test_client() as client:
        response = client.get(f"/v1/datasets?project_id={project_id}")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == dataset_response.name
        assert response.json()[0]["description"] == dataset_response.description
        assert response.json()[0]["path"] == dataset_response.path
        assert response.json()[0]["type"] == dataset_response.type


@patch("app.datasets.router.list_datasets")
def test_get_datasets_with_filters(mock_list_datasets, project_id, dataset_response):
    mock_list_datasets.return_value = [dataset_response]

    with get_test_client() as client:
        response = client.get(
            f"/v1/datasets?project_id={project_id}&type={DatasetType.FINETUNING.value}&name=Test%20Dataset"
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == dataset_response.name
        assert response.json()[0]["description"] == dataset_response.description
        assert response.json()[0]["path"] == dataset_response.path
        assert response.json()[0]["type"] == dataset_response.type


@patch("app.datasets.router.get_dataset_by_id")
def test_get_dataset(
    mock_get_dataset_by_id,
    project_id,
    dataset_id,
    dataset_response,
):
    mock_get_dataset_by_id.return_value = dataset_response

    with get_test_client() as client:
        response = client.get(f"/v1/datasets/{dataset_id}?project_id={project_id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == dataset_response.name
        assert response.json()["description"] == dataset_response.description
        assert response.json()["path"] == dataset_response.path
        assert response.json()["type"] == dataset_response.type


@patch("app.datasets.router.get_dataset_by_id")
def test_get_dataset_not_found(mock_get_dataset_by_id, project_id, dataset_id):
    mock_get_dataset_by_id.side_effect = NotFoundException("Dataset not found")

    with get_test_client() as client:
        response = client.get(f"/v1/datasets/{dataset_id}?project_id={project_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


@patch("app.datasets.router.update_dataset_by_id")
def test_modify_dataset(
    mock_update_dataset_by_id,
    project_id,
    dataset_id,
    dataset_response,
    dataset_edit,
):
    mock_update_dataset_by_id.return_value = dataset_response

    with get_test_client() as client:
        response = client.put(
            f"/v1/datasets/{dataset_id}?project_id={project_id}",
            json=dataset_edit.model_dump(exclude_unset=True),
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == dataset_response.name
        assert response.json()["description"] == dataset_response.description
        assert response.json()["path"] == dataset_response.path
        assert response.json()["type"] == dataset_response.type


@patch("app.datasets.router.update_dataset_by_id", side_effect=NotFoundException("Dataset not found"))
def test_modify_dataset_not_found(
    project_id,
    dataset_id,
    dataset_edit,
):
    with get_test_client() as client:
        response = client.put(
            f"/v1/datasets/{dataset_id}?project_id={project_id}",
            json=dataset_edit.model_dump(exclude_unset=True),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


@patch("app.datasets.router.download_dataset_file")
@patch("app.datasets.router.ensure_cluster_healthy")
def test_download_dataset(
    mock_ensure_healthy,
    mock_download_file,
    project_id,
    dataset_id,
):
    mock_response = Response(
        content=b'{"text": "test"}',
        media_type="application/jsonlines",
        headers={
            "Content-Disposition": 'attachment; filename="test.jsonl"',
            "Content-Type": "application/jsonl; charset=utf-8",
        },
    )
    mock_download_file.return_value = mock_response
    mock_ensure_healthy.return_value = None

    with get_test_client() as client:
        response = client.get(f"/v1/datasets/{dataset_id}/download?project_id={project_id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Content-Type"] == "application/jsonl; charset=utf-8"
        assert response.headers["Content-Disposition"] == 'attachment; filename="test.jsonl"'
        assert response.content == b'{"text": "test"}'


@patch("app.datasets.router.delete_datasets")
@patch("app.datasets.router.ensure_cluster_healthy")
def test_delete_dataset(
    mock_ensure_healthy,
    mock_delete_dataset_service,
    project_id,
    dataset_id,
):
    mock_delete_dataset_service.return_value = None
    mock_ensure_healthy.return_value = None

    with get_test_client() as client:
        response = client.delete(f"/v1/datasets/{dataset_id}?project_id={project_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""


@patch("app.datasets.router.delete_datasets", side_effect=NotFoundException("Dataset not found"))
@patch("app.datasets.router.ensure_cluster_healthy")
def test_delete_dataset_not_found(
    mock_ensure_healthy,
    project_id,
    dataset_id,
):
    mock_ensure_healthy.return_value = None

    with get_test_client() as client:
        response = client.delete(f"/v1/datasets/{dataset_id}?project_id={project_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


@patch("app.datasets.router.delete_datasets")
@patch("app.datasets.router.ensure_cluster_healthy")
def test_batch_delete_datasets(
    mock_ensure_healthy,
    mock_delete_datasets,
    project_id,
):
    dataset_ids = [uuid4(), uuid4()]
    mock_delete_datasets.return_value = dataset_ids
    mock_ensure_healthy.return_value = None

    with get_test_client() as client:
        request_data = {"ids": [str(id) for id in dataset_ids]}
        response = client.post(f"/v1/datasets/delete?project_id={project_id}", json=request_data)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""


@patch("app.datasets.router.delete_datasets", return_value=[])
@patch("app.datasets.router.ensure_cluster_healthy")
def test_batch_delete_datasets_not_found(
    mock_ensure_healthy,
    project_id,
):
    dataset_ids = [uuid4(), uuid4()]
    mock_ensure_healthy.return_value = None

    with get_test_client() as client:
        request_data = {"ids": [str(id) for id in dataset_ids]}
        response = client.post(f"/v1/datasets/delete?project_id={project_id}", json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
