# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from airm.messaging.schemas import (
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
    SecretsComponentKind,
)
from app.projects.enums import ProjectStatus
from app.secrets.enums import SecretScope, SecretStatus, SecretType, SecretUseCase
from app.secrets.models import ProjectSecret as ProjectSecretModel
from app.secrets.models import Secret as SecretModel
from app.secrets.repository import get_project_secret_by_id, get_secret_in_organization
from app.secrets.schemas import ProjectSecretsWithParentSecret, SecretIn, Secrets
from app.secrets.service import (
    create_secret_in_organization,
    get_project_secrets_in_project,
    get_secrets_with_assigned_project_secrets,
    submit_delete_project_secret,
    submit_delete_secret,
    update_project_secret_assignments,
    update_project_secret_status,
)
from app.utilities.exceptions import ConflictException, NotFoundException, ValidationException
from tests import factory


@pytest.mark.asyncio
async def test_get_secrets_with_assigned_project_secrets_all_secrets(db_session: AsyncSession):
    """Test retrieving all secrets with their project assignments."""
    env = await factory.create_basic_test_environment(db_session)

    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="secret1",
        secret_status=SecretStatus.SYNCED.value,
    )

    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="secret2",
        secret_status=SecretStatus.SYNCED.value,
    )

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization)

    assert isinstance(result, Secrets)
    assert len(result.secrets) == 2
    secret_names = [secret.name for secret in result.secrets]
    assert "secret1" in secret_names
    assert "secret2" in secret_names

    for secret in result.secrets:
        assert len(secret.project_secrets) == 1
        assert secret.project_secrets[0].project_id == env.project.id
        assert secret.project_secrets[0].project_name == env.project.name


@pytest.mark.asyncio
async def test_get_secrets_with_assigned_project_secrets_filtered_by_project(db_session: AsyncSession):
    """Test retrieving secrets filtered by specific project."""
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-002")

    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="secret1",
        secret_status=SecretStatus.SYNCED.value,
    )

    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        project2,
        name="secret2",
        secret_status=SecretStatus.SYNCED.value,
    )

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization, env.project)

    assert len(result.secrets) == 1
    assert result.secrets[0].name == "secret1"
    assert len(result.secrets[0].project_secrets) == 1
    assert result.secrets[0].project_secrets[0].project_name == env.project.name


@pytest.mark.asyncio
async def test_get_secrets_with_assigned_project_secrets_no_secrets(db_session: AsyncSession):
    """Test retrieving secrets when none exist."""
    env = await factory.create_basic_test_environment(db_session)

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization, env.project)

    assert isinstance(result, Secrets)
    assert len(result.secrets) == 0


@pytest.mark.asyncio
async def test_get_secrets_with_no_project_secrets(db_session: AsyncSession):
    """Test retrieving secrets that have no project assignments."""
    env = await factory.create_basic_test_environment(db_session)
    await factory.create_secret(
        db_session,
        env.organization,
        name="db-password",
        secret_type=SecretType.EXTERNAL.value,
        status=SecretStatus.PENDING.value,
    )

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization)

    assert isinstance(result, Secrets)
    assert len(result.secrets) == 1
    assert result.secrets[0].project_secrets == []


@pytest.mark.asyncio
async def test_get_project_secrets_in_project(db_session: AsyncSession):
    """Test retrieving project secrets for a specific project."""
    env = await factory.create_basic_test_environment(db_session)

    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="api-key",
        secret_status=SecretStatus.SYNCED.value,
        project_secret_status=ProjectSecretStatus.SYNCED.value,
    )

    result = await get_project_secrets_in_project(db_session, env.organization, env.project)

    assert isinstance(result, ProjectSecretsWithParentSecret)
    assert len(result.project_secrets) == 1

    project_secret = result.project_secrets[0]
    assert project_secret.project_id == env.project.id
    assert project_secret.status == ProjectSecretStatus.SYNCED
    assert project_secret.secret.name == "api-key"
    assert project_secret.secret.type == SecretType.EXTERNAL
    assert project_secret.secret.status == SecretStatus.SYNCED
    assert project_secret.secret.scope == SecretScope.ORGANIZATION


@pytest.mark.asyncio
async def test_create_secret_without_projects(db_session: AsyncSession):
    """Test successful secret creation without project assignments."""
    env = await factory.create_basic_test_environment(db_session)

    secret_in = SecretIn(
        name="test-secret",
        type=SecretType.EXTERNAL,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[],
    )

    with (
        patch("app.secrets.service.validate_external_secret_manifest") as mock_validate,
        patch("app.secrets.service.sanitize_external_secret_manifest") as mock_sanitize,
        patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit,
    ):
        mock_validate.return_value = {"apiVersion": "v1", "kind": "Secret"}
        mock_sanitize.return_value = "apiVersion: v1\nkind: Secret\nmetadata:\n  name: sanitized-secret"

        result = await create_secret_in_organization(db_session, env.organization.id, "test", secret_in)

    assert result is not None
    assert result.name == "test-secret"
    assert result.type == SecretType.EXTERNAL
    assert result.scope == SecretScope.ORGANIZATION
    assert result.project_secrets == []
    assert result.status == SecretStatus.UNASSIGNED
    mock_submit.assert_not_called()


@pytest.mark.asyncio
async def test_create_secret_with_projects(db_session: AsyncSession):
    """Test successful secret creation with project assignments."""
    env = await factory.create_basic_test_environment(db_session)

    secret_in = SecretIn(
        name="test-secret",
        type=SecretType.EXTERNAL,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[env.project.id],
    )

    with (
        patch("app.secrets.service.validate_external_secret_manifest") as mock_validate,
        patch("app.secrets.service.sanitize_external_secret_manifest") as mock_sanitize,
        patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit,
    ):
        mock_validate.return_value = {"apiVersion": "v1", "kind": "Secret"}
        mock_sanitize.return_value = "apiVersion: v1\nkind: Secret\nmetadata:\n  name: sanitized-secret"

        result = await create_secret_in_organization(db_session, env.organization.id, "test", secret_in)

    assert result.name == "test-secret"
    assert len(result.project_secrets) == 1
    assert result.project_secrets[0].project_id == env.project.id
    assert result.project_secrets[0].status == ProjectSecretStatus.PENDING
    mock_submit.assert_called_once()


@pytest.mark.asyncio
async def test_create_secret_duplicate_name(db_session: AsyncSession):
    """Test creating secret with duplicate name fails."""
    env = await factory.create_basic_test_environment(db_session)
    await factory.create_secret(db_session, env.organization, name="duplicate-secret")

    secret_in = SecretIn(
        name="duplicate-secret",
        type=SecretType.EXTERNAL,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[],
    )

    with (
        patch("app.secrets.service.validate_external_secret_manifest") as mock_validate,
        patch("app.secrets.service.sanitize_external_secret_manifest") as mock_sanitize,
    ):
        mock_validate.return_value = {"apiVersion": "v1", "kind": "Secret"}
        mock_sanitize.return_value = "apiVersion: v1\nkind: Secret\nmetadata:\n  name: sanitized-secret"

        with pytest.raises(ConflictException):
            await create_secret_in_organization(db_session, env.organization.id, "test", secret_in)


@pytest.mark.parametrize(
    "secret_status,use_case,expected_error",
    [
        (SecretStatus.PENDING.value, None, "Secret is in PENDING state and cannot be deleted"),
        (SecretStatus.DELETING.value, None, "Secret is already marked for deletion"),
        (SecretStatus.PENDING.value, SecretUseCase.HUGGING_FACE, "Secret is in PENDING state and cannot be deleted"),
        (SecretStatus.DELETING.value, SecretUseCase.HUGGING_FACE, "Secret is already marked for deletion"),
    ],
)
@pytest.mark.asyncio
async def test_submit_delete_secret_invalid_state(db_session: AsyncSession, secret_status, use_case, expected_error):
    """Test deleting secret in invalid states fails for both generic and Hugging Face secrets."""
    env = await factory.create_basic_test_environment(db_session)

    secret_type = SecretType.KUBERNETES_SECRET.value if use_case else SecretType.EXTERNAL.value
    secret_scope = SecretScope.PROJECT.value if use_case else SecretScope.ORGANIZATION.value

    secret = await factory.create_secret(
        db_session, env.organization, status=secret_status, secret_type=secret_type, secret_scope=secret_scope
    )

    if use_case:
        secret.use_case = use_case
        await db_session.flush()

    user = "test@example.com"

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        with pytest.raises(ConflictException, match=expected_error):
            await submit_delete_secret(db_session, secret, user)

        mock_submit.assert_not_called()


@pytest.mark.asyncio
async def test_submit_delete_secret_without_project_secrets(db_session: AsyncSession):
    """Test deleting secret without project assignments."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)

    user = "test@example.com"

    # Eagerly load the project_secrets relationship to avoid lazy loading issues
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        await submit_delete_secret(db_session, secret, user)
        mock_submit.assert_not_called()

    # Verify the secret was deleted directly since it had no project assignments
    # Check by querying the database since the object may be detached
    deleted_secret = await db_session.get(SecretModel, secret.id)
    assert deleted_secret is None or deleted_secret.status == SecretStatus.DELETED.value


@pytest.mark.asyncio
async def test_submit_delete_secret_with_project_secrets(db_session: AsyncSession):
    """Test deleting secret with project assignments."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    user = "test@example.com"

    # Eagerly load the project_secrets and their project relationships
    stmt = (
        select(SecretModel)
        .where(SecretModel.id == secret.id)
        .options(selectinload(SecretModel.project_secrets).selectinload(ProjectSecretModel.project))
    )
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        await submit_delete_secret(db_session, secret, user)

    await db_session.refresh(secret)
    assert secret.status == SecretStatus.DELETING.value

    # Verify project secret status was updated
    project_secret = secret.project_secrets[0]
    await db_session.refresh(project_secret)
    assert project_secret.status == ProjectSecretStatus.DELETING.value

    # Verify message was sent
    mock_submit.assert_called_once_with(
        env.project.cluster_id,
        ProjectSecretsDeleteMessage(
            message_type="project_secrets_delete",
            project_secret_id=project_secret.id,
            project_name=env.project.name,
            secret_type=SecretsComponentKind.EXTERNAL_SECRET,
        ),
    )


@pytest.mark.asyncio
async def test_update_project_secret_assignments_add_project(db_session: AsyncSession):
    """Test adding project to secret assignment."""
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")
    # Set project status to READY after creation
    project2.status = "Ready"
    await db_session.flush()

    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)

    # Eagerly load project_secrets to avoid lazy loading issues
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    user_email = "test@example.com"

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        await update_project_secret_assignments(
            session=db_session,
            user_email=user_email,
            organization_id=env.organization.id,
            secret=secret,
            project_ids=[project2.id],
        )

    await db_session.refresh(secret)
    assert len(secret.project_secrets) == 1
    assert secret.project_secrets[0].project_id == project2.id
    assert secret.status == SecretStatus.PENDING.value
    mock_submit.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_secret_assignments_remove_project(db_session: AsyncSession):
    """Test removing project from secret assignment."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Eagerly load project_secrets and their project relationships
    stmt = (
        select(SecretModel)
        .where(SecretModel.id == secret.id)
        .options(selectinload(SecretModel.project_secrets).selectinload(ProjectSecretModel.project))
    )
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    user_email = "test@example.com"

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        await update_project_secret_assignments(
            session=db_session,
            user_email=user_email,
            organization_id=env.organization.id,
            secret=secret,
            project_ids=[],
        )

    # The update_project_secret_assignments function only sends delete messages
    # but doesn't actually change the project secret status to DELETING.
    # That happens when the message is processed.
    mock_submit.assert_called_once()

    # Verify the secret status was set to PENDING due to the assignment change
    await db_session.refresh(secret)
    assert secret.project_secrets[0].status == ProjectSecretStatus.DELETING.value
    assert secret.status == SecretStatus.PENDING.value


@pytest.mark.asyncio
async def test_update_project_secret_assignments_no_changes(db_session: AsyncSession):
    """Test updating project assignments with no changes."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Eagerly load project_secrets to avoid lazy loading issues
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    with pytest.raises(ValueError, match="No changes in project assignments"):
        await update_project_secret_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            secret=secret,
            project_ids=[env.project.id],
        )


@pytest.mark.asyncio
async def test_update_project_secret_assignments_invalid_status(db_session: AsyncSession):
    """Test updating project assignments with invalid secret status."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.FAILED.value)

    # Eagerly load project_secrets to avoid lazy loading issues
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    with pytest.raises(ConflictException):
        await update_project_secret_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            secret=secret,
            project_ids=[env.project.id],
        )


@pytest.mark.asyncio
async def test_update_project_secret_assignments_project_not_ready(db_session: AsyncSession):
    """Test updating project assignments when project is not ready."""
    env = await factory.create_basic_test_environment(db_session)
    project = await factory.create_project(db_session, env.organization, env.cluster, name="failed-project")
    # Update project status to FAILED after creation
    project.status = ProjectStatus.FAILED.value

    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)

    # Eagerly load project_secrets to avoid lazy loading issues
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    with pytest.raises(ConflictException, match="Project failed-project is not in a READY state"):
        await update_project_secret_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            secret=secret,
            project_ids=[project.id],
        )


@pytest.mark.asyncio
async def test_submit_delete_project_secret_already_deleting(db_session: AsyncSession):
    """Test deleting project secret already marked for deletion."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )

    user = "test@example.com"

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        with pytest.raises(ConflictException, match="Project Secret is already marked for deletion"):
            await submit_delete_project_secret(db_session, env.organization.id, project_secret, user)

        mock_submit.assert_not_called()


@pytest.mark.asyncio
async def test_submit_delete_project_secret_success(db_session: AsyncSession):
    """Test successful project secret deletion."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    user = "test@example.com"

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        await submit_delete_project_secret(db_session, env.organization.id, project_secret, user)

    await db_session.refresh(project_secret)
    assert project_secret.status == ProjectSecretStatus.DELETING.value

    mock_submit.assert_called_once_with(
        env.project.cluster_id,
        ProjectSecretsDeleteMessage(
            message_type="project_secrets_delete",
            project_secret_id=project_secret.id,
            project_name=env.project.name,
            secret_type=SecretsComponentKind.EXTERNAL_SECRET,
        ),
    )


@pytest.mark.asyncio
async def test_update_project_secret_status_project_secret_not_found(db_session: AsyncSession):
    """Test updating project secret status when project secret doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=uuid4(),
        status=ProjectSecretStatus.SYNCED.value,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)


@pytest.mark.asyncio
async def test_update_project_secret_status_delete_child_and_parent(db_session: AsyncSession):
    """Test deleting both project secret and parent secret when last child is deleted."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be deleted
    deleted_ps = await get_project_secret_by_id(db_session, project_secret.id)
    assert deleted_ps is None

    # Parent secret should be deleted since it was DELETING and has no more children
    deleted_secret = await get_secret_in_organization(db_session, env.organization.id, secret.id)
    assert deleted_secret is None


@pytest.mark.asyncio
async def test_update_project_secret_status_child_deleted_parent_retained(db_session: AsyncSession):
    """Test keeping parent secret when other children remain after deletion."""
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)

    ps1 = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )
    _ = await factory.create_project_secret(db_session, project2, secret, status=ProjectSecretStatus.SYNCED.value)

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=ps1.id,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # First project secret should be deleted
    deleted_ps = await get_project_secret_by_id(db_session, ps1.id)
    assert deleted_ps is None

    # Parent secret should still exist since ps2 remains
    existing_secret = await get_secret_in_organization(db_session, env.organization.id, secret.id)
    assert existing_secret is not None


@pytest.mark.asyncio
async def test_update_project_secret_status_delete_failed(db_session: AsyncSession):
    """Test handling project secret delete failure."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.DELETE_FAILED,
        status_reason="Failed to delete",
        updated_at=datetime.now(UTC),
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be updated to DELETE_FAILED
    await db_session.refresh(project_secret)
    assert project_secret.status == ProjectSecretStatus.DELETE_FAILED
    assert project_secret.status_reason == "Failed to delete"

    # Parent secret should be updated to DELETE_FAILED
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.DELETE_FAILED.value


@pytest.mark.asyncio
async def test_update_project_secret_status_child_unsolicited_delete(db_session: AsyncSession):
    """Test handling unsolicited project secret deletion."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.DELETED,
        status_reason="Deleted from cluster",
        updated_at=datetime.now(UTC),
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be updated to DELETED
    await db_session.refresh(project_secret)
    assert project_secret.status == ProjectSecretStatus.DELETED

    # Parent secret should be updated to SYNCED_ERROR
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.SYNCED_ERROR.value


@pytest.mark.asyncio
async def test_update_project_secret_status_synced_update(db_session: AsyncSession):
    """Test updating project secret status to synced."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.PENDING.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.PENDING.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Successfully synced",
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be updated
    await db_session.refresh(project_secret)
    assert project_secret.status == ProjectSecretStatus.SYNCED
    assert project_secret.status_reason == "Successfully synced"

    # Parent secret should be updated based on resolution
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.SYNCED.value


@pytest.mark.asyncio
async def test_update_project_secret_status_unassigned_when_no_children(db_session: AsyncSession):
    """Test setting secret to unassigned when last project assignment is deleted during normal operation."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be deleted
    deleted_ps = await get_project_secret_by_id(db_session, project_secret.id)
    assert deleted_ps is None

    # Parent secret should be set to UNASSIGNED since it wasn't in DELETING state
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.UNASSIGNED.value


@pytest.mark.asyncio
async def test_update_project_secret_status_deletes_project_scoped_secret_with_no_assignments(
    db_session: AsyncSession,
):
    """Test that PROJECT-scoped secrets are deleted when they have no project assignments."""
    env = await factory.create_basic_test_environment(db_session)
    # Create a PROJECT-scoped secret (like HF tokens)
    secret = await factory.create_secret(
        db_session,
        env.organization,
        status=SecretStatus.PENDING.value,
        secret_scope=SecretScope.PROJECT.value,
    )
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be deleted
    deleted_ps = await get_project_secret_by_id(db_session, project_secret.id)
    assert deleted_ps is None

    # Parent secret should also be deleted since PROJECT-scoped secrets cannot exist without assignments
    deleted_secret = await get_secret_in_organization(db_session, env.organization.id, secret.id)
    assert deleted_secret is None


@pytest.mark.asyncio
async def test_create_secret_in_organization_invalid_yaml_manifest(db_session: AsyncSession):
    """Test creating secret with invalid YAML manifest raises ValidationException."""
    env = await factory.create_basic_test_environment(db_session)

    secret_in = SecretIn(
        name="invalid-yaml-secret",
        type="External",
        scope="Organization",
        manifest="invalid: yaml: [unclosed",  # Invalid YAML
        project_ids=[],
        description="test secret with invalid YAML",
    )

    with pytest.raises(ValidationException) as exc_info:
        await create_secret_in_organization(
            session=db_session,
            organization_id=env.organization.id,
            user_email="test@example.com",
            secret_in=secret_in,
        )

    assert "Invalid YAML manifest" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_delete_project_secret_parent_not_found(db_session: AsyncSession):
    """Test submit delete project secret when parent secret doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a real secret first, then create project secret
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    # Mock get_secret_in_organization to return None, simulating secret not found
    with patch("app.secrets.service.get_secret_in_organization", return_value=None):
        with pytest.raises(NotFoundException) as exc_info:
            await submit_delete_project_secret(
                session=db_session,
                organization_id=env.organization.id,
                project_secret=project_secret,
                user="test@example.com",
            )

    assert "Secret not found" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.secrets.service.submit_message_to_cluster_queue")
async def test_update_project_secret_assignments_project_not_found(mock_submit, db_session: AsyncSession):
    """Test updating project assignments when project doesn't exist in organization."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Eagerly load the project_secrets relationship to avoid lazy loading issues
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    # Try to assign to non-existent project
    non_existent_project_id = uuid4()

    with pytest.raises(ValueError) as exc_info:
        await update_project_secret_assignments(
            session=db_session,
            user_email="test@example.com",
            organization_id=env.organization.id,
            secret=secret,
            project_ids=[non_existent_project_id],
        )

    assert "does not exist in the organization" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.secrets.service.submit_message_to_cluster_queue")
async def test_update_project_secret_assignments_project_not_assigned_to_secret(mock_submit, db_session: AsyncSession):
    """Test removing project assignment when project is not assigned to secret."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a secret with project assignments using the factory
    secret = await factory.create_secret_with_project_assignment(
        db_session, env.organization, env.project, secret_status=SecretStatus.SYNCED.value
    )

    # Eagerly load the project_secrets relationship to avoid lazy loading issues
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    # Now mock get_project_secret to return None during the removal process
    # This simulates the error case where the project secret is missing during removal
    with patch("app.secrets.service.get_project_secret", return_value=None):
        with pytest.raises(ValueError) as exc_info:
            await update_project_secret_assignments(
                session=db_session,
                user_email="test@example.com",
                organization_id=env.organization.id,
                secret=secret,
                project_ids=[],  # Empty list means remove all assignments
            )

    assert "is not assigned to the secret" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_project_secret_status_secret_not_found(db_session: AsyncSession):
    """Test updating project secret status when parent secret doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a real secret and project secret first
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Updated",
    )

    # Mock get_secret_in_organization to return None, simulating secret not found
    with patch("app.secrets.service.get_secret_in_organization", return_value=None):
        # This should log error and return without raising exception
        await update_project_secret_status(db_session, env.cluster, msg)

    # Verify project secret still exists and unchanged (operation was skipped)
    await db_session.refresh(project_secret)
    assert project_secret.status == ProjectSecretStatus.SYNCED  # Should remain unchanged


@pytest.mark.asyncio
@patch("app.secrets.service.submit_message_to_cluster_queue")
async def test_update_project_secret_assignments_continue_on_missing_project_secret(
    mock_submit, db_session: AsyncSession
):
    """Test continue behavior when get_project_secret returns None during assignment creation."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Eagerly load the project_secrets relationship
    stmt = select(SecretModel).where(SecretModel.id == secret.id).options(selectinload(SecretModel.project_secrets))
    result = await db_session.execute(stmt)
    secret = result.scalar_one()

    # Ensure project is in READY state
    env.project.status = ProjectStatus.READY
    await db_session.flush()

    # Mock assign_secret_to_projects to succeed but then get_project_secret to return None
    # This simulates the rare edge case where project_secret is None after assignment
    with patch("app.secrets.service.assign_secret_to_projects") as mock_assign:
        with patch("app.secrets.service.get_project_secret", return_value=None):
            # This should not raise an error, just continue past the None project_secret
            await update_project_secret_assignments(
                session=db_session,
                user_email="test@example.com",
                organization_id=env.organization.id,
                secret=secret,
                project_ids=[env.project.id],
            )

    # assign_secret_to_projects should be called
    mock_assign.assert_called_once()
    # No message should be sent since project_secret was None
    mock_submit.assert_not_called()


@pytest.mark.asyncio
@patch("app.secrets.service.get_project_storages_by_project_secret")
@patch("app.secrets.service.update_project_storage_secret_status")
async def test_update_project_secret_status_updates_project_storage(
    mock_update_project_storage_secret_status, mock_get_project_storages_by_project_secret, db_session: AsyncSession
):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    from app.storages.models import ProjectStorage

    project_storage = ProjectStorage(
        id=uuid4(),
        project_id=env.project.id,
        storage_id=uuid4(),
        status="PENDING",
        created_by="test",
        updated_by="test",
    )

    mock_get_project_storages_by_project_secret.return_value = [project_storage]

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Test update",
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    mock_get_project_storages_by_project_secret.assert_called_once_with(db_session, project_secret)
    mock_update_project_storage_secret_status.assert_called_once_with(
        db_session, project_secret.secret_id, project_storage
    )


@pytest.mark.asyncio
async def test_submit_delete_huggingface_token_success(db_session: AsyncSession):
    """Test successful deletion of Hugging Face token including all three components."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a Hugging Face token secret with realistic Kubernetes secret manifest
    hf_token_manifest = """apiVersion: v1
kind: Secret
metadata:
  name: hf-token
type: Opaque
data:
  token: aGZfdG9rZW5fc2FtcGxl  # base64 encoded 'hf_token_sample'
"""
    hf_token = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="hf-token",
        secret_type=SecretType.KUBERNETES_SECRET,
        scope=SecretScope.PROJECT,
        manifest=hf_token_manifest,
        secret_status=SecretStatus.SYNCED.value,
        project_secret_status=ProjectSecretStatus.SYNCED.value,
    )

    # Set the use_case to Hugging Face after creation
    hf_token.use_case = SecretUseCase.HUGGING_FACE
    await db_session.flush()

    # Eagerly load the project_secrets and their project relationships
    stmt = (
        select(SecretModel)
        .where(SecretModel.id == hf_token.id)
        .options(selectinload(SecretModel.project_secrets).selectinload(ProjectSecretModel.project))
    )
    result = await db_session.execute(stmt)
    hf_token = result.scalar_one()

    user = "test@example.com"

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        await submit_delete_secret(db_session, hf_token, user)

    # Verify the secret status was set to DELETING
    await db_session.refresh(hf_token)
    assert hf_token.status == SecretStatus.DELETING.value

    # Verify project secret status was updated to DELETING
    project_secret = hf_token.project_secrets[0]
    await db_session.refresh(project_secret)
    assert project_secret.status == ProjectSecretStatus.DELETING.value

    # Verify cluster deletion message was sent
    mock_submit.assert_called_once_with(
        env.project.cluster_id,
        ProjectSecretsDeleteMessage(
            message_type="project_secrets_delete",
            project_secret_id=project_secret.id,
            project_name=env.project.name,
            secret_type=SecretsComponentKind.KUBERNETES_SECRET,
        ),
    )

    # Simulate successful cluster deletion response
    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Verify all three components are deleted:
    # 1. ProjectSecret entry should be deleted
    deleted_ps = await get_project_secret_by_id(db_session, project_secret.id)
    assert deleted_ps is None

    # 2. Secret record should be deleted (since it was DELETING and no more children)
    deleted_secret = await get_secret_in_organization(db_session, env.organization.id, hf_token.id)
    assert deleted_secret is None

    # 3. Cluster secret deletion: verified that ProjectSecretsDeleteMessage was sent to cluster queue above


@pytest.mark.asyncio
@patch("app.secrets.service.get_project_storages_by_project_secret")
@patch("app.secrets.service.update_project_storage_secret_status")
@patch("app.secrets.service.logger")
async def test_update_project_secret_status_logs_error_when_project_storage_not_found(
    mock_logger,
    mock_update_project_storage_secret_status,
    mock_get_project_storages_by_project_secret,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    project_secret = await factory.create_project_secret(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    mock_get_project_storages_by_project_secret.return_value = None

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=project_secret.id,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Test update",
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    mock_get_project_storages_by_project_secret.assert_called_once_with(db_session, project_secret)
    mock_logger.info.assert_called_once_with(f"No ProjectStorages found for ProjectSecret {project_secret.id}")
    mock_update_project_storage_secret_status.assert_not_called()


@pytest.mark.asyncio
async def test_huggingface_manifest_template_processing(db_session: AsyncSession):
    """Test that Hugging Face token Kubernetes secret manifests are processed correctly by the API."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a Hugging Face token manifest template (as provided by user)
    hf_token_manifest_template = """apiVersion: v1
kind: Secret
metadata:
  name: hf-token-template
type: Opaque
data:
  token: aGZfdG9rZW5fdGVtcGxhdGU=  # base64 encoded 'hf_token_template'
"""

    user = "test@example.com"

    with patch("app.secrets.service.submit_message_to_cluster_queue") as mock_submit:
        # Create the secret using the service layer (this tests _prepare_secret_input)
        secret_in = SecretIn(
            name="hf-token-template",
            type=SecretType.KUBERNETES_SECRET,
            scope=SecretScope.PROJECT,
            manifest=hf_token_manifest_template,
            project_ids=[env.project.id],
            use_case=SecretUseCase.HUGGING_FACE,
        )

        result = await create_secret_in_organization(db_session, env.organization.id, user, secret_in)

        # Verify the secret was created successfully
        assert result is not None
        assert result.name == "hf-token-template"
        assert result.type == SecretType.KUBERNETES_SECRET
        assert result.scope == SecretScope.PROJECT
        assert result.use_case == SecretUseCase.HUGGING_FACE

        # Verify that for Hugging Face Kubernetes secrets, the manifest is NOT stored in the database
        # (for security reasons - sensitive token data should not persist in DB)
        stored_secret = await get_secret_in_organization(db_session, env.organization.id, result.id)
        assert stored_secret is not None
        assert stored_secret.manifest == ""  # Empty string stored for security

        # Verify that the message sent to cluster queue contains the original manifest
        mock_submit.assert_called_once()
        call_args = mock_submit.call_args
        cluster_id, message = call_args[0]

        assert cluster_id == env.cluster.id
        assert isinstance(message, ProjectSecretsCreateMessage)
        assert message.project_name == env.project.name

        sent_manifest = yaml.safe_load(message.manifest)
        assert sent_manifest["metadata"]["labels"]["airm.silogen.com/use-case"] == SecretUseCase.HUGGING_FACE.lower()

        # Aside from the injected labels, the manifest sent to the cluster should remain unchanged
        stripped_manifest = yaml.safe_load(message.manifest)
        stripped_labels = stripped_manifest["metadata"].get("labels", {})
        stripped_labels.pop("airm.silogen.com/use-case", None)
        if not stripped_labels:
            stripped_manifest["metadata"].pop("labels", None)

        assert stripped_manifest == yaml.safe_load(hf_token_manifest_template)
