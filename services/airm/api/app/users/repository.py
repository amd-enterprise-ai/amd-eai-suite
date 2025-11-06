# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.exceptions import ConflictException
from .models import User


async def get_users_in_organization_by_ids(
    session: AsyncSession, organization_id: UUID, user_ids: list[UUID]
) -> list[User]:
    result = await session.execute(select(User).where(User.organization_id == organization_id, User.id.in_(user_ids)))
    return result.scalars().all()


async def get_users_in_organization(session: AsyncSession, organization_id: UUID) -> list[User]:
    result = await session.execute(select(User).where(User.organization_id == organization_id))
    return result.scalars().all()


async def get_user_in_organization(session: AsyncSession, organization_id: UUID, user_id: UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id, User.organization_id == organization_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(func.lower(User.email) == email.lower()))
    return result.scalar_one_or_none()


async def delete_user(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(delete(User).where(User.id == user_id))
    await session.flush()


async def create_user_in_organization(
    session: AsyncSession, organization_id: UUID, email: str, keycloak_user_id: str, creator: str
) -> User:
    new_user = User(
        email=email,
        organization_id=organization_id,
        keycloak_user_id=keycloak_user_id,
        created_by=creator,
        updated_by=creator,
    )

    session.add(new_user)
    try:
        await session.flush()
        return new_user
    except IntegrityError as e:
        error_message = str(e)
        if "users_email_key" in error_message:
            raise ConflictException(f"A user with email '{email}' already exists")
        elif "users_keycloak_user_id_key" in error_message:
            raise ConflictException(f"A user with Keycloak ID '{keycloak_user_id}' already exists")
        raise e


async def update_last_active_at(session: AsyncSession, user: User, last_active_at: datetime) -> None:
    user.last_active_at = last_active_at
    await session.flush()


async def get_users_in_organization_by_keycloak_ids(
    session: AsyncSession, organization_id: UUID, keycloak_user_ids: list[str]
) -> list[User]:
    """Get users in an organization by their Keycloak user IDs."""
    if not keycloak_user_ids:
        return []

    result = await session.execute(
        select(User).where(User.organization_id == organization_id, User.keycloak_user_id.in_(keycloak_user_ids))
    )
    return list(result.scalars().all())
