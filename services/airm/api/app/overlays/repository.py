# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.exceptions import ConflictException, NotFoundException
from .models import Overlay


async def insert_overlay(
    session: AsyncSession,
    chart_id: UUID,
    overlay_data: dict[str, Any],
    canonical_name: str | None = None,
    creator: str | None = None,
) -> Overlay:
    """
    Insert a new overlay record into the database.

    Raises:
        NotFoundException: If the chart_id references a non-existent chart
        ConflictException: If an overlay with the same chart_id and canonical_name already exists
    """
    overlay = Overlay(
        canonical_name=canonical_name,
        chart_id=chart_id,
        overlay=overlay_data,
        created_by=creator,
        updated_by=creator,
    )
    session.add(overlay)
    try:
        await session.flush()
        await session.refresh(overlay)
        return overlay
    except IntegrityError as e:
        error_message = str(e)
        if "ForeignKeyViolationError" in error_message and 'is not present in table "charts"' in error_message:
            raise NotFoundException(f"Chart with ID {chart_id} not found")
        else:
            raise ConflictException(
                f"Overlay with chart ID '{chart_id}' and canonical name '{canonical_name}' already exists."
            )


async def list_overlays(
    session: AsyncSession,
    chart_id: UUID | None = None,
    canonical_name: str | None = None,
    include_generic: bool = False,
) -> list[Overlay]:
    query = select(Overlay)
    if chart_id is not None:
        query = query.where(Overlay.chart_id == chart_id)

    if canonical_name is not None:
        if include_generic:
            query = query.where(or_(Overlay.canonical_name == canonical_name, Overlay.canonical_name.is_(None)))
        else:
            query = query.where(Overlay.canonical_name == canonical_name)
    result = await session.execute(query)
    return result.scalars().unique().all()


async def get_overlay(
    session: AsyncSession,
    overlay_id: UUID,
) -> Overlay | None:
    query = select(Overlay).where(Overlay.id == overlay_id)
    result = await session.execute(query)
    return result.unique().scalar_one_or_none()


async def get_overlay_by_chart_id(
    session: AsyncSession,
    chart_id: UUID,
) -> Overlay | None:
    """Get first overlay associated with a specific chart ID."""
    query = select(Overlay).where(Overlay.chart_id == chart_id)
    result = await session.execute(query)
    return result.scalars().unique().first()


async def delete_overlay(
    session: AsyncSession,
    overlay_id: UUID,
) -> bool:
    """Delete an overlay. Returns True if deleted, False if not found."""
    query = select(Overlay).where(Overlay.id == overlay_id)
    result = await session.execute(query)
    overlay = result.scalars().first()

    if overlay:
        await session.delete(overlay)
        await session.flush()
        return True
    else:
        return False


async def delete_overlays(session: AsyncSession, ids: list[UUID]) -> list[UUID]:
    """Delete overlays by IDs. Returns list of IDs that were actually deleted."""
    ids_to_delete = set(ids)

    if not ids_to_delete:
        return []

    # Find which IDs exist
    stmt = select(Overlay.id).where(Overlay.id.in_(ids_to_delete))
    result = await session.execute(stmt)
    found_ids = {row[0] for row in result.fetchall()}

    # Only delete existing overlays
    if found_ids:
        query = delete(Overlay).where(Overlay.id.in_(found_ids))
        await session.execute(query)
        await session.flush()

    return list(found_ids)
