# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from app.overlays.models import Overlay
from app.overlays.schemas import OverlayResponse


def test_generic_overlay_response_from_model(
    sample_generic_overlay: Overlay,
) -> None:
    """Test OverlayResponse validation from a model without canonical_name."""
    overlay = sample_generic_overlay
    response = OverlayResponse.model_validate(overlay)

    assert response.id == overlay.id
    assert response.chart_id == overlay.chart_id
    assert response.canonical_name is None
    assert response.overlay == overlay.overlay
    assert response.created_by == overlay.created_by
    assert response.created_at == overlay.created_at
    assert response.updated_at == overlay.updated_at


def test_model_overlay_response_from_model(
    sample_model_overlay: Overlay,
) -> None:
    """Test OverlayResponse validation from a model with canonical_name."""
    overlay = sample_model_overlay
    response = OverlayResponse.model_validate(overlay)

    assert response.id == overlay.id
    assert response.chart_id == overlay.chart_id
    assert response.canonical_name == overlay.canonical_name
    assert response.overlay == overlay.overlay
    assert response.created_by == overlay.created_by
    assert response.created_at == overlay.created_at
    assert response.updated_at == overlay.updated_at
