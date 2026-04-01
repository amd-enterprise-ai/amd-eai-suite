# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch
from uuid import uuid4

from fastapi import Response, status
from fastapi.testclient import TestClient

from api_common.exceptions import NotFoundException
from app import app  # type: ignore[attr-defined]
from app.datasets.models import DatasetType
from tests.datasets.conftest import make_dataset_response
from tests.dependency_overrides import MINIO_OVERRIDES, override_dependencies


@override_dependencies(MINIO_OVERRIDES)
def test_upload_dataset_success():
    """Test uploading a new dataset."""
    expected_response = make_dataset_response(
        name="Test Dataset",
        description="Test Description",
    )

    with patch("app.datasets.router.create_and_upload_dataset", autospec=True) as mock_service:
        mock_service.return_value = expected_response

        test_file_content = b'{"text": "test"}\n{"text": "test2"}'
        files = {"jsonl": ("test.jsonl", test_file_content, "application/jsonlines")}
        data = {
            "name": "Test Dataset",
            "description": "Test Description",
            "type": DatasetType.FINETUNING.value,
        }

        with TestClient(app) as client:
            response = client.post("/v1/namespaces/test-namespace/datasets/upload", files=files, data=data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Dataset"
    assert data["description"] == "Test Description"
    assert data["type"] == DatasetType.FINETUNING.value


@override_dependencies(MINIO_OVERRIDES)
def test_list_datasets_success():
    """Test listing datasets in a namespace."""
    expected_datasets = [
        make_dataset_response(
            name="Dataset 1", description="Description 1", path="test-namespace/datasets/dataset-1.jsonl"
        ),
        make_dataset_response(
            name="Dataset 2", description="Description 2", path="test-namespace/datasets/dataset-2.jsonl"
        ),
    ]

    with patch("app.datasets.router.list_datasets", autospec=True) as mock_service:
        mock_service.return_value = expected_datasets

        with TestClient(app) as client:
            response = client.get("/v1/namespaces/test-namespace/datasets")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "Dataset 1"
    assert data["data"][1]["name"] == "Dataset 2"


@override_dependencies(MINIO_OVERRIDES)
def test_list_datasets_with_filters():
    """Test listing datasets with type and name filters."""
    expected_datasets = [
        make_dataset_response(
            name="Filtered Dataset", description="Description", path="test-namespace/datasets/filtered-dataset.jsonl"
        )
    ]

    with patch("app.datasets.router.list_datasets", autospec=True) as mock_service:
        mock_service.return_value = expected_datasets

        with TestClient(app) as client:
            response = client.get(
                f"/v1/namespaces/test-namespace/datasets?type={DatasetType.FINETUNING.value}&name=Filtered Dataset"
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Filtered Dataset"


@override_dependencies(MINIO_OVERRIDES)
def test_get_dataset_success():
    """Test getting a single dataset by ID."""
    dataset_id = uuid4()
    expected_dataset = make_dataset_response(id=dataset_id, description="Test Description")

    with patch("app.datasets.router.get_dataset_by_id", autospec=True) as mock_service:
        mock_service.return_value = expected_dataset

        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/test-namespace/datasets/{dataset_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(dataset_id)
    assert data["name"] == "Test Dataset"


@override_dependencies(MINIO_OVERRIDES)
def test_get_dataset_not_found():
    """Test getting a non-existent dataset."""
    dataset_id = uuid4()

    with patch("app.datasets.router.get_dataset_by_id", autospec=True) as mock_service:
        mock_service.side_effect = NotFoundException(f"Dataset {dataset_id} not found")

        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/test-namespace/datasets/{dataset_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@override_dependencies(MINIO_OVERRIDES)
def test_download_dataset_success():
    """Test downloading a dataset file."""
    dataset_id = uuid4()

    mock_response = Response(
        content=b'{"text": "test"}\n',
        media_type="application/jsonlines",
        headers={"Content-Disposition": 'attachment; filename="test-dataset.jsonl"'},
    )

    with patch("app.datasets.router.download_dataset_file", autospec=True) as mock_service:
        mock_service.return_value = mock_response

        with TestClient(app) as client:
            response = client.get(f"/v1/namespaces/test-namespace/datasets/{dataset_id}/download")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/jsonlines"
    assert "test-dataset.jsonl" in response.headers.get("content-disposition", "")


@override_dependencies(MINIO_OVERRIDES)
def test_delete_dataset_success():
    """Test deleting a single dataset."""
    dataset_id = uuid4()

    with patch("app.datasets.router.delete_datasets", autospec=True) as mock_service:
        mock_service.return_value = [dataset_id]

        with TestClient(app) as client:
            response = client.delete(f"/v1/namespaces/test-namespace/datasets/{dataset_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@override_dependencies(MINIO_OVERRIDES)
def test_delete_dataset_not_found():
    """Test deleting a non-existent dataset - still returns 204."""
    dataset_id = uuid4()

    with patch("app.datasets.router.delete_datasets", autospec=True) as mock_service:
        mock_service.return_value = []

        with TestClient(app) as client:
            response = client.delete(f"/v1/namespaces/test-namespace/datasets/{dataset_id}")

    # The endpoint returns 204 even if nothing was deleted (idempotent)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@override_dependencies(MINIO_OVERRIDES)
def test_delete_datasets_batch_success():
    """Test batch deletion of datasets."""
    dataset_ids = [uuid4(), uuid4(), uuid4()]

    with patch("app.datasets.router.delete_datasets", autospec=True) as mock_service:
        mock_service.return_value = dataset_ids

        with TestClient(app) as client:
            response = client.post(
                "/v1/namespaces/test-namespace/datasets/delete", json={"ids": [str(id) for id in dataset_ids]}
            )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Response is a list of UUIDs (as strings)
    assert len(data) == 3
    assert all(str(id) in data for id in dataset_ids)


@override_dependencies(MINIO_OVERRIDES)
def test_delete_datasets_batch_partial_success():
    """Test batch deletion with some non-existent IDs raises NotFoundException."""
    existing_id = uuid4()
    non_existent_id = uuid4()

    with patch("app.datasets.router.delete_datasets", autospec=True) as mock_service:
        mock_service.return_value = [existing_id]

        with TestClient(app) as client:
            response = client.post(
                "/v1/namespaces/test-namespace/datasets/delete",
                json={"ids": [str(existing_id), str(non_existent_id)]},
            )

    # When some IDs are missing, the endpoint raises 404
    assert response.status_code == status.HTTP_404_NOT_FOUND


@override_dependencies(MINIO_OVERRIDES)
def test_list_datasets_empty():
    """Test listing datasets when namespace has none."""
    with patch("app.datasets.router.list_datasets", autospec=True) as mock_service:
        mock_service.return_value = []

        with TestClient(app) as client:
            response = client.get("/v1/namespaces/test-namespace/datasets")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 0
