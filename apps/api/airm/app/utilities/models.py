# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, MetaData, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

metadata = MetaData()


class AuditBase(DeclarativeBase):
    __abstract__ = True
    metadata = metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    created_by: Mapped[str] = mapped_column(String, nullable=True)
    updated_by: Mapped[str] = mapped_column(String, nullable=True)


class BaseEntity(AuditBase):
    __abstract__ = True
    metadata = metadata
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())


def set_updated_fields(entity: BaseEntity, updater: str, updated_at: datetime | None = None) -> None:
    entity.updated_at = updated_at or datetime.now(UTC)
    entity.updated_by = updater
