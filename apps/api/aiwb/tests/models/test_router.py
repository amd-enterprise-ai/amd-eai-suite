# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for models router endpoints using FastAPI TestClient with dependency overrides."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from api_common.exceptions import DeletionConflictException, NotFoundException
from app import app  # type: ignore[attr-defined]
from app.models.schemas import ModelResponse
from tests.dependency_overrides import MINIO_OVERRIDES, SESSION_OVERRIDES, override_dependencies
from tests.factory import make_inference_model


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.list_models", autospec=True)
def test_get_models(mock_list_models: MagicMock) -> None:
    """Test GET /v1/namespaces/{namespace}/models returns 200."""
    mock_list_models.return_value = [make_inference_model()]

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/models")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert len(response_data["data"]) == 1


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.list_models", autospec=True)
def test_get_models_with_filters(mock_list_models: MagicMock) -> None:
    """Test GET /v1/namespaces/{namespace}/models with filters returns 200."""
    mock_list_models.return_value = [make_inference_model(name="Filtered Model")]

    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/models?name=Filtered%20Model")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert len(response_data["data"]) == 1
    mock_list_models.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.get_model", autospec=True)
def test_get_model(mock_get_model: MagicMock) -> None:
    """Test GET /v1/namespaces/{namespace}/models/{model_id} returns 200."""
    model_id = uuid4()
    mock_get_model.return_value = make_inference_model(id=model_id)

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/models/{model_id}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == str(model_id)


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.get_model", autospec=True)
def test_get_model_not_found(mock_get_model: MagicMock) -> None:
    """Test GET /v1/namespaces/{namespace}/models/{model_id} returns 404 when not found."""
    model_id = uuid4()
    mock_get_model.side_effect = NotFoundException(f"Model with id {model_id} not found")

    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/models/{model_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Model with id {model_id} not found" in response.json()["detail"]


@override_dependencies(MINIO_OVERRIDES)
@patch("app.models.router.delete_model", autospec=True)
def test_delete_model(mock_delete_model: MagicMock) -> None:
    """Test DELETE /v1/namespaces/{namespace}/models/{model_id} returns 204."""
    model_id = uuid4()
    mock_delete_model.return_value = None

    with TestClient(app) as client:
        response = client.delete(f"/v1/namespaces/test-namespace/models/{model_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


@override_dependencies(MINIO_OVERRIDES)
@patch("app.models.router.delete_model", autospec=True)
def test_delete_model_not_found(mock_delete_model: MagicMock) -> None:
    """Test DELETE /v1/namespaces/{namespace}/models/{model_id} returns 404 when not found."""
    model_id = uuid4()
    mock_delete_model.side_effect = NotFoundException(f"Model with ID {model_id} not found in this namespace")

    with TestClient(app) as client:
        response = client.delete(f"/v1/namespaces/test-namespace/models/{model_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@override_dependencies(MINIO_OVERRIDES)
@patch("app.models.router.delete_model", autospec=True)
def test_delete_model_conflict(mock_delete_model: MagicMock) -> None:
    """Test DELETE /v1/namespaces/{namespace}/models/{model_id} returns 409 when in use."""
    model_id = uuid4()
    mock_delete_model.side_effect = DeletionConflictException(
        "Cannot delete model that is currently being used by a workload"
    )

    with TestClient(app) as client:
        response = client.delete(f"/v1/namespaces/test-namespace/models/{model_id}")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Cannot delete model" in response.json()["detail"]


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.get_finetunable_models", autospec=True)
def test_get_finetunable_models(mock_get_finetunable: MagicMock) -> None:
    """Test GET /v1/finetunable returns 200."""
    expected_models = ["meta-llama/Llama-3.1-8B", "microsoft/DialoGPT-medium"]
    mock_get_finetunable.return_value = expected_models

    with TestClient(app) as client:
        response = client.get("/v1/finetunable")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["data"] == expected_models


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.get_finetunable_models", autospec=True)
def test_get_finetunable_models_empty(mock_get_finetunable: MagicMock) -> None:
    """Test GET /v1/finetunable returns 200 with empty list."""
    mock_get_finetunable.return_value = []

    with TestClient(app) as client:
        response = client.get("/v1/finetunable")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["data"] == []


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_finetune_model_workload", autospec=True)
def test_finetune_model(mock_run_finetune: MagicMock) -> None:
    """Test POST /v1/namespaces/{namespace}/models/{model_id}/finetune returns 202."""
    model_id = uuid4()
    dataset_id = uuid4()
    mock_run_finetune.return_value = ModelResponse.model_validate(make_inference_model())

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/models/{model_id}/finetune",
            json={
                "name": "Finetuned Model",
                "dataset_id": str(dataset_id),
                "epochs": 3,
                "learning_rate": 0.001,
                "batch_size": 8,
            },
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    mock_run_finetune.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_finetune_model_workload", autospec=True)
def test_finetune_model_with_canonical_name(mock_run_finetune: MagicMock) -> None:
    """Test POST /v1/namespaces/{namespace}/models/{canonical_name}/finetune with canonical name."""
    canonical_name = "meta-llama/Llama-3.1-8B"
    dataset_id = uuid4()
    mock_run_finetune.return_value = ModelResponse.model_validate(make_inference_model())

    with TestClient(app) as client:
        # URL encode the canonical name
        response = client.post(
            f"/v1/namespaces/test-namespace/models/{canonical_name}/finetune",
            json={
                "name": "Finetuned Model",
                "dataset_id": str(dataset_id),
                "epochs": 3,
                "learning_rate": 0.001,
                "batch_size": 8,
            },
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    mock_run_finetune.assert_called_once()


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_finetune_model_workload", autospec=True)
def test_finetune_model_with_hf_token_secret(mock_run_finetune: MagicMock) -> None:
    """Test POST finetune accepts hf_token_secret_name and passes it to the service."""
    model_id = uuid4()
    dataset_id = uuid4()
    mock_run_finetune.return_value = ModelResponse.model_validate(make_inference_model())

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/models/{model_id}/finetune",
            json={
                "name": "Finetuned Model",
                "dataset_id": str(dataset_id),
                "epochs": 3,
                "learning_rate": 0.001,
                "batch_size": 8,
                "hf_token_secret_name": "hf-token-secret",
            },
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    mock_run_finetune.assert_called_once()
    call_kwargs = mock_run_finetune.call_args[1]
    assert call_kwargs["finetuning_data"].hf_token_secret_name == "hf-token-secret"


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_model_deployment", autospec=True)
def test_deploy_model(mock_run_deployment: MagicMock) -> None:
    """Test POST /v1/namespaces/{namespace}/models/{model_id}/deploy returns 202."""
    model_id = uuid4()
    mock_run_deployment.return_value = ModelResponse.model_validate(make_inference_model())

    with TestClient(app) as client:
        response = client.post(f"/v1/namespaces/test-namespace/models/{model_id}/deploy")

    assert response.status_code == status.HTTP_202_ACCEPTED


@override_dependencies(SESSION_OVERRIDES)
@patch("app.models.router.run_model_deployment", autospec=True)
def test_deploy_model_with_specs(mock_run_deployment: MagicMock) -> None:
    """Test POST /v1/namespaces/{namespace}/models/{model_id}/deploy with custom specs."""
    model_id = uuid4()
    mock_run_deployment.return_value = ModelResponse.model_validate(make_inference_model())

    with TestClient(app) as client:
        response = client.post(
            f"/v1/namespaces/test-namespace/models/{model_id}/deploy",
            json={
                "image": "custom/image:latest",
                "gpus": 2,
                "memory_per_gpu": 16.0,
                "cpu_per_gpu": 4.0,
                "replicas": 3,
            },
        )

    assert response.status_code == status.HTTP_202_ACCEPTED
    mock_run_deployment.assert_called_once()
