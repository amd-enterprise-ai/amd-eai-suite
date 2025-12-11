# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import AIMClusterModelStatus, WorkloadStatus
from app.aims.repository import select_aim, select_aim_workload, select_aims_with_workload
from app.workloads.enums import WorkloadType
from tests.factory import create_aim, create_aim_workload, create_basic_test_environment


async def test_select_aim(db_session: AsyncSession):
    """Test selecting AIM by ID."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model-0-1-0",
        image_reference="docker.io/amdenterpriseai/aim-test:0.1.0-test-model-20251001",
    )

    # Test finding existing AIM
    result = await select_aim(db_session, aim.id)
    assert result is not None
    assert result.resource_name == "aim-test-model-0-1-0"
    assert result.image_reference == "docker.io/amdenterpriseai/aim-test:0.1.0-test-model-20251001"
    assert result.id == aim.id

    # Test finding non-existent AIM
    result = await select_aim(db_session, uuid4())
    assert result is None


async def test_select_aims_with_workload(db_session: AsyncSession):
    """Test selecting AIMs with their workloads."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(
        db_session,
        resource_name="aim-test-model2-0-1-0",
        image_reference="docker.io/amdenterpriseai/aim:0.1.0-test-model2-20251001",
    )
    workload = await create_aim_workload(
        session=db_session,
        project=env.project,
        aim=aim,
        status=WorkloadStatus.RUNNING.value,
    )

    # Test selecting AIMs with workloads
    results = await select_aims_with_workload(db_session, env.project.id)
    assert len(results) >= 1
    assert results[0][1] is not None  # Has workload
    assert results[0][1].id == workload.id
    assert results[0][1].aim.resource_name == workload.aim.resource_name == "aim-test-model2-0-1-0"
    assert (
        results[0][1].aim.image_reference
        == workload.aim.image_reference
        == "docker.io/amdenterpriseai/aim:0.1.0-test-model2-20251001"
    )
    assert results[0][1].status == WorkloadStatus.RUNNING.value


async def test_select_aim_workload(db_session: AsyncSession):
    """Test selecting specific AIM workload."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session)
    workload = await create_aim_workload(
        session=db_session,
        project=env.project,
        aim=aim,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING.value,
    )

    # Test finding workload without filters
    result = await select_aim_workload(db_session, aim.id, env.project.id)
    assert result is not None
    assert result.aim_id == aim.id

    # Test finding workload
    result = await select_aim_workload(
        session=db_session,
        aim_id=aim.id,
        project_id=env.project.id,
        type=[WorkloadType.INFERENCE],
        status=[WorkloadStatus.PENDING],
    )
    assert result is not None
    assert result.id == workload.id
    assert result.status == WorkloadStatus.PENDING

    # Test with no matching status
    result = await select_aim_workload(
        session=db_session,
        aim_id=aim.id,
        project_id=env.project.id,
        status=[WorkloadStatus.RUNNING],
    )
    assert result is None


async def test_select_aims_ordering(db_session: AsyncSession):
    """Test that AIMs are ordered by image_reference."""
    env = await create_basic_test_environment(db_session)

    # Create AIMs with different image_references
    aim1 = await create_aim(
        db_session,
        resource_name="aim-zzz",
        image_reference="docker.io/amdenterpriseai/zzz:1.0.0",
    )
    aim2 = await create_aim(
        db_session,
        resource_name="aim-aaa",
        image_reference="docker.io/amdenterpriseai/aaa:1.0.0",
    )
    aim3 = await create_aim(
        db_session,
        resource_name="aim-mmm",
        image_reference="docker.io/amdenterpriseai/mmm:1.0.0",
    )

    # Test ordering
    results = await select_aims_with_workload(db_session, env.project.id)
    assert len(results) >= 3

    # Find our AIMs in results
    our_aims = [r[0] for r in results if r[0].resource_name in ["aim-aaa", "aim-mmm", "aim-zzz"]]
    assert len(our_aims) == 3

    # Verify alphabetical order by image_reference
    assert our_aims[0].resource_name == "aim-aaa"
    assert our_aims[1].resource_name == "aim-mmm"
    assert our_aims[2].resource_name == "aim-zzz"


async def test_select_aims_excludes_deleted(db_session: AsyncSession):
    """Test that AIMs with status='Deleted' can be filtered using statuses parameter."""
    env = await create_basic_test_environment(db_session)

    # Create active AIMs
    active_aim = await create_aim(
        db_session,
        resource_name="aim-active",
        image_reference="docker.io/amdenterpriseai/active:1.0.0",
        status=AIMClusterModelStatus.READY.value,
    )

    # Create deleted AIM
    deleted_aim = await create_aim(
        db_session,
        resource_name="aim-deleted",
        image_reference="docker.io/amdenterpriseai/deleted:1.0.0",
        status=AIMClusterModelStatus.DELETED.value,
    )

    # Test that deleted AIM is included by default (no filter)
    results = await select_aims_with_workload(db_session, env.project.id)
    aim_ids = [r[0].id for r in results]

    assert active_aim.id in aim_ids
    assert deleted_aim.id in aim_ids

    # Test that deleted AIM is excluded when filtering by READY status
    results = await select_aims_with_workload(db_session, env.project.id, statuses=[AIMClusterModelStatus.READY])
    aim_ids = [r[0].id for r in results]

    assert active_aim.id in aim_ids
    assert deleted_aim.id not in aim_ids

    # Verify deleted AIM can still be retrieved by ID
    direct_result = await select_aim(db_session, deleted_aim.id)
    assert direct_result is not None
    assert direct_result.status == AIMClusterModelStatus.DELETED.value


async def test_select_aims_with_deleted_and_active_workloads(db_session: AsyncSession):
    """Test that deleted AIMs with workloads can be filtered using statuses."""
    env = await create_basic_test_environment(db_session)

    # Create active AIM with workload
    active_aim = await create_aim(
        db_session,
        resource_name="aim-active-deployed",
        image_reference="docker.io/amdenterpriseai/active-deployed:1.0.0",
        status=AIMClusterModelStatus.READY.value,
    )
    active_workload = await create_aim_workload(
        session=db_session,
        project=env.project,
        aim=active_aim,
        status=WorkloadStatus.RUNNING.value,
    )

    # Create deleted AIM with workload (edge case)
    deleted_aim = await create_aim(
        db_session,
        resource_name="aim-deleted-deployed",
        image_reference="docker.io/amdenterpriseai/deleted-deployed:1.0.0",
        status=AIMClusterModelStatus.DELETED.value,
    )
    deleted_workload = await create_aim_workload(
        session=db_session,
        project=env.project,
        aim=deleted_aim,
        status=WorkloadStatus.RUNNING.value,
    )

    # Test that both AIMs are returned by default
    results = await select_aims_with_workload(db_session, env.project.id)
    aim_ids = [r[0].id for r in results]
    workload_ids = [r[1].id for r in results if r[1] is not None]

    assert active_aim.id in aim_ids
    assert deleted_aim.id in aim_ids
    assert active_workload.id in workload_ids
    assert deleted_workload.id in workload_ids

    # Test that only active AIM is returned when filtering by READY status
    results = await select_aims_with_workload(db_session, env.project.id, statuses=[AIMClusterModelStatus.READY])
    aim_ids = [r[0].id for r in results]
    workload_ids = [r[1].id for r in results if r[1] is not None]

    assert active_aim.id in aim_ids
    assert deleted_aim.id not in aim_ids
    assert active_workload.id in workload_ids
    assert deleted_workload.id not in workload_ids
