# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..utilities.models import BaseEntity


class AIM(BaseEntity):
    """Represents an AIMClusterModel discovered from the cluster."""

    __tablename__ = "aims"

    resource_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    image_reference: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    labels: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
