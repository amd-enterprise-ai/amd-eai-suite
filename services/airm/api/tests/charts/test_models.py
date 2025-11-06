# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest

from app.charts.models import Chart, ChartFile
from app.workloads.enums import WorkloadType


@pytest.mark.asyncio
async def test_chart_creation():
    test_files = [
        ChartFile(path="env.txt", content="ENV=production\nDEBUG=false"),
        ChartFile(path="config.yaml", content="key: value\nlist:\n  - item1\n  - item2"),
    ]

    # Create chart with files
    chart = Chart(
        name="Test Chart",
        slug="test-chart-slug",
        display_name="Test Chart Display Name",
        type=WorkloadType.FINE_TUNING,
        signature={"param1": "value1"},
        files=test_files,
        description="Test chart description",
        category="test-category",
        tags=["tag1", "tag2"],
    )

    # Assert chart basic properties
    assert chart.name == "Test Chart"
    assert chart.slug == "test-chart-slug"
    assert chart.display_name == "Test Chart Display Name"
    assert chart.signature == {"param1": "value1"}
    assert chart.type == WorkloadType.FINE_TUNING
    assert chart.description == "Test chart description"
    assert chart.category == "test-category"
    assert chart.tags == ["tag1", "tag2"]

    # Assert files
    assert len(chart.files) == 2

    # Check first file
    assert chart.files[0].path == "env.txt"
    assert chart.files[0].content == "ENV=production\nDEBUG=false"

    # Check second file
    assert chart.files[1].path == "config.yaml"
    assert chart.files[1].content == "key: value\nlist:\n  - item1\n  - item2"


@pytest.mark.asyncio
async def test_chart_creation_with_minimal_fields():
    """Test chart creation with only required fields."""
    chart = Chart(
        name="Minimal Chart",
        signature={},
    )

    assert chart.name == "Minimal Chart"
    assert chart.slug is None
    assert chart.display_name is None
    assert chart.type is None
    assert chart.signature == {}
    assert chart.description is None
    assert chart.category is None
    assert chart.tags is None
    assert chart.featured_image is None
    assert chart.required_resources is None
    assert chart.external_url is None
    assert len(chart.files) == 0


@pytest.mark.asyncio
async def test_chart_creation_with_all_metadata_fields():
    """Test chart creation with all metadata fields populated."""
    chart = Chart(
        name="Full Metadata Chart",
        slug="full-metadata-chart",
        display_name="Full Metadata Chart Display",
        type=WorkloadType.INFERENCE,
        signature={"model": "test-model"},
        description="A comprehensive test chart",
        long_description="This is a longer description with more details about the chart functionality.",
        category="machine-learning",
        tags=["inference", "ml", "test"],
        featured_image="https://example.com/image.png",
        required_resources={"cpu": "2", "memory": "4Gi", "gpu": "1"},
        external_url="https://example.com/docs",
    )

    assert chart.name == "Full Metadata Chart"
    assert chart.slug == "full-metadata-chart"
    assert chart.display_name == "Full Metadata Chart Display"
    assert chart.type == WorkloadType.INFERENCE
    assert chart.signature == {"model": "test-model"}
    assert chart.description == "A comprehensive test chart"
    assert chart.long_description == "This is a longer description with more details about the chart functionality."
    assert chart.category == "machine-learning"
    assert chart.tags == ["inference", "ml", "test"]
    assert chart.featured_image == "https://example.com/image.png"
    assert chart.required_resources == {"cpu": "2", "memory": "4Gi", "gpu": "1"}
    assert chart.external_url == "https://example.com/docs"
