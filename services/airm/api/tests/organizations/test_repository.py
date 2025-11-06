# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.organizations.repository import (
    create_organization,
    get_organization_by_id,
    get_organization_by_keycloak_org_id,
    get_organizations,
)
from app.utilities.exceptions import ConflictException
from tests import factory


@pytest.mark.asyncio
async def test_get_organizations(db_session: AsyncSession):
    await factory.create_organization(
        db_session, name="Test Organization 1", keycloak_organization_id="1234", keycloak_group_id="5678"
    )
    await factory.create_organization(
        db_session, name="Test Organization 2", keycloak_organization_id="1235", keycloak_group_id="5679"
    )

    organizations = await get_organizations(db_session)
    assert len(organizations) == 2


@pytest.mark.asyncio
async def test_get_organization_by_id(db_session: AsyncSession):
    org = await factory.create_organization(
        db_session, name="Test Organization", keycloak_organization_id="123", keycloak_group_id="456"
    )

    assert await get_organization_by_id(organization_id=org.id, session=db_session) is not None
    assert (
        await get_organization_by_id(organization_id="0aa18e92-002c-45b7-a06e-dcdb02779741", session=db_session) is None
    )


@pytest.mark.asyncio
async def test_get_organization_by_keycloak_org_id(db_session: AsyncSession):
    await factory.create_organization(
        db_session, name="Test Organization", keycloak_organization_id="123", keycloak_group_id="456"
    )

    assert await get_organization_by_keycloak_org_id(keycloak_org_id="123", session=db_session) is not None
    assert await get_organization_by_keycloak_org_id(keycloak_org_id="456", session=db_session) is None


@pytest.mark.asyncio
async def test_creates_organization(db_session: AsyncSession):
    new_organization = await create_organization(
        db_session, "Org1", "0aa18e92-002c-45b7-a06e-dcdb02779741", "143abac0-2b1f-4d3a-8c5e-9f6b7c8d9e0f"
    )

    assert new_organization.name == "Org1"
    assert new_organization.keycloak_organization_id == "0aa18e92-002c-45b7-a06e-dcdb02779741"
    assert new_organization.keycloak_group_id == "143abac0-2b1f-4d3a-8c5e-9f6b7c8d9e0f"


@pytest.mark.asyncio
async def test_creates_user_group_duplicate_name_raises_exception(db_session: AsyncSession):
    await create_organization(
        db_session, "Org1", "0aa18e92-002c-45b7-a06e-dcdb02779741", "143abac0-2b1f-4d3a-8c5e-9f6b7c8d9e0f"
    )

    with pytest.raises(ConflictException) as exc_info:
        await create_organization(
            db_session, "org1", "0aa18e92-002c-45b7-a06e-dcdb02779741", "143abac0-2b1f-4d3a-8c5e-9f6b7c8d9e0f"
        )
    assert "already exists" in str(exc_info.value)
