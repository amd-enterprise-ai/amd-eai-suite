# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.models import Chart
from app.workloads.enums import WorkloadType
from tests import factory


@pytest_asyncio.fixture
async def charts(db_session: AsyncSession) -> tuple[Chart, Chart]:
    chart1 = await factory.create_chart(
        db_session, name="Test Chart 1", chart_type=WorkloadType.FINE_TUNING, signature={"param1": "test"}
    )
    chart2 = await factory.create_chart(
        db_session, name="Test Chart 2", chart_type=WorkloadType.FINE_TUNING, signature={"param1": "test"}
    )
    return chart1, chart2


@pytest_asyncio.fixture
async def sample_chart(db_session: AsyncSession) -> Chart:
    """Creates a sample chart in the database for testing."""
    return await factory.create_chart(
        db_session, name=f"test-chart-{uuid4()}", chart_type=WorkloadType.INFERENCE, signature={"param": "value"}
    )


@pytest_asyncio.fixture
async def workspace_charts(db_session: AsyncSession) -> tuple[Chart, Chart]:
    """Creates workspace charts with specific names for testing usage_scope.

    Uses real chart names from config to test the usage_scope mapping:
    - dev-workspace-vscode -> user scope
    - dev-tracking-mlflow -> namespace scope
    """
    vscode_chart = await factory.create_chart(
        db_session, name="dev-workspace-vscode", chart_type=WorkloadType.WORKSPACE, signature={"param": "value"}
    )

    mlflow_chart = await factory.create_chart(
        db_session, name="dev-tracking-mlflow", chart_type=WorkloadType.WORKSPACE, signature={"param": "value"}
    )

    return vscode_chart, mlflow_chart
