# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from airm.messaging.schemas import (
    ProjectSecretsCreateMessage,
    ProjectSecretStatus,
    ProjectSecretsUpdateMessage,
    SecretKind,
    SecretScope,
)
from app.projects.enums import ProjectStatus
from app.secrets.enums import SecretStatus, SecretUseCase
from app.secrets.models import OrganizationScopedSecret, ProjectScopedSecret
from app.secrets.models import Secret as SecretModel
from app.secrets.repository import get_secret_assignment_by_id, get_secret_in_organization
from app.secrets.schemas import OrganizationSecretIn, ProjectSecretIn, ProjectSecretsWithParentSecret, SecretIn, Secrets
from app.secrets.service import (
    add_organization_secret_assignments,
    create_organization_scoped_secret_in_organization,
    create_project_scoped_secret_in_organization,
    get_project_secrets_in_project,
    get_secrets_with_assigned_project_secrets,
    remove_organization_secret_assignments,
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
async def test_get_secrets_with_assigned_project_secrets_returns_all_organization_secrets(db_session: AsyncSession):
    """Test retrieving all organization-scoped secrets with all their project assignments."""
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

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization)

    # Should return ALL organization-scoped secrets, not filtered by project
    assert len(result.secrets) == 2
    secret_names = {secret.name for secret in result.secrets}
    assert secret_names == {"secret1", "secret2"}

    # Each secret should have its own project assignments
    for secret in result.secrets:
        assert len(secret.project_secrets) == 1


@pytest.mark.asyncio
async def test_get_secrets_with_assigned_project_secrets_no_secrets(db_session: AsyncSession):
    """Test retrieving secrets when none exist."""
    env = await factory.create_basic_test_environment(db_session)

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization)

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
        secret_type=SecretKind.EXTERNAL_SECRET.value,
        status=SecretStatus.PENDING.value,
    )

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization)

    assert isinstance(result, Secrets)
    assert len(result.secrets) == 1
    assert result.secrets[0].project_secrets == []


@pytest.mark.asyncio
async def test_get_secrets_with_assigned_project_secrets_only_returns_organization_secrets(db_session: AsyncSession):
    """Test that get_secrets_with_assigned_project_secrets only returns ORGANIZATION-scoped secrets."""
    env = await factory.create_basic_test_environment(db_session)

    # Create an organization-scoped secret
    org_secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="org-secret",
        scope=SecretScope.ORGANIZATION,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Create a project-scoped secret (should NOT be included)
    await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="project-secret",
        secret_status=SecretStatus.SYNCED.value,
    )

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization)

    assert isinstance(result, Secrets)
    # Should only return the organization-scoped secret, not the project-scoped one
    assert len(result.secrets) == 1
    assert result.secrets[0].id == org_secret.id
    assert result.secrets[0].scope == SecretScope.ORGANIZATION
    assert len(result.secrets[0].project_secrets) == 1


@pytest.mark.asyncio
async def test_get_secrets_with_assigned_project_secrets_organization_scoped_only(db_session: AsyncSession):
    """Test that only ORGANIZATION-scoped secrets are returned, not PROJECT-scoped secrets."""
    env = await factory.create_basic_test_environment(db_session)

    # Create an organization-scoped secret with PENDING status
    org_secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="org-secret",
        scope=SecretScope.ORGANIZATION,
        secret_status=SecretStatus.PENDING.value,
    )

    result = await get_secrets_with_assigned_project_secrets(db_session, env.organization)

    assert len(result.secrets) == 1
    assert result.secrets[0].id == org_secret.id
    assert result.secrets[0].status == SecretStatus.PENDING
    assert result.secrets[0].scope == SecretScope.ORGANIZATION
    assert len(result.secrets[0].project_secrets) == 1


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
    assert project_secret.secret.type == SecretKind.EXTERNAL_SECRET
    assert project_secret.secret.status == SecretStatus.SYNCED
    assert project_secret.secret.scope == SecretScope.ORGANIZATION


@pytest.mark.asyncio
async def test_get_project_secrets_in_project_includes_project_scoped_secrets(db_session: AsyncSession):
    """Test that get_project_secrets_in_project includes project-scoped secrets."""
    env = await factory.create_basic_test_environment(db_session)

    # Create project-scoped secret
    project_secret = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="project-secret",
        secret_status=SecretStatus.SYNCED.value,
    )

    result = await get_project_secrets_in_project(db_session, env.organization, env.project)

    assert isinstance(result, ProjectSecretsWithParentSecret)
    assert len(result.project_secrets) == 1

    ps = result.project_secrets[0]
    # For project-scoped secrets, id should be the secret's id
    assert ps.id == project_secret.id
    assert ps.project_id == env.project.id
    assert ps.status == ProjectSecretStatus.SYNCED
    # Parent secret should be the same as the project secret
    assert ps.secret.id == project_secret.id
    assert ps.secret.name == "project-secret"
    assert ps.secret.scope == SecretScope.PROJECT


@pytest.mark.asyncio
async def test_get_project_secrets_in_project_includes_both_types(db_session: AsyncSession):
    """Test that get_project_secrets_in_project includes both organization and project-scoped secrets."""
    env = await factory.create_basic_test_environment(db_session)

    # Create organization-scoped secret
    org_secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        name="org-secret",
        secret_status=SecretStatus.SYNCED.value,
        project_secret_status=ProjectSecretStatus.SYNCED.value,
    )

    # Create project-scoped secret
    proj_secret = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="project-secret",
        secret_status=SecretStatus.SYNCED.value,
    )

    result = await get_project_secrets_in_project(db_session, env.organization, env.project)

    assert isinstance(result, ProjectSecretsWithParentSecret)
    assert len(result.project_secrets) == 2

    # Check that both secrets are included
    secret_names = {ps.secret.name for ps in result.project_secrets}
    assert "org-secret" in secret_names
    assert "project-secret" in secret_names


@pytest.mark.asyncio
async def test_get_project_secrets_in_project_filters_by_project(db_session: AsyncSession):
    """Test that get_project_secrets_in_project only returns secrets for the specified project."""
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-002")

    # Create secrets for project 1
    await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="project1-secret",
        secret_status=SecretStatus.SYNCED.value,
    )

    # Create secrets for project 2
    await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        project2,
        name="project2-secret",
        secret_status=SecretStatus.SYNCED.value,
    )

    result = await get_project_secrets_in_project(db_session, env.organization, env.project)

    assert len(result.project_secrets) == 1
    assert result.project_secrets[0].secret.name == "project1-secret"
    assert result.project_secrets[0].project_id == env.project.id


@pytest.mark.asyncio
async def test_create_secret_without_projects(db_session: AsyncSession):
    """Test successful secret creation without project assignments."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = OrganizationSecretIn(
        name="test-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[],
    )

    with (
        patch("app.secrets.service.validate_and_patch_secret_manifest") as mock_validate,
        patch("app.secrets.service.sanitize_external_secret_manifest") as mock_sanitize,
    ):
        mock_validate.return_value = {"apiVersion": "v1", "kind": "Secret"}
        mock_sanitize.return_value = "apiVersion: v1\nkind: Secret\nmetadata:\n  name: sanitized-secret"

        result = await create_organization_scoped_secret_in_organization(
            db_session, env.organization.id, "test", secret_in, message_sender=mock_message_sender
        )

    assert result is not None
    assert result.name == "test-secret"
    assert result.type == SecretKind.EXTERNAL_SECRET
    assert result.scope == SecretScope.ORGANIZATION
    assert result.project_secrets == []
    assert result.status == SecretStatus.UNASSIGNED


@pytest.mark.asyncio
async def test_create_secret_with_projects(db_session: AsyncSession):
    """Test successful secret creation with project assignments."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = OrganizationSecretIn(
        name="test-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[env.project.id],
    )

    with (
        patch("app.secrets.service.validate_and_patch_secret_manifest") as mock_validate,
        patch("app.secrets.service.sanitize_external_secret_manifest") as mock_sanitize,
    ):
        mock_validate.return_value = {"apiVersion": "v1", "kind": "Secret"}
        mock_sanitize.return_value = "apiVersion: v1\nkind: Secret\nmetadata:\n  name: sanitized-secret"

        result = await create_organization_scoped_secret_in_organization(
            db_session, env.organization.id, "test", secret_in, message_sender=mock_message_sender
        )

    assert result.name == "test-secret"
    assert len(result.project_secrets) == 1
    assert result.project_secrets[0].project_id == env.project.id
    assert result.project_secrets[0].status == ProjectSecretStatus.PENDING


@pytest.mark.asyncio
async def test_create_secret_duplicate_name(db_session: AsyncSession):
    """Test creating secret with duplicate name fails."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    await factory.create_secret(db_session, env.organization, name="duplicate-secret")

    secret_in = OrganizationSecretIn(
        name="duplicate-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[],
    )

    with (
        patch("app.secrets.service.validate_and_patch_secret_manifest") as mock_validate,
        patch("app.secrets.service.sanitize_external_secret_manifest") as mock_sanitize,
    ):
        mock_validate.return_value = {"apiVersion": "v1", "kind": "Secret"}
        mock_sanitize.return_value = "apiVersion: v1\nkind: Secret\nmetadata:\n  name: sanitized-secret"

        with pytest.raises(ConflictException):
            await create_organization_scoped_secret_in_organization(
                db_session, env.organization.id, "test", secret_in, message_sender=mock_message_sender
            )


@pytest.mark.parametrize(
    "secret_status,secret_type,secret_scope,use_case",
    [
        (SecretStatus.PENDING.value, SecretKind.EXTERNAL_SECRET, SecretScope.ORGANIZATION, None),
        (SecretStatus.PENDING.value, SecretKind.KUBERNETES_SECRET, SecretScope.PROJECT, SecretUseCase.HUGGING_FACE),
    ],
)
@pytest.mark.asyncio
async def test_submit_delete_secret_pending_state(
    db_session: AsyncSession, secret_status, secret_type, secret_scope, use_case
):
    """Test deleting secret in pending state is successful for both generic and Hugging Face secrets."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    if secret_scope == SecretScope.ORGANIZATION:
        secret = await factory.create_secret_with_project_assignment(
            db_session,
            env.organization,
            env.project,
            name="test-secret",
            secret_status=secret_status,
            secret_type=secret_type,
            scope=secret_scope,
            project_secret_status=ProjectSecretStatus.SYNCED.value,
        )
        # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
        stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
        result = await db_session.execute(stmt)
        secret = result.unique().scalar_one()
    else:
        secret = await factory.create_project_scoped_secret(
            db_session,
            env.organization,
            env.project,
            name="test-secret",
            secret_type=secret_type,
            secret_status=secret_status,
            use_case=use_case,
        )

    user = "test@example.com"

    with patch("app.secrets.service.publish_secret_deletion_message") as mock_submit:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)
        mock_submit.assert_called_once()


@pytest.mark.asyncio
async def test_submit_delete_org_secret_without_assignments(db_session: AsyncSession):
    """Test deleting secret without project assignments."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)

    user = "test@example.com"

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    with patch("app.secrets.service.publish_secret_deletion_message") as mock_submit:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)

    # Verify the secret was deleted directly since it had no project assignments
    # Check by querying the database since the object may be detached
    deleted_secret = await db_session.get(SecretModel, secret.id)
    assert deleted_secret is None or deleted_secret.status == SecretStatus.DELETED.value


@pytest.mark.asyncio
async def test_submit_delete_org_secret_with_assignments(db_session: AsyncSession):
    """Test deleting organization secret with project assignments."""
    mock_message_sender = AsyncMock()

    env = await factory.create_basic_test_environment(db_session)

    # Create a secret with legacy ProjectSecret assignment
    secret = await factory.create_secret(
        db_session,
        env.organization,
        status=SecretStatus.SYNCED.value,
    )
    org_secret_assignment = await factory.create_organization_secret_assignment(
        db_session,
        env.project,
        secret,
        status=ProjectSecretStatus.SYNCED.value,
    )

    user = "test@example.com"

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    with patch("app.secrets.service.publish_secret_deletion_message") as mock_submit:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)

    await db_session.refresh(secret)
    assert secret.status == SecretStatus.DELETING.value

    # Verify org secret assignment status was updated
    await db_session.refresh(org_secret_assignment)
    assert org_secret_assignment.status == ProjectSecretStatus.DELETING.value


@pytest.mark.asyncio
async def test_update_project_secret_assignments_add_project(db_session: AsyncSession):
    """Test adding project to secret assignment."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")
    # Set project status to READY after creation
    project2.status = ProjectStatus.READY.value
    await db_session.flush()

    # Create an organization-scoped secret (default scope is ORGANIZATION)
    org_secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Refresh to ensure relationships are loaded
    await db_session.refresh(org_secret)

    user_email = "test@example.com"

    with patch("app.secrets.service.publish_project_secret_creation_message") as mock_publish:
        await update_project_secret_assignments(
            session=db_session,
            user_email=user_email,
            organization_id=env.organization.id,
            org_secret=org_secret,
            project_ids=[project2.id],
            message_sender=mock_message_sender,
        )

    await db_session.refresh(org_secret)
    # For organization-scoped secrets, check organization_secret_assignments
    assert len(org_secret.organization_secret_assignments) == 1
    assert org_secret.organization_secret_assignments[0].project_id == project2.id
    assert org_secret.status == SecretStatus.PENDING.value
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_secret_assignments_remove_project(db_session: AsyncSession):
    """Test removing project from secret assignment."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Eagerly load organization_secret_assignments and their project relationships
    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(SecretModel).where(SecretModel.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    user_email = "test@example.com"

    # Now the implementation correctly checks organization_secret_assignments
    with patch("app.secrets.service.publish_project_secret_deletion_message") as mock_publish:
        await update_project_secret_assignments(
            session=db_session,
            user_email=user_email,
            organization_id=env.organization.id,
            org_secret=secret,
            project_ids=[],
            message_sender=mock_message_sender,
        )

    # Verify the assignment status was set to DELETING
    await db_session.refresh(secret)
    assert len(secret.organization_secret_assignments) == 1
    assert secret.organization_secret_assignments[0].status == ProjectSecretStatus.DELETING
    assert secret.status == SecretStatus.PENDING.value
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_secret_assignments_no_changes(db_session: AsyncSession):
    """Test updating project assignments with no changes."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    # Set project to READY state so it can be assigned
    env.project.status = ProjectStatus.READY.value
    await db_session.flush()

    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(SecretModel).where(SecretModel.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Now the implementation correctly recognizes the existing assignment
    # and raises "No changes" error
    with pytest.raises(ValueError, match="No changes in project assignments"):
        await update_project_secret_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            org_secret=secret,
            project_ids=[env.project.id],
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
async def test_update_project_secret_assignments_invalid_status(db_session: AsyncSession):
    """Test updating project assignments with invalid secret status."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    # Create an organization-scoped secret with FAILED status
    org_secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.FAILED.value)

    # Refresh to ensure relationships are loaded
    await db_session.refresh(org_secret)

    with pytest.raises(ConflictException):
        await update_project_secret_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            org_secret=org_secret,
            project_ids=[env.project.id],
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
async def test_update_project_secret_assignments_project_not_ready(db_session: AsyncSession):
    """Test updating project assignments when project is not ready."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project = await factory.create_project(db_session, env.organization, env.cluster, name="failed-project")
    # Update project status to FAILED after creation
    project.status = ProjectStatus.FAILED.value

    # Create an organization-scoped secret (default scope is ORGANIZATION)
    org_secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Refresh to ensure relationships are loaded
    await db_session.refresh(org_secret)

    with pytest.raises(ConflictException, match="Project failed-project is not in a READY state"):
        await update_project_secret_assignments(
            session=db_session,
            user_email="user@example.com",
            organization_id=env.organization.id,
            org_secret=org_secret,
            project_ids=[project.id],
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
async def test_submit_delete_secret_success(db_session: AsyncSession):
    """Test successful project secret deletion."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    user = "test@example.com"

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(SecretModel).where(SecretModel.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    with patch("app.secrets.service.publish_secret_deletion_message") as mock_submit:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)

    assert secret_assignment.status == ProjectSecretStatus.DELETING.value
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    with patch("app.secrets.service.publish_secret_deletion_message") as mock_submit:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)

    assert secret_assignment.status == ProjectSecretStatus.DELETING.value


@pytest.mark.asyncio
async def test_submit_delete_org_secret_from_all_projects(db_session: AsyncSession):
    """Test deleting an organization secret from all projects."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")

    # Create an organization secret with assignments to two projects
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    assignment1 = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )
    assignment2 = await factory.create_organization_secret_assignment(
        db_session, project2, secret, status=ProjectSecretStatus.SYNCED.value
    )

    user = "test@example.com"

    # Reload secret to get current state
    stmt = select(SecretModel).where(SecretModel.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Delete the secret from all projects (no project_id provided)
    with patch("app.secrets.service.publish_secret_deletion_message") as mock_publish:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)

    # Verify both assignments were set to DELETING
    await db_session.refresh(assignment1)
    await db_session.refresh(assignment2)
    assert assignment1.status == ProjectSecretStatus.DELETING
    assert assignment2.status == ProjectSecretStatus.DELETING

    # Verify secret status was updated to DELETING
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.DELETING.value

    # Verify deletion messages were sent for both projects
    assert mock_publish.call_count == 2


@pytest.mark.asyncio
async def test_submit_delete_project_scoped_secret_with_project_id(db_session: AsyncSession):
    """Test that project_id parameter is ignored for project-scoped secrets."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    # Create a project-scoped secret
    secret = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    user = "test@example.com"

    # Reload secret to get current state
    stmt = (
        select(ProjectScopedSecret)
        .where(ProjectScopedSecret.id == secret.id)
        .options(selectinload(ProjectScopedSecret.project))
    )
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Delete the secret (project_id should be ignored for project-scoped secrets)
    with patch("app.secrets.service.publish_secret_deletion_message") as mock_publish:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)

    # Verify secret status was updated to DELETING
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.DELETING.value

    # Verify deletion message was sent with PROJECT scope
    mock_publish.assert_called_once()
    call_args = mock_publish.call_args[0]
    assert call_args[0] == env.project.cluster_id  # cluster_id
    assert call_args[1] == secret.id  # secret_id
    assert call_args[4] == SecretScope.PROJECT  # secret_scope


@pytest.mark.asyncio
async def test_submit_delete_org_secret_single_assignment_with_project_id(db_session: AsyncSession):
    """Test deleting the last assignment of an organization secret using project_id."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    # Create an organization secret with a single assignment
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    user = "test@example.com"

    # Reload secret to get current state
    stmt = select(SecretModel).where(SecretModel.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Delete the secret from the only project it's assigned to
    with patch("app.secrets.service.publish_secret_deletion_message") as mock_publish:
        await submit_delete_secret(db_session, secret, user, message_sender=mock_message_sender)

    # Verify the assignment was set to DELETING
    await db_session.refresh(assignment)
    assert assignment.status == ProjectSecretStatus.DELETING

    # Verify secret status was updated to DELETING
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.DELETING.value

    # Verify deletion message was sent
    mock_publish.assert_called_once()
    call_args = mock_publish.call_args[0]
    assert call_args[1] == assignment.id  # assignment_id
    assert call_args[4] == SecretScope.ORGANIZATION  # secret_scope


@pytest.mark.asyncio
async def test_update_project_secret_status_project_secret_not_found(db_session: AsyncSession):
    """Test updating project secret status when project secret doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=uuid4(),
        secret_scope=SecretScope.PROJECT,
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
    secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=secret_assignment.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.DELETED,
        status_reason="Deleted from cluster",
        updated_at=datetime.now(UTC),
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be deleted
    deleted_ps = await get_secret_assignment_by_id(db_session, secret_assignment.id)
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

    secret_assignment_1 = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )

    _ = await factory.create_organization_secret_assignment(
        db_session, project2, secret, status=ProjectSecretStatus.SYNCED.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=secret_assignment_1.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # First project secret should be deleted
    deleted_ps = await get_secret_assignment_by_id(db_session, secret_assignment_1.id)
    assert deleted_ps is None

    # Parent secret should still exist since ps2 remains
    existing_secret = await get_secret_in_organization(db_session, env.organization.id, secret.id)
    assert existing_secret is not None


@pytest.mark.asyncio
async def test_update_project_secret_status_delete_failed(db_session: AsyncSession):
    """Test handling project secret delete failure."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)
    secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=secret_assignment.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.DELETE_FAILED,
        status_reason="Failed to delete",
        updated_at=datetime.now(UTC),
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be updated to DELETE_FAILED
    await db_session.refresh(secret_assignment)
    assert secret_assignment.status == ProjectSecretStatus.DELETE_FAILED
    assert secret_assignment.status_reason == "Failed to delete"

    # Parent secret should be updated to DELETE_FAILED
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.DELETE_FAILED.value


@pytest.mark.asyncio
async def test_update_project_secret_status_child_unsolicited_delete(db_session: AsyncSession):
    """Test handling unsolicited project secret deletion."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    org_secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=org_secret_assignment.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.DELETED,
        status_reason="Deleted from cluster",
        updated_at=datetime.now(UTC),
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be updated to DELETED
    await db_session.refresh(org_secret_assignment)
    assert org_secret_assignment.status == ProjectSecretStatus.DELETED

    # Parent secret should be updated to SYNCED_ERROR
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.SYNCED_ERROR.value


@pytest.mark.asyncio
async def test_update_project_secret_status_synced_update(db_session: AsyncSession):
    """Test updating project secret status to synced."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.PENDING.value)
    org_secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.PENDING.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=org_secret_assignment.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Successfully synced",
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # Project secret should be updated
    await db_session.refresh(org_secret_assignment)
    assert org_secret_assignment.status == ProjectSecretStatus.SYNCED
    assert org_secret_assignment.status_reason == "Successfully synced"

    # Parent secret should be updated based on resolution
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.SYNCED.value


@pytest.mark.asyncio
async def test_update_project_secret_status_unassigned_when_no_children(db_session: AsyncSession):
    """Test setting secret to unassigned when last project assignment is deleted during normal operation."""
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    org_secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.DELETING.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=org_secret_assignment.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    # secret assignment should be deleted
    deleted_assignment = await get_secret_assignment_by_id(db_session, org_secret_assignment.id)
    assert deleted_assignment is None

    # Parent secret should be set to UNASSIGNED since it wasn't in DELETING state
    await db_session.refresh(secret)
    assert secret.status == SecretStatus.UNASSIGNED.value


@pytest.mark.asyncio
async def test_update_project_secret_status_deletes_project_scoped_secret(
    db_session: AsyncSession,
):
    """Test that PROJECT-scoped secrets are deleted."""
    env = await factory.create_basic_test_environment(db_session)
    # Create a PROJECT-scoped secret (like HF tokens)
    secret = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        secret_type=SecretKind.KUBERNETES_SECRET.value,
        secret_status=SecretStatus.SYNCED.value,
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=secret.id,
        secret_scope=SecretScope.PROJECT,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        reason=None,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    #  Secret should also be deleted since PROJECT-scoped secrets
    deleted_secret = await get_secret_in_organization(db_session, env.organization.id, secret.id)
    assert deleted_secret is None


@pytest.mark.asyncio
async def test_create_organization_scoped_secret_invalid_yaml_manifest(db_session: AsyncSession):
    """Test creating secret with invalid YAML manifest raises ValidationException."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = OrganizationSecretIn(
        name="invalid-yaml-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope="Organization",
        manifest="invalid: yaml: [unclosed",  # Invalid YAML
        project_ids=[],
    )

    with pytest.raises(ValidationException) as exc_info:
        await create_organization_scoped_secret_in_organization(
            session=db_session,
            organization_id=env.organization.id,
            user_email="test@example.com",
            secret_in=secret_in,
            message_sender=mock_message_sender,
        )

    assert "Invalid Secret manifest" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_project_secret_assignments_project_not_found(db_session: AsyncSession):
    """Test updating project assignments when project doesn't exist in organization."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    # Create an organization-scoped secret (default scope is ORGANIZATION)
    org_secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Refresh to ensure relationships are loaded
    await db_session.refresh(org_secret)

    # Try to assign to non-existent project
    non_existent_project_id = uuid4()

    with pytest.raises(ValueError) as exc_info:
        await update_project_secret_assignments(
            session=db_session,
            user_email="test@example.com",
            organization_id=env.organization.id,
            org_secret=org_secret,
            project_ids=[non_existent_project_id],
            message_sender=mock_message_sender,
        )

    assert "does not exist in the organization" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_project_secret_assignments_switch_projects(db_session: AsyncSession):
    """Test switching a secret from one project to another."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")

    # Set project2 to READY status
    project2.status = ProjectStatus.READY.value
    await db_session.flush()

    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(SecretModel).where(SecretModel.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Switch from env.project to project2
    with (
        patch("app.secrets.service.publish_project_secret_creation_message"),
        patch("app.secrets.service.publish_project_secret_deletion_message"),
    ):
        await update_project_secret_assignments(
            session=db_session,
            user_email="test@example.com",
            organization_id=env.organization.id,
            org_secret=secret,
            project_ids=[project2.id],  # Switch to different project
            message_sender=mock_message_sender,
        )

    # Verify the switch worked
    await db_session.refresh(secret)
    assert len(secret.organization_secret_assignments) == 2  # One DELETING, one PENDING
    assigned_project_ids = {a.project_id for a in secret.organization_secret_assignments}
    assert assigned_project_ids == {env.project.id, project2.id}

    # Check statuses
    env_assignment = next(a for a in secret.organization_secret_assignments if a.project_id == env.project.id)
    project2_assignment = next(a for a in secret.organization_secret_assignments if a.project_id == project2.id)
    assert env_assignment.status == ProjectSecretStatus.DELETING
    assert project2_assignment.status == ProjectSecretStatus.PENDING


@pytest.mark.asyncio
async def test_update_project_secret_status_secret_not_found(db_session: AsyncSession):
    """Test updating project secret status when parent secret doesn't exist."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a real secret and project secret first
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    org_secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=org_secret_assignment.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Updated",
    )

    # Mock get_secret_in_organization to return None, simulating secret not found
    with patch("app.secrets.service.get_secret_in_organization", return_value=None):
        # This should log error and return without raising exception
        await update_project_secret_status(db_session, env.cluster, msg)

    # Verify project secret still exists and unchanged (operation was skipped)
    await db_session.refresh(org_secret_assignment)
    assert org_secret_assignment.status == ProjectSecretStatus.SYNCED  # Should remain unchanged


@pytest.mark.asyncio
async def test_update_project_secret_assignments_continue_on_missing_project_secret(db_session: AsyncSession):
    """Test assignment creation with organization-scoped secrets."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Ensure project is in READY state
    env.project.status = ProjectStatus.READY.value
    await db_session.flush()

    # Mock the publish function to avoid AMQP issues
    with patch("app.secrets.service.publish_project_secret_creation_message") as mock_publish:
        await update_project_secret_assignments(
            session=db_session,
            user_email="test@example.com",
            organization_id=env.organization.id,
            org_secret=secret,
            project_ids=[env.project.id],
            message_sender=mock_message_sender,
        )

    # Verify assignment was created
    await db_session.refresh(secret)
    assert len(secret.organization_secret_assignments) == 1
    assert secret.organization_secret_assignments[0].project_id == env.project.id
    # Message should be sent
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_add_organization_secret_assignments_success(db_session: AsyncSession):
    """Test successfully adding organization secret assignments to projects."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")

    # Set both projects to READY status
    env.project.status = ProjectStatus.READY.value
    project2.status = ProjectStatus.READY.value
    await db_session.flush()

    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    user_email = "test@example.com"
    project_ids = [env.project.id, project2.id]

    with patch("app.secrets.service.publish_project_secret_creation_message") as mock_publish:
        await add_organization_secret_assignments(
            session=db_session,
            organization_id=env.organization.id,
            org_secret=secret,
            project_ids=project_ids,
            user_email=user_email,
            message_sender=mock_message_sender,
        )

    # Refresh the secret to get updated assignments
    await db_session.refresh(secret)

    # Verify assignments were created
    assert len(secret.organization_secret_assignments) == 2
    assigned_project_ids = {a.project_id for a in secret.organization_secret_assignments}
    assert assigned_project_ids == {env.project.id, project2.id}

    # Verify creation messages were sent for both projects
    assert mock_publish.call_count == 2


@pytest.mark.asyncio
async def test_add_organization_secret_assignments_project_not_found(db_session: AsyncSession):
    """Test adding organization secret assignment with non-existent project."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    fake_project_id = uuid4()

    with pytest.raises(ValueError, match="does not exist in the organization"):
        await add_organization_secret_assignments(
            session=db_session,
            organization_id=env.organization.id,
            org_secret=secret,
            project_ids=[fake_project_id],
            user_email="test@example.com",
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
async def test_add_organization_secret_assignments_project_not_ready(db_session: AsyncSession):
    """Test adding organization secret assignment when project is not in READY state."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    # Keep project in non-READY state (default factory state)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.UNASSIGNED.value)

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    with pytest.raises(ConflictException, match="not in a READY state"):
        await add_organization_secret_assignments(
            session=db_session,
            organization_id=env.organization.id,
            org_secret=secret,
            project_ids=[env.project.id],
            user_email="test@example.com",
            message_sender=mock_message_sender,
        )


@pytest.mark.asyncio
async def test_remove_organization_secret_assignments_success(db_session: AsyncSession):
    """Test successfully removing organization secret assignments from projects."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")

    # Create secret with assignments to both projects
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Add a second assignment manually
    from app.secrets.repository import assign_organization_secret_to_projects

    await assign_organization_secret_to_projects(
        session=db_session,
        secret_id=secret.id,
        project_ids=[project2.id],
        user_email="test@example.com",
    )
    await db_session.flush()

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Verify we have 2 assignments before removal
    assert len(secret.organization_secret_assignments) == 2

    with patch("app.secrets.service.publish_project_secret_deletion_message") as mock_publish:
        await remove_organization_secret_assignments(
            session=db_session, org_secret=secret, project_ids=[env.project.id], message_sender=mock_message_sender
        )

    # Refresh the secret to get updated assignments
    await db_session.refresh(secret)

    # Verify assignment status was set to DELETING (not actually deleted from DB yet)
    assignment = next((a for a in secret.organization_secret_assignments if a.project_id == env.project.id), None)
    assert assignment is not None
    assert assignment.status == ProjectSecretStatus.DELETING

    # Verify deletion message was sent
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_remove_organization_secret_assignments_not_assigned(db_session: AsyncSession):
    """Test removing organization secret assignment that doesn't exist."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-2")

    # Create secret with assignment to only one project
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Reload secret to get current state (relationships are eagerly loaded via lazy="joined")
    stmt = select(OrganizationScopedSecret).where(OrganizationScopedSecret.id == secret.id)
    result = await db_session.execute(stmt)
    secret = result.unique().scalar_one()

    # Try to remove project2 which is not assigned
    with pytest.raises(ValueError, match="is not assigned to the secret"):
        await remove_organization_secret_assignments(
            session=db_session, org_secret=secret, project_ids=[project2.id], message_sender=mock_message_sender
        )


@pytest.mark.asyncio
@patch("app.secrets.service.get_project_storages_by_project_secret")
@patch("app.secrets.service.update_project_storage_secret_status")
async def test_update_project_secret_status_updates_project_storage(
    mock_update_project_storage_secret_status, mock_get_project_storages_by_project_secret, db_session: AsyncSession
):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    org_secret_assignment = await factory.create_organization_secret_assignment(
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
        project_secret_id=org_secret_assignment.id,
        secret_scope=SecretScope.ORGANIZATION,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Test update",
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    mock_get_project_storages_by_project_secret.assert_called_once_with(
        db_session, org_secret_assignment.organization_secret_id, org_secret_assignment.project_id
    )
    mock_update_project_storage_secret_status.assert_called_once_with(
        db_session, org_secret_assignment.organization_secret_id, project_storage
    )


@pytest.mark.skip(reason="Temporarily disabled")
@pytest.mark.asyncio
async def test_submit_delete_huggingface_token_success(db_session: AsyncSession):
    """Test successful deletion of Hugging Face token including all three components."""
    mock_message_sender = AsyncMock()
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
        secret_type=SecretKind.KUBERNETES_SECRET,
        scope=SecretScope.PROJECT,
        manifest=hf_token_manifest,
        secret_status=SecretStatus.SYNCED.value,
        project_secret_status=ProjectSecretStatus.SYNCED.value,
    )

    # Set the use_case to Hugging Face after creation
    hf_token.use_case = SecretUseCase.HUGGING_FACE
    await db_session.flush()

    # Eagerly load the project relationships
    stmt = (
        select(ProjectScopedSecret)
        .where(ProjectScopedSecret.id == hf_token.id)
        .options(selectinload(ProjectScopedSecret.project))
    )
    result = await db_session.execute(stmt)
    hf_token = result.unique().scalar_one()
    user = "test@example.com"

    with patch("app.secrets.service.publish_secret_deletion_message") as mock_submit:
        await submit_delete_secret(db_session, hf_token, user, message_sender=mock_message_sender)

    # Verify the secret status was set to DELETING
    await db_session.refresh(hf_token)
    assert hf_token.status == SecretStatus.DELETING.value

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=hf_token.id,
        secret_scope=SecretScope.PROJECT,
        status=ProjectSecretStatus.DELETED,
        updated_at=datetime.now(UTC),
        status_reason="Test update",
    )

    """
    TODO: uncomment when secret status handler has been re-implemented
    await update_project_secret_status(db_session, env.cluster, msg)

    # Verify all three components are deleted:
    # 1. ProjectScopedSecret entry should be deleted
    deleted_pss = await get_project_scoped_secret(db_session, env.organization.id, env.project.id, hf_token.id)
    assert deleted_pss is None

    # 2. Secret record should be deleted (since it was DELETING and no more children)
    deleted_secret = await get_secret_in_organization(db_session, env.organization.id, hf_token.id)
    assert deleted_secret is None


"""


@pytest.mark.asyncio
@patch("app.secrets.service.get_project_storages_by_project_secret")
@patch("app.secrets.service.update_project_storage_secret_status")
@patch("app.secrets.service.logger")
async def test_update_project_secret_status_logs_error_when_project_storage_not_found(
    mock_logger,
    mock_update_project_storage_secret_status,
    mock_get_organization_secret_assignment,
    db_session: AsyncSession,
):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.SYNCED.value)
    organization_secret_assignment = await factory.create_organization_secret_assignment(
        db_session, env.project, secret, status=ProjectSecretStatus.SYNCED.value
    )

    mock_get_organization_secret_assignment.return_value = None

    msg = ProjectSecretsUpdateMessage(
        message_type="project_secrets_update",
        project_secret_id=organization_secret_assignment.id,
        status=ProjectSecretStatus.SYNCED,
        updated_at=datetime.now(UTC),
        status_reason="Test update",
        secret_scope=SecretScope.ORGANIZATION,
    )

    await update_project_secret_status(db_session, env.cluster, msg)

    mock_get_organization_secret_assignment.assert_called_once_with(db_session, secret.id, env.project.id)
    mock_logger.info.assert_called_once_with(
        f"No ProjectStorages found for secret_id: {secret.id} project_id: {env.project.id}"
    )

    mock_update_project_storage_secret_status.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Hugging Face Kubernetes secrets require special handling that needs to be reimplemented")
async def test_huggingface_manifest_template_processing(db_session: AsyncSession):
    """Test that Hugging Face token Kubernetes secret manifests are processed correctly by the API."""
    mock_message_sender = AsyncMock()
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
    # Create the secret using the service layer (this tests _prepare_secret_input)
    secret_in = SecretIn(
        name="hf-token-template",
        type=SecretKind.KUBERNETES_SECRET,
        scope=SecretScope.ORGANIZATION,  # Changed to ORGANIZATION since the function creates org-scoped secrets
        manifest=hf_token_manifest_template,
        project_ids=[env.project.id],
        use_case=SecretUseCase.HUGGING_FACE,
    )

    result = await create_organization_scoped_secret_in_organization(
        db_session, env.organization.id, user, secret_in, message_sender=mock_message_sender
    )

    # Verify the secret was created successfully
    assert result is not None
    assert result.name == "hf-token-template"
    assert result.type == SecretKind.KUBERNETES_SECRET
    assert result.scope == SecretScope.ORGANIZATION  # Changed to match the actual scope created
    assert result.use_case == SecretUseCase.HUGGING_FACE

    # Note: The manifest security handling has been moved to a different part of the codebase
    # Verify the secret was stored
    stored_secret = await get_secret_in_organization(db_session, env.organization.id, result.id)
    assert stored_secret is not None
    call_args = mock_message_sender.enqueue.call_args
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


@pytest.mark.asyncio
async def test_create_project_scoped_secret_in_organization_success(db_session: AsyncSession):
    """Test successful creation of project-scoped secret."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = ProjectSecretIn(
        name="test-project-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope=SecretScope.PROJECT,
        use_case=SecretUseCase.HUGGING_FACE,
        manifest="""apiVersion: v1
kind: Secret
metadata:
  name: test-project-secret
type: Opaque
data:
  token: aGZfdG9rZW4=""",
    )

    with patch("app.secrets.service.publish_project_secret_creation_message") as mock_submit:
        result = await create_project_scoped_secret_in_organization(
            db_session,
            env.organization.id,
            env.project.id,
            "test@example.com",
            secret_in,
            message_sender=mock_message_sender,
        )

    assert result is not None
    assert result.name == "test-project-secret"
    assert result.type == SecretKind.KUBERNETES_SECRET
    assert result.scope == SecretScope.PROJECT
    assert result.status == SecretStatus.PENDING
    assert result.use_case == SecretUseCase.HUGGING_FACE
    assert len(result.project_secrets) == 1
    assert result.project_secrets[0].project_id == env.project.id
    assert result.project_secrets[0].project_name == env.project.name
    assert result.project_secrets[0].status == ProjectSecretStatus.PENDING

    call_args = mock_submit.call_args
    project_secret = call_args[0][0]
    assert project_secret.project.cluster_id == env.project.cluster_id


@pytest.mark.asyncio
async def test_create_project_scoped_secret_in_organization_project_not_found(db_session: AsyncSession):
    """Test creating project-scoped secret when project doesn't exist."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = ProjectSecretIn(
        name="test-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope=SecretScope.PROJECT,
        manifest="""apiVersion: v1
kind: Secret
metadata:
  name: test-secret
type: Opaque
data:
  token: dGVzdA==""",
    )

    non_existent_project_id = uuid4()

    with pytest.raises(NotFoundException) as exc_info:
        await create_project_scoped_secret_in_organization(
            db_session,
            env.organization.id,
            non_existent_project_id,
            "test@example.com",
            secret_in,
            message_sender=mock_message_sender,
        )

    assert "not found in your organization" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_project_scoped_secret_in_organization_invalid_manifest(db_session: AsyncSession):
    """Test creating project-scoped secret with invalid Kubernetes manifest."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = ProjectSecretIn(
        name="test-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope=SecretScope.PROJECT,
        manifest="invalid: yaml: [unclosed",  # Invalid YAML
    )

    with pytest.raises(ValidationException) as exc_info:
        await create_project_scoped_secret_in_organization(
            db_session,
            env.organization.id,
            env.project.id,
            "test@example.com",
            secret_in,
            message_sender=mock_message_sender,
        )

    assert "Invalid Secret manifest" in str(exc_info.value)
    assert "Failed to load YAML" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_project_scoped_secret_in_organization_with_use_case_labels(db_session: AsyncSession):
    """Test that use case labels are properly added to the manifest."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = ProjectSecretIn(
        name="hf-token",
        type=SecretKind.KUBERNETES_SECRET,
        scope=SecretScope.PROJECT,
        use_case=SecretUseCase.HUGGING_FACE,
        manifest="""apiVersion: v1
kind: Secret
metadata:
  name: hf-token
type: Opaque
data:
  token: aGZfdG9rZW4=""",
    )

    with patch("app.secrets.service.publish_project_secret_creation_message") as mock_submit:
        result = await create_project_scoped_secret_in_organization(
            db_session,
            env.organization.id,
            env.project.id,
            "test@example.com",
            secret_in,
            message_sender=mock_message_sender,
        )

    # Verify the manifest sent to cluster includes use case labels
    call_args = mock_submit.call_args
    message = call_args[0][1]

    # Parse the manifest to check for labels
    import yaml

    manifest_dict = yaml.safe_load(message)
    assert "labels" in manifest_dict["metadata"]
    assert "airm.silogen.com/use-case" in manifest_dict["metadata"]["labels"]
    assert manifest_dict["metadata"]["labels"]["airm.silogen.com/use-case"] == "huggingface"


@pytest.mark.asyncio
async def test_create_project_scoped_secret_in_organization_without_use_case(db_session: AsyncSession):
    """Test creating project-scoped secret without use case."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = ProjectSecretIn(
        name="generic-secret",
        type=SecretKind.KUBERNETES_SECRET,
        scope=SecretScope.PROJECT,
        use_case=None,  # No use case
        manifest="""apiVersion: v1
kind: Secret
metadata:
  name: generic-secret
type: Opaque
data:
  password: cGFzc3dvcmQ=""",
    )

    with patch("app.secrets.service.publish_project_secret_creation_message") as mock_submit:
        result = await create_project_scoped_secret_in_organization(
            db_session,
            env.organization.id,
            env.project.id,
            "test@example.com",
            secret_in,
            message_sender=mock_message_sender,
        )

    assert result.use_case is None
    call_args = mock_submit.call_args
    message = call_args[0][1]

    # Parse the manifest - should not have use case labels when use_case is None
    import yaml

    manifest_dict = yaml.safe_load(message)
    labels = manifest_dict["metadata"].get("labels", {})
    assert "airm.silogen.com/use-case" not in labels


@pytest.mark.asyncio
async def test_create_organization_scoped_secret_in_organization_no_projects(db_session):
    mock_message_sender = AsyncMock()
    # Arrange: create org and input
    env = await factory.create_basic_test_environment(db_session)
    secret_in = OrganizationSecretIn(
        name="org-secret-no-projects",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: org-secret-no-projects
spec:
  secretStoreRef:
    name: test-store
  target:
    name: test-target
  data: []""",
        project_ids=[],
    )

    # Act: create the secret
    result = await create_organization_scoped_secret_in_organization(
        db_session, env.organization.id, "test@example.com", secret_in, message_sender=mock_message_sender
    )

    # Assert: check attributes and no project assignments
    assert result is not None
    assert result.name == "org-secret-no-projects"
    assert result.type == SecretKind.EXTERNAL_SECRET
    assert result.scope == SecretScope.ORGANIZATION
    assert result.status == SecretStatus.UNASSIGNED
    assert result.project_secrets == []


@pytest.mark.asyncio
async def test_create_organization_scoped_secret_in_organization_success_with_projects(db_session: AsyncSession):
    """Test successful creation of organization-scoped secret with project assignments."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    secret_in = OrganizationSecretIn(
        name="org-secret-with-projects",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: org-secret-with-projects
spec:
  secretStoreRef:
    name: test-store
  target:
    name: test-target
  data: []""",
        project_ids=[env.project.id],
    )

    with (
        patch("app.secrets.service.validate_and_patch_secret_manifest") as mock_validate,
        patch("app.secrets.service.sanitize_external_secret_manifest") as mock_sanitize,
        patch("app.secrets.service.publish_project_secret_creation_message") as mock_publish,
    ):
        mock_validate.return_value = {"apiVersion": "external-secrets.io/v1beta1", "kind": "ExternalSecret"}
        mock_sanitize.return_value = "sanitized manifest"

        result = await create_organization_scoped_secret_in_organization(
            db_session, env.organization.id, "test@example.com", secret_in, message_sender=mock_message_sender
        )

        assert result is not None
        assert result.name == "org-secret-with-projects"
        assert result.type == SecretKind.EXTERNAL_SECRET
        assert result.scope == SecretScope.ORGANIZATION
        assert result.status == SecretStatus.PENDING
        assert len(result.project_secrets) == 1
        assert result.project_secrets[0].project_id == env.project.id
        assert result.project_secrets[0].status == ProjectSecretStatus.PENDING
        mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_create_organization_scoped_secret_in_organization_duplicate_name(db_session: AsyncSession):
    """Should raise ConflictException when creating an org-scoped secret with a duplicate name in the same org."""
    mock_message_sender = AsyncMock()
    env = await factory.create_basic_test_environment(db_session)

    # Create the first secret
    secret_in_1 = OrganizationSecretIn(
        name="duplicate-org-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: duplicate-org-secret
spec:
  secretStoreRef:
    name: test-store
  target:
    name: test-target
  data: []""",
        project_ids=[],
    )
    await create_organization_scoped_secret_in_organization(
        db_session, env.organization.id, "test@example.com", secret_in_1, message_sender=mock_message_sender
    )

    # Attempt to create a second secret with the same name
    secret_in_2 = OrganizationSecretIn(
        name="duplicate-org-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: duplicate-org-secret
spec:
  secretStoreRef:
    name: test-store
  target:
    name: test-target
  data: []""",
        project_ids=[],
    )

    with pytest.raises(ConflictException) as exc_info:
        await create_organization_scoped_secret_in_organization(
            db_session, env.organization.id, "test@example.com", secret_in_2, message_sender=mock_message_sender
        )
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unique_constraint_different_projects_same_secret_name(db_session: AsyncSession):
    """Test that two different projects can have secrets with the same name.

    This verifies the unique constraint works correctly for project-scoped secrets:
    the constraint is on (organization_id, project_id, name, type), so different
    project_ids allow the same name.
    """
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.organization, env.cluster, name="project-002")

    # Create a project-scoped secret in project 1
    secret1 = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="shared-secret-name",
        secret_status=SecretStatus.SYNCED.value,
    )

    # Create a project-scoped secret with the same name in project 2
    secret2 = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        project2,
        name="shared-secret-name",
        secret_status=SecretStatus.SYNCED.value,
    )

    # Verify both secrets were created successfully
    assert secret1.id != secret2.id
    assert secret1.name == secret2.name == "shared-secret-name"
    assert secret1.scope == secret2.scope == SecretScope.PROJECT
    assert secret1.type == secret2.type == SecretKind.EXTERNAL_SECRET
    assert secret1.project_id == env.project.id
    assert secret2.project_id == project2.id


@pytest.mark.asyncio
async def test_unique_constraint_org_and_project_secret_same_name(db_session: AsyncSession):
    """Test that an organization secret and a project secret can have the same name.

    This verifies the unique constraint allows the same name when one secret is
    organization-scoped (project_id is NULL) and another is project-scoped
    (project_id is set). The constraint is on (organization_id, project_id, name, type).
    """
    env = await factory.create_basic_test_environment(db_session)

    # Create an organization-scoped secret
    org_secret = await factory.create_secret(
        db_session,
        env.organization,
        name="common-name",
        secret_type=SecretKind.EXTERNAL_SECRET.value,
        secret_scope=SecretScope.ORGANIZATION.value,
        status=SecretStatus.UNASSIGNED.value,
    )

    # Create a project-scoped secret with the same name
    project_secret = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="common-name",
        secret_status=SecretStatus.SYNCED.value,
    )

    # Verify both secrets were created successfully
    assert org_secret.id != project_secret.id
    assert org_secret.name == project_secret.name == "common-name"
    assert org_secret.type == project_secret.type == SecretKind.EXTERNAL_SECRET
    assert org_secret.scope == SecretScope.ORGANIZATION
    assert project_secret.scope == SecretScope.PROJECT
    # Organization secret has no project_id (NULL)
    assert not hasattr(org_secret, "project_id") or org_secret.project_id is None
    # Project secret has a project_id
    assert project_secret.project_id == env.project.id


@pytest.mark.asyncio
async def test_unique_constraint_violation_same_project_same_name(db_session: AsyncSession):
    """Test that creating duplicate project-scoped secrets in the same project fails.

    This verifies the unique constraint prevents duplicates when
    (organization_id, project_id, name, type) are all the same.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Create the first project-scoped secret
    await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="duplicate-project-secret",
        secret_status=SecretStatus.SYNCED.value,
    )

    # Attempt to create a second project-scoped secret with the same name in the same project
    with pytest.raises(IntegrityError) as exc_info:
        await factory.create_project_scoped_secret(
            db_session,
            env.organization,
            env.project,
            name="duplicate-project-secret",
            secret_status=SecretStatus.SYNCED.value,
        )

    # Verify it's the unique constraint that failed
    assert "uq_secret_org_proj_name_type" in str(exc_info.value) or "unique" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_unique_constraint_violation_same_org_secret_name(db_session: AsyncSession):
    """Test that creating duplicate organization-scoped secrets in the same organization fails.

    This verifies the unique constraint prevents duplicates for organization-scoped secrets
    when (organization_id, project_id=NULL, name, type) are all the same.
    Note: postgresql_nulls_not_distinct=True means NULL values are treated as equal.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Create the first organization-scoped secret
    await factory.create_secret(
        db_session,
        env.organization,
        name="duplicate-org-secret",
        secret_type=SecretKind.EXTERNAL_SECRET.value,
        secret_scope=SecretScope.ORGANIZATION.value,
        status=SecretStatus.UNASSIGNED.value,
    )

    # Attempt to create a second organization-scoped secret with the same name
    with pytest.raises(IntegrityError) as exc_info:
        await factory.create_secret(
            db_session,
            env.organization,
            name="duplicate-org-secret",
            secret_type=SecretKind.EXTERNAL_SECRET.value,
            secret_scope=SecretScope.ORGANIZATION.value,
            status=SecretStatus.UNASSIGNED.value,
        )

    # Verify it's the unique constraint that failed
    assert "uq_secret_org_proj_name_type" in str(exc_info.value) or "unique" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_unique_constraint_org_secrets_different_types_same_name(db_session: AsyncSession):
    """Test that 2 org secrets (same org) can share the same name if they have different types.

    This verifies that the type field is part of the unique constraint for organization-scoped
    secrets, so changing the type allows the same name within the same organization.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Create an organization-scoped secret with type EXTERNAL
    org_secret1 = await factory.create_secret(
        db_session,
        env.organization,
        name="org-multi-type-secret",
        secret_type=SecretKind.EXTERNAL_SECRET.value,
        secret_scope=SecretScope.ORGANIZATION.value,
        status=SecretStatus.UNASSIGNED.value,
    )

    # Create an organization-scoped secret with the same name but type KUBERNETES_SECRET
    org_secret2 = await factory.create_secret(
        db_session,
        env.organization,
        name="org-multi-type-secret",
        secret_type=SecretKind.KUBERNETES_SECRET.value,
        secret_scope=SecretScope.ORGANIZATION.value,
        status=SecretStatus.UNASSIGNED.value,
    )

    # Verify both secrets were created successfully
    assert org_secret1.id != org_secret2.id
    assert org_secret1.name == org_secret2.name == "org-multi-type-secret"
    assert org_secret1.scope == org_secret2.scope == SecretScope.ORGANIZATION
    assert org_secret1.type == SecretKind.EXTERNAL_SECRET
    assert org_secret2.type == SecretKind.KUBERNETES_SECRET


@pytest.mark.asyncio
async def test_unique_constraint_project_secrets_same_project_different_types(db_session: AsyncSession):
    """Test that 2 project secrets can share the same name if they belong to the same project but have different types.

    This verifies that the type field is part of the unique constraint for project-scoped secrets,
    so changing the type allows the same name within the same project.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Create a project-scoped secret with type EXTERNAL
    secret1 = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="multi-type-secret",
        secret_type=SecretKind.EXTERNAL_SECRET.value,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Create a project-scoped secret with the same name but type KUBERNETES_SECRET in the same project
    secret2 = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="multi-type-secret",
        secret_type=SecretKind.KUBERNETES_SECRET.value,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Verify both secrets were created successfully
    assert secret1.id != secret2.id
    assert secret1.name == secret2.name == "multi-type-secret"
    assert secret1.project_id == secret2.project_id == env.project.id
    assert secret1.type == SecretKind.EXTERNAL_SECRET
    assert secret2.type == SecretKind.KUBERNETES_SECRET
