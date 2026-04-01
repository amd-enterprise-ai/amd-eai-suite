# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api_common.models import BaseEntity

from ..workloads.enums import WorkloadType
from ..workspaces.enums import WORKSPACE_USAGE_SCOPE_MAPPING, WorkspaceUsageScope, workspace_type_chart_name_mapping


class Chart(BaseEntity):
    __tablename__ = "charts"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    type: Mapped[WorkloadType] = mapped_column(
        SQLAlchemyEnum(WorkloadType, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=True,
        default=None,
    )
    signature: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    files: Mapped[list["ChartFile"]] = relationship(
        "ChartFile", back_populates="chart", cascade="all, delete-orphan", lazy="joined"
    )
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    slug: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    long_description: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    featured_image: Mapped[str | None] = mapped_column(String, nullable=True)
    required_resources: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    external_url: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (Index("chart_name_key", func.lower(name), unique=True),)

    @property
    def usage_scope(self) -> WorkspaceUsageScope:
        """
        Determine usage scope based on chart name using static mapping.

        Returns:
            WorkspaceUsageScope.NAMESPACE for namespace-scoped workspace types, WorkspaceUsageScope.USER for user-scoped workspace types
        """
        # Find workspace type for this chart by reversing the mapping
        for workspace_type, mapped_chart_name in workspace_type_chart_name_mapping.items():
            if self.name == mapped_chart_name:
                return WORKSPACE_USAGE_SCOPE_MAPPING.get(workspace_type, WorkspaceUsageScope.USER)

        return WorkspaceUsageScope.USER


class ChartFile(BaseEntity):
    __tablename__ = "chart_files"

    path: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    chart_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("charts.id", ondelete="CASCADE"), index=True
    )
    chart: Mapped["Chart"] = relationship(back_populates="files", lazy="joined")
