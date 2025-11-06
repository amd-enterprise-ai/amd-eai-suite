# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from airm.messaging.schemas import ConfigMapStatus, ProjectStorageStatus

from ..projects.models import Project
from ..utilities.models import BaseEntity
from .enums import StorageScope, StorageStatus, StorageType


class Storage(BaseEntity):
    __tablename__ = "storages"

    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[StorageType] = mapped_column(
        SQLAlchemyEnum(StorageType, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    scope: Mapped[StorageScope] = mapped_column(
        SQLAlchemyEnum(StorageScope, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    secret_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("secrets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[StorageStatus] = mapped_column(
        SQLAlchemyEnum(StorageStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    bucket_url: Mapped[str | None] = mapped_column(String, nullable=True)
    access_key_name: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_key_name: Mapped[str | None] = mapped_column(String, nullable=True)

    project_storages: Mapped[list["ProjectStorage"]] = relationship(
        "ProjectStorage", back_populates="storage", lazy="joined"
    )

    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_storage_org_name"),)


class ProjectStorage(BaseEntity):
    __tablename__ = "project_storages"

    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("storages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ProjectStorageStatus] = mapped_column(
        SQLAlchemyEnum(ProjectStorageStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str] = mapped_column(String, nullable=True)

    storage: Mapped["Storage"] = relationship("Storage", back_populates="project_storages")
    project: Mapped["Project"] = relationship("Project", lazy="joined")


class ProjectStorageConfigmap(BaseEntity):
    __tablename__ = "project_storages_configmap"

    project_storage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("project_storages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ConfigMapStatus] = mapped_column(
        SQLAlchemyEnum(ConfigMapStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    status_reason: Mapped[str] = mapped_column(String, nullable=True)

    storage: Mapped["ProjectStorage"] = relationship("ProjectStorage", lazy="joined")
