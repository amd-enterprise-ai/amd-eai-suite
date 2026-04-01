# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.repository import (
    create_workload,
    delete_workload,
    get_workload_by_id,
    get_workloads,
    update_workload_status,
)
from tests import factory


@pytest.mark.asyncio
async def test_create_workload_success(db_session: AsyncSession) -> None:
    """Test creating a workload with required fields."""
    chart = await factory.create_chart(db_session, name="test-chart")

    workload = await create_workload(
        db_session,
        display_name="Test Workload",
        workload_type=WorkloadType.WORKSPACE,
        chart_id=chart.id,
        namespace="test-namespace",
        submitter="test@example.com",
        status=WorkloadStatus.PENDING,
    )

    assert workload.display_name == "Test Workload"
    assert workload.type == WorkloadType.WORKSPACE
    assert workload.namespace == "test-namespace"
    assert workload.status == WorkloadStatus.PENDING
    assert workload.chart_id == chart.id
    assert workload.created_by == "test@example.com"
    assert workload.name.startswith("wb-")


@pytest.mark.asyncio
async def test_create_workload_with_all_fields(db_session: AsyncSession) -> None:
    """Test creating a workload with all optional fields including model and dataset."""
    chart = await factory.create_chart(db_session, name="inference-chart")
    dataset = await factory.create_dataset(db_session, name="test-dataset")
    model = await factory.create_inference_model(db_session, name="test-model")

    workload = await create_workload(
        db_session,
        display_name="Inference Workload",
        workload_type=WorkloadType.INFERENCE,
        chart_id=chart.id,
        namespace="test-namespace",
        submitter="test@example.com",
        status=WorkloadStatus.RUNNING,
        model_id=model.id,
        dataset_id=dataset.id,
    )

    assert workload.model_id == model.id
    assert workload.dataset_id == dataset.id
    assert workload.type == WorkloadType.INFERENCE
    assert workload.status == WorkloadStatus.RUNNING


@pytest.mark.asyncio
async def test_create_workload_name_generation(db_session: AsyncSession) -> None:
    """Test that workload name is auto-generated based on chart and ID."""
    chart = await factory.create_chart(db_session, name="my-test-chart")

    workload = await create_workload(
        db_session,
        display_name="",  # Empty display name should be auto-generated
        workload_type=WorkloadType.WORKSPACE,
        chart_id=chart.id,
        namespace="test-namespace",
        submitter="test@example.com",
        status=WorkloadStatus.PENDING,
    )

    assert workload.name.startswith("wb-my-test-chart-")
    assert len(workload.name) <= 53  # Kubernetes name length limit
    assert workload.display_name != ""


@pytest.mark.asyncio
async def test_get_workload_by_id_found(db_session: AsyncSession) -> None:
    """Test retrieving a workload by ID when it exists."""
    workload = await factory.create_workload(db_session, namespace="test-namespace")

    retrieved = await get_workload_by_id(db_session, workload.id)

    assert retrieved is not None
    assert retrieved.id == workload.id
    assert retrieved.namespace == "test-namespace"


@pytest.mark.asyncio
async def test_get_workload_by_id_not_found(db_session: AsyncSession) -> None:
    """Test retrieving a workload by ID when it doesn't exist."""
    non_existent_id = uuid4()

    retrieved = await get_workload_by_id(db_session, non_existent_id)

    assert retrieved is None


@pytest.mark.asyncio
async def test_get_workload_by_id_with_namespace(db_session: AsyncSession) -> None:
    """Test retrieving a workload by ID filtered by namespace."""
    workload = await factory.create_workload(db_session, namespace="namespace-a")

    # Should find with matching namespace
    retrieved = await get_workload_by_id(db_session, workload.id, namespace="namespace-a")
    assert retrieved is not None
    assert retrieved.id == workload.id

    # Should not find with different namespace
    not_found = await get_workload_by_id(db_session, workload.id, namespace="namespace-b")
    assert not_found is None


@pytest.mark.asyncio
async def test_get_workload_by_id_without_namespace(db_session: AsyncSession) -> None:
    """Test retrieving a workload by ID without namespace filter."""
    workload = await factory.create_workload(db_session, namespace="any-namespace")

    retrieved = await get_workload_by_id(db_session, workload.id, namespace=None)

    assert retrieved is not None
    assert retrieved.id == workload.id


@pytest.mark.asyncio
async def test_get_workloads_no_filters(db_session: AsyncSession) -> None:
    """Test listing all workloads without filters (within a namespace)."""
    await factory.create_workload(db_session, display_name="Workload 1")
    await factory.create_workload(db_session, display_name="Workload 2")

    workloads = await get_workloads(db_session, namespace="test-namespace")

    assert len(workloads) == 2
    display_names = {w.display_name for w in workloads}
    assert "Workload 1" in display_names
    assert "Workload 2" in display_names


@pytest.mark.asyncio
async def test_get_workloads_by_namespace(db_session: AsyncSession) -> None:
    """Test listing workloads filtered by namespace."""
    await factory.create_workload(db_session, namespace="namespace-a", display_name="Workload A")
    await factory.create_workload(db_session, namespace="namespace-b", display_name="Workload B")
    await factory.create_workload(db_session, namespace="namespace-a", display_name="Workload A2")

    workloads = await get_workloads(db_session, namespace="namespace-a")

    assert len(workloads) == 2
    assert all(w.namespace == "namespace-a" for w in workloads)


@pytest.mark.asyncio
async def test_get_workloads_by_type(db_session: AsyncSession) -> None:
    """Test listing workloads filtered by type and namespace."""
    await factory.create_workload(db_session, workload_type=WorkloadType.WORKSPACE)
    await factory.create_workload(db_session, workload_type=WorkloadType.INFERENCE)
    await factory.create_workload(db_session, workload_type=WorkloadType.WORKSPACE)

    workloads = await get_workloads(db_session, namespace="test-namespace", workload_types=[WorkloadType.WORKSPACE])

    assert len(workloads) == 2
    assert all(w.type == WorkloadType.WORKSPACE for w in workloads)


@pytest.mark.asyncio
async def test_get_workloads_by_status(db_session: AsyncSession) -> None:
    """Test listing workloads filtered by status and namespace."""
    await factory.create_workload(db_session, status=WorkloadStatus.PENDING)
    await factory.create_workload(db_session, status=WorkloadStatus.RUNNING)
    await factory.create_workload(db_session, status=WorkloadStatus.RUNNING)
    await factory.create_workload(db_session, status=WorkloadStatus.FAILED)

    workloads = await get_workloads(
        db_session, namespace="test-namespace", status_filter=[WorkloadStatus.RUNNING, WorkloadStatus.PENDING]
    )

    assert len(workloads) == 3
    statuses = {w.status for w in workloads}
    assert statuses == {WorkloadStatus.RUNNING, WorkloadStatus.PENDING}


@pytest.mark.asyncio
async def test_get_workloads_by_chart_name(db_session: AsyncSession) -> None:
    """Test listing workloads filtered by chart name."""
    chart1 = await factory.create_chart(db_session, name="workspace-chart")
    chart2 = await factory.create_chart(db_session, name="inference-chart")

    await factory.create_workload(db_session, chart=chart1)
    await factory.create_workload(db_session, chart=chart2)
    await factory.create_workload(db_session, chart=chart1)

    workloads = await get_workloads(db_session, chart_name="workspace-chart")

    assert len(workloads) == 2
    assert all(w.chart.name == "workspace-chart" for w in workloads)


@pytest.mark.asyncio
async def test_get_workloads_combined_filters(db_session: AsyncSession) -> None:
    """Test listing workloads with multiple filters combined."""
    chart = await factory.create_chart(db_session, name="test-chart")

    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-ns",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="test-ns",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.RUNNING,
    )
    await factory.create_workload(
        db_session,
        chart=chart,
        namespace="other-ns",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    workloads = await get_workloads(
        db_session,
        namespace="test-ns",
        workload_types=[WorkloadType.INFERENCE],
        status_filter=[WorkloadStatus.RUNNING],
    )

    assert len(workloads) == 1
    assert workloads[0].namespace == "test-ns"
    assert workloads[0].type == WorkloadType.INFERENCE
    assert workloads[0].status == WorkloadStatus.RUNNING


@pytest.mark.asyncio
async def test_update_workload_status_success(db_session: AsyncSession) -> None:
    """Test updating a workload's status."""
    workload = await factory.create_workload(db_session, status=WorkloadStatus.PENDING)

    updated = await update_workload_status(db_session, workload.id, WorkloadStatus.RUNNING, "updater@example.com")

    assert updated is not None
    assert updated.status == WorkloadStatus.RUNNING
    assert updated.updated_by == "updater@example.com"


@pytest.mark.asyncio
async def test_update_workload_status_not_found(db_session: AsyncSession) -> None:
    """Test updating a non-existent workload's status returns None."""
    non_existent_id = uuid4()

    updated = await update_workload_status(db_session, non_existent_id, WorkloadStatus.RUNNING, "updater@example.com")

    assert updated is None


@pytest.mark.asyncio
async def test_delete_workload_success(db_session: AsyncSession) -> None:
    """Test deleting a workload."""
    workload = await factory.create_workload(db_session)

    result = await delete_workload(db_session, workload.id)

    assert result is True
    # Flush to ensure deletion is visible in the same transaction
    await db_session.flush()
    # Verify it's actually deleted
    retrieved = await get_workload_by_id(db_session, workload.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_workload_not_found(db_session: AsyncSession) -> None:
    """Test deleting a non-existent workload returns False."""
    non_existent_id = uuid4()

    result = await delete_workload(db_session, non_existent_id)

    assert result is False


# Edge Case Tests


@pytest.mark.asyncio
async def test_get_workloads_empty_database(db_session: AsyncSession) -> None:
    """Test get_workloads returns empty list when no workloads exist."""
    workloads = await get_workloads(db_session)

    assert workloads == []
    assert len(workloads) == 0


@pytest.mark.asyncio
async def test_create_workload_invalid_chart_id(db_session: AsyncSession) -> None:
    """Test constraint violation with non-existent chart_id, verify IntegrityError raised."""
    non_existent_chart_id = uuid4()

    with pytest.raises(IntegrityError):
        await create_workload(
            db_session,
            display_name="Test Workload",
            workload_type=WorkloadType.WORKSPACE,
            chart_id=non_existent_chart_id,
            namespace="test-namespace",
            submitter="test@example.com",
            status=WorkloadStatus.PENDING,
        )
        # Force the constraint violation to be checked
        await db_session.flush()


@pytest.mark.asyncio
async def test_delete_workload_cascade_behavior(db_session: AsyncSession) -> None:
    """Test cascade delete when chart is deleted (verify workload cascade deleted if configured)."""
    # Create a chart and workload
    chart = await factory.create_chart(db_session, name="test-chart")
    workload = await factory.create_workload(db_session, chart=chart)

    # Verify workload exists
    retrieved_workload = await get_workload_by_id(db_session, workload.id)
    assert retrieved_workload is not None

    # Delete the chart (should cascade delete the workload due to ondelete="CASCADE")
    await db_session.delete(chart)
    await db_session.flush()

    # Verify workload was cascade deleted
    retrieved_workload = await get_workload_by_id(db_session, workload.id)
    assert retrieved_workload is None
