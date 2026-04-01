# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..utilities.models import BaseEntity


class User(BaseEntity):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, nullable=False)
    keycloak_user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_by: Mapped[str] = mapped_column(String, nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("users_email_key", func.lower(email), unique=True),)
