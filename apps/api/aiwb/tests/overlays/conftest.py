# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.models import Chart
from app.overlays.models import Overlay
from app.workloads.enums import WorkloadType
from tests import factory


@pytest_asyncio.fixture
async def sample_chart(db_session: AsyncSession) -> Chart:
    """Creates a sample chart in the database for testing overlays."""
    return await factory.create_chart(
        db_session, name=f"test-chart-{uuid4()}", chart_type=WorkloadType.INFERENCE, signature={"param": "value"}
    )


@pytest_asyncio.fixture
async def sample_generic_overlay(db_session: AsyncSession, sample_chart: Chart) -> Overlay:  # noqa: F811
    return await factory.create_overlay(
        db_session, chart_id=sample_chart.id, overlay_data={"key": "no_canonical"}, created_by="test-user"
    )


@pytest_asyncio.fixture
async def sample_model_overlay(db_session: AsyncSession, sample_chart: Chart) -> Overlay:  # noqa: F811
    return await factory.create_overlay(
        db_session,
        chart_id=sample_chart.id,
        canonical_name="meta-llama/Llama-3.1-8B",
        overlay_data={"key": "value"},
        created_by="test-user",
    )
