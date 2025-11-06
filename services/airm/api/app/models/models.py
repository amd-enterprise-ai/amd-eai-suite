# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from ..projects.models import Project

from ..utilities.models import BaseEntity


class OnboardingStatus(StrEnum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class InferenceModel(BaseEntity):
    """Model for inference models."""

    __tablename__ = "inference_models"

    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project: Mapped["Project"] = relationship("Project", lazy="joined")
    name: Mapped[str] = mapped_column(String, nullable=False)
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        SQLAlchemyEnum(OnboardingStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    model_weights_path: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_name: Mapped[str] = mapped_column(String, nullable=True)
    hf_token_secret_name: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (UniqueConstraint("name", "project_id", name="inference_models_name_project_id_key"),)
