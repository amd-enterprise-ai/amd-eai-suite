# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.models import Chart
from app.overlays.models import Overlay

from ..charts.conftest import sample_chart as sample_chart


@pytest_asyncio.fixture
async def sample_generic_overlay(db_session: AsyncSession, sample_chart: Chart) -> Overlay:  # noqa: F811
    overlay_id = uuid.uuid4()
    creator = "test-user"
    overlay_data = {"key": "no_canonical"}
    created_at = datetime.now(UTC)

    overlay = Overlay(
        id=overlay_id,
        chart_id=sample_chart.id,
        overlay=overlay_data,
        created_by=creator,
        updated_by=creator,
        created_at=created_at,
        updated_at=created_at,
        # canonical_name is None by default
    )
    db_session.add(overlay)
    await db_session.flush()
    await db_session.refresh(overlay)
    return overlay


@pytest_asyncio.fixture
async def sample_model_overlay(db_session: AsyncSession, sample_chart: Chart) -> Overlay:  # noqa: F811
    overlay_id = uuid.uuid4()
    canonical_name = "meta-llama/Llama-3.1-8B"
    creator = "test-user"
    overlay_data = {"key": "value"}
    created_at = datetime.now(UTC)

    overlay = Overlay(
        id=overlay_id,
        chart_id=sample_chart.id,
        canonical_name=canonical_name,
        overlay=overlay_data,
        created_by=creator,
        updated_by=creator,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(overlay)
    await db_session.flush()
    await db_session.refresh(overlay)
    return overlay
