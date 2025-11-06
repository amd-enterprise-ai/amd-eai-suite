# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..projects.models import Project
from ..utilities.models import BaseEntity


class ApiKey(BaseEntity):
    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String, nullable=False)
    truncated_key: Mapped[str] = mapped_column(String, nullable=False)
    cluster_auth_key_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Note: ttl, expires_at, renewable, and num_uses are fetched from Cluster Auth (source of truth) and not stored in DB

    project: Mapped[Project] = relationship("Project", lazy="joined")

    __table_args__ = (Index("api_keys_name_project_id_key", name, project_id, unique=True),)
