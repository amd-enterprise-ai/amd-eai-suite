# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime

import pytest

from app.overlays.models import Overlay


@pytest.mark.asyncio
async def test_overlay_creation() -> None:
    """Test Overlay model direct creation and attribute assertion."""
    # Define properties for the overlay
    test_id = uuid.uuid4()
    test_chart_id = uuid.uuid4()
    test_canonical_name = "meta-llama/Llama-3.1-8B"
    test_overlay_data = {"param": "value", "nested": {"config": True}}
    test_creator = "creator-user"
    test_time = datetime.now(UTC)

    # Create Overlay instance (only direct fields)
    overlay = Overlay(
        chart_id=test_chart_id,
        canonical_name=test_canonical_name,
        overlay=test_overlay_data,
    )

    # Manually set BaseEntity fields (like in fixtures)
    overlay.id = test_id
    overlay.created_at = test_time
    overlay.updated_at = test_time
    overlay.created_by = test_creator

    # Assert Overlay-specific properties
    assert overlay.chart_id == test_chart_id
    assert overlay.canonical_name == test_canonical_name
    assert overlay.overlay == test_overlay_data

    # Assert BaseEntity properties (that we manually set)
    assert overlay.id == test_id
    assert overlay.created_at == test_time
    assert overlay.updated_at == test_time
    assert overlay.created_by == test_creator
