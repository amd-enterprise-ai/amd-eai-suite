# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.schemas import ProjectSecretStatus, SecretKind, SecretScope
from app.secrets.enums import SecretStatus, SecretUseCase
from app.secrets.models import OrganizationScopedSecret, ProjectScopedSecret
from app.secrets.repository import (
    assign_organization_secret_to_projects,
    create_organization_scoped_secret,
    create_project_scoped_secret,
    delete_secret,
    delete_secret_assignment,
    get_organization_scoped_secret,
    get_organization_secret_assignment,
    get_organization_secrets_assigned_to_project,
    get_project_scoped_secret,
    get_secret,
    get_secret_by_id_and_use_case,
    get_secrets,
    get_secrets_for_project,
    update_org_assignment_status,
    update_org_scoped_secret_status,
    update_project_scoped_secret_status,
)
from app.secrets.schemas import OrganizationSecretIn
from tests import factory  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_secrets_returns_secrets_with_projects(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.cluster, name="unique-project-2")
    await factory.create_secret_with_project_assignment(
        db_session, env.project, secret_status=SecretStatus.SYNCED.value
    )
    await factory.create_project_scoped_secret(
        db_session, env.project, name="project-secret", secret_status=SecretStatus.SYNCED.value
    )
    await factory.create_project_scoped_secret(
        db_session, project2, name="project-secret2", secret_status=SecretStatus.SYNCED.value
    )

    secrets = await get_secrets(db_session)

    assert len(secrets) == 3

    org_secrets = [s for s in secrets if isinstance(s, OrganizationScopedSecret)]
    project_secrets = [s for s in secrets if isinstance(s, ProjectScopedSecret)]

    assert len(org_secrets) == 1
    org_secret = org_secrets[0]
    assert len(org_secret.organization_secret_assignments) == 1
    assert org_secret.organization_secret_assignments[0].project.name == "test-project"

    assert len(project_secrets) == 2


@pytest.mark.asyncio
async def test_get_secret(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, status=SecretStatus.DELETING.value)

    result = await get_secret(db_session, secret.id)

    assert result.id == secret.id


@pytest.mark.asyncio
async def test_update_project_scoped_secret_status(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(
        db_session, status=SecretStatus.DELETING.value, secret_scope=SecretScope.PROJECT
    )
    now = datetime.now(UTC)

    await update_project_scoped_secret_status(
        db_session, secret, ProjectSecretStatus.PENDING, "Updating Secret", now, "admin@example.com"
    )

    assert secret.status == "Pending"
    assert secret.status_reason == "Updating Secret"


@pytest.mark.asyncio
async def test_update_org_scoped_secret_status(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, status=SecretStatus.DELETING.value)
    now = datetime.now(UTC)

    await update_org_scoped_secret_status(
        db_session, secret, SecretStatus.PENDING, "Updating Secret", now, "admin@example.com"
    )

    assert secret.status == "Pending"
    assert secret.status_reason == "Updating Secret"


@pytest.mark.asyncio
async def test_delete_secret(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, status=SecretStatus.DELETING.value)

    await delete_secret(db_session, secret)

    assert await get_secret(db_session, secret.id) is None


@pytest.mark.asyncio
async def test_get_project_secret_found(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    # Create an organization-scoped secret with project assignment
    org_secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, secret_status=SecretStatus.SYNCED.value
    )

    # Test getting the organization secret assignment (modern equivalent of ProjectSecret join table)
    result = await get_organization_secret_assignment(db_session, org_secret.id, env.project.id)
    assert result is not None
    assert result.organization_secret_id == org_secret.id
    assert result.project_id == env.project.id


@pytest.mark.asyncio
async def test_get_project_secret_not_found(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    _ = await factory.create_secret(db_session, status=SecretStatus.UNASSIGNED.value, secret_scope=SecretScope.PROJECT)

    result = await get_project_scoped_secret(db_session, uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_delete_secret_assignment(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    # Create an organization-scoped secret with project assignment
    org_secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, secret_status=SecretStatus.SYNCED.value
    )

    # Get the assignment
    assignment = await get_organization_secret_assignment(db_session, org_secret.id, env.project.id)
    assert assignment is not None

    # Delete the assignment
    await delete_secret_assignment(db_session, assignment)

    # Verify it's deleted
    result = await get_organization_secret_assignment(db_session, org_secret.id, env.project.id)
    assert result is None


@pytest.mark.asyncio
async def test_create_project_scoped_secret(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"
    secret_status = SecretStatus.PENDING

    result = await create_project_scoped_secret(
        session=db_session,
        project_id=env.project.id,
        name="test-project-secret",
        secret_type=SecretKind.KUBERNETES_SECRET,
        status=secret_status,
        creator=creator,
        use_case=SecretUseCase.HUGGING_FACE,
    )

    assert isinstance(result, ProjectScopedSecret)
    assert result.name == "test-project-secret"
    assert result.type == SecretKind.KUBERNETES_SECRET
    assert result.scope == SecretScope.PROJECT
    assert result.project_id == env.project.id
    assert result.use_case == SecretUseCase.HUGGING_FACE
    assert result.status == secret_status
    assert result.created_by == creator
    assert result.updated_by == creator


@pytest.mark.asyncio
async def test_create_organization_scoped_secret_success(db_session):
    env = await factory.create_basic_test_environment(db_session)
    creator = "org-admin@example.com"
    secret_status = SecretStatus.UNASSIGNED
    secret_in = OrganizationSecretIn(
        name="org-secret",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: external-secrets.io/v1beta1\nkind: ExternalSecret\nmetadata:\n  name: org-secret",
        project_ids=[env.project.id],
    )

    result = await create_organization_scoped_secret(
        session=db_session, secret_in=secret_in, secret_status=secret_status, creator=creator
    )

    assert result.name == "org-secret"
    assert result.type == SecretKind.EXTERNAL_SECRET
    assert result.scope == SecretScope.ORGANIZATION
    assert result.status == secret_status
    assert result.created_by == creator
    assert result.updated_by == creator
    assert result.manifest.startswith("apiVersion: external-secrets.io/v1beta1")


@pytest.mark.asyncio
async def test_create_organization_scoped_secret_duplicate_name_conflict(db_session):
    env = await factory.create_basic_test_environment(db_session)
    creator = "org-admin@example.com"
    secret_status = SecretStatus.UNASSIGNED
    secret_in = OrganizationSecretIn(
        name="org-secret-dup",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: external-secrets.io/v1beta1\nkind: ExternalSecret\nmetadata:\n  name: org-secret-dup",
        project_ids=[],
    )

    await create_organization_scoped_secret(
        session=db_session, secret_in=secret_in, secret_status=secret_status, creator=creator
    )

    with pytest.raises(Exception) as exc_info:
        await create_organization_scoped_secret(
            session=db_session, secret_in=secret_in, secret_status=secret_status, creator=creator
        )
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_assign_organization_secret_to_projects_idempotent(db_session):
    env = await factory.create_basic_test_environment(db_session)
    creator = "org-admin@example.com"
    secret_status = SecretStatus.UNASSIGNED
    secret_in = OrganizationSecretIn(
        name="org-secret-idempotent",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: external-secrets.io/v1beta1\nkind: ExternalSecret\nmetadata:\n  name: org-secret-idempotent",
        project_ids=[],
    )
    secret = await create_organization_scoped_secret(
        session=db_session, secret_in=secret_in, secret_status=secret_status, creator=creator
    )

    # Assign to the same project twice
    project_ids = [env.project.id]
    await assign_organization_secret_to_projects(
        session=db_session, secret=secret, project_ids=project_ids, user_email=creator
    )
    await assign_organization_secret_to_projects(
        session=db_session, secret=secret, project_ids=project_ids, user_email=creator
    )

    secret = await get_organization_scoped_secret(session=db_session, secret_id=secret.id)

    # Should not create duplicate assignments
    assert len(secret.organization_secret_assignments) == 1


@pytest.mark.asyncio
async def test_assign_organization_secret_to_projects_multiple_projects(db_session):
    env = await factory.create_basic_test_environment(db_session)
    creator = "org-admin@example.com"
    secret_status = SecretStatus.UNASSIGNED
    secret_in = OrganizationSecretIn(
        name="org-secret-multi",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: external-secrets.io/v1beta1\nkind: ExternalSecret\nmetadata:\n  name: org-secret-multi",
        project_ids=[],
    )
    secret = await create_organization_scoped_secret(
        session=db_session, secret_in=secret_in, secret_status=secret_status, creator=creator
    )

    project2 = await factory.create_project(db_session, env.cluster, name="project2")
    project_ids = [env.project.id, project2.id]
    await assign_organization_secret_to_projects(
        session=db_session, secret=secret, project_ids=project_ids, user_email=creator
    )

    secret = await get_organization_scoped_secret(session=db_session, secret_id=secret.id)

    assigned_ids = {a.project_id for a in secret.organization_secret_assignments}
    assert env.project.id in assigned_ids
    assert project2.id in assigned_ids
    assert len(secret.organization_secret_assignments) == 2


@pytest.mark.asyncio
async def test_assign_organization_secret_to_projects_adds_only_new_assignments(db_session):
    env = await factory.create_basic_test_environment(db_session)
    creator = "org-admin@example.com"
    secret_status = SecretStatus.UNASSIGNED
    secret_in = OrganizationSecretIn(
        name="org-secret-partial",
        type=SecretKind.EXTERNAL_SECRET,
        scope=SecretScope.ORGANIZATION,
        manifest="apiVersion: external-secrets.io/v1beta1\nkind: ExternalSecret\nmetadata:\n  name: org-secret-partial",
        project_ids=[],
    )
    secret = await create_organization_scoped_secret(
        session=db_session, secret_in=secret_in, secret_status=secret_status, creator=creator
    )

    # Assign to the first project
    await assign_organization_secret_to_projects(
        session=db_session, secret=secret, project_ids=[env.project.id], user_email=creator
    )

    # Create a second project with a unique name
    project2 = await factory.create_project(db_session, env.cluster, name="unique-project-2")

    # Assign to both projects (one already assigned, one new)
    await assign_organization_secret_to_projects(
        session=db_session, secret=secret, project_ids=[env.project.id, project2.id], user_email=creator
    )

    secret = await get_organization_scoped_secret(session=db_session, secret_id=secret.id)

    assigned_ids = {a.project_id for a in secret.organization_secret_assignments}
    assert env.project.id in assigned_ids
    assert project2.id in assigned_ids
    assert len(secret.organization_secret_assignments) == 2


@pytest.mark.asyncio
async def test_get_secrets_for_project_returns_organization_secrets(db_session: AsyncSession) -> None:
    """Test that get_secrets_for_project returns organization-scoped secrets assigned to project."""
    env = await factory.create_basic_test_environment(db_session)

    # Create organization-scoped secret assigned to project
    org_secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, name="org-secret", secret_status=SecretStatus.SYNCED.value
    )

    secrets = await get_secrets_for_project(db_session, env.project.id)

    assert len(secrets) == 1
    assert secrets[0].id == org_secret.id
    assert secrets[0].scope == SecretScope.ORGANIZATION
    # For organization-scoped secrets, check organization_secret_assignments instead of project_secrets
    assert len(secrets[0].organization_secret_assignments) == 1
    assert secrets[0].organization_secret_assignments[0].project_id == env.project.id


@pytest.mark.asyncio
async def test_get_secrets_for_project_returns_project_scoped_secrets(db_session: AsyncSession) -> None:
    """Test that get_secrets_for_project returns project-scoped secrets belonging to project."""
    env = await factory.create_basic_test_environment(db_session)

    # Create project-scoped secret
    project_secret = await factory.create_project_scoped_secret(
        db_session, env.project, name="project-secret", secret_status=SecretStatus.SYNCED.value
    )

    secrets = await get_secrets_for_project(db_session, env.project.id)

    assert len(secrets) == 1
    assert secrets[0].id == project_secret.id
    assert secrets[0].scope == SecretScope.PROJECT
    assert secrets[0].project_id == env.project.id


@pytest.mark.asyncio
async def test_get_secrets_for_project_returns_both_types(db_session: AsyncSession) -> None:
    """Test that get_secrets_for_project returns both organization and project-scoped secrets."""
    env = await factory.create_basic_test_environment(db_session)

    # Create organization-scoped secret
    org_secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, name="org-secret", secret_status=SecretStatus.SYNCED.value
    )

    # Create project-scoped secret
    project_secret = await factory.create_project_scoped_secret(
        db_session, env.project, name="project-secret", secret_status=SecretStatus.SYNCED.value
    )

    secrets = await get_secrets_for_project(db_session, env.project.id)

    assert len(secrets) == 2
    secret_ids = {s.id for s in secrets}
    assert org_secret.id in secret_ids
    assert project_secret.id in secret_ids


@pytest.mark.asyncio
async def test_get_secrets_for_project_filters_by_project_id(db_session: AsyncSession) -> None:
    """Test that get_secrets_for_project only returns secrets for the specified project."""
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.cluster, name="project-2")

    # Create secrets for project 1
    secret1 = await factory.create_project_scoped_secret(
        db_session, env.project, name="project1-secret", secret_status=SecretStatus.SYNCED.value
    )

    # Create secrets for project 2
    await factory.create_project_scoped_secret(
        db_session, project2, name="project2-secret", secret_status=SecretStatus.SYNCED.value
    )

    secrets = await get_secrets_for_project(db_session, env.project.id)

    assert len(secrets) == 1
    assert secrets[0].id == secret1.id
    assert secrets[0].project_id == env.project.id


@pytest.mark.asyncio
async def test_get_secrets_for_project_filters_by_secret_type(db_session: AsyncSession) -> None:
    """Test that get_secrets_for_project can filter by secret type."""
    env = await factory.create_basic_test_environment(db_session)

    # Create external secret
    external_secret = await factory.create_project_scoped_secret(
        db_session,
        env.project,
        name="external-secret",
        secret_type=SecretKind.EXTERNAL_SECRET,
        secret_status=SecretStatus.SYNCED.value,
    )

    # Create kubernetes secret
    await factory.create_project_scoped_secret(
        db_session,
        env.project,
        name="k8s-secret",
        secret_type=SecretKind.KUBERNETES_SECRET,
        secret_status=SecretStatus.SYNCED.value,
    )

    secrets = await get_secrets_for_project(db_session, env.project.id, secret_type=SecretKind.EXTERNAL_SECRET)

    assert len(secrets) == 1
    assert secrets[0].id == external_secret.id
    assert secrets[0].type == SecretKind.EXTERNAL_SECRET


@pytest.mark.asyncio
async def test_get_organization_scoped_secret_success(db_session: AsyncSession) -> None:
    """Test retrieving an organization-scoped secret by ID within an organization."""
    env = await factory.create_basic_test_environment(db_session)

    # Create an organization-scoped secret with an assignment
    secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, secret_status=SecretStatus.SYNCED.value
    )

    # Retrieve the secret using the new function
    retrieved_secret = await get_organization_scoped_secret(db_session, secret.id)

    assert retrieved_secret is not None
    assert retrieved_secret.id == secret.id
    assert retrieved_secret.name == secret.name
    # Verify relationships are eagerly loaded
    assert len(retrieved_secret.organization_secret_assignments) == 1


@pytest.mark.asyncio
async def test_get_organization_scoped_secret_not_found(db_session: AsyncSession) -> None:
    """Test retrieving a non-existent secret."""

    env = await factory.create_basic_test_environment(db_session)

    fake_secret_id = uuid4()
    retrieved_secret = await get_organization_scoped_secret(db_session, fake_secret_id)

    assert retrieved_secret is None


@pytest.mark.asyncio
async def test_get_organization_secret_assignment_success(db_session: AsyncSession) -> None:
    """Test retrieving an organization secret assignment by secret and project IDs."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a secret with an assignment
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
        project_secret_status=ProjectSecretStatus.PENDING.value,
    )

    # Retrieve the assignment
    assignment = await get_organization_secret_assignment(db_session, secret.id, env.project.id)

    assert assignment is not None
    assert assignment.organization_secret_id == secret.id
    assert assignment.project_id == env.project.id
    assert assignment.status == ProjectSecretStatus.PENDING


@pytest.mark.asyncio
async def test_get_organization_secret_assignment_not_found(db_session: AsyncSession) -> None:
    """Test retrieving a non-existent assignment."""

    env = await factory.create_basic_test_environment(db_session)

    fake_secret_id = uuid4()
    assignment = await get_organization_secret_assignment(db_session, fake_secret_id, env.project.id)

    assert assignment is None


@pytest.mark.asyncio
async def test_get_organization_secret_assignment_wrong_project(db_session: AsyncSession) -> None:
    """Test that an assignment cannot be retrieved with the wrong project ID."""
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.cluster, name="project-2")

    # Create a secret with assignment to project1
    secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, secret_status=SecretStatus.SYNCED.value
    )

    # Try to retrieve assignment for project2
    assignment = await get_organization_secret_assignment(db_session, secret.id, project2.id)

    assert assignment is None


@pytest.mark.asyncio
async def test_update_organization_secret_assignment_status_success(db_session: AsyncSession) -> None:
    """Test updating the status of an organization secret assignment."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a secret with an assignment in PENDING status
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
        project_secret_status=ProjectSecretStatus.PENDING.value,
    )

    # Get the assignment
    assignment = await get_organization_secret_assignment(db_session, secret.id, env.project.id)
    assert assignment.status == ProjectSecretStatus.PENDING

    # Update the status
    updated_by = "test@example.com"
    new_status = ProjectSecretStatus.SYNCED
    reason = "Successfully synced"
    updated_at = datetime.now(UTC)

    await update_org_assignment_status(db_session, assignment, new_status, reason, updated_at, updated_by)

    # Verify the update
    await db_session.refresh(assignment)
    assert assignment.status == new_status
    assert assignment.status_reason == reason
    assert assignment.updated_by == updated_by
    assert assignment.updated_at == updated_at


@pytest.mark.asyncio
async def test_update_organization_secret_assignment_status_to_failed(db_session: AsyncSession) -> None:
    """Test updating an assignment status to FAILED."""
    env = await factory.create_basic_test_environment(db_session)

    # Create a secret with an assignment
    secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, secret_status=SecretStatus.SYNCED.value
    )

    # Get the assignment
    assignment = await get_organization_secret_assignment(db_session, secret.id, env.project.id)

    # Update the status to FAILED
    updated_by = "system"
    new_status = ProjectSecretStatus.FAILED
    reason = "External secret store unavailable"
    updated_at = datetime.now(UTC)

    await update_org_assignment_status(db_session, assignment, new_status, reason, updated_at, updated_by)

    # Verify the update
    await db_session.refresh(assignment)
    assert assignment.status == ProjectSecretStatus.FAILED
    assert assignment.status_reason == reason


@pytest.mark.asyncio
async def test_get_secret_by_id_and_use_case_found(db_session: AsyncSession) -> None:
    """Test getting a secret by ID and use case when it exists."""
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    secret = await create_project_scoped_secret(
        session=db_session,
        project_id=env.project.id,
        name="test-hf-secret",
        secret_type=SecretKind.KUBERNETES_SECRET,
        status=SecretStatus.SYNCED,
        creator=creator,
        use_case=SecretUseCase.HUGGING_FACE,
    )

    result = await get_secret_by_id_and_use_case(
        session=db_session, secret_id=secret.id, use_case=SecretUseCase.HUGGING_FACE
    )

    assert result is not None
    assert result.id == secret.id
    assert result.name == "test-hf-secret"
    assert result.use_case == SecretUseCase.HUGGING_FACE
    assert isinstance(result, ProjectScopedSecret)


@pytest.mark.asyncio
async def test_get_secret_by_id_and_use_case_not_found(db_session: AsyncSession) -> None:
    """Test getting a secret by ID and use case when use case doesn't match."""
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    secret = await create_project_scoped_secret(
        session=db_session,
        project_id=env.project.id,
        name="test-hf-secret",
        secret_type=SecretKind.KUBERNETES_SECRET,
        status=SecretStatus.SYNCED,
        creator=creator,
        use_case=SecretUseCase.HUGGING_FACE,
    )

    # Test: Try to get with wrong use case
    result = await get_secret_by_id_and_use_case(
        session=db_session,
        secret_id=secret.id,
        use_case=SecretUseCase.S3,  # Wrong use case
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_organization_secrets_assigned_to_project(db_session: AsyncSession) -> None:
    """Test getting all organization-scoped secrets assigned to a specific project."""
    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.cluster, name="project-2")

    # Create organization-scoped secrets assigned to project 1
    secret1 = await factory.create_secret_with_project_assignment(
        db_session, env.project, name="secret-1", secret_status=SecretStatus.SYNCED.value
    )
    secret2 = await factory.create_secret_with_project_assignment(
        db_session, env.project, name="secret-2", secret_status=SecretStatus.PENDING.value
    )

    # Create organization-scoped secret assigned to project 2
    secret3 = await factory.create_secret_with_project_assignment(
        db_session, project2, name="secret-3", secret_status=SecretStatus.SYNCED.value
    )

    # Create organization-scoped secret not assigned to any project
    await factory.create_secret(db_session, name="unassigned-secret", status=SecretStatus.UNASSIGNED.value)

    # Get secrets assigned to project 1
    result = await get_organization_secrets_assigned_to_project(db_session, env.project.id)

    assert len(result) == 2
    secret_ids = {s.id for s in result}
    assert secret1.id in secret_ids
    assert secret2.id in secret_ids
    assert secret3.id not in secret_ids


@pytest.mark.asyncio
async def test_get_organization_secrets_assigned_to_project_empty(db_session: AsyncSession) -> None:
    """Test getting organization secrets for a project with no assignments."""

    env = await factory.create_basic_test_environment(db_session)

    # Create some unassigned secrets
    await factory.create_secret(db_session, name="secret-1", status=SecretStatus.UNASSIGNED.value)
    await factory.create_secret(db_session, name="secret-2", status=SecretStatus.UNASSIGNED.value)

    # Get secrets for project with no assignments
    result = await get_organization_secrets_assigned_to_project(db_session, env.project.id)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_organization_secrets_assigned_to_project_multiple_assignments(db_session: AsyncSession) -> None:
    """Test that a secret assigned to multiple projects is returned for each project."""

    env = await factory.create_basic_test_environment(db_session)
    project2 = await factory.create_project(db_session, env.cluster, name="project-2")

    # Create a secret and assign it to both projects
    secret = await factory.create_secret_with_project_assignment(
        db_session, env.project, name="shared-secret", secret_status=SecretStatus.SYNCED.value
    )

    # Assign the same secret to project 2
    await factory.create_organization_secret_assignment(
        db_session, project2, secret, status=ProjectSecretStatus.SYNCED.value
    )

    # Get secrets for each project
    result_project1 = await get_organization_secrets_assigned_to_project(db_session, env.project.id)
    result_project2 = await get_organization_secrets_assigned_to_project(db_session, project2.id)

    # Both projects should see the same secret
    assert len(result_project1) == 1
    assert len(result_project2) == 1
    assert result_project1[0].id == secret.id
    assert result_project2[0].id == secret.id
