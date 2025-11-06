# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus
from app.aims.repository import select_aim, select_aim_workload, select_aims_with_workload
from app.workloads.enums import WorkloadType
from tests.factory import create_aim, create_aim_workload, create_basic_test_environment


async def test_select_aim(db_session: AsyncSession):
    """Test selecting AIM by ID."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session, image_name="aim-test", image_tag="0.1.0-test-model-20251001")

    # Test finding existing AIM
    result = await select_aim(db_session, aim.id)
    assert result is not None
    assert result.image_name == "aim-test"
    assert result.image_tag == "0.1.0-test-model-20251001"
    assert result.id == aim.id

    # Test finding non-existent AIM
    result = await select_aim(db_session, uuid4())
    assert result is None


async def test_select_aims_with_workload(db_session: AsyncSession):
    """Test selecting AIMs with their workloads."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session, image_name="aim", image_tag="0.1.0-test-model2-20251001")
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
    assert results[0][1].aim.image_name == workload.aim.image_name == "aim"
    assert results[0][1].aim.image_tag == workload.aim.image_tag == "0.1.0-test-model2-20251001"
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


async def test_select_aim_by_name_and_tag(db_session: AsyncSession):
    """Test selecting AIM by image name and tag."""
    from app.aims.repository import select_aim_by_name_and_tag

    aim1 = await create_aim(db_session, image_name="aim-select", image_tag="1.2.3-test-tag")
    aim2 = await create_aim(db_session, image_name="aim-select", image_tag="2.0.0-other-tag")
    aim3 = await create_aim(db_session, image_name="other-name", image_tag="1.2.3-test-tag")
    aim_special = await create_aim(db_session, image_name="special!@#", image_tag="tag$%^")

    # Test finding AIM by correct name and tag
    result = await select_aim_by_name_and_tag(db_session, "aim-select", "1.2.3-test-tag")
    assert result is not None
    assert result.id == aim1.id
    assert result.image_name == "aim-select"
    assert result.image_tag == "1.2.3-test-tag"

    # Test not finding AIM with wrong name
    result = await select_aim_by_name_and_tag(db_session, "wrong-name", "1.2.3-test-tag")
    assert result is None

    # Test not finding AIM with wrong tag
    result = await select_aim_by_name_and_tag(db_session, "aim-select", "wrong-tag")
    assert result is None

    # Test finding different AIM by correct name and tag
    result = await select_aim_by_name_and_tag(db_session, "aim-select", "2.0.0-other-tag")
    assert result is not None
    assert result.id == aim2.id

    # Test finding AIM with different name
    result = await select_aim_by_name_and_tag(db_session, "other-name", "1.2.3-test-tag")
    assert result is not None
    assert result.id == aim3.id

    # Test not finding AIM with empty name or tag
    result = await select_aim_by_name_and_tag(db_session, "", "1.2.3-test-tag")
    assert result is None
    result = await select_aim_by_name_and_tag(db_session, "aim-select", "")
    assert result is None

    # Test finding AIM with special characters
    result = await select_aim_by_name_and_tag(db_session, "special!@#", "tag$%^")
    assert result is not None
    assert result.id == aim_special.id

    # Test not finding AIM with wrong special characters
    result = await select_aim_by_name_and_tag(db_session, "special!@#", "wrongtag")
    assert result is None
