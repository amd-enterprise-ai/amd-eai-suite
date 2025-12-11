# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.exceptions import ConflictException
from .models import Organization as OrganizationModel


async def get_organizations(session: AsyncSession) -> list[OrganizationModel]:
    result = await session.execute(select(OrganizationModel))
    return result.scalars().all()


async def get_organization_by_id(session: AsyncSession, organization_id: UUID) -> OrganizationModel | None:
    result = await session.execute(select(OrganizationModel).where(OrganizationModel.id == organization_id))
    return result.scalar_one_or_none()


async def get_organization_by_keycloak_org_id(session: AsyncSession, keycloak_org_id: str) -> OrganizationModel | None:
    result = await session.execute(
        select(OrganizationModel).where(OrganizationModel.keycloak_organization_id == keycloak_org_id)
    )
    return result.scalar_one_or_none()


# Create a new organization
async def create_organization(
    session: AsyncSession, organization_name: str, keycloak_organization_id: str, keycloak_group_id: str
) -> OrganizationModel:
    new_organization = OrganizationModel(
        name=organization_name, keycloak_organization_id=keycloak_organization_id, keycloak_group_id=keycloak_group_id
    )

    session.add(new_organization)
    try:
        await session.flush()
        return new_organization
    except IntegrityError as e:
        error_message = str(e)
        if "organizations_name_key" in error_message:
            raise ConflictException(f"An organization with name '{organization_name}' already exists")
        elif "organizations_keycloak_organization_id_key" in error_message:
            raise ConflictException(f"An organization with Keycloak ID '{keycloak_organization_id}' already exists")
        raise e
