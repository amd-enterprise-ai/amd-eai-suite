# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..clusters.models import Cluster
from ..utilities.models import BaseEntity
from .enums import ProjectStatus


class Project(BaseEntity):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cluster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ProjectStatus] = mapped_column(
        SQLAlchemyEnum(ProjectStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str] = mapped_column(String, nullable=True)
    keycloak_group_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    cluster: Mapped[Cluster] = relationship("Cluster", lazy="joined")

    quota = relationship("Quota", back_populates="project", uselist=False, lazy="joined", cascade="all, delete-orphan")

    __table_args__ = (Index("projects_name_organization_id_key", name, organization_id, unique=True),)
