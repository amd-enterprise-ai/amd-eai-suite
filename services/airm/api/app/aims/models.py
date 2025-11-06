# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..utilities.models import BaseEntity


class AIM(BaseEntity):
    """Represents an AIM that can be deployed."""

    __tablename__ = "aims"

    image_name: Mapped[str] = mapped_column(String, nullable=False)
    image_tag: Mapped[str] = mapped_column(String, nullable=False)
    labels: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (UniqueConstraint("image_name", "image_tag", name="aims_image_name_image_tag_key"),)
