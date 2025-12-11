# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from airm.messaging.schemas import ProjectSecretStatus, SecretKind, SecretScope

from ..projects.models import Project
from ..utilities.models import BaseEntity
from .enums import SecretStatus, SecretUseCase


class Secret(BaseEntity):
    __tablename__ = "secrets"
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[SecretKind] = mapped_column(
        SQLAlchemyEnum(SecretKind, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    scope: Mapped[SecretScope] = mapped_column(
        SQLAlchemyEnum(SecretScope, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )

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

    __mapper_args__ = {
        "polymorphic_on": "scope",
        "polymorphic_abstract": True,
        "with_polymorphic": "*",
    }


class ProjectScopedSecret(Secret):
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    __mapper_args__ = {
        "polymorphic_identity": SecretScope.PROJECT,
    }
    project: Mapped["Project"] = relationship("Project", lazy="joined")


class OrganizationSecretAssignment(BaseEntity):
    __tablename__ = "organization_secret_assignments"

    organization_secret_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("secrets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ProjectSecretStatus] = mapped_column(
        SQLAlchemyEnum(ProjectSecretStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    secret: Mapped["OrganizationScopedSecret"] = relationship(
        "OrganizationScopedSecret", back_populates="organization_secret_assignments", lazy="joined"
    )
    project: Mapped["Project"] = relationship("Project", lazy="joined")


class OrganizationScopedSecret(Secret):
    manifest: Mapped[str] = mapped_column(String, nullable=True)
    __mapper_args__ = {
        "polymorphic_identity": SecretScope.ORGANIZATION,
    }

    organization_secret_assignments: Mapped[list["OrganizationSecretAssignment"]] = relationship(
        "OrganizationSecretAssignment", back_populates="secret", lazy="joined"
    )


UniqueConstraint(
    Secret.__table__.c.organization_id,
    Secret.__table__.c.project_id,
    Secret.__table__.c.name,
    Secret.__table__.c.type,
    name="uq_secret_org_proj_name_type",
    postgresql_nulls_not_distinct=True,
)
