# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.service import get_chart
from app.utilities.exceptions import NotFoundException
from app.workloads.enums import WorkloadType
from tests import factory


@pytest.mark.asyncio
async def test_get_chart_by_name_success(db_session: AsyncSession):
    """Test successful chart retrieval by name."""
    chart_name = "test-chart-by-name"
    chart = await factory.create_chart(db_session, name=chart_name, chart_type=WorkloadType.INFERENCE)

    result = await get_chart(db_session, chart_name=chart_name)

    assert result.id == chart.id
    assert result.name == chart_name
    assert result.type == WorkloadType.INFERENCE


@pytest.mark.asyncio
async def test_get_chart_by_id_success(db_session: AsyncSession):
    """Test successful chart retrieval by ID."""
    chart = await factory.create_chart(db_session, name="test-chart-by-id", chart_type=WorkloadType.FINE_TUNING)

    result = await get_chart(db_session, chart_id=chart.id)

    assert result.id == chart.id
    assert result.name == chart.name
    assert result.type == WorkloadType.FINE_TUNING


@pytest.mark.asyncio
async def test_get_chart_by_name_not_found(db_session: AsyncSession):
    """Test handling when chart is not found by name."""
    nonexistent_chart_name = "nonexistent-chart"

    with pytest.raises(NotFoundException) as exc_info:
        await get_chart(db_session, chart_name=nonexistent_chart_name)

    assert f"Chart with name {nonexistent_chart_name} not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_chart_by_id_not_found(db_session: AsyncSession):
    """Test handling when chart is not found by ID."""
    nonexistent_chart_id = uuid4()

    with pytest.raises(NotFoundException) as exc_info:
        await get_chart(db_session, chart_id=nonexistent_chart_id)

    assert f"Chart with ID {nonexistent_chart_id} not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_chart_no_parameters(db_session: AsyncSession):
    """Test handling when neither name nor ID is provided."""
    with pytest.raises(ValueError) as exc_info:
        await get_chart(db_session)

    assert "Either chart_name or chart_id must be provided" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_chart_by_name_with_multiple_charts(db_session: AsyncSession):
    """Test chart retrieval by name when multiple charts exist."""
    # Create multiple charts to ensure we get the right one
    await factory.create_chart(db_session, name="chart-1")
    target_chart = await factory.create_chart(db_session, name="target-chart")
    await factory.create_chart(db_session, name="chart-3")

    result = await get_chart(db_session, chart_name="target-chart")

    assert result.id == target_chart.id
    assert result.name == "target-chart"


@pytest.mark.asyncio
async def test_get_chart_by_id_with_multiple_charts(db_session: AsyncSession):
    """Test chart retrieval by ID when multiple charts exist."""
    # Create multiple charts to ensure we get the right one
    await factory.create_chart(db_session, name="chart-1")
    target_chart = await factory.create_chart(db_session, name="chart-2")
    await factory.create_chart(db_session, name="chart-3")

    result = await get_chart(db_session, chart_id=target_chart.id)

    assert result.id == target_chart.id
    assert result.name == "chart-2"
