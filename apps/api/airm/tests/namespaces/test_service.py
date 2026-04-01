# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from keycloak import KeycloakAdmin
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.schemas import (
    NamespaceDeletedMessage,
    NamespaceStatus,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceStatusMessage,
    QuotaStatus,
    UnmanagedNamespaceMessage,
)
from app.namespaces.repository import (
    get_namespace_by_name_and_cluster,
    get_namespace_by_project_and_cluster,
)
from app.namespaces.service import (
    create_namespace_for_project,
    delete_namespace_in_cluster,
    handle_namespace_deleted,
    record_unmanaged_namespace,
    update_project_namespace_status,
)
from app.projects.enums import ProjectStatus
from app.projects.repository import get_project_by_id
from app.utilities.exceptions import NotFoundException
from app.workloads.constants import PROJECT_ID_LABEL
from tests import factory  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_create_namespace_for_project_success(db_session: AsyncSession) -> None:
    """Test creating namespace for project with real database operations."""
    env = await factory.create_basic_test_environment(db_session)
    user = "test_user@example.com"

    mock_message_sender = AsyncMock()

    namespace = await create_namespace_for_project(db_session, env.project, env.cluster.id, user, mock_message_sender)

    assert namespace.project_id == env.project.id
    assert namespace.name == env.project.name
    assert namespace.cluster_id == env.cluster.id
    assert namespace.status == NamespaceStatus.PENDING
    assert namespace.status_reason == "creating"
    assert namespace.created_by == user
    assert namespace.updated_by == user

    mock_message_sender.enqueue.assert_awaited_once()
    args, kwargs = mock_message_sender.enqueue.call_args
    assert args[0] == env.project.cluster_id
    assert isinstance(args[1], ProjectNamespaceCreateMessage)
    assert args[1].message_type == "project_namespace_create"
    assert args[1].namespace_manifest.metadata.name == namespace.name
    assert args[1].namespace_manifest.metadata.labels is not None
    assert args[1].namespace_manifest.metadata.labels.get(PROJECT_ID_LABEL) == str(env.project.id)

    stored_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)
    assert stored_namespace is not None
    assert stored_namespace.name == env.project.name


@pytest.mark.asyncio
async def test_create_namespace_for_project_db_error(db_session: AsyncSession) -> None:
    """Test namespace creation with database error."""
    env = await factory.create_basic_test_environment(db_session)
    user = "test_user@example.com"

    mock_message_sender = AsyncMock()

    with patch("app.namespaces.service.create_namespace", side_effect=Exception("Database error")):
        with pytest.raises(Exception) as exc_info:
            await create_namespace_for_project(db_session, env.project, env.cluster.id, user, mock_message_sender)

    assert "Database error" in str(exc_info.value)
    mock_message_sender.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_project_namespace_status_success(db_session: AsyncSession) -> None:
    """Test updating project namespace status with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    namespace = await factory.create_namespace(
        db_session,
        cluster=env.cluster,
        project=env.project,
        status=NamespaceStatus.PENDING.value,
        status_reason="creating",
    )

    message = ProjectNamespaceStatusMessage(
        message_type="project_namespace_status",
        project_id=env.project.id,
        status=NamespaceStatus.ACTIVE,
        status_reason="namespace is ready",
        updated_at=datetime.now(UTC),
    )

    dummy_kc_admin = object()

    with patch("app.projects.service.update_project_status_from_components") as mock_update_project_status:
        await update_project_namespace_status(dummy_kc_admin, db_session, env.cluster, message)

    mock_update_project_status.assert_awaited_once_with(dummy_kc_admin, db_session, env.project)

    updated_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)
    assert updated_namespace is not None
    assert updated_namespace.status == NamespaceStatus.ACTIVE
    assert updated_namespace.status_reason == "namespace is ready"


@pytest.mark.asyncio
async def test_update_project_namespace_status_namespace_not_found(db_session: AsyncSession) -> None:
    """Test updating namespace status when namespace doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    non_existent_project_id = uuid4()
    message = ProjectNamespaceStatusMessage(
        message_type="project_namespace_status",
        project_id=non_existent_project_id,
        status=NamespaceStatus.ACTIVE,
        status_reason="namespace is ready",
        updated_at=datetime.now(UTC),
    )

    dummy_kc_admin = object()

    with pytest.raises(NotFoundException) as exc_info:
        await update_project_namespace_status(dummy_kc_admin, db_session, env.cluster, message)

    assert f"Namespace for project {message.project_id} not found in cluster {env.cluster.id}." in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_project_namespace_status_project_not_found(db_session: AsyncSession) -> None:
    """Test updating namespace status when project doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    _ = await factory.create_namespace(
        db_session,
        cluster=env.cluster,
        project=env.project,
        status=NamespaceStatus.PENDING.value,
        status_reason="creating",
    )

    message = ProjectNamespaceStatusMessage(
        message_type="project_namespace_status",
        project_id=env.project.id,
        status=NamespaceStatus.ACTIVE,
        status_reason="namespace is ready",
        updated_at=datetime.now(UTC),
    )

    dummy_kc_admin = object()

    with (
        patch("app.namespaces.service.get_project_by_id", return_value=None),
        pytest.raises(NotFoundException) as exc_info,
    ):
        await update_project_namespace_status(dummy_kc_admin, db_session, env.cluster, message)

    assert f"Project {env.project.id} not found." in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_namespace_in_cluster_success(db_session: AsyncSession) -> None:
    """Test deleting namespace with real database operations."""
    env = await factory.create_basic_test_environment(db_session)

    _ = await factory.create_namespace(
        db_session,
        cluster=env.cluster,
        project=env.project,
        status=NamespaceStatus.ACTIVE.value,
        status_reason="namespace is ready",
    )

    updater = "test_user@example.com"
    mock_message_sender = AsyncMock()

    await delete_namespace_in_cluster(db_session, env.project, updater, mock_message_sender)

    mock_message_sender.enqueue.assert_awaited_once()
    args, kwargs = mock_message_sender.enqueue.call_args
    assert args[0] == env.project.cluster_id
    assert args[1].message_type == "project_namespace_delete"
    assert args[1].name == env.project.name
    assert args[1].project_id == env.project.id

    updated_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)
    assert updated_namespace is not None
    assert updated_namespace.status == NamespaceStatus.TERMINATING
    assert updated_namespace.status_reason == "Namespace is being deleted"


@pytest.mark.asyncio
async def test_delete_namespace_in_cluster_namespace_not_found(db_session: AsyncSession) -> None:
    """Test deleting namespace when it doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    updater = "test_user@example.com"
    mock_message_sender = AsyncMock()

    with pytest.raises(NotFoundException) as exc_info:
        await delete_namespace_in_cluster(db_session, env.project, updater, mock_message_sender)

    assert f"Namespace for project {env.project.id} not found in cluster {env.project.cluster_id}." in str(
        exc_info.value
    )
    mock_message_sender.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_unmanaged_namespace_create_new(db_session: AsyncSession) -> None:
    """Test recording unmanaged namespace creates new namespace when it doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    message = UnmanagedNamespaceMessage(
        message_type="unmanaged_namespace", namespace_name="external-namespace", namespace_status=NamespaceStatus.ACTIVE
    )

    await record_unmanaged_namespace(db_session, env.cluster, message)

    created_namespace = await get_namespace_by_name_and_cluster(db_session, env.cluster.id, message.namespace_name)
    assert created_namespace is not None
    assert created_namespace.name == message.namespace_name
    assert created_namespace.cluster_id == env.cluster.id
    assert created_namespace.project_id is None  # Unmanaged
    assert created_namespace.status == NamespaceStatus.ACTIVE
    assert created_namespace.status_reason == "Unmanaged namespace status: Active"


@pytest.mark.asyncio
async def test_record_unmanaged_namespace_update_existing(db_session: AsyncSession) -> None:
    """Test recording unmanaged namespace updates existing namespace when found."""
    env = await factory.create_basic_test_environment(db_session)

    existing_namespace = await factory.create_namespace(
        db_session,
        cluster=env.cluster,
        project=None,
        name="external-namespace",
        status=NamespaceStatus.ACTIVE.value,
        status_reason="Unmanaged namespace",
        creator="system",
    )

    message = UnmanagedNamespaceMessage(
        message_type="unmanaged_namespace",
        namespace_name="external-namespace",
        namespace_status=NamespaceStatus.TERMINATING,
    )

    await record_unmanaged_namespace(db_session, env.cluster, message)

    updated_namespace = await get_namespace_by_name_and_cluster(db_session, env.cluster.id, message.namespace_name)
    assert updated_namespace is not None
    assert updated_namespace.id == existing_namespace.id
    assert updated_namespace.status == NamespaceStatus.TERMINATING


@pytest.mark.asyncio
async def test_handle_namespace_deleted_managed_namespace(db_session: AsyncSession) -> None:
    """Test handling namespace deleted message for a managed namespace, where project is not DELETING."""
    env = await factory.create_basic_test_environment(db_session)

    namespace = await factory.create_namespace(
        db_session,
        cluster=env.cluster,
        project=env.project,
        status=NamespaceStatus.TERMINATING.value,
        status_reason="Namespace is being deleted",
    )

    message = NamespaceDeletedMessage(
        message_type="namespace_deleted",
        namespace_name=namespace.name,
    )

    await handle_namespace_deleted(AsyncMock(spec=KeycloakAdmin), db_session, env.cluster, message)

    updated_namespace = await get_namespace_by_name_and_cluster(db_session, env.cluster.id, namespace.name)
    assert updated_namespace is not None
    assert updated_namespace.status == NamespaceStatus.DELETED
    assert updated_namespace.status_reason == "Namespace deleted"

    project = await get_project_by_id(db_session, env.project.id)
    assert project is not None
    assert project.status == ProjectStatus.FAILED


@patch("app.projects.service.delete_group")
@pytest.mark.asyncio
async def test_handle_namespace_deleted_managed_namespace_deleting_project(
    mock_delete_group: MagicMock, db_session: AsyncSession
) -> None:
    """Test handling namespace deleted message for a managed namespace, where the project is in DELETING status."""
    env = await factory.create_basic_test_environment(db_session, create_project_quota=True)
    env.project.status = ProjectStatus.DELETING
    env.project.quota.status = QuotaStatus.DELETED
    env.project.keycloak_group_id = "test-group-id"
    await db_session.flush()

    namespace = await factory.create_namespace(
        db_session,
        cluster=env.cluster,
        project=env.project,
        status=NamespaceStatus.TERMINATING.value,
        status_reason="Namespace is being deleted",
    )

    message = NamespaceDeletedMessage(
        message_type="namespace_deleted",
        namespace_name=namespace.name,
    )

    dummy_kc_admin = AsyncMock(spec=KeycloakAdmin)

    await handle_namespace_deleted(dummy_kc_admin, db_session, env.cluster, message)

    assert await get_namespace_by_name_and_cluster(db_session, env.cluster.id, namespace.name) is None
    assert await get_project_by_id(db_session, env.project.id) is None

    mock_delete_group.assert_awaited_once_with(dummy_kc_admin, "test-group-id")


@pytest.mark.asyncio
async def test_handle_namespace_deleted_unmanaged_namespace(db_session: AsyncSession) -> None:
    """Test handling namespace deleted message for an unmanaged namespace."""
    env = await factory.create_basic_test_environment(db_session)
    namespace = await factory.create_namespace(
        db_session,
        cluster=env.cluster,
        project=None,
        name="unmanaged-namespace",
        status=NamespaceStatus.TERMINATING.value,
        status_reason="Unmanaged namespace being deleted",
        creator="system",
    )

    message = NamespaceDeletedMessage(
        message_type="namespace_deleted",
        namespace_name=namespace.name,
    )

    await handle_namespace_deleted(AsyncMock(spec=KeycloakAdmin), db_session, env.cluster, message)
    assert await get_namespace_by_name_and_cluster(db_session, env.cluster.id, namespace.name) is None


@pytest.mark.asyncio
async def test_handle_namespace_deleted_namespace_not_found(db_session: AsyncSession) -> None:
    """Test handling namespace deleted message when namespace doesn't exist in database."""
    env = await factory.create_basic_test_environment(db_session)

    message = NamespaceDeletedMessage(
        message_type="namespace_deleted",
        namespace_name="nonexistent-namespace",
    )

    with pytest.raises(NotFoundException):
        await handle_namespace_deleted(AsyncMock(spec=KeycloakAdmin), db_session, env.cluster, message)
