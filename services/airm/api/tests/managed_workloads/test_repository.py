# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.managed_workloads.enums import WorkloadStatus
from app.managed_workloads.repository import insert_workload, select_workload, select_workloads
from app.managed_workloads.schemas import ChartWorkloadCreate
from app.workloads.enums import WorkloadType
from tests import factory


@pytest.mark.asyncio
async def test_insert_workload(db_session: AsyncSession):
    """Test inserting a managed workload with real database operations."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    creator = "test@example.com"
    workload_name = "test-managed-workload"

    # Create workload data
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        display_name=workload_name,
        user_inputs={"replicas": 1},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.display_name == workload_name
    assert workload.name.startswith("mw-")  # System generates workload name
    assert workload.chart_id == env.chart.id
    assert workload.model_id == env.model.id
    assert workload.cluster_id == env.cluster.id
    assert workload.project_id == env.project.id
    assert workload.status == WorkloadStatus.PENDING
    assert workload.type == WorkloadType.INFERENCE
    assert workload.created_by == creator
    assert workload.updated_by == creator


@pytest.mark.asyncio
async def test_select_workload_with_membership(db_session: AsyncSession):
    """Test selecting workload accessible to user with project membership."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    creator = "test@example.com"

    # Create workload data
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        display_name="test-workload",
        user_inputs={"replicas": 1},
    )

    workload = await insert_workload(
        session=db_session,
        creator=creator,
        project=env.project,
        workload_data=workload_create,
    )

    # Test: User with membership should access workload
    # Since project membership is now handled by Keycloak, we'll pass the project directly
    projects = [env.project]  # User has access to this project
    accessible_workload = await select_workload(db_session, workload.id, projects)
    assert accessible_workload is not None
    assert accessible_workload.id == workload.id
    assert accessible_workload.display_name == "test-workload"


@pytest.mark.asyncio
async def test_select_workload_without_membership(db_session: AsyncSession):
    """Test selecting workload inaccessible to user without project membership."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    # Create workload data
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        display_name="test-workload",
        user_inputs={"replicas": 1},
    )

    workload = await insert_workload(
        db_session,
        "test@example.com",
        env.project,
        workload_create,
    )

    # Test: User without membership should not access workload
    # Since project membership is now handled by Keycloak, we'll pass an empty list
    inaccessible_workload = await select_workload(db_session, workload.id, [])  # No projects accessible
    assert inaccessible_workload is None


@pytest.mark.asyncio
async def test_select_workload_different_user(db_session: AsyncSession):
    """Test workload access isolation between different users."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    # Create another user without project membership
    other_user = await factory.create_user(db_session, env.organization, email="other@example.com")

    # Create workload data
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        display_name="test-workload",
        user_inputs={"replicas": 1},
    )

    workload = await insert_workload(
        db_session,
        "test@example.com",
        env.project,
        workload_create,
    )

    # Test: Original user with membership can access
    accessible_to_member = await select_workload(db_session, workload.id, [env.project])
    assert accessible_to_member is not None

    # Test: Other user without membership cannot access
    accessible_to_other = await select_workload(db_session, workload.id, [])  # Other user has no projects
    assert accessible_to_other is None


@pytest.mark.asyncio
async def test_insert_chart_only_workload(db_session: AsyncSession):
    """Test inserting a managed workload with chart only (no model or dataset)."""
    env = await factory.create_full_test_environment(db_session, with_chart=True)

    creator = "test@example.com"
    workload_name = "chart-only-workload"

    # Create workload data without model or dataset
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.CUSTOM,
        chart_id=env.chart.id,
        display_name=workload_name,
        user_inputs={"custom_param": "value"},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.display_name == workload_name
    assert workload.name.startswith("mw-")
    assert workload.chart_id == env.chart.id
    assert workload.model_id is None
    assert workload.dataset_id is None
    assert workload.cluster_id == env.cluster.id
    assert workload.project_id == env.project.id
    assert workload.status == WorkloadStatus.PENDING
    assert workload.type == WorkloadType.CUSTOM
    assert workload.user_inputs == {"custom_param": "value"}


@pytest.mark.asyncio
async def test_insert_workload_with_custom_display_name(db_session: AsyncSession):
    """Test inserting workload with custom display name handling."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    creator = "test@example.com"
    custom_display_name = "My Custom Workload Name"

    # Create workload data with custom display name
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        display_name=custom_display_name,
        user_inputs={"replicas": 2},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.display_name == custom_display_name
    assert workload.name.startswith("mw-")


@pytest.mark.asyncio
async def test_insert_workload_auto_generated_display_name(db_session: AsyncSession):
    """Test inserting workload with auto-generated display name when none provided."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    creator = "test@example.com"

    # Create workload data without display name
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        # No display_name provided
        user_inputs={"replicas": 1},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.display_name is not None
    assert env.chart.name in workload.display_name
    assert env.model.name in workload.display_name
    assert str(workload.id)[:8] in workload.display_name


@pytest.mark.asyncio
async def test_insert_workload_auto_generated_display_name_chart_only(db_session: AsyncSession):
    """Test auto-generated display name format for chart-only workloads."""
    env = await factory.create_full_test_environment(db_session, with_chart=True)

    creator = "test@example.com"

    # Create workload data without display name or model
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.CUSTOM,
        chart_id=env.chart.id,
        user_inputs={"setting": "value"},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.display_name is not None
    assert env.chart.name in workload.display_name
    assert str(workload.id)[:8] in workload.display_name
    # Should not contain model name since no model
    assert len(workload.display_name.split("-")) == 2  # chart-uuid format


@pytest.mark.asyncio
async def test_insert_workload_name_format_validation(db_session: AsyncSession):
    """Test auto-generated workload name format validation."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    creator = "test@example.com"

    # Create workload data
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        display_name="test-workload",
        user_inputs={"replicas": 1},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.name.startswith("mw-")
    name_parts = workload.name.split("-")
    assert len(name_parts) >= 4  # mw, chart_name, timestamp, uuid_prefix
    assert len(workload.name) <= 53  # Kubernetes name length limit
    assert str(workload.id)[:4] in workload.name


@pytest.mark.asyncio
async def test_insert_workload_different_types(db_session: AsyncSession):
    """Test inserting workloads with different WorkloadType values."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    creator = "test@example.com"

    # Test different workload types
    workload_types = [
        WorkloadType.INFERENCE,
        WorkloadType.FINE_TUNING,
        WorkloadType.WORKSPACE,
        WorkloadType.CUSTOM,
    ]

    workloads = []
    for workload_type in workload_types:
        workload_create = ChartWorkloadCreate(
            type=workload_type,
            chart_id=env.chart.id,
            model_id=env.model.id,
            dataset_id=env.dataset.id if workload_type == WorkloadType.FINE_TUNING else None,
            display_name=f"{workload_type.value.lower()}-workload",
            user_inputs={"type_specific_param": workload_type.value},
        )

        workload = await insert_workload(
            db_session,
            creator,
            env.project,
            workload_create,
        )

        workloads.append(workload)

    for i, workload in enumerate(workloads):
        assert workload.type == workload_types[i]
        assert workload.display_name == f"{workload_types[i].value.lower()}-workload"


@pytest.mark.asyncio
async def test_insert_workload_comprehensive_field_validation(db_session: AsyncSession):
    """Test comprehensive field validation for workload creation."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    creator = "test@example.com"
    complex_user_inputs = {
        "replicas": 3,
        "resources": {"cpu": "500m", "memory": "1Gi"},
        "environment": {"ENV_VAR": "value"},
        "nested": {"config": {"debug": True}},
    }

    # Create workload with comprehensive field values
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        dataset_id=env.dataset.id,
        display_name="comprehensive-test-workload",
        user_inputs=complex_user_inputs,
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.type == WorkloadType.INFERENCE
    assert workload.chart_id == env.chart.id
    assert workload.model_id == env.model.id
    assert workload.dataset_id == env.dataset.id
    assert workload.cluster_id == env.cluster.id
    assert workload.project_id == env.project.id
    assert workload.display_name == "comprehensive-test-workload"
    assert workload.user_inputs == complex_user_inputs
    assert workload.status == WorkloadStatus.PENDING
    assert workload.created_by == creator
    assert workload.updated_by == creator
    assert workload.name.startswith("mw-")
    assert workload.id is not None


@pytest.mark.asyncio
async def test_insert_workload_edge_case_combinations(db_session: AsyncSession):
    """Test edge cases for different entity combinations."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True, with_dataset=True)

    creator = "test@example.com"

    # Test case 1: Model without dataset
    workload_create_model_only = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        # No dataset_id
        display_name="model-only-workload",
        user_inputs={"inference_param": "value"},
    )

    workload_model_only = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create_model_only,
    )

    assert workload_model_only.model_id == env.model.id
    assert workload_model_only.dataset_id is None

    # Test case 2: Dataset without model
    workload_create_dataset_only = ChartWorkloadCreate(
        type=WorkloadType.CUSTOM,
        chart_id=env.chart.id,
        # No model_id
        dataset_id=env.dataset.id,
        display_name="dataset-only-workload",
        user_inputs={"data_param": "value"},
    )

    workload_dataset_only = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create_dataset_only,
    )

    assert workload_dataset_only.model_id is None
    assert workload_dataset_only.dataset_id == env.dataset.id

    # Test case 3: Empty user_inputs
    workload_create_empty_inputs = ChartWorkloadCreate(
        type=WorkloadType.WORKSPACE,
        chart_id=env.chart.id,
        display_name="empty-inputs-workload",
        user_inputs={},  # Empty inputs
    )

    workload_empty_inputs = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create_empty_inputs,
    )

    assert workload_empty_inputs.user_inputs == {}


@pytest.mark.asyncio
async def test_select_workloads_by_project(db_session: AsyncSession):
    """Test selecting workloads by project ID."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    # Create multiple workloads in the project
    workload_data = [
        {"type": WorkloadType.INFERENCE, "display_name": "inference-workload"},
        {"type": WorkloadType.CUSTOM, "display_name": "custom-workload"},
        {"type": WorkloadType.WORKSPACE, "display_name": "workspace-workload"},
    ]

    created_workloads = []
    for data in workload_data:
        workload_create = ChartWorkloadCreate(
            type=data["type"],
            chart_id=env.chart.id,
            model_id=env.model.id if data["type"] == WorkloadType.INFERENCE else None,
            display_name=data["display_name"],
            user_inputs={"test": "value"},
        )

        workload = await insert_workload(
            db_session,
            "test@example.com",
            env.project,
            workload_create,
        )
        created_workloads.append(workload)

    # Test: Select all workloads for the project
    workloads = await select_workloads(db_session, env.project.id)
    assert len(workloads) == 3

    for workload in workloads:
        assert workload.project_id == env.project.id


@pytest.mark.asyncio
async def test_select_workloads_filtered_by_type(db_session: AsyncSession):
    """Test selecting workloads filtered by type."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    creator = "test@example.com"

    # Create workloads of different types
    workload_types = [WorkloadType.INFERENCE, WorkloadType.CUSTOM, WorkloadType.WORKSPACE]

    for workload_type in workload_types:
        workload_create = ChartWorkloadCreate(
            type=workload_type,
            chart_id=env.chart.id,
            model_id=env.model.id if workload_type == WorkloadType.INFERENCE else None,
            display_name=f"{workload_type.value.lower()}-workload",
            user_inputs={"test": "value"},
        )

        await insert_workload(
            db_session,
            creator,
            env.project,
            workload_create,
        )

    # Test: Filter by INFERENCE type only
    inference_workloads = await select_workloads(db_session, env.project.id, type=[WorkloadType.INFERENCE])
    assert len(inference_workloads) == 1
    assert inference_workloads[0].type == WorkloadType.INFERENCE

    # Test: Filter by multiple types
    multiple_types = await select_workloads(
        db_session, env.project.id, type=[WorkloadType.CUSTOM, WorkloadType.WORKSPACE]
    )
    assert len(multiple_types) == 2
    for workload in multiple_types:
        assert workload.type in [WorkloadType.CUSTOM, WorkloadType.WORKSPACE]


@pytest.mark.asyncio
async def test_select_workloads_filtered_by_status(db_session: AsyncSession):
    """Test selecting workloads filtered by status."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    creator = "test@example.com"

    # Create workload (all start as PENDING by default)
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        display_name="status-test-workload",
        user_inputs={"test": "value"},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    # Test: Filter by PENDING status
    pending_workloads = await select_workloads(db_session, env.project.id, status=[WorkloadStatus.PENDING])
    assert len(pending_workloads) == 1
    assert pending_workloads[0].status == WorkloadStatus.PENDING
    assert pending_workloads[0].id == workload.id


@pytest.mark.asyncio
async def test_insert_workload_with_overlay(db_session: AsyncSession):
    """Test creating workload using overlay factory pattern."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    overlay_data = {
        "resources": {"limits": {"memory": "2Gi", "cpu": "1000m"}},
        "replicas": 2,
        "environment": {"DEBUG": "true"},
    }
    overlay = await factory.create_overlay(
        db_session, env.chart, canonical_name="test-overlay", overlay_data=overlay_data
    )

    creator = "test@example.com"

    # Create workload that could use the overlay
    workload_create = ChartWorkloadCreate(
        type=WorkloadType.INFERENCE,
        chart_id=env.chart.id,
        model_id=env.model.id,
        display_name="overlay-workload",
        user_inputs={"use_overlay": True, "overlay_config": "test-overlay"},
    )

    workload = await insert_workload(
        db_session,
        creator,
        env.project,
        workload_create,
    )

    assert workload.chart_id == env.chart.id
    assert workload.chart_id == overlay.chart_id
    assert overlay.canonical_name == "test-overlay"
    assert overlay.overlay == overlay_data


@pytest.mark.asyncio
async def test_select_workloads_with_aim_ids_filter(db_session: AsyncSession):
    """Test selecting workloads filtered by AIM IDs."""
    from tests.factory import create_aim, create_aim_workload

    env = await factory.create_basic_test_environment(db_session)

    # Create AIMs
    aim1 = await create_aim(db_session, resource_name="llama-v1", image_reference="docker.io/test/llama:v1")
    aim2 = await create_aim(db_session, resource_name="gpt-v2", image_reference="docker.io/test/gpt:v2")
    aim3 = await create_aim(db_session, resource_name="mistral-v3", image_reference="docker.io/test/mistral:v3")

    # Create workloads for different AIMs
    workload1 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim1,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        name="llama-workload",
    )
    workload2 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim2,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        name="gpt-workload",
    )
    workload3 = await create_aim_workload(
        db_session,
        env.project,
        aim=aim3,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING.value,
        name="mistral-workload",
    )

    # Test filtering by single AIM ID
    workloads = await select_workloads(
        session=db_session,
        project_id=env.project.id,
        aim_ids=[aim1.id],
    )
    assert len(workloads) == 1
    assert workloads[0].id == workload1.id
    assert workloads[0].aim_id == aim1.id

    # Test filtering by multiple AIM IDs
    workloads = await select_workloads(
        session=db_session,
        project_id=env.project.id,
        aim_ids=[aim1.id, aim2.id],
    )
    assert len(workloads) == 2
    aim_ids = {w.aim_id for w in workloads}
    assert aim1.id in aim_ids
    assert aim2.id in aim_ids
    assert aim3.id not in aim_ids

    # Test filtering by non-existent AIM ID
    from uuid import uuid4

    workloads = await select_workloads(
        session=db_session,
        project_id=env.project.id,
        aim_ids=[uuid4()],
    )
    assert len(workloads) == 0

    # Test combining AIM ID filter with other filters
    workloads = await select_workloads(
        session=db_session,
        project_id=env.project.id,
        type=[WorkloadType.INFERENCE],
        status=[WorkloadStatus.RUNNING],
        aim_ids=[aim1.id, aim2.id],
    )
    assert len(workloads) == 2

    # Test with no AIM ID filter (should return all workloads)
    workloads = await select_workloads(
        session=db_session,
        project_id=env.project.id,
        type=[WorkloadType.INFERENCE],
        status=[WorkloadStatus.RUNNING],
    )
    assert len(workloads) == 3  # All three workloads
