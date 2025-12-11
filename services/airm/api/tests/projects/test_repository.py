# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.enums import ProjectStatus
from app.projects.repository import create_project as create_project_repo
from app.projects.repository import (
    delete_project,
    get_active_project_count_per_cluster,
    get_project_by_name_in_organization,
    get_project_in_organization,
    get_projects_by_names_in_organization,
    get_projects_in_cluster,
    get_projects_in_organization,
    update_project,
    update_project_status,
)
from app.projects.schemas import ProjectCreate, ProjectEdit
from app.quotas.schemas import QuotaBase
from app.utilities.exceptions import ConflictException
from tests import factory


@pytest.mark.asyncio
async def test_creates_project(db_session: AsyncSession):
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

    project = await create_project_repo(
        db_session, env.organization.id, project_data, creator, keycloak_group_id="1fa3c3b8-31af-1413-3143-1234567890ab"
    )

    assert project.name == "new-test-project"
    assert project.description == "A test project"
    assert project.organization_id == env.organization.id
    assert project.cluster_id == env.cluster.id
    assert project.created_by == creator
    assert project.updated_by == creator
    assert project.keycloak_group_id == "1fa3c3b8-31af-1413-3143-1234567890ab"


@pytest.mark.asyncio
async def test_creates_project_duplicate_name_raises_exception(db_session: AsyncSession):
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
    await create_project_repo(
        db_session, env.organization.id, project_data, creator, keycloak_group_id="1fa3c3b8-31af-1413-3143-1234567890ab"
    )

    # Try to create duplicate - should raise error
    with pytest.raises(ConflictException) as exc_info:
        await create_project_repo(
            db_session,
            env.organization.id,
            project_data,
            creator,
            keycloak_group_id="231413af-5983-2345-6334-af32ba21aa",
        )
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_project_in_organization(db_session: AsyncSession):
    """Test getting project within organization scope."""
    environments = await factory.create_multi_organization_environment(db_session, org_count=2)
    org1, _, project1 = environments[0]
    org2, _, _ = environments[1]

    # Test: Project should be found in correct organization
    found_project = await get_project_in_organization(db_session, org1.id, project1.id)
    assert found_project is not None
    assert found_project.id == project1.id

    # Test: Project should NOT be found in different organization
    not_found = await get_project_in_organization(db_session, org2.id, project1.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_update_project(db_session: AsyncSession):
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
async def test_delete_project(db_session: AsyncSession):
    """Test deleting a project."""
    env = await factory.create_basic_test_environment(db_session)

    found_project = await get_project_in_organization(db_session, env.organization.id, env.project.id)
    assert found_project is not None

    # Delete project
    await delete_project(db_session, env.project)

    deleted_project = await get_project_in_organization(db_session, env.organization.id, env.project.id)
    assert deleted_project is None


@pytest.mark.asyncio
async def test_get_projects_in_organization(db_session: AsyncSession):
    """Test getting all projects in an organization."""
    # Create multiple projects in same organization
    organization, _, projects = await factory.create_multi_project_environment(db_session, project_count=3)

    # Get projects in organization
    org_projects = await get_projects_in_organization(db_session, organization.id)

    assert len(org_projects) == 3
    project_ids = {p.id for p in org_projects}
    expected_ids = {p.id for p in projects}
    assert project_ids == expected_ids


@pytest.mark.asyncio
async def test_get_projects_in_cluster(db_session: AsyncSession):
    """Test getting all projects in a cluster."""
    # Create multiple projects in same cluster
    organization, cluster, projects = await factory.create_multi_project_environment(db_session, project_count=2)

    # Create another cluster with different projects
    other_cluster = await factory.create_cluster(db_session, organization, name="Other Cluster")
    other_project = await factory.create_project(db_session, organization, other_cluster, name="Other Project")

    # Get projects in original cluster
    cluster_projects = await get_projects_in_cluster(db_session, cluster.id)

    assert len(cluster_projects) == 2
    project_ids = {p.id for p in cluster_projects}
    expected_ids = {p.id for p in projects}
    assert project_ids == expected_ids
    assert other_project.id not in project_ids


@pytest.mark.asyncio
async def test_get_active_project_count_per_cluster(db_session: AsyncSession):
    """Test counting active projects per cluster."""
    # Create projects in cluster
    _, cluster, projects = await factory.create_multi_project_environment(db_session, project_count=3)
    projects[1].status = ProjectStatus.DELETING
    await db_session.flush()
    # Count should match number of projects created, not in deleting status
    count = await get_active_project_count_per_cluster(db_session, cluster.id)
    assert count == 2


@pytest.mark.asyncio
async def test_update_project_status(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    updated_project = await update_project_status(db_session, env.project, "FAILED", "Something went wrong", "system")

    assert updated_project.id == env.project.id
    assert updated_project.status == "FAILED"
    assert updated_project.status_reason == "Something went wrong"


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
async def test_get_projects_by_names(db_session, names, expected_count):
    """Test various input scenarios for get_projects_by_names_in_organization."""
    org, _, projects = await factory.create_multi_project_environment(db_session, project_count=3)

    result = await get_projects_by_names_in_organization(db_session, names, org.id)
    assert len(result) == expected_count


@pytest.mark.asyncio
async def test_get_projects_by_names_different_orgs(db_session):
    """Test get project by names, in different organizations."""
    org, _, projects = await factory.create_multi_project_environment(db_session, project_count=1)

    result = await get_projects_by_names_in_organization(db_session, [projects[0].name], uuid4())
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_project_by_name_in_organization(db_session):
    """Test getting project by name in organization."""
    org, _, projects = await factory.create_multi_project_environment(db_session, project_count=2)
    name = projects[0].name

    result = await get_project_by_name_in_organization(db_session, org.id, name)
    assert result is not None

    assert await get_project_by_name_in_organization(db_session, org.id, None) is None  # No name
    assert await get_project_by_name_in_organization(db_session, org.id, "NonExistent") is None  # Different name
    assert await get_project_by_name_in_organization(db_session, org.id, name.title()) is None  # Capitalization
    assert await get_project_by_name_in_organization(db_session, uuid4(), name) is None  # Different orgs
