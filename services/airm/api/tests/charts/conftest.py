# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from io import BytesIO
from uuid import uuid4

import pytest
import pytest_asyncio
import yaml
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.models import Chart
from app.charts.repository import create_chart
from app.charts.schemas import ChartCreate
from app.workloads.enums import WorkloadType


@pytest.fixture
def test_cluster_id():
    """Return a test cluster ID."""
    return uuid4()


@pytest_asyncio.fixture
async def charts(db_session: AsyncSession):
    chart1 = Chart(
        name="Test Chart 1",
        type=WorkloadType.FINE_TUNING,
        signature={"param1": "test"},
    )

    chart2 = Chart(
        name="Test Chart 2",
        type=WorkloadType.FINE_TUNING,
        signature={"param1": "test"},
    )

    db_session.add_all([chart1, chart2])
    await db_session.commit()
    await db_session.refresh(chart1)
    await db_session.refresh(chart2)
    return chart1, chart2


@pytest_asyncio.fixture
async def sample_chart(db_session: AsyncSession) -> Chart:
    """Creates a sample chart in the database for testing."""
    # Create UploadFile objects for signature and files
    signature_content = yaml.dump({"param": "value"})
    signature_file = UploadFile(filename="values.yaml", file=BytesIO(signature_content.encode()))
    chart_files = [UploadFile(filename="file1.yaml", file=BytesIO(b"content1"))]

    chart_data = ChartCreate(
        name=f"test-chart-{uuid4()}",
        type=WorkloadType.INFERENCE,
        signature=signature_file,
        files=chart_files,
    )
    chart = await create_chart(session=db_session, chart_schema=chart_data, creator="fixture_user")
    return chart


@pytest_asyncio.fixture
async def workspace_charts(db_session: AsyncSession) -> tuple[Chart, Chart]:
    """Creates workspace charts with specific names for testing usage_scope."""
    # Create VSCode workspace chart (user scope)
    vscode_signature_content = yaml.dump({"param": "value"})
    vscode_signature_file = UploadFile(filename="values.yaml", file=BytesIO(vscode_signature_content.encode()))

    vscode_chart_data = ChartCreate(
        name="development-workspace",  # Maps to VSCode -> user scope
        type=WorkloadType.INFERENCE,
        signature=vscode_signature_file,
        files=[],
    )
    vscode_chart = await create_chart(session=db_session, chart_schema=vscode_chart_data, creator="fixture_user")

    # Create MLFlow workspace chart (project scope)
    mlflow_signature_content = yaml.dump({"param": "value"})
    mlflow_signature_file = UploadFile(filename="values.yaml", file=BytesIO(mlflow_signature_content.encode()))

    mlflow_chart_data = ChartCreate(
        name="dev-tracking-mlflow",  # Maps to MLFlow -> project scope
        type=WorkloadType.INFERENCE,
        signature=mlflow_signature_file,
        files=[],
    )
    mlflow_chart = await create_chart(session=db_session, chart_schema=mlflow_chart_data, creator="fixture_user")

    return vscode_chart, mlflow_chart
