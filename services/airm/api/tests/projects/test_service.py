# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from keycloak import KeycloakAdmin
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import NamespaceStatus, QuotaStatus
from app.clusters.models import Cluster as ClusterModel
from app.clusters.schemas import ClusterResponse
from app.organizations.models import Organization
from app.projects.enums import ProjectStatus
from app.projects.models import Project
from app.projects.schemas import (
    ProjectCreate,
    Projects,
    ProjectsWithResourceAllocation,
)
from app.projects.service import (
    add_users_to_project_and_keycloak_group,
    create_project,
    create_quota,
    delete_project_if_components_deleted,
    get_projects_with_resource_allocation,
    get_submittable_projects,
    remove_user_from_project_and_keycloak_group,
    submit_delete_project,
    update_project_status_from_components,
)
from app.quotas.schemas import QuotaBase, QuotaResponse
from app.utilities.exceptions import NotFoundException, UnhealthyException, ValidationException
from tests import factory


@pytest.mark.asyncio
@patch(
    "app.projects.service.create_project_in_db",
    return_value=Project(
        name="test-project",
        description="A test project",
        organization_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
        keycloak_group_id="1fa3c3b8-31af-1413-3143-1234567890ab",
    ),
    autospec=True,
)
@patch("app.projects.service.create_group", return_value="1fa3c3b8-31af-1413-3143-1234567890ab")
@patch(
    "app.projects.service.get_active_project_count_per_cluster",
    return_value=1,
)
@patch(
    "app.projects.service.get_organization_by_id",
    return_value=Organization(
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        name="TestOrganization",
        keycloak_organization_id="1fa3c3b8-31af-1413-3143-1234567890ab",
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
)
async def test_create_project(_, __, ___, ____):
    project_data = ProjectCreate(
        name="test-project",
        description="A test project",
        cluster_id=uuid4(),
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
            gpu_count=0,
            description="test quota",
        ),
    )
    cluster = ClusterModel(
        id=uuid4(),
        organization_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        name="TestCluster",
        base_url="https://test-cluster.example.com",
        last_heartbeat_at=datetime.now(tz=UTC),
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    creator = "test_creator"

    project = await create_project(
        AsyncMock(spec=KeycloakAdmin), AsyncMock(spec=AsyncSession), cluster, project_data, creator
    )

    assert project.name == "test-project"
    assert project.description == "A test project"
    assert project.organization_id == "f33bf805-2a5f-4f01-8e3b-339fd8c9e092"
    assert project.keycloak_group_id == "1fa3c3b8-31af-1413-3143-1234567890ab"


@pytest.mark.asyncio
@patch(
    "app.projects.service.create_project_in_db",
    return_value=Project(
        name="test-project",
        description="A test project",
        organization_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
    autospec=True,
)
async def test_create_project_unhealthy_cluster(_):
    project_data = ProjectCreate(
        name="test-project",
        description="A test project",
        cluster_id=uuid4(),
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
            gpu_count=0,
            description="test quota",
        ),
    )
    cluster = ClusterModel(
        id=uuid4(),
        organization_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        name="TestCluster",
        base_url="https://test-cluster.example.com",
        last_heartbeat_at=datetime.now(tz=UTC) - timedelta(10),
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    creator = "test_creator"

    with pytest.raises(UnhealthyException) as e:
        await create_project(
            AsyncMock(spec=KeycloakAdmin), AsyncMock(spec=AsyncSession), cluster, project_data, creator
        )

    assert "Project cannot be created for an unhealthy cluster." in str(e.value)


@pytest.mark.asyncio
@patch(
    "app.projects.service.create_project_in_db",
    return_value=Project(
        name="test-project",
        description="A test project",
        organization_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        cluster_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    ),
    autospec=True,
)
@patch(
    "app.projects.service.get_active_project_count_per_cluster",
    return_value=2000,
)
async def test_create_project_too_many_projects(_, __):
    project_data = ProjectCreate(
        name="test-project",
        description="A test project",
        cluster_id=uuid4(),
        quota=QuotaBase(
            cpu_milli_cores=1000,
            memory_bytes=1024 * 1024 * 1024,
            ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
            gpu_count=0,
            description="test quota",
        ),
    )
    cluster = ClusterModel(
        id=uuid4(),
        organization_id="f33bf805-2a5f-4f01-8e3b-339fd8c9e092",
        name="TestCluster",
        base_url="https://test-cluster.example.com",
        last_heartbeat_at=datetime.now(tz=UTC),
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    creator = "test_creator"

    with pytest.raises(ValidationException) as e:
        await create_project(
            AsyncMock(spec=KeycloakAdmin), AsyncMock(spec=AsyncSession), cluster, project_data, creator
        )

    assert "Maximum of 999 projects per cluster exceeded." in str(e.value)


@pytest.mark.asyncio
async def test_add_users_to_project_success(db_session: AsyncSession):
    """Test adding users to project with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    users = await factory.create_multiple_users(db_session, env.organization, user_count=2)
    user_ids = [user.id for user in users]
    kc_admin = AsyncMock(spec=KeycloakAdmin)

    await add_users_to_project_and_keycloak_group(kc_admin, db_session, env.project, user_ids)


@pytest.mark.asyncio
async def test_add_users_to_project_user_not_found(db_session: AsyncSession):
    """Test adding non-existent users to project raises NotFoundException."""
    env = await factory.create_basic_test_environment(db_session)

    user_ids = [uuid4()]
    kc_admin = AsyncMock(spec=KeycloakAdmin)

    with pytest.raises(NotFoundException) as exc_info:
        await add_users_to_project_and_keycloak_group(kc_admin, db_session, env.project, user_ids)

    assert "Some users not found in the organization." in str(exc_info.value)


@pytest.mark.asyncio
async def test_remove_user_from_project_success(db_session: AsyncSession):
    """Test removing user from project with real database operations."""
    env = await factory.create_full_test_environment(db_session)
    kc_admin = AsyncMock(spec=KeycloakAdmin)

    await remove_user_from_project_and_keycloak_group(kc_admin, db_session, env.project, env.user.id)


@pytest.mark.asyncio
async def test_get_projects_with_resource_allocation(db_session: AsyncSession):
    """Test getting projects with resource allocation information."""
    # Create environment with project that has a quota
    env = await factory.create_basic_test_environment(db_session, create_project_quota=True)
    project1, quota1 = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-with-quota"
    )

    # Test the function
    result = await get_projects_with_resource_allocation(db_session, env.organization)

    assert isinstance(result, ProjectsWithResourceAllocation)
    assert len(result.projects) >= 1  # Should include our project plus potentially the base environment project

    # Find our project in the results
    project_result = None
    for p in result.projects:
        if p.id == project1.id:
            project_result = p
            break

    assert project_result is not None, "Project not found in results"
    assert project_result.name == project1.name

    # Check that computed fields are present
    assert hasattr(project_result, "gpu_allocation_percentage")
    assert hasattr(project_result, "gpu_allocation_exceeded")
    assert hasattr(project_result, "cpu_allocation_percentage")
    assert hasattr(project_result, "cpu_allocation_exceeded")
    assert hasattr(project_result, "memory_allocation_percentage")
    assert hasattr(project_result, "memory_allocation_exceeded")

    # Verify allocation percentages are numeric values
    assert isinstance(project_result.gpu_allocation_percentage, int | float)
    assert isinstance(project_result.cpu_allocation_percentage, int | float)
    assert isinstance(project_result.memory_allocation_percentage, int | float)

    # Verify exceeded flags are boolean values
    assert isinstance(project_result.gpu_allocation_exceeded, bool)
    assert isinstance(project_result.cpu_allocation_exceeded, bool)
    assert isinstance(project_result.memory_allocation_exceeded, bool)


@pytest.mark.asyncio
async def test_get_projects_with_resource_allocation_no_projects(db_session: AsyncSession):
    """Test getting projects with resource allocation when no projects exist."""
    # Create organization with no projects
    organization = await factory.create_organization(db_session)

    result = await get_projects_with_resource_allocation(db_session, organization)

    assert isinstance(result, ProjectsWithResourceAllocation)
    assert len(result.projects) == 0


@pytest.mark.asyncio
async def test_get_submittable_projects(db_session: AsyncSession):
    """Test getting submittable projects with new Keycloak-based approach."""
    env = await factory.create_basic_test_environment(db_session)

    # Create project with quota for this test
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="submittable-project"
    )

    # Refresh project to load relationships
    await db_session.refresh(project, ["quota", "cluster"])

    # Test with list of accessible projects (from Keycloak groups)
    accessible_projects = [project]
    result = await get_submittable_projects(accessible_projects)

    assert isinstance(result, Projects)
    assert len(result.projects) == 1
    assert result.projects[0].id == project.id
    assert result.projects[0].name == "submittable-project"
    assert result.projects[0].cluster is not None
    assert result.projects[0].quota is not None


@pytest.mark.asyncio
@patch("app.projects.service.get_cluster_with_resources")
@patch("app.projects.service.validate_quota_against_available_cluster_resources")
@patch("app.projects.service.create_quota_for_cluster")
async def test_create_quota_success(
    mock_create_quota,
    mock_validate_quota,
    mock_get_cluster_resources,
    db_session: AsyncSession,
):
    """Test creating quota with valid resources using real database operations."""
    env = await factory.create_basic_test_environment(db_session)
    session = AsyncMock(spec=AsyncSession)

    cluster = ClusterResponse(
        id=str(env.cluster.id),
        name="test-cluster",
        base_url="https://test-cluster.example.com",
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    quota_data = QuotaBase(
        cpu_milli_cores=1000,
        memory_bytes=1024 * 1024 * 1024,
        ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
        gpu_count=0,
    )

    user = "test@example.com"

    cluster_with_resources = MagicMock()
    cluster_with_resources.gpu_info.vendor = "NVIDIA"
    mock_get_cluster_resources.return_value = cluster_with_resources

    mock_validate_quota.return_value = []

    expected_quota = QuotaResponse(
        id=str(uuid4()),
        cpu_milli_cores=1000,
        memory_bytes=1024 * 1024 * 1024,
        ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
        gpu_count=0,
        status="Ready",
        project=env.project,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    mock_create_quota.return_value = expected_quota

    result = await create_quota(session, env.project, cluster, quota_data, user)

    assert result == expected_quota

    mock_get_cluster_resources.assert_called_once_with(session, cluster)
    mock_validate_quota.assert_called_once()
    mock_create_quota.assert_called_once()

    quota_create = mock_create_quota.call_args[0][4]
    assert quota_create.cpu_milli_cores == 1000
    assert quota_create.memory_bytes == 1024 * 1024 * 1024
    assert quota_create.ephemeral_storage_bytes == 5 * 1024 * 1024 * 1024
    assert quota_create.gpu_count == 0
    assert quota_create.cluster_id == env.project.cluster_id
    assert quota_create.project_id == env.project.id


@pytest.mark.asyncio
@patch("app.projects.service.get_cluster_with_resources")
@patch("app.projects.service.validate_quota_against_available_cluster_resources")
async def test_create_quota_validation_error(mock_validate_quota, mock_get_cluster_resources, db_session: AsyncSession):
    """Test that quota validation errors are properly raised."""
    env = await factory.create_basic_test_environment(db_session)
    session = AsyncMock(spec=AsyncSession)

    cluster = ClusterResponse(
        id=str(env.cluster.id),
        name="test-cluster",
        base_url="https://test-cluster.example.com",
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    quota_data = QuotaBase(
        cpu_milli_cores=1000000,
        memory_bytes=1024 * 1024 * 1024 * 1024,
        ephemeral_storage_bytes=5 * 1024 * 1024 * 1024,
        gpu_count=0,
    )

    user = "test@example.com"

    cluster_with_resources = MagicMock()
    mock_get_cluster_resources.return_value = cluster_with_resources

    mock_validate_quota.return_value = ["CPU exceeds limit", "Memory exceeds limit"]

    with pytest.raises(ValidationException) as exc_info:
        await create_quota(session, env.project, cluster, quota_data, user)

    assert "Quota exceeds available cluster resources" in str(exc_info.value)
    assert "CPU exceeds limit" in str(exc_info.value)
    assert "Memory exceeds limit" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.projects.service.get_namespace_by_project_and_cluster")
@patch("app.projects.service.update_project_status")
@patch("app.projects.service.resolve_project_status")
async def test_update_project_status_from_components_success(
    mock_resolve_status, mock_update_status, mock_get_namespace, db_session: AsyncSession
):
    """Test successful update of project status from components."""

    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-with-quota"
    )

    namespace = MagicMock()
    namespace.status = "Active"
    namespace.status_reason = "Ready"
    mock_get_namespace.return_value = namespace
    dummy_kc_admin = object()
    mock_resolve_status.return_value = (ProjectStatus.READY, "All components ready")

    await update_project_status_from_components(dummy_kc_admin, db_session, project)

    mock_get_namespace.assert_called_once_with(db_session, project.id, project.cluster_id)
    mock_resolve_status.assert_called_once_with(namespace, quota, project)
    mock_update_status.assert_called_once_with(
        db_session, project, ProjectStatus.READY, "All components ready", "system"
    )


@pytest.mark.asyncio
@patch("app.projects.service.get_namespace_by_project_and_cluster")
@patch("app.projects.service.update_project_status")
async def test_update_project_status_from_components_namespace_not_found(
    mock_update_status, mock_get_namespace, db_session: AsyncSession
):
    """Test update when namespace is not found."""
    env = await factory.create_basic_test_environment(db_session)

    mock_get_namespace.return_value = None
    dummy_kc_admin = object()

    await update_project_status_from_components(dummy_kc_admin, db_session, env.project)

    mock_get_namespace.assert_called_once_with(db_session, env.project.id, env.project.cluster_id)
    mock_update_status.assert_called_once_with(
        db_session, env.project, ProjectStatus.FAILED, "Namespace not found", "system"
    )


@pytest.mark.asyncio
@patch("app.projects.service.get_namespace_by_project_and_cluster")
@patch("app.projects.service.update_project_status")
async def test_update_project_status_from_components_quota_not_found(
    mock_update_status, mock_get_namespace, db_session: AsyncSession
):
    """Test update when quota is not found."""
    env = await factory.create_basic_test_environment(db_session)

    namespace = MagicMock()
    mock_get_namespace.return_value = namespace
    dummy_kc_admin = object()

    # Use the project without quota from the basic environment
    await update_project_status_from_components(dummy_kc_admin, db_session, env.project)

    mock_get_namespace.assert_called_once_with(db_session, env.project.id, env.project.cluster_id)
    mock_update_status.assert_called_once_with(
        db_session, env.project, ProjectStatus.FAILED, "Quota not found", "system"
    )


@pytest.mark.asyncio
@patch("app.projects.service.get_namespace_by_project_and_cluster")
@patch("app.projects.service.update_project_status")
@patch("app.projects.service.resolve_project_status")
async def test_update_project_status_from_components_failed_status(
    mock_resolve_status, mock_update_status, mock_get_namespace, db_session: AsyncSession
):
    """Test update when components indicate failed status."""
    env = await factory.create_basic_test_environment(db_session)

    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-failed"
    )

    namespace = MagicMock()
    namespace.status = "Failed"
    namespace.status_reason = "Creation failed"
    mock_get_namespace.return_value = namespace
    dummy_kc_admin = object()

    mock_resolve_status.return_value = (
        ProjectStatus.FAILED,
        "Failed components: namespace. namespace: Creation failed",
    )

    await update_project_status_from_components(dummy_kc_admin, db_session, project)

    mock_get_namespace.assert_called_once_with(db_session, project.id, project.cluster_id)
    mock_resolve_status.assert_called_once_with(namespace, quota, project)
    mock_update_status.assert_called_once_with(
        db_session, project, ProjectStatus.FAILED, "Failed components: namespace. namespace: Creation failed", "system"
    )


@pytest.mark.asyncio
@patch("app.projects.service.ensure_project_safe_to_delete")
@patch("app.projects.service.delete_quota_for_cluster")
@patch("app.projects.service.delete_namespace_in_cluster")
@patch("app.projects.service.update_project_status")
async def test_submit_delete_project_success(
    mock_update_project_status,
    mock_delete_namespace,
    mock_delete_quota,
    mock_ensure_safe_to_delete,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-to-delete"
    )

    await db_session.refresh(project, ["cluster", "quota"])

    user = "test_user@example.com"
    gpu_vendor = "NVIDIA"

    await submit_delete_project(db_session, project, user, gpu_vendor)

    mock_ensure_safe_to_delete.assert_called_once_with(project)
    mock_delete_quota.assert_called_once_with(db_session, quota, project.cluster, gpu_vendor, user)
    mock_delete_namespace.assert_called_once_with(db_session, project, user)
    mock_update_project_status.assert_called_once_with(
        db_session, project, ProjectStatus.DELETING, "Project is being deleted", user
    )


@pytest.mark.asyncio
@patch("app.projects.service.ensure_project_safe_to_delete")
@patch("app.projects.service.delete_quota_for_cluster")
@patch("app.projects.service.delete_namespace_in_cluster")
@patch("app.projects.service.update_project_status")
async def test_submit_delete_project_with_none_gpu_vendor(
    mock_update_project_status,
    mock_delete_namespace,
    mock_delete_quota,
    mock_ensure_safe_to_delete,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-no-gpu"
    )

    await db_session.refresh(project, ["cluster", "quota"])

    user = "test_user@example.com"
    gpu_vendor = None

    await submit_delete_project(db_session, project, user, gpu_vendor)

    mock_ensure_safe_to_delete.assert_called_once_with(project)
    mock_delete_quota.assert_called_once_with(db_session, quota, project.cluster, gpu_vendor, user)
    mock_delete_namespace.assert_called_once_with(db_session, project, user)
    mock_update_project_status.assert_called_once_with(
        db_session, project, ProjectStatus.DELETING, "Project is being deleted", user
    )


@pytest.mark.asyncio
@patch("app.projects.service.ensure_project_safe_to_delete")
@patch("app.projects.service.delete_quota_for_cluster")
@patch("app.projects.service.delete_namespace_in_cluster")
@patch("app.projects.service.update_project_status")
async def test_submit_delete_project_not_safe_to_delete(
    mock_update_project_status,
    mock_delete_namespace,
    mock_delete_quota,
    mock_ensure_safe_to_delete,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-unsafe"
    )

    await db_session.refresh(project, ["cluster", "quota"])

    user = "test_user@example.com"
    gpu_vendor = "NVIDIA"

    mock_ensure_safe_to_delete.side_effect = ValidationException("Project has active workloads")

    with pytest.raises(ValidationException) as exc_info:
        await submit_delete_project(db_session, project, user, gpu_vendor)

    assert "Project has active workloads" in str(exc_info.value)
    mock_ensure_safe_to_delete.assert_called_once_with(project)

    mock_delete_quota.assert_not_called()
    mock_delete_namespace.assert_not_called()
    mock_update_project_status.assert_not_called()


@pytest.mark.asyncio
@patch("app.projects.service.delete_project")
@patch("app.projects.service.delete_group")
async def test_delete_project_if_components_deleted_success(
    mock_delete_group,
    mock_delete_project,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-to-delete"
    )

    namespace = MagicMock()
    namespace.status = NamespaceStatus.DELETED

    project.status = ProjectStatus.DELETING
    quota.status = QuotaStatus.DELETED
    project.keycloak_group_id = "test-group-id"

    dummy_kc_admin = object()

    result = await delete_project_if_components_deleted(dummy_kc_admin, db_session, project, quota, namespace)

    assert result is True
    mock_delete_project.assert_called_once_with(db_session, project)
    mock_delete_group.assert_called_once_with(dummy_kc_admin, "test-group-id")


@pytest.mark.asyncio
@patch("app.projects.service.delete_project")
@patch("app.projects.service.delete_group")
async def test_delete_project_if_components_deleted_project_not_deleting(
    mock_delete_group,
    mock_delete_project,
    db_session: AsyncSession,
):
    """Test that project is not deleted when project status is not DELETING."""
    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-active"
    )

    namespace = MagicMock()
    namespace.status = NamespaceStatus.DELETED

    project.status = ProjectStatus.READY
    quota.status = QuotaStatus.DELETED

    dummy_kc_admin = object()

    result = await delete_project_if_components_deleted(dummy_kc_admin, db_session, project, quota, namespace)

    assert result is False
    mock_delete_project.assert_not_called()
    mock_delete_group.assert_not_called()


@pytest.mark.asyncio
@patch("app.projects.service.delete_project")
@patch("app.projects.service.delete_group")
async def test_delete_project_if_components_deleted_quota_not_deleted(
    mock_delete_group,
    mock_delete_project,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-quota-pending"
    )

    namespace = MagicMock()
    namespace.status = NamespaceStatus.DELETED

    project.status = ProjectStatus.DELETING
    quota.status = QuotaStatus.PENDING

    dummy_kc_admin = object()

    result = await delete_project_if_components_deleted(dummy_kc_admin, db_session, project, quota, namespace)

    assert result is False
    mock_delete_project.assert_not_called()
    mock_delete_group.assert_not_called()


@pytest.mark.asyncio
@patch("app.projects.service.delete_project")
@patch("app.projects.service.delete_group")
async def test_delete_project_if_components_deleted_namespace_not_deleted(
    mock_delete_group,
    mock_delete_project,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    project, quota = await factory.create_project_with_quota(
        db_session, env.organization, env.cluster, project_name="test-project-namespace-active"
    )

    namespace = MagicMock()
    namespace.status = NamespaceStatus.ACTIVE

    project.status = ProjectStatus.DELETING
    quota.status = QuotaStatus.DELETED

    dummy_kc_admin = object()

    result = await delete_project_if_components_deleted(dummy_kc_admin, db_session, project, quota, namespace)

    assert result is False
    mock_delete_project.assert_not_called()
    mock_delete_group.assert_not_called()
