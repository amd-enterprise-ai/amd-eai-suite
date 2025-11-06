# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..utilities.models import BaseEntity


class DatasetType(StrEnum):
    FINETUNING = "Fine-tuning"


class Dataset(BaseEntity):
    """Base class for datasets."""

    __tablename__ = "datasets"
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[DatasetType] = mapped_column(
        SQLAlchemyEnum(DatasetType, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=True,
        default=None,
    )

    # Unique constraints
    __table_args__ = (
        # Dataset name must be unique within a project_id scope (case-insensitive)
        Index("datasets_name_project_id_key", func.lower(name), project_id, unique=True),
        # Dataset path must be globally unique
        Index("datasets_path_key", path, unique=True),
    )
