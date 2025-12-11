# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import SecretKind, SecretScope
from app.secrets.enums import SecretStatus
from app.secrets.models import OrganizationScopedSecret, ProjectScopedSecret, Secret
from tests import factory


@pytest.mark.asyncio
async def test_secret_is_polymorphic_abstract_cannot_instantiate_directly(db_session: AsyncSession):
    """
    Test that Secret cannot be instantiated directly since it's polymorphic abstract.

    This ensures that only concrete implementations (ProjectScopedSecret, OrganizationScopedSecret)
    can be created, enforcing proper type-based instantiation.

    With polymorphic_abstract=True, SQLAlchemy will raise an InvalidRequestError when trying
    to add a Secret instance directly to the session, as it doesn't have a valid polymorphic
    identity.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Attempting to create and persist a Secret directly should raise an error
    # because polymorphic abstract classes cannot be instantiated without a concrete identity
    with pytest.raises(InvalidRequestError, match="polymorphic_abstract"):
        secret = Secret(
            id=uuid4(),
            name="test-secret",
            type=SecretKind.EXTERNAL_SECRET.value,
            scope=SecretScope.ORGANIZATION.value,
            status=SecretStatus.UNASSIGNED.value,
            organization_id=env.organization.id,
            created_by="test@example.com",
            updated_by="test@example.com",
        )
        db_session.add(secret)
        await db_session.flush()


@pytest.mark.asyncio
async def test_project_scoped_secret_can_be_instantiated(db_session: AsyncSession):
    """
    Test that ProjectScopedSecret can be instantiated successfully.

    This verifies that the concrete implementation works correctly with the
    polymorphic abstract base class.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Creating a ProjectScopedSecret should work
    secret = ProjectScopedSecret(
        id=uuid4(),
        name="test-project-secret",
        type=SecretKind.EXTERNAL_SECRET.value,
        scope=SecretScope.PROJECT.value,
        status=SecretStatus.UNASSIGNED.value,
        organization_id=env.organization.id,
        project_id=env.project.id,
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    db_session.add(secret)
    await db_session.flush()

    # Verify it was created successfully
    assert secret.id is not None
    assert secret.name == "test-project-secret"
    assert secret.scope == SecretScope.PROJECT.value
    assert secret.project_id == env.project.id
    # Verify polymorphic identity
    assert isinstance(secret, ProjectScopedSecret)
    assert isinstance(secret, Secret)


@pytest.mark.asyncio
async def test_organization_scoped_secret_can_be_instantiated(db_session: AsyncSession):
    """
    Test that OrganizationScopedSecret can be instantiated successfully.

    This verifies that the concrete implementation works correctly with the
    polymorphic abstract base class and that the manifest field is accessible.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Creating an OrganizationScopedSecret should work
    secret = OrganizationScopedSecret(
        id=uuid4(),
        name="test-org-secret",
        type=SecretKind.EXTERNAL_SECRET.value,
        scope=SecretScope.ORGANIZATION.value,
        status=SecretStatus.UNASSIGNED.value,
        organization_id=env.organization.id,
        manifest="apiVersion: v1\nkind: Secret",
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    db_session.add(secret)
    await db_session.flush()

    # Verify it was created successfully
    assert secret.id is not None
    assert secret.name == "test-org-secret"
    assert secret.scope == SecretScope.ORGANIZATION.value
    assert secret.manifest == "apiVersion: v1\nkind: Secret"
    # Verify polymorphic identity
    assert isinstance(secret, OrganizationScopedSecret)
    assert isinstance(secret, Secret)


@pytest.mark.asyncio
async def test_polymorphic_query_returns_correct_subclass(db_session: AsyncSession):
    """
    Test that querying by Secret returns the correct subclass instances.

    This verifies that SQLAlchemy's polymorphic loading correctly instantiates
    the appropriate subclass based on the discriminator (scope) column.
    """
    env = await factory.create_basic_test_environment(db_session)

    # Create a ProjectScopedSecret
    project_secret = await factory.create_project_scoped_secret(
        db_session,
        env.organization,
        env.project,
        name="project-secret",
        secret_status=SecretStatus.SYNCED.value,
    )

    # Create an OrganizationScopedSecret
    org_secret = await factory.create_secret(
        db_session,
        env.organization,
        name="org-secret",
        secret_scope=SecretScope.ORGANIZATION.value,
        status=SecretStatus.SYNCED.value,
    )

    # Query all secrets in the organization
    result = await db_session.execute(select(Secret).where(Secret.organization_id == env.organization.id))
    # Use .unique() because the query includes joined eager loads against collections
    secrets = result.unique().scalars().all()

    # Verify we got both secrets
    assert len(secrets) == 2

    # Verify correct types were returned based on polymorphic identity
    secret_types = {type(secret) for secret in secrets}
    assert ProjectScopedSecret in secret_types
    assert OrganizationScopedSecret in secret_types

    # Verify that each secret is also an instance of the base Secret class
    for secret in secrets:
        assert isinstance(secret, Secret)
