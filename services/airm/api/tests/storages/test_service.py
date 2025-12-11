# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from airm.messaging.schemas import (
    ConfigMapStatus,
    ProjectSecretStatus,
    ProjectStorageStatus,
    ProjectStorageUpdateMessage,
    SecretScope,
)
from app.projects.enums import ProjectStatus
from app.secrets.enums import SecretUseCase
from app.storages.enums import StorageScope, StorageStatus, StorageType
from app.storages.models import ProjectStorage as ProjectStorageModel
from app.storages.models import Storage as StorageModel
from app.storages.repository import create_project_storage_configmap, get_project_storage
from app.storages.schemas import ProjectStoragesWithParentStorage, S3Spec, StorageIn, Storages
from app.storages.service import (
    create_storage_in_organization,
    get_project_storages_in_project,
    get_storages_with_assigned_project_storages,
    submit_delete_project_storage,
    submit_delete_storage,
    update_configmap_status,
    update_project_storage_assignments,
    update_project_storage_composite_status,
    update_project_storage_secret_status,
    update_storage_overall_status,
)
from app.utilities.exceptions import ConflictException, NotFoundException, ValidationException
from tests import factory


@pytest.mark.asyncio
async def test_get_storages_with_assigned_project_storages_all_storages(db_session: AsyncSession):
    """Test retrieving all storages with their project assignments."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        name="storage1",
        storage_status=StorageStatus.SYNCED.value,
    )

    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        name="storage2",
        storage_status=StorageStatus.SYNCED.value,
    )

    result = await get_storages_with_assigned_project_storages(db_session, env.organization)

    assert isinstance(result, Storages)
    assert len(result.storages) == 2
    storage_names = [storage.name for storage in result.storages]
    assert "storage1" in storage_names
    assert "storage2" in storage_names

    for secret in result.storages:
        assert len(secret.project_storages) == 1
        assert secret.project_storages[0].project_id == env.project.id
        assert secret.project_storages[0].project_name == env.project.name


@pytest.mark.asyncio
async def test_get_storages_with_assigned_project_storages_filtered_by_project(db_session: AsyncSession):
    """Test retrieving storages filtered by specific project."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-002")

    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        name="storage1",
        storage_status=StorageStatus.SYNCED.value,
    )

    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        project2,
        secret,
        name="storage2",
        storage_status=StorageStatus.SYNCED.value,
    )

    result = await get_storages_with_assigned_project_storages(db_session, env.organization, env.project)

    assert len(result.storages) == 1
    assert result.storages[0].name == "storage1"
    assert len(result.storages[0].project_storages) == 1
    assert result.storages[0].project_storages[0].project_name == env.project.name


@pytest.mark.asyncio
async def test_get_storages_with_assigned_project_storages_no_storages(db_session: AsyncSession):
    """Test retrieving storages when none exist."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    await factory.create_storage(db_session, env.organization, secret_id=secret.id)

    result = await get_storages_with_assigned_project_storages(db_session, env.organization, env.project)

    assert isinstance(result, Storages)
    assert len(result.storages) == 0


@pytest.mark.asyncio
async def test_get_storages_with_no_project_storages(db_session: AsyncSession):
    """Test retrieving storages that have no project assignments."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    await factory.create_storage(
        db_session,
        env.organization,
        name="db-password",
        storage_type=StorageType.S3.value,
        status=StorageStatus.PENDING.value,
        secret_id=secret.id,
    )

    result = await get_storages_with_assigned_project_storages(db_session, env.organization)

    assert isinstance(result, Storages)
    assert len(result.storages) == 1
    assert result.storages[0].project_storages == []


@pytest.mark.asyncio
async def test_get_project_storages_in_project(db_session: AsyncSession):
    """Test retrieving project storages for a specific project."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret=secret,
        name="new-storage",
        storage_status=StorageStatus.SYNCED.value,
        project_storage_status=ProjectStorageStatus.SYNCED.value,
    )

    result = await get_project_storages_in_project(db_session, env.organization, env.project)

    assert isinstance(result, ProjectStoragesWithParentStorage)
    assert len(result.project_storages) == 1

    project_storage = result.project_storages[0]
    assert project_storage.project_id == env.project.id
    assert project_storage.status == ProjectStorageStatus.SYNCED
    assert project_storage.storage.name == "new-storage"
    assert project_storage.storage.type == StorageType.S3
    assert project_storage.storage.status == StorageStatus.SYNCED
    assert project_storage.storage.scope == StorageScope.ORGANIZATION


@pytest.mark.asyncio
async def test_create_storage_without_projects(db_session: AsyncSession):
    """Test successful storage creation without project assignments."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    storage_in = StorageIn(
        name="test-storage",
        type=StorageType.S3,
        scope=StorageScope.ORGANIZATION,
        secret_id=secret.id,
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        project_ids=[],
    )

    with (
        patch("app.storages.service.get_organization_secret_assignment") as mock_get_organization_secret_assignment,
        patch(
            "app.storages.service.create_organization_secret_assignment"
        ) as mock_create_organization_secret_assignment,
    ):
        result = await create_storage_in_organization(
            db_session, env.organization.id, "test", storage_in, message_sender=mock_message_sender
        )

    assert result is not None
    assert result.name == "test-storage"
    assert result.type == StorageType.S3
    assert result.scope == StorageScope.ORGANIZATION
    assert result.status == StorageStatus.UNASSIGNED
    assert result.project_storages == []

    mock_get_organization_secret_assignment.assert_not_awaited()
    mock_create_organization_secret_assignment.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_storage_with_projects(db_session: AsyncSession):
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    project = await factory.create_project(
        db_session, env.organization, env.cluster, name="project1", project_status=ProjectStatus.READY
    )

    storage_in = StorageIn(
        name="test-storage",
        type=StorageType.S3,
        scope=StorageScope.ORGANIZATION,
        secret_id=secret.id,
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        project_ids=[project.id],
    )

    fake_project_secret = SimpleNamespace(
        id=uuid4(),
        project_id=project.id,
        project=project,
        secret_id=secret.id,
        secret=secret,
        status=ProjectSecretStatus.PENDING,
    )

    fake_project_storage = SimpleNamespace(
        id=uuid4(),
        project_id=project.id,
        project=project,
        secret_id=secret.id,
        secret=secret,
        status=ProjectStorageStatus.PENDING,
    )

    with (
        patch("app.storages.service.get_organization_secret_assignment") as mock_get_organization_secret_assignment,
        patch(
            "app.storages.service.create_organization_secret_assignment"
        ) as mock_create_organization_secret_assignment,
        patch("app.storages.service.assign_storage_to_projects") as mock_create_project_storage,
        patch("app.storages.service.get_project_storage") as mock_get_project_storage,
        patch("app.storages.service.create_project_storage_configmap") as mock_create_project_storage_configmap,
    ):
        mock_get_organization_secret_assignment.return_value = fake_project_secret
        mock_create_project_storage.return_value = fake_project_storage
        mock_get_project_storage.return_value = fake_project_storage
        result = await create_storage_in_organization(
            db_session, env.organization.id, "test@example.com", storage_in, message_sender=mock_message_sender
        )
    assert result.name == "test-storage"
    assert result.status == StorageStatus.PENDING

    mock_get_organization_secret_assignment.assert_awaited()
    mock_create_organization_secret_assignment.assert_not_awaited()
    mock_create_project_storage.assert_awaited()
    mock_create_project_storage_configmap.assert_awaited()

    assert mock_message_sender.enqueue.await_count == 1


@pytest.mark.asyncio
async def test_create_storage_duplicate_name(db_session: AsyncSession):
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    await factory.create_storage(db_session, env.organization, secret_id=secret.id, name="duplicate-secret")

    storage_in = StorageIn(
        name="duplicate-secret",
        type=StorageType.S3,
        scope=StorageScope.ORGANIZATION,
        secret_id=secret.id,
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        project_ids=[],
    )

    with (
        patch("app.storages.service.get_organization_secret_assignment"),
    ):
        with pytest.raises(
            ConflictException, match=f"A storage with the name '{storage_in.name}' already exists in the organization"
        ):
            await create_storage_in_organization(
                db_session, env.organization.id, "test@example.com", storage_in, message_sender=mock_message_sender
            )


@pytest.mark.asyncio
async def test_create_storage_secret_not_found(db_session: AsyncSession):
    """Test creating storage with non-existent secret raises NotFoundException."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    non_existent_secret_id = uuid4()

    storage_in = StorageIn(
        name="test-storage",
        type=StorageType.S3,
        scope=StorageScope.ORGANIZATION,
        secret_id=non_existent_secret_id,
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        project_ids=[],
    )

    with pytest.raises(NotFoundException, match=f"Secret with ID {non_existent_secret_id} not found in organization"):
        await create_storage_in_organization(
            db_session, env.organization.id, "test@example.com", storage_in, message_sender=mock_message_sender
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "secret_scope,use_case,test_description",
    [
        (
            SecretScope.PROJECT.value,
            SecretUseCase.S3.value,
            "project-scoped secret with S3 use case",
        ),
        (
            SecretScope.ORGANIZATION.value,
            SecretUseCase.HUGGING_FACE.value,
            "organization-scoped secret with HuggingFace use case",
        ),
        (
            SecretScope.ORGANIZATION.value,
            None,
            "organization-scoped secret with no use case",
        ),
    ],
)
async def test_create_storage_invalid_secret_rejected(
    db_session: AsyncSession, secret_scope: str, use_case: str | None, test_description: str
):
    """Test creating storage with invalid secret configuration raises ValidationException."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    # Create a secret with the specified scope and use case
    secret = await factory.create_secret(db_session, env.organization, secret_scope=secret_scope, use_case=use_case)

    storage_in = StorageIn(
        name="test-storage",
        type=StorageType.S3,
        scope=StorageScope.ORGANIZATION,
        secret_id=secret.id,
        spec=S3Spec(
            bucket_url="https://some-bucket-name.s3.amazonaws.com/path/",
            access_key_name="accessKeyName",
            secret_key_name="secretKeyName",
        ),
        project_ids=[],
    )

    with pytest.raises(
        ValidationException,
        match="Only organization-scoped secrets with S3 use case can be used for storage",
    ):
        await create_storage_in_organization(
            db_session, env.organization.id, "test@example.com", storage_in, message_sender=mock_message_sender
        )


@pytest.mark.asyncio
async def test_submit_delete_storage_pending_state(db_session: AsyncSession):
    """Test deleting storage in pending state fails."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.PENDING.value
    )

    user = "test@example.com"
    with pytest.raises(ConflictException, match="Storage is in PENDING state and cannot be deleted"):
        await submit_delete_storage(db_session, storage, user, message_sender=mock_message_sender)


@pytest.mark.asyncio
async def test_submit_delete_storage_already_deleting(db_session: AsyncSession):
    """Test deleting storage already marked for deletion."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.DELETING.value
    )

    user = "test@example.com"
    with pytest.raises(ConflictException, match="Storage is already marked for deletion"):
        await submit_delete_storage(db_session, storage, user, message_sender=mock_message_sender)


@pytest.mark.asyncio
async def test_submit_delete_storage_without_project_storages(db_session: AsyncSession):
    """Test deleting storage without project assignments."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.SYNCED.value
    )

    user = "test@example.com"

    # Eagerly load the project_storages relationship to avoid lazy loading issues
    stmt = (
        select(StorageModel).where(StorageModel.id == storage.id).options(selectinload(StorageModel.project_storages))
    )
    result = await db_session.execute(stmt)
    storage = result.scalar_one()
    await submit_delete_storage(db_session, storage, user, message_sender=mock_message_sender)

    # Verify the storage was deleted directly since it had no project assignments
    # Check by querying the database since the object may be detached
    deleted_storage = await db_session.get(StorageModel, storage.id)
    assert deleted_storage is None or deleted_storage.status == StorageStatus.DELETED.value


@pytest.mark.asyncio
async def test_submit_delete_storage_with_project_secrets(db_session: AsyncSession):
    """Test deleting storage with project assignments."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    storage = await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        name="storage1",
        storage_status=StorageStatus.SYNCED.value,
    )

    user = "test@example.com"

    # Eagerly load the project_storages and their project relationships
    stmt = (
        select(StorageModel)
        .where(StorageModel.id == storage.id)
        .options(selectinload(StorageModel.project_storages).selectinload(ProjectStorageModel.project))
    )
    result = await db_session.execute(stmt)
    storage = result.scalar_one()
    await submit_delete_storage(db_session, storage, user, message_sender=mock_message_sender)

    await db_session.refresh(storage)
    assert storage.status == StorageStatus.DELETING.value

    # Verify project storage status was updated
    project_storage = storage.project_storages[0]
    await db_session.refresh(project_storage)
    assert project_storage.status == ProjectStorageStatus.DELETING.value


@pytest.mark.asyncio
async def test_submit_delete_project_storage_already_deleting(db_session: AsyncSession):
    """Test deleting project storage already marked for deletion."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    storage = await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        name="storage1",
        storage_status=StorageStatus.SYNCED.value,
    )

    project_secret = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )
    project_storage = await factory.create_project_storage(
        db_session, env.project, storage, status=ProjectStorageStatus.DELETING.value
    )

    user = "test@example.com"
    with pytest.raises(ConflictException, match="Project Storage is already marked for deletion"):
        await submit_delete_project_storage(
            db_session, env.organization.id, project_storage, user, message_sender=mock_message_sender
        )


@pytest.mark.asyncio
async def test_submit_delete_project_storage_success(db_session: AsyncSession):
    """Test successful project storage deletion."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)

    storage = await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        name="storage1",
        storage_status=StorageStatus.SYNCED.value,
    )

    project_secret = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )
    project_storage = await factory.create_project_storage(
        db_session, env.project, storage, status=ProjectStorageStatus.SYNCED.value
    )

    user = "test@example.com"
    await submit_delete_project_storage(
        db_session, env.organization.id, project_storage, user, message_sender=mock_message_sender
    )

    await db_session.refresh(project_storage)
    assert project_storage.status == ProjectStorageStatus.DELETING.value


@pytest.mark.asyncio
async def test_update_project_storage_assignments_remove_project(db_session: AsyncSession):
    """Test removing project from storage assignment."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        storage_status=StorageStatus.SYNCED.value,
    )

    stmt = (
        select(StorageModel)
        .where(StorageModel.id == storage.id)
        .options(selectinload(StorageModel.project_storages).selectinload(ProjectStorageModel.project))
    )
    result = await db_session.execute(stmt)
    storage = result.scalar_one()

    user_email = "test@example.com"
    await update_project_storage_assignments(
        session=db_session,
        user_email=user_email,
        organization_id=env.organization.id,
        storage=storage,
        project_ids=[],
        message_sender=mock_message_sender,
    )

    await db_session.refresh(storage)
    assert storage.project_storages[0].status == ProjectStorageStatus.DELETING.value
    assert storage.status == StorageStatus.PENDING.value


@pytest.mark.asyncio
async def test_update_project_storage_assignments_no_changes(db_session: AsyncSession):
    """Test updating project assignments with no changes."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret,
        storage_status=StorageStatus.SYNCED.value,
    )

    stmt = (
        select(StorageModel).where(StorageModel.id == storage.id).options(selectinload(StorageModel.project_storages))
    )
    result = await db_session.execute(stmt)
    storage = result.scalar_one()

    with pytest.raises(ValueError, match="No changes in project assignments"):
        await update_project_storage_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            storage=storage,
            project_ids=[env.project.id],
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
async def test_update_project_storage_assignments_invalid_status(db_session: AsyncSession):
    """Test updating project assignments with invalid storage status."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=StorageStatus.FAILED.value)
    storage = await factory.create_storage(
        db_session,
        env.organization,
        secret_id=secret.id,
        status=StorageStatus.SYNCED.value,
    )

    stmt = (
        select(StorageModel).where(StorageModel.id == storage.id).options(selectinload(StorageModel.project_storages))
    )
    result = await db_session.execute(stmt)
    storage = result.scalar_one()

    with pytest.raises(ValidationException, match=f"project id={env.project.id} not READY"):
        await update_project_storage_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            storage=storage,
            project_ids=[env.project.id],
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
async def test_update_project_storage_assignments_project_not_ready(db_session: AsyncSession):
    """Test updating project assignments when project is not ready."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project = await factory.create_project(db_session, env.organization, env.cluster, name="failed-project")
    project.status = ProjectStatus.FAILED.value

    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage(
        db_session, env.organization, secret_id=secret.id, status=StorageStatus.SYNCED.value
    )

    stmt = (
        select(StorageModel).where(StorageModel.id == storage.id).options(selectinload(StorageModel.project_storages))
    )
    result = await db_session.execute(stmt)
    storage = result.scalar_one()

    with pytest.raises(ValidationException, match=f"project id={project.id} not READY"):
        await update_project_storage_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            storage=storage,
            project_ids=[project.id],
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
@patch("app.storages.service.update_storage_overall_status")
@patch("app.storages.service.get_configmap_by_project_storage_id")
@patch("app.storages.service.get_project_storage_by_id")
@patch("app.storages.service.delete_project_storage")
@patch("app.storages.service.update_project_storage_configmap_status")
@patch("app.storages.service.update_project_storage_composite_status")
async def test_update_configmap_status_deleted_status(
    mock_update_composite,
    mock_update_configmap,
    mock_delete_project_storage,
    mock_get_project_storage,
    mock_get_configmap,
    mock_update_storage_overall_status,
    db_session: AsyncSession,
):
    """Test update_configmap_status when status is DELETED."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.DELETING.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)
    configmap = await create_project_storage_configmap(
        session=db_session, project_storage_id=project_storage.id, user_email="tester@example.com"
    )

    message = ProjectStorageUpdateMessage(
        message_type="project_storage_update",
        project_storage_id=project_storage.id,
        status=ConfigMapStatus.DELETED,
        status_reason="ConfigMap deleted",
        updated_at=datetime.now(UTC),
    )

    mock_get_configmap.return_value = configmap
    mock_get_project_storage.return_value = project_storage

    await update_configmap_status(db_session, env.cluster, message)

    mock_get_configmap.assert_called_once_with(db_session, env.cluster.organization_id, project_storage.id)
    mock_get_project_storage.assert_called_once_with(db_session, project_storage.id)
    mock_delete_project_storage.assert_called_once_with(db_session, project_storage)
    mock_update_storage_overall_status.assert_called_once_with(
        db_session, env.organization.id, project_storage.storage_id
    )
    mock_update_configmap.assert_not_called()
    mock_update_composite.assert_not_called()


@pytest.mark.asyncio
@patch("app.storages.service.get_configmap_by_project_storage_id")
@patch("app.storages.service.get_project_storage_by_id")
@patch("app.storages.service.delete_project_storage")
@patch("app.storages.service.update_project_storage_configmap_status")
@patch("app.storages.service.update_project_storage_composite_status")
async def test_update_configmap_status_other_status(
    mock_update_composite,
    mock_update_configmap,
    mock_delete_project_storage,
    mock_get_project_storage,
    mock_get_configmap,
    db_session: AsyncSession,
):
    """Test update_configmap_status when status is not DELETED."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)
    configmap = await create_project_storage_configmap(
        session=db_session, project_storage_id=project_storage.id, user_email="tester@example.com"
    )

    message = ProjectStorageUpdateMessage(
        message_type="project_storage_update",
        project_storage_id=project_storage.id,
        status=ConfigMapStatus.ADDED,
        status_reason="ConfigMap added",
        updated_at=datetime.now(UTC),
    )

    mock_get_configmap.return_value = configmap
    mock_get_project_storage.return_value = project_storage

    await update_configmap_status(db_session, env.cluster, message)

    mock_get_configmap.assert_called_once_with(db_session, env.cluster.organization_id, project_storage.id)
    mock_get_project_storage.assert_called_once_with(db_session, project_storage.id)
    mock_delete_project_storage.assert_not_called()
    mock_update_configmap.assert_called_once_with(
        db_session, configmap, ConfigMapStatus.ADDED, "ConfigMap added", "system"
    )
    mock_update_composite.assert_called_once_with(db_session, env.cluster.organization_id, project_storage)


@pytest.mark.asyncio
@patch("app.storages.service.get_configmap_by_project_storage_id")
async def test_update_configmap_status_configmap_not_found(mock_get_configmap, db_session: AsyncSession):
    """Test update_configmap_status raises NotFoundException when configmap not found."""
    env = await factory.create_basic_test_environment(db_session)

    message = ProjectStorageUpdateMessage(
        message_type="project_storage_update",
        project_storage_id=uuid4(),
        status=ConfigMapStatus.ADDED,
        status_reason="Test",
        updated_at=datetime.now(UTC),
    )

    mock_get_configmap.return_value = None

    with pytest.raises(NotFoundException, match="ProjectStorageConfigmap for project_storage_id .* not found"):
        await update_configmap_status(db_session, env.cluster, message)


@pytest.mark.asyncio
@patch("app.storages.service.get_configmap_by_project_storage_id")
@patch("app.storages.service.get_project_storage_by_id")
async def test_update_configmap_status_project_storage_not_found(
    mock_get_project_storage, mock_get_configmap, db_session: AsyncSession
):
    """Test update_configmap_status raises NotFoundException when project_storage not found."""
    env = await factory.create_basic_test_environment(db_session)

    message = ProjectStorageUpdateMessage(
        message_type="project_storage_update",
        project_storage_id=uuid4(),
        status=ConfigMapStatus.ADDED,
        status_reason="Test",
        updated_at=datetime.now(UTC),
    )

    mock_get_configmap.return_value = SimpleNamespace()  # Mock configmap
    mock_get_project_storage.return_value = None

    with pytest.raises(NotFoundException, match="ProjectStorage with id .* not found"):
        await update_configmap_status(db_session, env.cluster, message)


@pytest.mark.asyncio
@patch("app.storages.service.get_storage_by_secret_id")
@patch("app.storages.service.update_project_storage_composite_status")
async def test_update_project_storage_secret_status_success(
    mock_update_composite, mock_get_storage, db_session: AsyncSession
):
    """Test update_project_storage_secret_status successful execution."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)

    mock_get_storage.return_value = storage

    await update_project_storage_secret_status(db_session, secret.id, project_storage)

    mock_get_storage.assert_called_once_with(db_session, secret.id)
    mock_update_composite.assert_called_once_with(db_session, storage.organization_id, project_storage)


@pytest.mark.asyncio
@patch("app.storages.service.get_storage_by_secret_id")
async def test_update_project_storage_secret_status_storage_not_found(mock_get_storage, db_session: AsyncSession):
    """Test update_project_storage_secret_status raises NotFoundException when storage not found."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)

    mock_get_storage.return_value = None

    with pytest.raises(NotFoundException, match="Storage with secret_id .* not found"):
        await update_project_storage_secret_status(db_session, secret.id, project_storage)


@pytest.mark.asyncio
@patch("app.storages.service.get_configmap_by_project_storage_id")
@patch("app.storages.service.get_organization_secret_assignment")
@patch("app.storages.service.resolve_project_storage_composite_status")
@patch("app.storages.service.update_project_storage_status")
async def test_update_project_storage_composite_status_success(
    mock_update_status, mock_resolve_status, mock_get_project_secret, mock_get_configmap, db_session: AsyncSession
):
    """Test update_project_storage_composite_status successful execution."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)
    configmap = await create_project_storage_configmap(
        session=db_session, project_storage_id=project_storage.id, user_email="tester@example.com"
    )
    project_secret = await factory.create_organization_secret_assignment(db_session, env.project, secret)

    mock_get_configmap.return_value = configmap
    mock_get_project_secret.return_value = project_secret
    mock_resolve_status.return_value = (ProjectStorageStatus.SYNCED, "All components synced")

    await update_project_storage_composite_status(db_session, env.organization.id, project_storage)

    mock_get_configmap.assert_called_once_with(db_session, env.organization.id, project_storage.id)
    mock_get_project_secret.assert_called_once_with(db_session, secret.id, project_storage.project_id)
    mock_resolve_status.assert_called_once_with(configmap, project_secret)
    mock_update_status.assert_called_once_with(
        db_session, project_storage, ProjectStorageStatus.SYNCED, "All components synced", "system"
    )


@pytest.mark.asyncio
@patch("app.storages.service.get_configmap_by_project_storage_id")
async def test_update_project_storage_composite_status_configmap_not_found(
    mock_get_configmap, db_session: AsyncSession
):
    """Test update_project_storage_composite_status raises NotFoundException when configmap not found."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)

    mock_get_configmap.return_value = None

    with pytest.raises(NotFoundException, match="ProjectStorageConfigmap for project_storage_id .* not found"):
        await update_project_storage_composite_status(db_session, env.organization.id, project_storage)


@pytest.mark.asyncio
@patch("app.storages.service.get_configmap_by_project_storage_id")
@patch("app.storages.service.get_organization_secret_assignment")
async def test_update_project_storage_composite_status_project_secret_not_found(
    mock_get_organization_secret_assignment, mock_get_configmap, db_session: AsyncSession
):
    """Test update_project_storage_composite_status raises NotFoundException when project_secret not found."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization)
    storage = await factory.create_storage_with_project_assignment(
        db_session, env.organization, env.project, secret, storage_status=StorageStatus.SYNCED.value
    )

    project_storage = await get_project_storage(db_session, storage.id, env.project.id)
    configmap = await create_project_storage_configmap(
        session=db_session, project_storage_id=project_storage.id, user_email="tester@example.com"
    )

    mock_get_configmap.return_value = configmap
    mock_get_organization_secret_assignment.return_value = None

    with pytest.raises(
        NotFoundException, match="OrganizationSecretAssignment for secret_id .* and project_id .* not found"
    ):
        await update_project_storage_composite_status(db_session, env.organization.id, project_storage)


@pytest.mark.asyncio
async def test_update_storage_status_storage_not_found(db_session: AsyncSession):
    """Test updating storage status when storage doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    with (
        patch("app.storages.service.get_storage_in_organization") as mock_get_storage_in_organization,
        patch("app.storages.service.resolve_storage_status") as mock_resolve_storage_status,
        patch("app.storages.service.delete_storage_in_db") as mock_delete_storage_in_db,
        patch("app.storages.service.update_storage_status_in_db") as mock_update_storage_status_in_db,
        patch("app.storages.service.logger") as mock_logger,
    ):
        mock_get_storage_in_organization.return_value = None

        await update_storage_overall_status(db_session, env.organization.id, uuid4())

    mock_get_storage_in_organization.assert_awaited_once()
    mock_logger.error.assert_called_once()
    mock_resolve_storage_status.assert_not_called()
    mock_delete_storage_in_db.assert_not_called()
    mock_update_storage_status_in_db.assert_not_called()


@pytest.mark.asyncio
async def test_update_storage_status_delete__parent(db_session: AsyncSession):
    """Test deleting storage when last child is deleted."""
    env = await factory.create_basic_test_environment(db_session)

    storage = SimpleNamespace(id=uuid4(), name="my-storage", status=StorageStatus.DELETING.value, project_storages=[])

    with (
        patch("app.storages.service.get_storage_in_organization") as mock_get_storage_in_organization,
        patch("app.storages.service.resolve_storage_status") as mock_resolve_storage_status,
        patch("app.storages.service.delete_storage_in_db") as mock_delete_storage_in_db,
        patch("app.storages.service.update_storage_status_in_db") as mock_update_storage_status_in_db,
    ):
        mock_get_storage_in_organization.return_value = storage
        mock_resolve_storage_status.return_value = (StorageStatus.DELETED, None)

        await update_storage_overall_status(db_session, env.organization.id, storage.id)

    mock_get_storage_in_organization.assert_awaited_once()
    mock_resolve_storage_status.assert_called_once_with(storage.status, storage.project_storages)
    mock_delete_storage_in_db.assert_awaited_once_with(db_session, storage)
    mock_update_storage_status_in_db.assert_not_called()


@pytest.mark.asyncio
async def test_update_storage_status_child_deleted_parent_unassigned(db_session: AsyncSession):
    """Test keeping parent secret when other children remain after deletion."""
    env = await factory.create_basic_test_environment(db_session)

    storage = SimpleNamespace(id=uuid4(), name="my-storage", status=StorageStatus.DELETING.value, project_storages=[])

    with (
        patch("app.storages.service.get_storage_in_organization") as mock_get_storage_in_organization,
        patch("app.storages.service.resolve_storage_status") as mock_resolve_storage_status,
        patch("app.storages.service.delete_storage_in_db") as mock_delete_storage_in_db,
        patch("app.storages.service.update_storage_status_in_db") as mock_update_storage_status_in_db,
    ):
        mock_get_storage_in_organization.return_value = storage
        mock_resolve_storage_status.return_value = (StorageStatus.UNASSIGNED, None)

        await update_storage_overall_status(db_session, env.organization.id, storage.id)

    mock_get_storage_in_organization.assert_awaited_once()
    mock_resolve_storage_status.assert_called_once_with(storage.status, storage.project_storages)
    mock_delete_storage_in_db.assert_not_called()
    mock_update_storage_status_in_db.assert_awaited_once_with(
        db_session,
        storage,
        StorageStatus.UNASSIGNED,
        None,
        "system",
    )


@pytest.mark.asyncio
async def test_update_storage_overall_status__status_unchanged_does_nothing(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    storage = SimpleNamespace(
        id="stg-1",
        name="my-storage",
        status=StorageStatus.SYNCED,
        project_storages=[SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())],
    )

    with (
        patch("app.storages.service.get_storage_in_organization") as mock_get_storage_in_organization,
        patch("app.storages.service.resolve_storage_status") as mock_resolve_storage_status,
        patch("app.storages.service.delete_storage_in_db") as mock_delete_storage_in_db,
        patch("app.storages.service.update_storage_status_in_db") as mock_update_storage_status_in_db,
    ):
        mock_get_storage_in_organization.return_value = storage
        mock_resolve_storage_status.return_value = (StorageStatus.SYNCED, None)

        await update_storage_overall_status(db_session, env.organization.id, storage.id)

        mock_delete_storage_in_db.assert_not_called()
        mock_update_storage_status_in_db.assert_not_called()


@pytest.mark.asyncio
async def test_update_storage_overall_status__status_changed_updates(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)

    storage = SimpleNamespace(
        id=uuid4(),
        name="my-storage",
        status=StorageStatus.PENDING,
        project_storages=[SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())],
    )
    with (
        patch("app.storages.service.get_storage_in_organization") as mock_get_storage_in_organization,
        patch("app.storages.service.resolve_storage_status") as mock_resolve_storage_status,
        patch("app.storages.service.delete_storage_in_db") as mock_delete_storage_in_db,
        patch("app.storages.service.update_storage_status_in_db") as mock_update_storage_status_in_db,
    ):
        mock_get_storage_in_organization.return_value = storage
        mock_resolve_storage_status.return_value = (StorageStatus.SYNCED, None)

        await update_storage_overall_status(db_session, env.organization.id, storage.id)

        mock_delete_storage_in_db.assert_not_called()
        mock_update_storage_status_in_db.assert_awaited_once_with(
            db_session,
            storage,
            StorageStatus.SYNCED,
            None,
            "system",
        )
