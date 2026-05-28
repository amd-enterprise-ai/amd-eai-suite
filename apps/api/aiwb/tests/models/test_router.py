# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for models router endpoints using FastAPI TestClient with dependency overrides."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from api_common.exceptions import DeletionConflictException, NotFoundException
from app import app  # type: ignore[attr-defined]
from app.aims.crds import AIMModelResource
from app.minio import get_minio_client
from app.models.schemas import FinetunableModelResponse, FinetuneJobResponse
from app.workloads.enums import WorkloadStatus
from tests.dependency_overrides import BASE_OVERRIDES, SESSION_OVERRIDES, override_dependencies

# Delete endpoint needs kube client + minio + a DB session (to mark workload DELETED)
DELETE_OVERRIDES = {**SESSION_OVERRIDES, get_minio_client: lambda: None}


def make_aim_model_resource(**kwargs: object) -> AIMModelResource:
    resource_name = kwargs.get("resource_name", "test-model-cr")
    return AIMModelResource.model_validate(
        {
            "metadata": {"name": resource_name, "labels": {}},
            "spec": {"image": "test-image:latest"},
            "status": {"status": "Ready", "imageMetadata": {"model": {}}},
        }
    )


def make_finetune_job_response(**kwargs: object) -> FinetuneJobResponse:
    return FinetuneJobResponse(
        workload_id=kwargs.get("workload_id", uuid4()),
        model_name=kwargs.get("model_name", "test-finetune"),
        base_model=kwargs.get("base_model", "test/base-model"),
        namespace=kwargs.get("namespace", "test-namespace"),
    )


@override_dependencies(BASE_OVERRIDES)
@patch("app.models.router.list_aim_models", new_callable=AsyncMock)
def test_get_models(mock_list_aim_models: AsyncMock) -> None:
    mock_list_aim_models.return_value = [make_aim_model_resource()]

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/aims/models")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert len(response_data["data"]) == 1


@override_dependencies(BASE_OVERRIDES)
@patch("app.models.router.list_aim_models", new_callable=AsyncMock)
def test_get_models_returns_k8s_sourced_data(mock_list_aim_models: AsyncMock) -> None:
    mock_list_aim_models.return_value = [
        make_aim_model_resource(name="Finetuned Model A", status=WorkloadStatus.COMPLETE),
        make_aim_model_resource(name="Finetuned Model B", status=WorkloadStatus.COMPLETE),
    ]

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/aims/models")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert len(response_data["data"]) == 2
    mock_list_aim_models.assert_called_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.models.router.get_aim_model", new_callable=AsyncMock)
def test_get_model(mock_get_aim_model: AsyncMock) -> None:
    resource_name = "wb-finetuning-abc123"
    mock_get_aim_model.return_value = make_aim_model_resource(resource_name=resource_name)

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/aims/models/{resource_name}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["metadata"]["name"] == resource_name


@override_dependencies(BASE_OVERRIDES)
@patch("app.models.router.get_aim_model", new_callable=AsyncMock)
def test_get_model_not_found(mock_get_aim_model: AsyncMock) -> None:
    resource_name = "nonexistent-model"
    mock_get_aim_model.side_effect = NotFoundException(f"Model {resource_name} not found")

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/aims/models/{resource_name}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Model {resource_name} not found" in response.json()["detail"]


@override_dependencies(DELETE_OVERRIDES)
@patch("app.models.router.delete_model", autospec=True)
def test_delete_model(mock_delete_model: MagicMock) -> None:
    mock_delete_model.return_value = None

    with TestClient(app) as client:
        response = client.delete("/v1/namespaces/test-namespace/aims/models/my-finetuned-model")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


@override_dependencies(DELETE_OVERRIDES)
@patch("app.models.router.delete_model", autospec=True)
def test_delete_model_force(mock_delete_model: MagicMock) -> None:
    mock_delete_model.return_value = None

    with TestClient(app) as client:
        response = client.delete("/v1/namespaces/test-namespace/aims/models/my-finetuned-model?force=true")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    call_kwargs = mock_delete_model.call_args[1]
    assert call_kwargs["force"] is True


@override_dependencies(DELETE_OVERRIDES)
@patch("app.models.router.delete_model", autospec=True)
def test_delete_model_not_found(mock_delete_model: MagicMock) -> None:
    mock_delete_model.side_effect = NotFoundException("Model my-finetuned-model not found in this namespace")

    with TestClient(app) as client:
        response = client.delete("/v1/namespaces/test-namespace/aims/models/my-finetuned-model")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@override_dependencies(DELETE_OVERRIDES)
@patch("app.models.router.delete_model", autospec=True)
def test_delete_model_conflict(mock_delete_model: MagicMock) -> None:
    mock_delete_model.side_effect = DeletionConflictException(
        "Model my-finetuned-model has 1 active deployment(s). Use force=true to delete anyway."
    )

    with TestClient(app) as client:
        response = client.delete("/v1/namespaces/test-namespace/aims/models/my-finetuned-model")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "active deployment" in response.json()["detail"]


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.get_finetunable_models", autospec=True)
def test_get_finetunable_models(mock_get_finetunable: MagicMock) -> None:
    """Test GET /v1/finetunable returns 200 with enriched model info."""
    expected_models = [
        FinetunableModelResponse(
            canonical_name="meta-llama/Llama-3.1-8B", gpu_count=1, compatible_accelerators=["74a1"]
        ),
        FinetunableModelResponse(
            canonical_name="microsoft/DialoGPT-medium", gpu_count=None, compatible_accelerators=[]
        ),
    ]
    mock_get_finetunable.return_value = expected_models

    with TestClient(app) as client:
        response = client.get("/v1/finetunable")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["canonicalName"] == "meta-llama/Llama-3.1-8B"
    assert data[0]["gpuCount"] == 1
    assert data[0]["compatibleAccelerators"] == ["74a1"]
    assert data[1]["canonicalName"] == "microsoft/DialoGPT-medium"
    assert data[1]["gpuCount"] is None
    assert data[1]["compatibleAccelerators"] == []


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.get_finetunable_models", autospec=True)
def test_get_finetunable_models_empty(mock_get_finetunable: MagicMock) -> None:
    mock_get_finetunable.return_value = []

    with TestClient(app) as client:
        response = client.get("/v1/finetunable")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == []


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_finetune_model_workload", autospec=True)
def test_finetune_model(mock_run_finetune: MagicMock) -> None:
    model_id = uuid4()
    dataset_id = uuid4()
    mock_run_finetune.return_value = make_finetune_job_response()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/models/{model_id}/finetune",
            json={
                "name": "Finetuned-Model",
                "datasetId": str(dataset_id),
                "epochs": 3,
                "learningRate": 0.001,
                "batchSize": 8,
            },
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    mock_run_finetune.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_finetune_model_workload", autospec=True)
def test_finetune_model_with_canonical_name(mock_run_finetune: MagicMock) -> None:
    canonical_name = "meta-llama/Llama-3.1-8B"
    dataset_id = uuid4()
    mock_run_finetune.return_value = make_finetune_job_response()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/models/{canonical_name}/finetune",
            json={
                "name": "Finetuned-Model",
                "datasetId": str(dataset_id),
                "epochs": 3,
                "learningRate": 0.001,
                "batchSize": 8,
            },
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    mock_run_finetune.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_finetune_model_workload", autospec=True)
def test_finetune_model_with_hf_token_secret(mock_run_finetune: MagicMock) -> None:
    model_id = uuid4()
    dataset_id = uuid4()
    mock_run_finetune.return_value = make_finetune_job_response()

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/models/{model_id}/finetune",
            json={
                "name": "Finetuned-Model",
                "datasetId": str(dataset_id),
                "epochs": 3,
                "learningRate": 0.001,
                "batchSize": 8,
                "hfTokenSecretName": "hf-token-secret",
            },
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    mock_run_finetune.assert_called_once()
    call_kwargs = mock_run_finetune.call_args[1]
    assert call_kwargs["finetuning_data"].hf_token_secret_name == "hf-token-secret"


@override_dependencies(SESSION_OVERRIDES)
def test_finetune_model_invalid_name_rejected() -> None:
    """Names with spaces or special chars are rejected before reaching the service."""
    model_id = uuid4()
    dataset_id = uuid4()

    invalid_names = ["Finetuned Model", "my model!", "name@org", ""]

    with TestClient(app) as client:
        for name in invalid_names:
            response = client.post(
                f"/v1/namespaces/test-namespace/models/{model_id}/finetune",
                json={"name": name, "datasetId": str(dataset_id)},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
                f"Expected 422 for name={name!r}, got {response.status_code}"
            )
