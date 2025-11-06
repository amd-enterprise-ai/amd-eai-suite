# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLAlchemyEnum

from airm.messaging.schemas import WorkloadStatus

from ..utilities.models import BaseEntity
from .enums import WorkloadType


class Workload(BaseEntity):
    __tablename__ = "workloads"
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[WorkloadType] = mapped_column(
        SQLAlchemyEnum(WorkloadType, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=True,
    )
    cluster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[WorkloadStatus] = mapped_column(
        SQLAlchemyEnum(WorkloadStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String, default="generic")
    last_status_transition_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_workloads_project_id_status", project_id, status),
        Index("ix_workloads_cluster_id_status_project_id", cluster_id, status, project_id),
        Index("ix_workloads_project_id_created_at", project_id, "created_at"),
        Index("ix_workloads_display_name", display_name),
    )

    __mapper_args__ = {
        "polymorphic_identity": "generic",
        "polymorphic_on": "kind",
    }


class WorkloadComponent(BaseEntity):
    __tablename__ = "workload_components"

    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    api_version: Mapped[str] = mapped_column(String, nullable=False)
    workload_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workloads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    status_reason: Mapped[str] = mapped_column(String, nullable=True)


class WorkloadTimeSummary(BaseEntity):
    __tablename__ = "workload_time_summaries"

    workload_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workloads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[WorkloadStatus] = mapped_column(
        SQLAlchemyEnum(WorkloadStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    total_elapsed_seconds: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("ix_workload_time_summaries_workload_id_status", workload_id, status, unique=True),)
