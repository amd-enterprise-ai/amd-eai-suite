# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Seed AIM metadata into the database using environment-provided configuration."""

import asyncio
from typing import Any

import yaml
from loguru import logger

from ..utilities.database import init_db, session_scope
from .config import AIM_METADATA_FILE_PATH
from .models import AIM
from .repository import select_aim_by_name_and_tag


async def seed(metadata: dict[str, Any]) -> tuple[int, int]:
    """Seed AIM metadata from collected registry data."""
    inserted = 0
    updated = 0

    async with session_scope() as session:
        for image in metadata.get("images", []):
            image_name = image.get("name")
            if not image_name:
                continue

            for tag in image.get("tags", []):
                image_tag = tag.get("tag")
                labels = tag.get("labels", {})

                if not image_tag or not labels:
                    continue

                existing = await select_aim_by_name_and_tag(session, image_name, image_tag)
                if existing:
                    if existing.labels != labels:
                        existing.labels = labels
                        updated += 1
                        logger.info(f"Updated AIM: {image_name}:{image_tag}")
                else:
                    session.add(
                        AIM(
                            image_name=image_name,
                            image_tag=image_tag,
                            labels=labels,
                            updated_by="system",
                            created_by="system",
                        )
                    )
                    inserted += 1
                    logger.info(f"Seeded AIM: {image_name}:{image_tag}")

    return inserted, updated


def run() -> None:
    """Run AIM metadata registration from baked-in metadata file."""
    try:
        init_db()
        with AIM_METADATA_FILE_PATH.open("r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}

        if not metadata:
            logger.error("Empty metadata file")
            return

        inserted, updated = asyncio.run(seed(metadata))
        logger.info(f"AIM registration complete: inserted={inserted}, updated={updated}")
    except FileNotFoundError:
        logger.warning(f"Metadata file not found: {AIM_METADATA_FILE_PATH}")
        logger.warning("Skipping AIM registration")
    except Exception:
        logger.exception("Failed to register AIM metadata")
        raise


if __name__ == "__main__":
    run()
