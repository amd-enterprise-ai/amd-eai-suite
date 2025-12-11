# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from contextlib import asynccontextmanager

import yaml
from loguru import logger

from workloads_manager.core.workloads import get_registerable_workloads
from workloads_manager.models import OverlayData

from ..overlays.repository import list_overlays
from ..overlays.schemas import OverlayUpdate
from ..overlays.service import create_overlay, update_overlay
from ..utilities.database import get_session, init_db
from .repository import create_chart, select_chart, update_chart
from .schemas import ChartCreate, ChartUpdate

session_ctx = asynccontextmanager(get_session)


async def register_workloads() -> None:
    """Register workloads in the system."""
    registerable_workloads = get_registerable_workloads()

    if len(registerable_workloads) == 0:
        logger.error("No workloads found to register. This usually means the workloads directory is missing or empty.")
        logger.error(
            "Please run 'uv run wm init' manually in the workloads_manager package directory to initialize the workloads repository."
        )
        raise ValueError("No workloads found to register.")

    logger.info(f"Registering {len(registerable_workloads)} workloads.")
    created = 0
    updated = 0
    async with session_ctx() as session:
        try:
            for workload in registerable_workloads:
                # Register workload to create or update charts
                form_data: dict[str, str | list | dict | None] = {"name": workload.chart_name, "type": workload.type}
                metadata = workload.get_metadata_for_api()
                api_files = workload.get_chart_upload_data()

                form_data.update(metadata)
                form_data.update(normalize_api_files(api_files))
                chart = await select_chart(session, chart_name=workload.chart_name)
                if chart:
                    updated += 1
                    schema = ChartUpdate(**form_data)
                    chart = await update_chart(session, chart_id=chart.id, update_schema=schema, creator="system")
                    pass
                else:
                    created += 1
                    schema = ChartCreate(**form_data)
                    chart = await create_chart(session, chart_schema=schema, creator="system")
                    pass
                # Register workload files
                overlay_files = workload.get_overlay_files()
                for file_path, rel_path_str in overlay_files:
                    content = file_path.read_text(encoding="utf-8")
                    canonical_name = None
                    raw_data = yaml.safe_load(content)
                    if raw_data and isinstance(raw_data, dict):
                        overlay_data = OverlayData(**raw_data)
                        canonical_name = overlay_data.canonical_name
                    # Find existing overlay by chart_id AND canonical_name
                    existing_overlays = await list_overlays(
                        session=session, chart_id=chart.id, canonical_name=canonical_name
                    )
                    overlay_schema = {"chart_id": chart.id}
                    if raw_data:
                        overlay_schema["overlay"] = raw_data
                    if existing_overlays:
                        # Update the existing overlay with matching canonical_name
                        overlay = existing_overlays[0]  # Should only be one due to unique constraint
                        await update_overlay(
                            session=session,
                            overlay_id=overlay.id,
                            overlay_update=OverlayUpdate(**overlay_schema, updated_by="system"),
                        )
                    else:
                        if not raw_data:
                            raise ValueError("Overlay data is required for creating an overlay.")
                        await create_overlay(
                            session=session,
                            chart_id=chart.id,
                            overlay_data=raw_data,
                            canonical_name=canonical_name,
                            creator="system",
                        )
            logger.info(f"Registration complete: {created} created, {updated} updated workloads")
        except Exception as e:
            await session.rollback()
            logger.exception("Registration failed")
            raise e


def normalize_api_files(files: dict) -> dict[str, str]:
    """Normalize files for API upload."""
    signature = files.get("signature")
    if isinstance(signature, list) and signature:
        signature = signature[0]
    return {"files": files["files"], "signature": signature}


if __name__ == "__main__":
    import asyncio
    import sys

    try:
        init_db()
    except Exception as e:
        logger.exception("Failed to initialize database", e)
        sys.exit(1)

    try:
        asyncio.run(register_workloads())
    except Exception as e:
        logger.exception("Failed to register workloads", e)
        sys.exit(1)
