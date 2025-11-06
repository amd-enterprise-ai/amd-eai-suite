# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio

from keycloak import KeycloakAdmin
from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.keycloak_admin import (
    create_group,
    create_organization_in_keycloak,
    get_idps,
    get_idps_for_organization,
    get_realm,
)
from ..utilities.keycloak_admin import get_organization_by_id as get_organization_from_keycloak
from ..utilities.keycloak_admin import get_organizations as get_organizations_from_keycloak
from .models import Organization as OrganizationModel
from .repository import create_organization as create_organization_in_db
from .repository import get_organizations as get_organizations_from_db
from .schemas import OrganizationCreate, OrganizationResponse
from .utils import is_smtp_enabled_for_realm, merge_organization_details


async def create_organization(
    kc_admin: KeycloakAdmin, session: AsyncSession, organization: OrganizationCreate
) -> OrganizationModel:
    keycloak_organization_id, keycloak_group_id, realm = await asyncio.gather(
        create_organization_in_keycloak(kc_admin=kc_admin, organization=organization),
        create_group(kc_admin=kc_admin, group_name=organization.name),
        get_realm(kc_admin=kc_admin),
    )

    smtp_enabled = is_smtp_enabled_for_realm(realm)

    db_organization = await create_organization_in_db(
        session,
        organization_name=organization.name,
        keycloak_organization_id=keycloak_organization_id,
        keycloak_group_id=keycloak_group_id,
    )
    keycloak_org = await get_organization_from_keycloak(kc_admin=kc_admin, organization_id=keycloak_organization_id)

    return merge_organization_details(keycloak_org, db_organization, False, smtp_enabled)


async def get_all_organizations(kc_admin: KeycloakAdmin, session: AsyncSession) -> list[OrganizationResponse]:
    keycloak_organizations, db_organizations, idps, realm = await asyncio.gather(
        get_organizations_from_keycloak(kc_admin=kc_admin),
        get_organizations_from_db(session),
        get_idps(kc_admin=kc_admin),
        get_realm(kc_admin=kc_admin),
    )

    keycloak_orgs_by_id = {org["id"]: org for org in keycloak_organizations}
    orgs_with_idps = {idp["organizationId"] for idp in idps if "organizationId" in idp and idp["enabled"]}
    smtp_enabled = is_smtp_enabled_for_realm(realm)

    return [
        merge_organization_details(
            keycloak_orgs_by_id[org.keycloak_organization_id],
            org,
            org.keycloak_organization_id in orgs_with_idps,
            smtp_enabled,
        )
        for org in db_organizations
        if org.keycloak_organization_id in keycloak_orgs_by_id
    ]


async def enrich_organization_details(kc_admin: KeycloakAdmin, organization: OrganizationModel) -> OrganizationResponse:
    keycloak_org, idps, realm = await asyncio.gather(
        get_organization_from_keycloak(kc_admin=kc_admin, organization_id=organization.keycloak_organization_id),
        get_idps_for_organization(kc_admin=kc_admin, organization_id=organization.keycloak_organization_id),
        get_realm(kc_admin=kc_admin),
    )
    idp_linked = len([idp for idp in idps if idp["enabled"]]) > 0
    smtp_enabled = is_smtp_enabled_for_realm(realm)

    return merge_organization_details(keycloak_org, organization, idp_linked, smtp_enabled)
