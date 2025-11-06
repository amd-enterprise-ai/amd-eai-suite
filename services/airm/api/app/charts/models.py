# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from typing import Literal

from sqlalchemy import Column, ForeignKey, Index, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..utilities.models import BaseEntity
from ..workloads.enums import WorkloadType
from ..workspaces.enums import WORKSPACE_USAGE_SCOPE_MAPPING, workspace_type_chart_name_mapping


class Chart(BaseEntity):
    __tablename__ = "charts"

    name: Mapped[str] = Column(String, nullable=False, unique=True)
    type: Mapped[WorkloadType] = mapped_column(
        SQLAlchemyEnum(WorkloadType, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=True,
        default=None,
    )
    signature: Mapped[dict] = Column(JSONB, nullable=False, default=dict)
    files: Mapped[list["ChartFile"]] = relationship(
        "ChartFile", back_populates="chart", cascade="all, delete-orphan", lazy="joined"
    )
    display_name: Mapped[str | None] = Column(String, nullable=True)
    slug: Mapped[str | None] = Column(String, nullable=True)
    description: Mapped[str | None] = Column(String, nullable=True)
    long_description: Mapped[str | None] = Column(String, nullable=True)
    category: Mapped[str | None] = Column(String, nullable=True)
    tags: Mapped[list[str] | None] = Column(JSONB, nullable=True)
    featured_image: Mapped[str | None] = Column(String, nullable=True)
    required_resources: Mapped[dict | None] = Column(JSONB, nullable=True)
    external_url: Mapped[str | None] = Column(String, nullable=True)

    __table_args__ = (Index("chart_name_key", func.lower(name), unique=True),)

    @property
    def usage_scope(self) -> Literal["user", "project"]:
        """
        Determine usage scope based on chart name using static mapping.

        Returns:
            "project" for project-scoped workspace types, "user" for others
        """
        # Find workspace type for this chart by reversing the mapping
        for workspace_type, mapped_chart_name in workspace_type_chart_name_mapping.items():
            if self.name == mapped_chart_name:
                return WORKSPACE_USAGE_SCOPE_MAPPING.get(workspace_type, "user")  # type: ignore[return-value]

        return "user"


class ChartFile(BaseEntity):
    __tablename__ = "chart_files"

    path: Mapped[str] = Column(String, nullable=False)
    content: Mapped[str] = Column(String, nullable=False)
    chart_id: Mapped[uuid.UUID] = Column(PGUUID(as_uuid=True), ForeignKey("charts.id", ondelete="CASCADE"), index=True)
    chart: Mapped["Chart"] = relationship(back_populates="files", lazy="joined")
