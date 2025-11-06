# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Deprecated: capabilities will be replaced by AIMs labels"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..charts.config import INFERENCE_CHART_NAME
from ..charts.service import get_chart
from ..models.models import InferenceModel
from ..overlays.repository import list_overlays


async def get_model_capabilities_from_overlays(
    session: AsyncSession,
    model: InferenceModel,
) -> list[str]:
    """Determine model capabilities by examining its associated workload chart overlays."""
    capabilities = set()

    # Return empty capabilities if model has no canonical name
    if not model.canonical_name:
        return []

    # Get inference chart overlays for the model
    chart = await get_chart(session, chart_name=INFERENCE_CHART_NAME)
    overlays = await list_overlays(session, chart_id=chart.id, canonical_name=model.canonical_name)
    for overlay in overlays:
        # Skip overlays that don't have the overlay attribute
        if not hasattr(overlay, "overlay") or not overlay.overlay or not isinstance(overlay.overlay, dict):
            continue

        # Get metadata and labels
        metadata = overlay.overlay.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        labels = metadata.get("labels", {})
        if not isinstance(labels, dict):
            continue

        # Check for chat capability
        chat_value = labels.get("chat")
        if chat_value == "true" or chat_value is True:
            capabilities.add("chat")

    return list(capabilities)
