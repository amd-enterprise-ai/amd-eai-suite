# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from api_common.models import BaseEntity


class AIMService(BaseEntity):
    """Historical record of AIMService deployments."""

    __tablename__ = "aim_services"

    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model: Mapped[str] = mapped_column(String, nullable=False, comment="AIM model resource name")
    status: Mapped[str] = mapped_column(String, nullable=False, comment="AIMService status")
    metric: Mapped[str | None] = mapped_column(String, nullable=True, comment="Performance metric")
