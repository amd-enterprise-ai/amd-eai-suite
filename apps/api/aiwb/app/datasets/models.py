# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api_common.models import BaseEntity


class DatasetType(StrEnum):
    FINETUNING = "Fine-tuning"


class Dataset(BaseEntity):
    """Base class for datasets."""

    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[DatasetType] = mapped_column(
        SQLAlchemyEnum(DatasetType, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=True,
        default=None,
    )

    __table_args__ = (
        Index("datasets_name_namespace_key", func.lower(name), namespace, unique=True),
        Index("datasets_path_key", path, unique=True),
    )
