# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app import app  # type: ignore
from app.aims.schemas import AIMDeployRequest, AIMResponse
from app.apikeys.cluster_auth_client import get_cluster_auth_client
from app.utilities.database import get_session
from app.utilities.security import BearerToken, auth_token_claimset, get_user_email, validate_and_get_project_from_query
from tests.factory import create_aim, create_aim_workload, create_basic_test_environment

from ..conftest import get_test_client


def setup_test_dependencies(env, db_session, mock_claimset, mock_cluster_auth_client):
    """Set up common test dependencies."""
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[validate_and_get_project_from_query] = lambda: env.project
    app.dependency_overrides[get_user_email] = lambda: "test@example.com"
    app.dependency_overrides[BearerToken] = lambda: "test-token"
    app.dependency_overrides[get_cluster_auth_client] = lambda: mock_cluster_auth_client


@patch("app.aims.router.list_aims")
async def test_list_aims(mock_list_aims, db_session: AsyncSession, mock_claimset, mock_cluster_auth_client):
    """Test list AIMs endpoint returns 200."""
    env = await create_basic_test_environment(db_session)
    mock_list_aims.return_value = []

    setup_test_dependencies(env, db_session, mock_claimset, mock_cluster_auth_client)

    with get_test_client() as client:
        response = client.get(f"/v1/aims?project={env.project.id}")
        assert response.status_code == status.HTTP_200_OK


@patch("app.aims.router.get_aim")
async def test_get_aim(mock_get_aim, db_session: AsyncSession, mock_claimset, mock_cluster_auth_client):
    """Test get AIM by ID endpoint returns 200."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session)
    mock_aim_response = AIMResponse.model_validate(aim)
    mock_get_aim.return_value = mock_aim_response

    setup_test_dependencies(env, db_session, mock_claimset, mock_cluster_auth_client)

    with get_test_client() as client:
        response = client.get(f"/v1/aims/{aim.id}")
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["id"] == str(aim.id)
        assert response_data["image_reference"] == aim.image_reference
        # Verify computed fields are present
        assert "image_name" in response_data
        assert "image_tag" in response_data


@patch("app.aims.router.deploy_aim")
@patch("app.aims.router.ensure_cluster_healthy")
@patch("app.aims.router.ensure_base_url_configured")
async def test_deploy_aim(
    mock_ensure_healthy,
    mock_ensure_base_url_configured,
    mock_deploy_aim,
    db_session: AsyncSession,
    mock_claimset,
    mock_cluster_auth_client,
):
    """Test deploy AIM endpoint returns 202."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session)
    workload = await create_aim_workload(
        db_session, env.project, aim, name="test-deployment", display_name="Test Deployment"
    )
    mock_deploy_aim.return_value = workload

    setup_test_dependencies(env, db_session, mock_claimset, mock_cluster_auth_client)

    with get_test_client() as client:
        response = client.post(
            f"/v1/aims/{aim.id}/deploy?project={env.project.id}", json=AIMDeployRequest().model_dump()
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["id"] == str(workload.id)

    mock_ensure_base_url_configured.assert_called_once()
    mock_ensure_healthy.assert_called_once()


@patch("app.aims.router.undeploy_aim")
@patch("app.aims.router.ensure_cluster_healthy")
async def test_undeploy_aim(
    mock_ensure_healthy, mock_undeploy_aim, db_session: AsyncSession, mock_claimset, mock_cluster_auth_client
):
    """Test undeploy AIM endpoint returns 204."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session, resource_name="aim-test-model-v1-0", image_reference="docker.io/amd/aim:test-model-v1.0"
    )

    mock_ensure_healthy.return_value = None
    mock_undeploy_aim.return_value = None

    setup_test_dependencies(env, db_session, mock_claimset, mock_cluster_auth_client)

    with get_test_client() as client:
        response = client.post(f"/v1/aims/{aim.id}/undeploy?project={env.project.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
