# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for overlay models."""

import pytest
from pydantic import ValidationError

from workloads_manager.models.overlay import OverlayData, OverlayType, OverlayUploadData


def test_overlay_data_canonical_name():
    """Test OverlayData canonical_name property."""
    # Test with model field
    overlay1 = OverlayData(model="gpt-4")
    assert overlay1.canonical_name == "gpt-4"

    # Test with modelId field (using alias)
    overlay2 = OverlayData(modelId="claude-3")
    assert overlay2.canonical_name == "claude-3"
    assert overlay2.model_id == "claude-3"  # Internal field name

    # Test with both fields (model takes precedence)
    overlay3 = OverlayData(model="gpt-4", modelId="claude-3")
    assert overlay3.canonical_name == "gpt-4"

    # Test with neither field
    overlay4 = OverlayData()
    assert overlay4.canonical_name is None

    # Test that alias works in both directions
    overlay5 = OverlayData(**{"modelId": "test-model"})
    assert overlay5.model_id == "test-model"
    assert overlay5.canonical_name == "test-model"


def test_overlay_upload_data_validation():
    """Test OverlayUploadData validation."""
    # Valid data
    data = OverlayUploadData(
        chart_id="chart-123", canonical_name="model/test", content="overlay: content", overlay_type=OverlayType.MODEL
    )

    assert data.chart_id == "chart-123"
    assert data.canonical_name == "model/test"
    assert data.content == "overlay: content"
    assert data.overlay_type == OverlayType.MODEL

    # Empty chart ID
    with pytest.raises(ValidationError) as exc_info:
        OverlayUploadData(chart_id="", content="test")
    assert "String should have at least 1 character" in str(exc_info.value)

    # Empty content
    with pytest.raises(ValidationError) as exc_info:
        OverlayUploadData(chart_id="chart-123", content="")
    assert "String should have at least 1 character" in str(exc_info.value)
