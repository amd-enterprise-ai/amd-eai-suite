# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from airm.messaging.schemas import NamespaceStatus

from ..utilities.models import BaseEntity


class Namespace(BaseEntity):
    __tablename__ = "namespaces"

    name: Mapped[str] = mapped_column(String, nullable=False)
    cluster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[NamespaceStatus] = mapped_column(
        SQLAlchemyEnum(NamespaceStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str] = mapped_column(String, nullable=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_namespaces_project_id", project_id),
        Index("ix_namespaces_cluster_id", cluster_id),
    )
