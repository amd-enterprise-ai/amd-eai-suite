# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..utilities.exceptions import ConflictException, NotFoundException
from ..utilities.models import set_updated_fields
from ..workloads.enums import WorkloadType
from .models import Chart, ChartFile
from .schemas import ChartCreate, ChartUpdate


async def create_chart(session: AsyncSession, chart_schema: ChartCreate, creator: str) -> Chart:
    """Create a new chart with associated files."""
    data = await chart_schema.to_data()
    files_data = data.pop("files", [])  # Files need to be added as separate records

    db_chart = Chart(**data, created_by=creator, updated_by=creator)
    session.add(db_chart)
    try:
        await session.flush()  # Flush to get the chart ID
        if files_data:
            await create_file_records(session, db_chart.id, files_data, creator)

        await session.flush()
        await session.refresh(db_chart)
        return db_chart
    except IntegrityError as e:
        error_message = str(e)
        if "charts_name_key" in error_message:
            raise ConflictException(f"Chart with name '{db_chart.name}' already exists")
        raise e


async def list_charts(session: AsyncSession, chart_type: WorkloadType | None = None) -> list[Chart]:
    """List charts, optionally filtered by workload type."""
    query = select(Chart)
    if chart_type is not None:
        query = query.where(Chart.type == chart_type)
    results = await session.execute(query)
    return results.scalars().unique().all()


async def delete_chart(session: AsyncSession, chart_id: UUID) -> bool:
    """Delete a chart. Returns True if deleted, False if not found."""
    query = select(Chart).where(Chart.id == chart_id)
    result = await session.execute(query)
    chart = result.scalars().first()

    if chart:
        await session.delete(chart)
        await session.flush()
        return True
    else:
        return False


async def select_chart(
    session: AsyncSession, chart_id: UUID | None = None, chart_name: str | None = None
) -> Chart | None:
    query = select(Chart)
    if chart_id:
        query = query.where(Chart.id == chart_id)
    elif chart_name:
        query = query.where(Chart.name == chart_name)
    else:
        # Return None instead of raising exception - let service layer handle validation
        return None

    result = await session.execute(query)
    return result.scalars().first()


async def update_chart(session: AsyncSession, chart_id: UUID, update_schema: ChartUpdate, creator: str) -> Chart:
    """Update an existing chart with the provided fields."""
    chart = await select_chart(session, chart_id=chart_id)
    if not chart:
        raise NotFoundException(f"Chart with ID {chart_id} not found")

    data = await update_schema.to_data()
    files_data = data.pop("files", None)

    # Update chart fields (excluding files)
    for field, value in data.items():
        setattr(chart, field, value)

    # Files are replaced completely for simplicity
    if files_data is not None:
        await delete_chart_files(session, chart_id)
        if files_data:  # Only create records if there are files
            await create_file_records(session, chart_id, files_data, creator)

    set_updated_fields(chart, creator)

    await session.flush()
    return chart


async def delete_chart_files(session: AsyncSession, chart_id: UUID) -> None:
    """Delete specific files from a chart."""
    query = select(ChartFile).where(ChartFile.chart_id == chart_id)
    result = await session.execute(query)
    files_to_delete = result.unique().scalars().all()

    for file in files_to_delete:
        await session.delete(file)

    await session.flush()


async def create_file_records(session: AsyncSession, chart_id: UUID, files: list[dict], creator: str) -> None:
    """Create file records for a chart."""
    for file in files:
        db_file = ChartFile(
            chart_id=chart_id, path=file["path"], content=file["content"], created_by=creator, updated_by=creator
        )
        session.add(db_file)

    await session.flush()
