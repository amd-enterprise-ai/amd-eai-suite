# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from airm.messaging.schemas import ProjectSecretStatus

from ..projects.models import Project
from ..utilities.models import BaseEntity
from .enums import SecretScope, SecretStatus, SecretType, SecretUseCase


class Secret(BaseEntity):
    __tablename__ = "secrets"
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[SecretType] = mapped_column(
        SQLAlchemyEnum(SecretType, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]), nullable=False
    )
    scope: Mapped[SecretScope] = mapped_column(
        SQLAlchemyEnum(SecretScope, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    manifest: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[SecretStatus] = mapped_column(
        SQLAlchemyEnum(SecretStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    use_case: Mapped[SecretUseCase | None] = mapped_column(
        SQLAlchemyEnum(SecretUseCase, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=True,
    )
    project_secrets: Mapped[list["ProjectSecret"]] = relationship(
        "ProjectSecret", back_populates="secret", lazy="joined"
    )

    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_secret_org_name"),)


class ProjectSecret(BaseEntity):
    __tablename__ = "project_secrets"

    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    secret_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("secrets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ProjectSecretStatus] = mapped_column(
        SQLAlchemyEnum(ProjectSecretStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str] = mapped_column(String, nullable=True)

    secret: Mapped["Secret"] = relationship("Secret", back_populates="project_secrets")
    project: Mapped["Project"] = relationship("Project", lazy="joined")
