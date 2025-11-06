# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..charts.models import Chart
from ..utilities.models import BaseEntity


class Overlay(BaseEntity):
    __tablename__ = "overlays"

    canonical_name: Mapped[str] = mapped_column(String, nullable=True)
    overlay: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    chart_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chart: Mapped[Chart] = relationship(Chart, lazy="joined")

    __table_args__ = (Index("overlays_chart_id_canonical_name_key", chart_id, canonical_name, unique=True),)
