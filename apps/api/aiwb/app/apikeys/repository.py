# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import ConflictException

from .models import ApiKey


async def get_api_keys_for_namespace(
    session: AsyncSession,
    namespace: str,
) -> list[ApiKey]:
    """
    Get all API keys for a specific namespace.

    Args:
        session: Database session
        namespace: The namespace name

    Returns:
        List of API keys
    """
    result = await session.execute(
        select(ApiKey).where(ApiKey.namespace == namespace).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def get_api_key_by_id(
    session: AsyncSession,
    api_key_id: UUID,
    namespace: str,
) -> ApiKey | None:
    """
    Get an API key by its ID within a namespace.

    Args:
        session: Database session
        api_key_id: The ID of the API key
        namespace: The namespace name

    Returns:
        The API key if found, None otherwise
    """
    result = await session.execute(select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.namespace == namespace))
    return result.scalar_one_or_none()


async def create_api_key(
    session: AsyncSession,
    name: str,
    truncated_key: str,
    cluster_auth_key_id: str,
    namespace: str,
    creator: str,
) -> ApiKey:
    """
    Create a new API key in the database.

    Args:
        session: Database session
        name: User-friendly name for the API key
        truncated_key: Truncated key for display
        cluster_auth_key_id: Cluster Auth accessor/key_id
        namespace: The namespace name
        creator: Email of the user creating the key

    Returns:
        The created API key

    Raises:
        ConflictException: If an API key with the same name already exists in the namespace

    Note:
        ttl, expires_at, renewable, and num_uses are not stored in the database.
        They are fetched from Cluster Auth on demand as it is the source of truth for key validity.
    """
    new_api_key = ApiKey(
        name=name,
        truncated_key=truncated_key,
        cluster_auth_key_id=cluster_auth_key_id,
        namespace=namespace,
        created_by=creator,
        updated_by=creator,
    )

    session.add(new_api_key)
    try:
        await session.flush()
        return new_api_key
    except IntegrityError as e:
        error_message = str(e)
        if "uq_api_keys_name_namespace" in error_message or "name" in error_message.lower():
            raise ConflictException(f"An API key with the name '{name}' already exists in the namespace '{namespace}'")
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
