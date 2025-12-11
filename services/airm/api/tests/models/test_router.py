# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.models.router import finetune_model
from app.models.schemas import FinetuneCreate, ModelDeployRequest, ModelEdit, ModelResponse
from app.utilities.database import get_session
from app.utilities.exceptions import DeletionConflictException, NotFoundException
from app.utilities.minio import MinioClient, get_minio_client
from app.utilities.security import (
    BearerToken,
    auth_token_claimset,
    get_user,
    get_user_organization,
    validate_and_get_project_from_query,
)
from app.workloads.enums import WorkloadType
from tests import factory

from ..conftest import get_test_client


def setup_test_dependencies(env, db_session, mock_claimset):
    """Set up common test dependencies."""
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: env.project
    app.dependency_overrides[get_user] = lambda: env.creator
    app.dependency_overrides[get_user_organization] = lambda: MagicMock(id=uuid4())
    app.dependency_overrides[BearerToken] = lambda: "test-token"
    app.dependency_overrides[get_minio_client] = lambda: MagicMock(spec=MinioClient)


@patch("app.models.router.list_models")
@patch("app.models.router.update_onboarding_statuses")
async def test_get_models(mock_update_statuses, mock_list_models, db_session: AsyncSession, mock_claimset):
    """Test list models endpoint returns 200."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    model_response = ModelResponse.model_validate(env.model)
    mock_list_models.return_value = [model_response]
    mock_update_statuses.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.get(f"/v1/models?project={env.project.id}")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert response_data["data"][0]["name"] == model_response.name


@patch("app.models.router.list_models")
@patch("app.models.router.update_onboarding_statuses")
async def test_get_models_with_filters(mock_update_statuses, mock_list_models, db_session: AsyncSession, mock_claimset):
    """Test list models with filters endpoint returns 200."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    model_response = ModelResponse.model_validate(env.model)
    mock_list_models.return_value = [model_response]
    mock_update_statuses.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.get(f"/v1/models?project={env.project.id}&name=Test%20Model")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "data" in response_data
        assert len(response_data["data"]) == 1
        assert response_data["data"][0]["name"] == model_response.name
        mock_list_models.assert_called_once()


@patch("app.models.router.get_model")
@patch("app.models.router.update_onboarding_statuses")
async def test_get_model(mock_update_statuses, mock_get_model, db_session: AsyncSession, mock_claimset):
    """Test get model by ID endpoint returns 200."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    model_response = ModelResponse.model_validate(env.model)
    mock_get_model.return_value = model_response
    mock_update_statuses.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.get(f"/v1/models/{env.model.id}?project={env.project.id}")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["name"] == model_response.name


@patch("app.models.router.get_model")
@patch("app.models.router.update_onboarding_statuses")
async def test_get_model_not_found(mock_update_statuses, mock_get_model, db_session: AsyncSession, mock_claimset):
    """Test get model by ID endpoint returns 404 when model not found."""
    env = await factory.create_basic_test_environment(db_session)
    model_id = uuid4()
    mock_get_model.side_effect = NotFoundException(f"Model with id {model_id} not found")
    mock_update_statuses.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.get(f"/v1/models/{model_id}?project={env.project.id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert f"Model with id {model_id} not found" in response.json()["detail"]


@patch("app.models.router.update_model_by_id", autospec=True)
@patch("app.models.router.update_onboarding_statuses")
async def test_modify_model(mock_update_statuses, mock_update_model_by_id, db_session: AsyncSession, mock_claimset):
    """Test modify model endpoint returns 200."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    model_response = ModelResponse.model_validate(env.model)
    mock_update_model_by_id.return_value = env.model
    mock_update_statuses.return_value = None

    model_edit = ModelEdit(name="Updated Model")

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.put(
            f"/v1/models/{env.model.id}?project={env.project.id}",
            json=model_edit.model_dump(),
        )

        assert response.status_code == status.HTTP_200_OK


@patch("app.models.router.update_model_by_id", side_effect=NotFoundException("Model not found"))
@patch("app.models.router.update_onboarding_statuses")
async def test_modify_model_not_found(
    mock_update_statuses, mock_update_model_by_id, db_session: AsyncSession, mock_claimset
):
    """Test modify model endpoint returns 404 when model not found."""
    env = await factory.create_basic_test_environment(db_session)
    model_id = uuid4()
    model_edit = ModelEdit(name="Updated Model")
    mock_update_statuses.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.put(
            f"/v1/models/{model_id}?project={env.project.id}",
            json=model_edit.model_dump(),
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Model not found" in response.json()["detail"]
    mock_update_model_by_id.assert_called_once()


@patch("app.models.router.ensure_cluster_healthy", autospec=True)
@patch("app.models.router.get_minio_client", autospec=True)
@patch("app.models.router.delete_model", autospec=True)
async def test_delete_model(
    mock_delete_model, mock_get_minio_client, mock_ensure_healthy, db_session: AsyncSession, mock_claimset
):
    """Test delete model endpoint returns 204."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    mock_delete_model.return_value = None  # Successfully deleted
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.delete(f"/v1/models/{env.model.id}?project={env.project.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""


@patch("app.models.router.get_minio_client", autospec=True)
@patch(
    "app.models.router.delete_model", side_effect=NotFoundException("Model with id MODEL_ID not found in this project")
)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_delete_model_not_found(
    mock_ensure_healthy, mock_delete_model, mock_get_minio_client, db_session: AsyncSession, mock_claimset
):
    """Test delete model endpoint returns 404 when model not found."""
    env = await factory.create_basic_test_environment(db_session)
    model_id = uuid4()
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.delete(f"/v1/models/{model_id}?project={env.project.id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Model with id MODEL_ID not found in this project" in response.json()["detail"]


@patch("app.models.router.get_minio_client", autospec=True)
@patch("app.models.router.delete_models", autospec=True)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_batch_delete_models(
    mock_ensure_healthy, mock_delete_models, mock_get_minio_client, db_session: AsyncSession, mock_claimset
):
    """Test batch delete models endpoint returns 200."""
    env = await factory.create_basic_test_environment(db_session)
    model_ids = [uuid4(), uuid4()]
    mock_delete_models.return_value = model_ids  # Return the IDs as if they were successfully deleted
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        request_data = {"ids": [str(id) for id in model_ids]}
        response = client.post(f"/v1/models/delete?project={env.project.id}", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        # Should return the list of deleted IDs
        response_data = response.json()
        assert len(response_data) == 2


@patch("app.models.router.get_minio_client", autospec=True)
@patch("app.models.router.delete_models", side_effect=NotFoundException("Models not found"))
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_batch_delete_models_not_found(
    mock_ensure_healthy, mock_delete_models, mock_get_minio_client, db_session: AsyncSession, mock_claimset
):
    """Test batch delete models endpoint returns 404 when models not found."""
    env = await factory.create_basic_test_environment(db_session)
    model_ids = [uuid4(), uuid4()]
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        request_data = {"ids": [str(id) for id in model_ids]}
        response = client.post(f"/v1/models/delete?project={env.project.id}", json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Models not found" in response.json()["detail"]


@patch(
    "app.models.router.delete_model",
    side_effect=DeletionConflictException("Cannot delete model that is in use by a managed workload"),
)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
@patch("app.models.router.get_minio_client", autospec=True)
async def test_delete_deployed_model(
    mock_get_minio_client, mock_ensure_healthy, mock_delete_model, db_session: AsyncSession, mock_claimset
):
    """Test delete deployed model endpoint returns 409."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.delete(f"/v1/models/{env.model.id}?project={env.project.id}")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Cannot delete model that is in use by a managed workload" in response.json()["detail"]


@patch("app.models.router.ensure_cluster_healthy", autospec=True)
@patch("app.models.router.get_minio_client", autospec=True)
@patch("app.models.router.delete_models", autospec=True)
async def test_batch_delete_models_with_conflict_errors(
    mock_delete_models, mock_get_minio_client, mock_ensure_healthy, db_session: AsyncSession, mock_claimset
):
    """Test batch deletion where some models have conflicts and some succeed."""
    env = await factory.create_basic_test_environment(db_session)
    model_ids = [uuid4(), uuid4()]
    mock_ensure_healthy.return_value = None

    # Mock to simulate ExceptionGroup with not found errors
    not_found_errors = [
        NotFoundException(f"Model with ID {model_id} not found in this project") for model_id in model_ids
    ]
    mock_delete_models.side_effect = ExceptionGroup("Some models could not be deleted", not_found_errors)

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        request_data = {"ids": [str(id) for id in model_ids]}
        response = client.post(f"/v1/models/delete?project={env.project.id}", json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
        mock_delete_models.assert_called_once()


@patch("app.models.router.ensure_cluster_healthy", autospec=True)
@patch("app.models.router.get_minio_client", autospec=True)
@patch("app.models.router.delete_models", autospec=True)
async def test_batch_delete_models_with_mixed_errors(
    mock_delete_models, mock_get_minio_client, mock_ensure_healthy, db_session: AsyncSession, mock_claimset
):
    """Test batch deletion with mixed error types (not found and conflict errors)."""
    env = await factory.create_basic_test_environment(db_session)
    model_ids = [uuid4(), uuid4(), uuid4()]
    mock_ensure_healthy.return_value = None

    # Mock to simulate ExceptionGroup with mixed errors
    mixed_errors = [
        NotFoundException(f"Model with ID {model_ids[0]} not found in this project"),
        DeletionConflictException("Cannot delete model that is in use by a managed workload"),
    ]
    mock_delete_models.side_effect = ExceptionGroup("Some models could not be deleted", mixed_errors)

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        request_data = {"ids": [str(id) for id in model_ids]}
        response = client.post(f"/v1/models/delete?project={env.project.id}", json=request_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_detail = response.json()["detail"]
        assert "Some models could not be deleted" in response_detail
        assert "not found" in response_detail
        assert "managed workload" in response_detail
        mock_delete_models.assert_called_once()


@patch("app.models.router.run_finetune_model_workload", autospec=True)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
@pytest.mark.parametrize("model_id", [uuid4()])
async def test_finetune_model(
    mock_ensure_healthy, mock_run_finetune_workload, db_session: AsyncSession, mock_claimset, model_id
):
    """Test finetune model endpoint returns 202."""
    env = await factory.create_full_test_environment(db_session, with_model=True, with_dataset=True)
    workload = await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=await factory.create_chart(db_session),
        workload_type=WorkloadType.FINE_TUNING,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        name="test-finetune",
        display_name="Test Finetune Workload",
    )
    mock_run_finetune_workload.return_value = workload
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        finetune_data = {
            "name": "Finetuned Model",
            "dataset_id": str(env.dataset.id),
            "epochs": 1,
            "learning_rate": 1.41421,
            "batch_size": 2,
        }
        response = client.post(f"/v1/models/{model_id}/finetune?project={env.project.id}", json=finetune_data)

        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["id"] == str(workload.id)
        assert response_data["type"] == WorkloadType.FINE_TUNING.value

        # Verify the service was called with the correct arguments
        mock_run_finetune_workload.assert_called_once()
        call_args = mock_run_finetune_workload.call_args
        # The router should convert the UUID string to a UUID object
        assert call_args.kwargs["model_id"] == model_id  # model_id should be passed as UUID object


@patch("app.models.router.run_model_deployment", autospec=True)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_deploy_model(mock_ensure_healthy, mock_run_deployment, db_session: AsyncSession, mock_claimset):
    """Test deploy model endpoint returns 202."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    workload = await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=await factory.create_chart(db_session),
        workload_type=WorkloadType.INFERENCE,
        model_id=env.model.id,
        name="test-inference",
        display_name="Test Inference Workload",
    )
    mock_run_deployment.return_value = workload
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(f"/v1/models/{env.model.id}/deploy?project={env.project.id}")

        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["id"] == str(workload.id)
        assert response_data["type"] == WorkloadType.INFERENCE.value


@patch("app.models.router.run_model_deployment", autospec=True)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_deploy_model_with_replicas(
    mock_ensure_healthy, mock_run_deployment, db_session: AsyncSession, mock_claimset
):
    """Test deploy model with replicas endpoint returns 202."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    workload = await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=await factory.create_chart(db_session),
        workload_type=WorkloadType.INFERENCE,
        model_id=env.model.id,
        name="test-inference",
        display_name="Test Inference Workload",
    )
    mock_run_deployment.return_value = workload
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(f"/v1/models/{env.model.id}/deploy?project={env.project.id}", json={"replicas": 3})

        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["id"] == str(workload.id)
        assert response_data["type"] == WorkloadType.INFERENCE.value

        # Verify the service was called with replicas parameter
        mock_run_deployment.assert_called_once()
        call_args = mock_run_deployment.call_args
        assert call_args.kwargs["request"].replicas == 3


@patch("app.models.router.run_model_deployment", autospec=True)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_deploy_model_with_different_specs(
    mock_ensure_healthy, mock_run_deployment, db_session: AsyncSession, mock_claimset
):
    """Test deploy model with different specs endpoint returns 202."""
    env = await factory.create_full_test_environment(db_session, with_model=True)
    workload = await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=await factory.create_chart(db_session),
        workload_type=WorkloadType.INFERENCE,
        model_id=env.model.id,
        name="test-inference",
        display_name="Test Inference Workload",
    )
    mock_run_deployment.return_value = workload
    mock_ensure_healthy.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.post(
            f"/v1/models/{env.model.id}/deploy?project={env.project.id}",
            json={
                "image": "custom/ml-image:latest",
                "gpus": 2,
                "memory_per_gpu": 16.0,
                "cpu_per_gpu": 4.0,
                "replicas": 3,
            },
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["id"] == str(workload.id)
        assert response_data["type"] == WorkloadType.INFERENCE.value

        # Verify the service was called with replicas parameter
        mock_run_deployment.assert_called_once()
        call_args = mock_run_deployment.call_args
        model_deploy_request = ModelDeployRequest(
            image="custom/ml-image:latest",
            gpus=2,
            memory_per_gpu=16.0,
            cpu_per_gpu=4.0,
            replicas=3,
        )
        assert call_args.kwargs["request"] == model_deploy_request


@patch("app.models.router.get_finetunable_models")
def test_get_finetunable_models_endpoint(mock_get_finetunable_models):
    """Test the get_finetunable_models endpoint."""
    expected_models = ["model1", "model2"]
    mock_get_finetunable_models.return_value = expected_models

    with get_test_client() as client:
        response = client.get("/v1/models/finetunable")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["data"] == expected_models
        mock_get_finetunable_models.assert_called_once()


@patch("app.models.router.get_finetunable_models")
async def test_get_finetunable_models_endpoint_empty_list(
    mock_get_finetunable_models, db_session: AsyncSession, mock_claimset
):
    """Test retrieval when no finetunable models are available."""
    env = await factory.create_basic_test_environment(db_session)
    mock_get_finetunable_models.return_value = []

    setup_test_dependencies(env, db_session, mock_claimset)
    with get_test_client() as client:
        response = client.get("/v1/models/finetunable")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["data"] == []
        mock_get_finetunable_models.assert_called_once()


@patch("app.models.router.run_finetune_model_workload", autospec=True)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_finetune_router_function_handles_canonical_name(
    mock_ensure_healthy,
    mock_run_finetune_workload,
    db_session: AsyncSession,
):
    """Test that the router function correctly handles canonical names (already decoded by FastAPI)."""
    env = await factory.create_full_test_environment(db_session, with_model=True, with_dataset=True)
    workload = await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=await factory.create_chart(db_session),
        workload_type=WorkloadType.FINE_TUNING,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        name="test-finetune",
        display_name="Test Finetune Workload",
    )

    mock_run_finetune_workload.return_value = workload
    mock_ensure_healthy.return_value = None

    # Canonical name as it would be received by the router function (already decoded by FastAPI)
    canonical_name = "meta-llama/Llama-3.1-8B-Instruct"

    finetuning_data = FinetuneCreate(dataset_id=uuid4(), name="my-finetuned-model")

    # Call the router function directly
    result = await finetune_model(
        model_id=canonical_name,
        finetuning_data=finetuning_data,
        project=env.project,
        display_name=None,
        token="fake_token",
        author="test@example.com",
        session=db_session,
    )

    # Verify the service was called
    mock_run_finetune_workload.assert_called_once()
    call_args = mock_run_finetune_workload.call_args
    actual_model_id = call_args.kwargs["model_id"]

    # Should be passed through as-is
    assert actual_model_id == canonical_name, f"Expected '{canonical_name}' but got '{actual_model_id}'"


@patch("app.models.router.run_finetune_model_workload", autospec=True)
@patch("app.models.router.ensure_cluster_healthy", autospec=True)
async def test_finetune_router_function_converts_uuid_string_to_uuid(
    mock_ensure_healthy,
    mock_run_finetune_workload,
    db_session: AsyncSession,
):
    """Test that the router function converts UUID strings to UUID objects."""
    env = await factory.create_full_test_environment(db_session, with_model=True, with_dataset=True)
    workload = await factory.create_chart_workload(
        db_session,
        project=env.project,
        chart=await factory.create_chart(db_session),
        workload_type=WorkloadType.FINE_TUNING,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        name="test-finetune",
        display_name="Test Finetune Workload",
    )

    mock_run_finetune_workload.return_value = workload
    mock_ensure_healthy.return_value = None

    # UUID as string (as it would come from the path parameter)
    uuid_string = "edde6a14-001b-43bf-8457-65c6bbb42e96"
    expected_uuid = UUID(uuid_string)

    finetuning_data = FinetuneCreate(dataset_id=uuid4(), name="my-finetuned-model")

    # Call the router function directly
    result = await finetune_model(
        model_id=uuid_string,
        finetuning_data=finetuning_data,
        project=env.project,
        display_name=None,
        token="fake_token",
        author="test@example.com",
        session=db_session,
    )

    # Verify the service was called
    mock_run_finetune_workload.assert_called_once()
    call_args = mock_run_finetune_workload.call_args
    actual_model_id = call_args.kwargs["model_id"]

    # Should be converted to UUID
    assert actual_model_id == expected_uuid, (
        f"Expected UUID {expected_uuid} but got {actual_model_id} of type {type(actual_model_id)}"
    )
