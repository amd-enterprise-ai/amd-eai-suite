# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Organizations service tests."""

from unittest.mock import AsyncMock, patch

import pytest
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakGetError
from sqlalchemy.ext.asyncio import AsyncSession

from app.organizations.repository import get_organization_by_id, get_organizations
from app.organizations.schemas import OrganizationCreate
from app.organizations.service import create_organization, enrich_organization_details, get_all_organizations
from tests import factory


@pytest.mark.asyncio
async def test_creates_organization(db_session: AsyncSession):
    """Test successful organization creation with real database operations."""
    org_data = OrganizationCreate(name="Test Organization", domains=["domain1.com"])

    with (
        patch(
            "app.organizations.service.create_organization_in_keycloak",
            return_value="0aa18e92-002c-45b7-a06e-dcdb02779741",
            autospec=True,
        ),
        patch(
            "app.organizations.service.create_group",
            return_value="13f8c5b2-5c3e-4c5b-8c5e-5c3e4c5b8c5e",
            autospec=True,
        ),
        patch(
            "app.organizations.service.get_organization_from_keycloak",
            return_value={
                "domains": [
                    {"name": "domain1.com"},
                ]
            },
        ),
        patch("app.organizations.service.get_realm", return_value={"smtpServer": {}}),
        patch("app.organizations.service.is_smtp_enabled_for_realm", return_value=False),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        new_organization = await create_organization(kc_admin, db_session, org_data)

    assert new_organization.name == "Test Organization"
    assert new_organization.domains == ["domain1.com"]
    assert new_organization.idp_linked is False
    assert new_organization.smtp_enabled is False

    db_org = await get_organization_by_id(db_session, new_organization.id)
    assert db_org is not None
    assert db_org.name == "Test Organization"
    assert db_org.keycloak_organization_id == "0aa18e92-002c-45b7-a06e-dcdb02779741"
    assert db_org.keycloak_group_id == "13f8c5b2-5c3e-4c5b-8c5e-5c3e4c5b8c5e"


@pytest.mark.asyncio
async def test_create_organization_keycloak_error(db_session: AsyncSession):
    """Test organization creation when Keycloak fails."""
    org_data = OrganizationCreate(name="Failed Org", domains=["domain1.com"])

    with patch(
        "app.organizations.service.create_organization_in_keycloak",
        side_effect=KeycloakGetError("Keycloak error"),
        autospec=True,
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)

        with pytest.raises(KeycloakGetError):
            await create_organization(kc_admin, db_session, org_data)

    db_orgs = await get_organizations(db_session)
    assert len(db_orgs) == 0


@pytest.mark.asyncio
async def test_get_organizations_success(db_session: AsyncSession):
    """Test retrieving organizations with real database data."""
    org1 = await factory.create_organization(
        db_session, name="organization_1", keycloak_organization_id="d2faf377-776e-468c-a08c-bd1347f794bf"
    )
    org2 = await factory.create_organization(
        db_session, name="organization_2", keycloak_organization_id="03890db1-9627-4663-ae0b-6a74ef1ff638"
    )

    keycloak_orgs = [
        {
            "id": "d2faf377-776e-468c-a08c-bd1347f794bf",
            "name": "organization_1",
            "enabled": True,
            "domains": [{"name": "example1.com"}],
        },
        {
            "id": "03890db1-9627-4663-ae0b-6a74ef1ff638",
            "name": "organization_2",
            "enabled": True,
            "domains": [{"name": "example2.com"}],
        },
        {
            "id": "fb925978-fafe-4b91-bb48-4467105deb46",
            "name": "organization_3",
            "enabled": True,
            "domains": [{"name": "example1.com"}],
        },
    ]

    keycloak_idps = [
        {
            "organizationId": "d2faf377-776e-468c-a08c-bd1347f794bf",
            "enabled": True,
        },
        {
            "organizationId": "03890db1-9627-4663-ae0b-6a74ef1ff638",
            "enabled": False,
        },
    ]

    with (
        patch("app.organizations.service.get_organizations_from_keycloak", return_value=keycloak_orgs),
        patch("app.organizations.service.get_idps", return_value=keycloak_idps),
        patch("app.organizations.service.get_realm", return_value={"smtpServer": {}}),
        patch("app.organizations.service.is_smtp_enabled_for_realm", return_value=False),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        organizations = await get_all_organizations(kc_admin, db_session)

    assert len(organizations) == 2

    org1_result = next(org for org in organizations if org.id == org1.id)
    org2_result = next(org for org in organizations if org.id == org2.id)

    assert org1_result.name == "organization_1"
    assert org1_result.domains == ["example1.com"]
    assert org1_result.idp_linked is True
    assert org1_result.smtp_enabled is False

    assert org2_result.name == "organization_2"
    assert org2_result.domains == ["example2.com"]
    assert org2_result.idp_linked is False
    assert org1_result.smtp_enabled is False


@pytest.mark.asyncio
async def test_get_organizations_no_organizations_in_keycloak(db_session: AsyncSession):
    """Test getting organizations when Keycloak returns empty list."""
    await factory.create_organization(
        db_session, name="organization_1", keycloak_organization_id="d2faf377-776e-468c-a08c-bd1347f794bf"
    )

    with (
        patch("app.organizations.service.get_organizations_from_keycloak", return_value=[]),
        patch("app.organizations.service.get_idps", return_value=[]),
        patch("app.organizations.service.get_realm", return_value={"smtpServer": {}}),
        patch("app.organizations.service.is_smtp_enabled_for_realm", return_value=False),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        organizations = await get_all_organizations(kc_admin, db_session)

    assert len(organizations) == 0


@pytest.mark.asyncio
async def test_enrich_organization_details(db_session: AsyncSession):
    """Test enriching organization with Keycloak details."""
    organization = await factory.create_organization(
        db_session, name="organization_1", keycloak_organization_id="d2faf377-776e-468c-a08c-bd1347f794bf"
    )

    with (
        patch(
            "app.organizations.service.get_organization_from_keycloak",
            return_value={
                "id": "d2faf377-776e-468c-a08c-bd1347f794bf",
                "name": "organization_1",
                "enabled": True,
                "domains": [{"name": "example1.com"}],
            },
        ),
        patch(
            "app.organizations.service.get_idps_for_organization",
            return_value=[
                {
                    "enabled": True,
                },
            ],
        ),
        patch("app.organizations.service.is_smtp_enabled_for_realm", return_value=True),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        enriched_organization = await enrich_organization_details(kc_admin, organization)

    assert enriched_organization.id == organization.id
    assert enriched_organization.name == "organization_1"
    assert enriched_organization.domains == ["example1.com"]
    assert enriched_organization.idp_linked
    assert enriched_organization.smtp_enabled


@pytest.mark.asyncio
async def test_get_organizations_with_users(db_session: AsyncSession):
    """Test getting organizations that have users associated."""
    # Create first environment with users
    env1 = await factory.create_full_test_environment(
        db_session,
        org_name="Active Organization",
        user_email="user1@active.com",
        creator="test@example.com",
    )
    # Add an additional user to the active organization
    await factory.create_user(db_session, env1.organization, email="user2@active.com", invited_by="test@example.com")

    # Update the organization with specific keycloak ID for test consistency
    env1.organization.keycloak_organization_id = "active-org-id"
    await db_session.flush()

    # Create second organization without users (empty)
    org2 = await factory.create_organization(
        db_session, name="Empty Organization", keycloak_organization_id="empty-org-id"
    )

    keycloak_orgs = [
        {
            "id": "active-org-id",
            "name": "Active Organization",
            "enabled": True,
            "domains": [{"name": "active.com"}],
        },
        {
            "id": "empty-org-id",
            "name": "Empty Organization",
            "enabled": True,
            "domains": [{"name": "empty.com"}],
        },
    ]

    with (
        patch("app.organizations.service.get_organizations_from_keycloak", return_value=keycloak_orgs),
        patch("app.organizations.service.get_idps", return_value=[]),
        patch("app.organizations.service.get_realm", return_value={"smtpServer": {}}),
        patch("app.organizations.service.is_smtp_enabled_for_realm", return_value=False),
    ):
        kc_admin = AsyncMock(spec=KeycloakAdmin)
        organizations = await get_all_organizations(kc_admin, db_session)

    # Both organizations should be returned (service doesn't filter by user count)
    assert len(organizations) == 2

    org_names = [org.name for org in organizations]
    assert "Active Organization" in org_names
    assert "Empty Organization" in org_names
