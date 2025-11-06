# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import ProjectSecretStatus
from app.secrets.enums import SecretStatus
from app.secrets.models import Secret
from app.secrets.repository import (
    create_secret,
    delete_project_secret,
    delete_secret,
    get_project_secret,
    get_project_secret_by_id,
    get_secret_in_organization,
    get_secrets_in_organization,
    update_secret_status,
)
from app.secrets.schemas import SecretIn
from tests import factory


@pytest.mark.asyncio
async def test_get_secrets_in_organization_returns_secrets_with_projects(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    secrets = await get_secrets_in_organization(db_session, env.organization.id)

    assert len(secrets) == 1
    assert secrets[0].organization_id == env.organization.id
    assert secrets[0].project_secrets[0].project.name == "test-project"


@pytest.mark.asyncio
async def test_get_secrets_in_organization_returns_secrets_with_project_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    secrets = await get_secrets_in_organization(db_session, env.organization.id, project_id=env.project.id)

    assert len(secrets) == 1
    assert secrets[0].organization_id == env.organization.id
    assert secrets[0].project_secrets[0].project.name == "test-project"


@pytest.mark.asyncio
async def test_get_secrets_in_organization_no_project_secrets_found(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    secrets = await get_secrets_in_organization(
        db_session, env.organization.id, project_id=UUID("bde8d859-609d-4186-9486-6c93732b2e99")
    )

    assert len(secrets) == 0


@pytest.mark.asyncio
async def test_create_secret(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"
    secret_status = SecretStatus.UNASSIGNED.value

    secret_in = SecretIn(
        name="test-secret",
        type="External",
        scope="Organization",
        manifest="apiVersion: v1\nkind: Secret",  # example manifest
        project_ids=[],
        description="test secret",
    )

    result = await create_secret(
        session=db_session,
        organization_id=env.organization.id,
        secret_in=secret_in,
        secret_status=secret_status,
        creator=creator,
    )

    assert isinstance(result, Secret)
    assert result.name == "test-secret"
    assert result.manifest == "apiVersion: v1\nkind: Secret"
    assert result.organization_id == env.organization.id
    assert result.status == secret_status
    assert result.created_by == creator
    assert result.updated_by == creator


@pytest.mark.asyncio
async def test_create_secret_duplicate_name_conflict(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"

    # Create first secret
    secret_in = SecretIn(
        name="duplicate-secret",
        type="External",
        scope="Organization",
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[],
        description="first secret",
    )

    await create_secret(
        session=db_session,
        organization_id=env.organization.id,
        secret_in=secret_in,
        secret_status=SecretStatus.UNASSIGNED.value,
        creator=creator,
    )

    # Try to create second secret with same name - should raise ConflictException
    secret_in_duplicate = secret_in.model_copy(update={"description": "duplicate secret"})

    with pytest.raises(Exception) as exc_info:
        await create_secret(
            session=db_session,
            organization_id=env.organization.id,
            secret_in=secret_in_duplicate,
            secret_status=SecretStatus.UNASSIGNED.value,
            creator=creator,
        )

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_secret_with_generic_integrity_error(db_session: AsyncSession):
    """Test creating secret with generic IntegrityError that doesn't match name pattern."""

    env = await factory.create_basic_test_environment(db_session)
    creator = "test-user@example.com"
    secret_status = SecretStatus.UNASSIGNED.value

    secret_in = SecretIn(
        name="test-secret-generic-error",
        type="External",
        scope="Organization",
        manifest="apiVersion: v1\nkind: Secret",
        project_ids=[],
        description="test secret",
    )

    # Mock session.flush to raise a generic IntegrityError that doesn't contain name keywords
    original_flush = db_session.flush

    async def mock_flush():
        raise IntegrityError("Generic constraint violation", None, None)

    with patch.object(db_session, "flush", side_effect=mock_flush):
        with pytest.raises(IntegrityError) as exc_info:
            await create_secret(
                session=db_session,
                organization_id=env.organization.id,
                secret_in=secret_in,
                secret_status=secret_status,
                creator=creator,
            )

    # Should be the original IntegrityError, not converted to ConflictException
    assert "Generic constraint violation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_secret_in_organization(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)

    result = await get_secret_in_organization(db_session, env.organization.id, secret.id)

    assert result.id == secret.id


@pytest.mark.asyncio
async def test_update_secret_status(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)
    now = datetime.now(UTC)

    await update_secret_status(
        db_session, secret, ProjectSecretStatus.PENDING, "Updating Secret", now, "admin@example.com"
    )

    assert secret.status == "Pending"
    assert secret.status_reason == "Updating Secret"


@pytest.mark.asyncio
async def test_delete_secret(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)

    await delete_secret(db_session, secret)

    assert await get_secret_in_organization(db_session, env.organization.id, secret.id) is None


@pytest.mark.asyncio
async def test_get_project_secret_found(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )

    result = await get_project_secret(db_session, secret.id, env.project.id)
    assert result.project.name == "test-project"


@pytest.mark.asyncio
async def test_get_project_secret_not_found(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret(db_session, env.organization, status=SecretStatus.DELETING.value)

    result = await get_project_secret(db_session, secret.id, env.project.id)
    assert result is None


@pytest.mark.asyncio
async def test_delete_project_secret(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )
    result = await get_project_secret(db_session, secret.id, env.project.id)

    await delete_project_secret(db_session, result)

    assert await get_project_secret(db_session, secret.id, env.project.id) is None


@pytest.mark.asyncio
async def test_get_project_secret_by_id(db_session: AsyncSession):
    env = await factory.create_basic_test_environment(db_session)
    secret = await factory.create_secret_with_project_assignment(
        db_session,
        env.organization,
        env.project,
        secret_status=SecretStatus.SYNCED.value,
    )
    proj_secret = await get_project_secret(db_session, secret.id, env.project.id)
    result = await get_project_secret_by_id(db_session, proj_secret.id)
    assert result == proj_secret
