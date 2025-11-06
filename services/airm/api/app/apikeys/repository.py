# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.exceptions import ConflictException
from .models import ApiKey


async def get_api_keys_for_project(
    session: AsyncSession,
    project_id: UUID,
) -> list[ApiKey]:
    """
    Get all API keys for a specific project.

    Args:
        session: Database session
        project_id: The ID of the project

    Returns:
        List of API keys
    """
    result = await session.execute(
        select(ApiKey).where(ApiKey.project_id == project_id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def get_api_key_by_id(
    session: AsyncSession,
    api_key_id: UUID,
    project_id: UUID,
) -> ApiKey | None:
    """
    Get an API key by its ID within a project.

    Args:
        session: Database session
        api_key_id: The ID of the API key
        project_id: The ID of the project

    Returns:
        The API key if found, None otherwise
    """
    result = await session.execute(select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.project_id == project_id))
    return result.scalar_one_or_none()


async def create_api_key(
    session: AsyncSession,
    name: str,
    truncated_key: str,
    cluster_auth_key_id: str,
    project_id: UUID,
    creator: str,
) -> ApiKey:
    """
    Create a new API key in the database.

    Args:
        session: Database session
        name: User-friendly name for the API key
        truncated_key: Truncated key for display
        cluster_auth_key_id: Cluster Auth accessor/key_id
        project_id: The ID of the project
        creator: Email of the user creating the key

    Returns:
        The created API key

    Raises:
        ConflictException: If an API key with the same name already exists in the project

    Note:
        ttl, expires_at, renewable, and num_uses are not stored in the database.
        They are fetched from Cluster Auth on demand as it is the source of truth for key validity.
    """
    new_api_key = ApiKey(
        name=name,
        truncated_key=truncated_key,
        cluster_auth_key_id=cluster_auth_key_id,
        project_id=project_id,
        created_by=creator,
        updated_by=creator,
    )

    session.add(new_api_key)
    try:
        await session.flush()
        return new_api_key
    except IntegrityError as e:
        error_message = str(e)
        if "api_keys_name_project_id_key" in error_message or "name" in error_message.lower():
            raise ConflictException(f"An API key with the name '{name}' already exists in the project")
        raise e


async def delete_api_key(session: AsyncSession, api_key: ApiKey) -> None:
    """
    Delete an API key from the database.

    Args:
        session: Database session
        api_key: The API key to delete
    """
    await session.delete(api_key)
    await session.flush()
