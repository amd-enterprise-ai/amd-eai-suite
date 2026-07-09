# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api_common.models import BaseEntity


class ApiKey(BaseEntity):
    """
    API key model for AIWB.

    API keys are scoped to namespaces (not projects).
    The actual key data and metadata (ttl, expires_at, etc.) are stored
    in the cluster-auth service - this table only tracks references.
    """

    __tablename__ = "api_keys"

    display_name: Mapped[str] = mapped_column(String, nullable=False)
    truncated_key: Mapped[str] = mapped_column(String, nullable=False)
    cluster_auth_key_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Note: ttl, expires_at, renewable, and num_uses are fetched from Cluster Auth (source of truth)

    __table_args__ = (UniqueConstraint("display_name", "namespace", name="uq_api_keys_display_name_namespace"),)
