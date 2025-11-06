# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Overlay-related models."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class OverlayType(StrEnum):
    """Types of overlay files."""

    MODEL = "model"
    SIGNATURE = "signature"
    OTHER = "other"


class OverlayData(BaseModel):
    """Data structure for overlay files."""

    model: str | None = Field(None, description="Model identifier")
    model_id: str | None = Field(None, alias="modelId", description="Alternative model identifier")

    @property
    def canonical_name(self) -> str | None:
        """Get the canonical name from model or model_id."""
        return self.model or self.model_id


class OverlayUploadData(BaseModel):
    """Data for overlay upload operations."""

    chart_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
        Field(..., description="ID of the associated chart"),
    ]
    canonical_name: str | None = Field(None, description="Canonical name for the overlay")
    content: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
        Field(..., description="Content of the overlay file"),
    ]
    overlay_type: OverlayType = Field(OverlayType.OTHER, description="Type of overlay")
