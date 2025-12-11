# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import AIMClusterModelsMessage, AIMClusterModelStatus

from ..utilities.models import set_updated_fields
from .models import AIM


async def reconcile_aims_from_cluster(session: AsyncSession, message: AIMClusterModelsMessage) -> dict[str, int]:
    """Sync database AIMs with cluster state. Returns counts: added, updated, deleted, skipped."""
    stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0}

    result = await session.execute(select(AIM))
    db_aims = {aim.image_reference: aim for aim in result.scalars().all()}
    cluster_keys = {model.image_reference for model in message.models}

    for model in message.models:
        existing_aim = db_aims.get(model.image_reference)
        if existing_aim:
            changed = False
            for field in ("resource_name", "labels", "status"):
                if getattr(existing_aim, field) != getattr(model, field):
                    setattr(existing_aim, field, getattr(model, field))
                    changed = True
            if changed:
                set_updated_fields(existing_aim, "system")
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        else:
            session.add(
                AIM(
                    resource_name=model.resource_name,
                    image_reference=model.image_reference,
                    labels=model.labels,
                    status=model.status,
                    created_by="system",
                )
            )
            stats["added"] += 1

    for image_ref in set(db_aims.keys()) - cluster_keys:
        aim = db_aims[image_ref]
        if aim.status != AIMClusterModelStatus.DELETED:
            aim.status = AIMClusterModelStatus.DELETED
            set_updated_fields(aim, "system")
            stats["deleted"] += 1
        else:
            stats["skipped"] += 1

    await session.commit()
    logger.info(f"AIM reconciliation: {stats} (cluster total: {len(message.models)})")
    return stats
