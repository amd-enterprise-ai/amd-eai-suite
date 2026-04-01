# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api_common.models import BaseEntity


class OnboardingStatus(StrEnum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class InferenceModel(BaseEntity):
    """Model for fine-tuned inference models."""

    __tablename__ = "inference_models"

    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        SQLAlchemyEnum(OnboardingStatus, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]),
        nullable=False,
    )
    model_weights_path: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_name: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (UniqueConstraint("name", "namespace", name="inference_models_name_namespace_key"),)
