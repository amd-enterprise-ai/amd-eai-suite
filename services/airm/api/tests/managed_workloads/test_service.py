# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Managed workloads service tests."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.config import INFERENCE_CHART_NAME
from app.managed_workloads.enums import WorkloadStatus
from app.managed_workloads.schemas import AIMWorkloadResponse, ChartWorkloadResponse
from app.managed_workloads.service import delete_workload, get_workload, submit_chart_workload
from app.utilities.exceptions import NotFoundException, PreconditionNotMetException
from app.workloads.enums import WorkloadType
from tests import factory


@pytest.mark.asyncio
async def test_get_workload_success(db_session: AsyncSession):
    """Test getting a workload by ID."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    # TODO: temporary, when we delete the capabilities, please delete code below
    await factory.create_chart(
        db_session,
        name=INFERENCE_CHART_NAME,
        chart_type=WorkloadType.INFERENCE,
        creator="test@example.com",
    )

    workload = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="test-workload",
        display_name="Test Workload",
    )

    result = await get_workload(db_session, [env.project], workload.id)

    assert result is not None
    assert result.id == workload.id
    assert result.chart_id == env.chart.id
    assert result.model_id == env.model.id


@pytest.mark.asyncio
async def test_get_workload_not_found(db_session: AsyncSession):
    """Test getting a non-existent workload."""
    env = await factory.create_basic_test_environment(db_session)

    with pytest.raises(NotFoundException, match="Workload with ID .* not found"):
        await get_workload(db_session, [env.project], uuid4())


@pytest.mark.asyncio
async def test_get_workload_require_aim_success(db_session: AsyncSession):
    """Test getting an AIM workload with require_aim=True."""
    env = await factory.create_full_test_environment(db_session)
    aim = await factory.create_aim(db_session)
    workload = await factory.create_aim_workload(
        db_session,
        env.project,
        aim=aim,
        status=WorkloadStatus.RUNNING.value,
        name="test-aim-workload",
        display_name="Test AIM Workload",
    )

    result = await get_workload(db_session, [env.project], workload.id, require_aim=True)

    assert result is not None
    assert result.id == workload.id
    assert result.aim_id == aim.id


@pytest.mark.asyncio
async def test_get_workload_require_aim_fails_for_chart_workload(db_session: AsyncSession):
    """Test that require_aim=True fails for chart workloads."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)
    workload = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=env.chart,
        model_id=env.model.id,
        status=WorkloadStatus.RUNNING.value,
        name="test-chart-workload",
        display_name="Test Chart Workload",
    )

    with pytest.raises(NotFoundException, match="AIM Workload with ID .* not found"):
        await get_workload(db_session, [env.project], workload.id, require_aim=True)


@pytest.mark.asyncio
async def test_get_chart_workload_returns_chart_response(db_session: AsyncSession):
    """Test that workload with chart_id returns ChartWorkloadResponse with IDs."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)
    # TODO: temporary, when we delete the capabilities, please delete code below
    await factory.create_chart(
        db_session,
        name=INFERENCE_CHART_NAME,
        chart_type=WorkloadType.INFERENCE,
        creator="test@example.com",
    )

    workload = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=env.chart,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        workload_type=WorkloadType.FINE_TUNING,
        status=WorkloadStatus.RUNNING.value,
        name="test-finetune-workload",
        display_name="Test Fine-tune Workload",
    )

    result = await get_workload(db_session, [env.project], workload.id)

    # Verify it's a ChartWorkloadResponse
    assert isinstance(result, ChartWorkloadResponse)

    # Verify IDs are present
    assert result.chart_id == env.chart.id
    assert result.model_id == env.model.id
    assert result.dataset_id == env.dataset.id


@pytest.mark.asyncio
async def test_get_workload_returns_aim_response_with_aim_id(db_session: AsyncSession):
    """Test that workload with aim_id returns AIMWorkloadResponse with aim_id."""
    env = await factory.create_full_test_environment(db_session)
    aim = await factory.create_aim(db_session)
    workload = await factory.create_aim_workload(
        db_session,
        env.project,
        aim=aim,
        status=WorkloadStatus.RUNNING.value,
        name="test-aim-workload",
        display_name="Test AIM Workload",
    )

    result = await get_workload(db_session, [env.project], workload.id)

    # Verify it's an AIMWorkloadResponse
    assert isinstance(result, AIMWorkloadResponse)

    # Verify aim_id is present
    assert result.aim_id is not None
    assert result.aim_id == aim.id


@pytest.mark.asyncio
async def test_submit_workload_success(db_session: AsyncSession):
    """Test successful workload submission with real database operations."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    creator = "test@example.com"
    token = "test-token"
    user_inputs = {"replicas": 1, "model_name": "test-model"}
    overlays_values = [{"cpu": "100m", "memory": "256Mi"}]

    with (
        patch("app.managed_workloads.service.render_helm_template") as mock_render,
        patch("app.managed_workloads.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.managed_workloads.service.extract_components_and_submit_workload") as mock_extract,
        patch(
            "app.managed_workloads.service.get_workload_internal_host",
            return_value="test-host.example.com",
        ) as mock_service_host,
        patch(
            "app.managed_workloads.service.get_workload_host_from_HTTPRoute_manifest",
            return_value="test-route.example.com",
        ) as mock_route_host,
    ):
        mock_render.return_value = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service\n"
        mock_validate.return_value = [{"apiVersion": "v1", "kind": "Service"}]
        mock_extract.return_value = None
        mock_message_sender = AsyncMock()

        result = await submit_chart_workload(
            db_session,
            creator,
            token,
            env.project,
            env.chart,
            overlays_values,
            mock_message_sender,
            user_inputs,
            env.model,
            env.dataset,
            "Test Workload",
        )

    assert result is not None
    assert result.display_name == "Test Workload"
    assert result.chart_id == env.chart.id
    assert result.model_id == env.model.id
    assert result.dataset_id == env.dataset.id
    assert result.project_id == env.project.id
    assert result.created_by == creator
    assert result.status == WorkloadStatus.PENDING.value

    mock_render.assert_called_once()
    mock_validate.assert_called_once()
    mock_extract.assert_called_once()


@pytest.mark.asyncio
async def test_submit_workload_without_base_url_failure(db_session: AsyncSession):
    """Test workload submission without base URL fails real database operations."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)
    env.cluster.workloads_base_url = None

    creator = "test@example.com"
    token = "test-token"
    user_inputs = {"replicas": 1, "model_name": "test-model"}
    overlays_values = [{"cpu": "100m", "memory": "256Mi"}]
    mock_message_sender = AsyncMock()

    with pytest.raises(PreconditionNotMetException):
        await submit_chart_workload(
            db_session,
            creator,
            token,
            env.project,
            env.chart,
            overlays_values,
            mock_message_sender,
            user_inputs,
            env.model,
            env.dataset,
            "Test Workload",
        )


@pytest.mark.asyncio
async def test_submit_workload_without_optional_entities(db_session: AsyncSession):
    """Test workload submission without model and dataset."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=False, with_dataset=False)

    creator = "test@example.com"
    token = "test-token"
    user_inputs = {"replicas": 1}
    overlays_values = [{"cpu": "100m", "memory": "256Mi"}]

    with (
        patch("app.managed_workloads.service.render_helm_template") as mock_render,
        patch("app.managed_workloads.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.managed_workloads.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_render.return_value = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service\n"
        mock_validate.return_value = [{"apiVersion": "v1", "kind": "Service"}]
        mock_extract.return_value = None
        mock_message_sender = AsyncMock()

        result = await submit_chart_workload(
            db_session,
            creator,
            token,
            env.project,
            env.chart,
            overlays_values,
            mock_message_sender,
            user_inputs,
            model=None,
            dataset=None,
            display_name="Test Workload No Dependencies",
        )

    assert result is not None
    assert result.display_name == "Test Workload No Dependencies"
    assert result.chart_id == env.chart.id
    assert result.model_id is None
    assert result.dataset_id is None
    assert result.status == WorkloadStatus.PENDING.value


@pytest.mark.asyncio
async def test_delete_workload_success(db_session: AsyncSession):
    """Test successful workload deletion with database status verification."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    creator = "test@example.com"
    token = "test-token"
    overlays_values = [{"cpu": "100m"}]

    with (
        patch(
            "app.managed_workloads.service.render_helm_template",
            return_value="apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service\n",
        ),
        patch(
            "app.managed_workloads.service.validate_and_parse_workload_manifest",
            return_value=[{"kind": "Service"}],
        ),
        patch("app.managed_workloads.service.extract_components_and_submit_workload"),
    ):
        mock_message_sender = AsyncMock()
        workload = await submit_chart_workload(
            db_session,
            creator,
            token,
            env.project,
            env.chart,
            overlays_values,
            mock_message_sender,
            {},
            env.model,
            None,
            "Test Workload For Deletion",
        )

    # Mock external deletion services only - keep database operations real
    result = await delete_workload(db_session, workload.id, [env.project], mock_message_sender)

    # Verify deletion was successful
    assert result is True

    # Verify external service was called correctly
    mock_message_sender.enqueue.assert_called_once()

    # Verify database status was updated to DELETING
    await db_session.refresh(workload)
    assert workload.status == WorkloadStatus.DELETING.value


@pytest.mark.asyncio
async def test_delete_workload_not_found(db_session: AsyncSession):
    """Test deleting non-existent workload."""
    env = await factory.create_basic_test_environment(db_session)
    mock_message_sender = AsyncMock()

    with pytest.raises(NotFoundException):
        await delete_workload(db_session, uuid4(), [env.project], mock_message_sender)


@pytest.mark.asyncio
async def test_submit_chart_workload_includes_canonical_name_from_model(db_session: AsyncSession):
    """Test that canonical name is extracted from model and added to user_inputs."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    # Update model with a specific canonical name
    env.model.canonical_name = "llama-3-8b-instruct"
    await db_session.flush()

    creator = "test@example.com"
    token = "test-token"
    user_inputs = {"replicas": 2, "gpu": "1"}
    overlays_values = [{"cpu": "200m"}]

    with (
        patch("app.managed_workloads.service.render_helm_template") as mock_render,
        patch("app.managed_workloads.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.managed_workloads.service.extract_components_and_submit_workload") as mock_extract,
        patch("app.managed_workloads.service.get_workload_internal_host", return_value="test-host.example.com"),
        patch(
            "app.managed_workloads.service.get_workload_host_from_HTTPRoute_manifest",
            return_value="test-route.example.com",
        ),
    ):
        mock_render.return_value = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service\n"
        mock_validate.return_value = [{"apiVersion": "v1", "kind": "Service"}]
        mock_extract.return_value = None
        mock_message_sender = AsyncMock()

        result = await submit_chart_workload(
            db_session,
            creator,
            token,
            env.project,
            env.chart,
            overlays_values,
            mock_message_sender,
            user_inputs,
            env.model,
            None,
            "Test Workload With Model",
        )

    # Verify canonical_name was added to user_inputs
    assert result.user_inputs is not None
    assert result.user_inputs.get("canonical_name") == "llama-3-8b-instruct"
    # Verify original user_inputs are preserved
    assert result.user_inputs.get("replicas") == 2
    assert result.user_inputs.get("gpu") == "1"


@pytest.mark.asyncio
async def test_submit_chart_workload_canonical_name_none_when_model_is_none(db_session: AsyncSession):
    """Test that canonical_name is None when model is not provided."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=False)

    creator = "test@example.com"
    token = "test-token"
    user_inputs = {"replicas": 1}
    overlays_values = [{"cpu": "100m"}]

    with (
        patch("app.managed_workloads.service.render_helm_template") as mock_render,
        patch("app.managed_workloads.service.validate_and_parse_workload_manifest") as mock_validate,
        patch("app.managed_workloads.service.extract_components_and_submit_workload") as mock_extract,
    ):
        mock_render.return_value = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service\n"
        mock_validate.return_value = [{"apiVersion": "v1", "kind": "Service"}]
        mock_extract.return_value = None
        mock_message_sender = AsyncMock()

        result = await submit_chart_workload(
            db_session,
            creator,
            token,
            env.project,
            env.chart,
            overlays_values,
            mock_message_sender,
            user_inputs,
            model=None,
            dataset=None,
            display_name="Test Workload Without Model",
        )

    # Verify canonical_name is None when model is not provided
    assert result.user_inputs is not None
    assert result.user_inputs.get("canonical_name") is None
