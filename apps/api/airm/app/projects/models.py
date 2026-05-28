# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api_common.models import BaseEntity

from ..clusters.models import Cluster
from .enums import GpuPreemptionPolicy, ProjectStatus


class Project(BaseEntity):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    cluster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ProjectStatus] = mapped_column(
        SQLAlchemyEnum(ProjectStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str] = mapped_column(String, nullable=True)
    keycloak_group_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    gpu_preemption_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    gpu_preemption_threshold: Mapped[int | None] = mapped_column(nullable=True)
    gpu_preemption_grace_period: Mapped[int | None] = mapped_column(nullable=True)
    gpu_preemption_policy: Mapped[GpuPreemptionPolicy | None] = mapped_column(
        SQLAlchemyEnum(GpuPreemptionPolicy, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=True,
    )

    cluster: Mapped[Cluster] = relationship("Cluster", lazy="joined")

    quota = relationship("Quota", back_populates="project", uselist=False, lazy="joined", cascade="all, delete-orphan")
