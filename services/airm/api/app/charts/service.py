# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.exceptions import NotFoundException
from .models import Chart
from .repository import select_chart


async def get_chart(session: AsyncSession, chart_name: str | None = None, chart_id: UUID | None = None) -> Chart:
    """
    Get a chart by name or ID.

    Raises:
        NotFoundException: If the chart with the given name/ID is not found
        ValueError: If neither chart_name nor chart_id is provided
    """
    if not chart_name and not chart_id:
        raise ValueError("Either chart_name or chart_id must be provided")

    chart = await select_chart(session, chart_id=chart_id, chart_name=chart_name)
    if not chart:
        identifier = chart_name if chart_name else str(chart_id)
        raise NotFoundException(f"Chart with {'name' if chart_name else 'ID'} {identifier} not found")
    return chart
