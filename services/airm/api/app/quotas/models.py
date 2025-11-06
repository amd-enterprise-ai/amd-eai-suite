# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import BigInteger, Integer, SmallInteger

from airm.messaging.schemas import QuotaStatus

from ..clusters.models import Cluster
from ..utilities.models import BaseEntity


class Quota(BaseEntity):
    __tablename__ = "quotas"

    cluster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cluster: Mapped[Cluster] = relationship("Cluster", lazy="joined")

    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project = relationship("Project", back_populates="quota", uselist=False, lazy="joined")

    cpu_milli_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ephemeral_storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    gpu_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[QuotaStatus] = mapped_column(
        SQLAlchemyEnum(QuotaStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (Index("quotas_project_id_key", project_id, unique=True),)
