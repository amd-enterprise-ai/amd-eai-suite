# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.enums import ProjectStatus
from app.projects.repository import (
    create_project,
    delete_project,
    get_active_project_count_per_cluster,
    get_project_by_id,
    get_project_by_name,
    get_projects,
    get_projects_by_names,
    get_projects_in_cluster,
    get_projects_in_clusters,
    update_keycloak_group_id,
    update_project,
    update_project_status,
)
from app.projects.schemas import ProjectCreate, ProjectEdit
from app.quotas.schemas import QuotaBase
from app.utilities.exceptions import ConflictException
from tests import factory  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_creates_project(db_session: AsyncSession) -> None:
    """Test creating a project with quota."""
    env = await factory.create_basic_test_environment(db_session)

    project_data = ProjectCreate(
        name="new-test-project",
        description="A test project",
        cluster_id=env.cluster.id,
        status=ProjectStatus.READY,
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
            gpu_count=0,
            description="desc",
        ),
    )
    creator = "test_creator"

    project = await create_project(
        db_session, project_data, creator, keycloak_group_id="1fa3c3b8-31af-1413-3143-1234567890ab"
    )

    assert project.name == "new-test-project"
    assert project.description == "A test project"
    assert project.cluster_id == env.cluster.id
    assert project.created_by == creator
    assert project.updated_by == creator
    assert project.keycloak_group_id == "1fa3c3b8-31af-1413-3143-1234567890ab"


@pytest.mark.asyncio
async def test_creates_project_duplicate_name_raises_exception(db_session: AsyncSession) -> None:
    """Test that creating duplicate project names raises integrity error."""
    env = await factory.create_basic_test_environment(db_session)

    project_data = ProjectCreate(
        name="duplicate-project",
        description="A test project",
        cluster_id=env.cluster.id,
        status=ProjectStatus.READY,
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024**3,
            ephemeral_storage_bytes=5 * 1024**3,
            gpu_count=0,
            description="desc",
        ),
    )
    creator = "test_creator"

    # Create first project
    await create_project(db_session, project_data, creator, keycloak_group_id="1fa3c3b8-31af-1413-3143-1234567890ab")

    # Try to create duplicate - should raise error
    with pytest.raises(ConflictException) as exc_info:
        await create_project(db_session, project_data, creator, keycloak_group_id="231413af-5983-2345-6334-af32ba21aa")
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_project_by_id(db_session: AsyncSession) -> None:
    """Test getting project."""
    env = await factory.create_basic_test_environment(db_session)
    project1 = env.project

    # Test: Project should be found in correct organization
    found_project = await get_project_by_id(db_session, project1.id)
    assert found_project is not None
    assert found_project.id == project1.id


@pytest.mark.asyncio
async def test_update_project(db_session: AsyncSession) -> None:
    """Test updating project details and quota."""
    env = await factory.create_basic_test_environment(db_session)

    original_description = env.project.description

    # Define updated quota
    updated_quota = QuotaBase(
        cpu_milli_cores=2000,
        memory_bytes=2 * 1024 * 1024 * 1024,
        ephemeral_storage_bytes=10 * 1024 * 1024 * 1024,
        gpu_count=1,
        description="Updated quota",
    )

    edits = ProjectEdit(description="An updated project", quota=updated_quota)

    updated_project = await update_project(db_session, env.project, edits, "updater")

    assert updated_project.id == env.project.id
    assert updated_project.description == "An updated project"
    assert updated_project.description != original_description
    assert updated_project.updated_by == "updater"


@pytest.mark.asyncio
async def test_delete_project(db_session: AsyncSession) -> None:
    """Test deleting a project."""
    env = await factory.create_basic_test_environment(db_session)

    found_project = await get_project_by_id(db_session, env.project.id)
    assert found_project is not None

    # Delete project
    await delete_project(db_session, env.project)

    deleted_project = await get_project_by_id(db_session, env.project.id)
    assert deleted_project is None


@pytest.mark.asyncio
async def test_get_projects(db_session: AsyncSession) -> None:
    """Test getting all projects."""
    env = await factory.create_basic_test_environment(db_session)
    _ = await factory.create_project(db_session, env.cluster, name="project-2")
    __ = await factory.create_project(db_session, env.cluster, name="project-3")
    projects = await get_projects(db_session)

    assert len(projects) == 3


@pytest.mark.asyncio
async def test_get_projects_in_cluster(db_session: AsyncSession) -> None:
    """Test getting all projects in a cluster."""
    # Create multiple projects in same cluster
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.cluster, name="project-2")

    # Create another cluster with different projects
    other_cluster = await factory.create_cluster(db_session, name="Other Cluster")
    other_project = await factory.create_project(db_session, other_cluster, name="Other Project")

    # Get projects in original cluster
    cluster_projects = await get_projects_in_cluster(db_session, env.cluster.id)

    assert len(cluster_projects) == 2
    project_ids = {p.id for p in cluster_projects}
    expected_ids = {env.project.id, project2.id}
    assert project_ids == expected_ids
    assert other_project.id not in project_ids


@pytest.mark.asyncio
async def test_get_projects_in_clusters(db_session: AsyncSession) -> None:
    """Test getting all projects in multiple clusters."""
    # Create projects in first cluster
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.cluster, name="project-2")

    cluster2 = await factory.create_cluster(db_session, name="Cluster 2")
    project3 = await factory.create_project(db_session, cluster2, name="project-3")
    project4 = await factory.create_project(db_session, cluster2, name="project-4")

    # Create a third cluster that we won't query
    cluster3 = await factory.create_cluster(db_session, name="Cluster 3")
    _ = await factory.create_project(db_session, cluster3, name="project-5")

    projects = await get_projects_in_clusters(db_session, [env.cluster.id, cluster2.id])

    assert len(projects) == 4
    project_ids = {p.id for p in projects}
    expected_ids = {env.project.id, project2.id, project3.id, project4.id}
    assert project_ids == expected_ids


@pytest.mark.asyncio
async def test_get_active_project_count_per_cluster(db_session: AsyncSession) -> None:
    """Test counting active projects per cluster."""
    # Create projects in cluster
    env = await factory.create_basic_test_environment(db_session)
    _ = await factory.create_project(db_session, env.cluster, name="project-2")
    project3 = await factory.create_project(db_session, env.cluster, name="project-3")
    project3.status = ProjectStatus.DELETING
    await db_session.flush()
    # Count should match number of projects created, not in deleting status
    count = await get_active_project_count_per_cluster(db_session, env.cluster.id)
    assert count == 2


@pytest.mark.asyncio
async def test_update_project_status(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    await update_project_status(db_session, env.project, ProjectStatus.FAILED, "Something went wrong", "system")

    project = await get_project_by_id(db_session, env.project.id)
    assert project.id == env.project.id
    assert project.status == ProjectStatus.FAILED
    assert project.status_reason == "Something went wrong"


@pytest.mark.asyncio
async def test_update_keycloak_group_id(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    new_kc_id = str(uuid4())
    await update_keycloak_group_id(db_session, env.project, new_kc_id, "system")

    project = await get_project_by_id(db_session, env.project.id)
    assert project.id == env.project.id
    assert project.keycloak_group_id == new_kc_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "names,expected_count",
    [
        (["test-project-1", "test-project-2"], 2),  # matching projects
        ([], 0),  # empty list
        (["NonExistent"], 0),  # no matches
        (["test-project-1", "NonExistent"], 1),  # partial match
        (["Test-ProjecT-1"], 0),  # case sensitive
    ],
)
async def test_get_projects_by_names(db_session: AsyncSession, names: list[str], expected_count: int) -> None:
    """Test various input scenarios for get_projects_by_names."""
    env = await factory.create_basic_test_environment(db_session, project_name="test-project-1")
    await factory.create_project(db_session, env.cluster, name="test-project-2")
    await factory.create_project(db_session, env.cluster, name="test-project-3")

    result = await get_projects_by_names(db_session, names)
    assert len(result) == expected_count


@pytest.mark.asyncio
async def test_get_project_by_name(db_session: AsyncSession) -> None:
    """Test getting project by name."""
    env = await factory.create_basic_test_environment(db_session)
    _ = await factory.create_project(db_session, env.cluster, name="another-project")

    name = env.project.name

    result = await get_project_by_name(db_session, name)
    assert result is not None

    assert await get_project_by_name(db_session, None) is None  # No name
    assert await get_project_by_name(db_session, "NonExistent") is None  # Different name
    assert await get_project_by_name(db_session, name.title()) is None  # Capitalization
