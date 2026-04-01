# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Repository for AIM-related database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.models import set_updated_fields

from .enums import AIMServiceStatus, OptimizationMetric
from .models import AIMService


async def create_aim_service(
    session: AsyncSession,
    namespace: str,
    model: str,
    status: AIMServiceStatus,
    metric: OptimizationMetric | None,
    submitter: str,
    id: UUID | None = None,
) -> AIMService:
    """Create a new AIMService record in the database."""

    aim_service = AIMService(
        namespace=namespace,
        model=model,
        status=status,
        metric=metric,
        created_by=submitter,
        updated_by=submitter,
    )

    # Set ID if provided (e.g., from K8s id label)
    if id is not None:
        aim_service.id = id

    set_updated_fields(aim_service, submitter)
    session.add(aim_service)
    return aim_service


async def get_aim_service_by_id(
    session: AsyncSession,
    id: UUID,
    namespace: str | None = None,
) -> AIMService | None:
    """Get an AIMService by ID from the database."""
    query = select(AIMService).where(AIMService.id == id)

    if namespace:
        query = query.where(AIMService.namespace == namespace)

    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_aim_services_history(
    session: AsyncSession,
    namespace: str | None = None,
    status: AIMServiceStatus | None = None,
) -> list[AIMService]:
    """List AIMService records from the database."""
    query = select(AIMService).order_by(AIMService.created_at.desc())

    if namespace:
        query = query.where(AIMService.namespace == namespace)

    if status:
        query = query.where(AIMService.status == status)

    result = await session.execute(query)
    return list(result.scalars().all())


async def update_aim_service_status(
    session: AsyncSession,
    aim_service: AIMService,
    status: AIMServiceStatus,
    updater: str = "system",
) -> AIMService:
    """Update the status of an AIMService."""
    aim_service.status = status
    set_updated_fields(aim_service, updater)
    await session.flush()
    return aim_service
