# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger, Integer, SmallInteger

from airm.messaging.schemas import GPUVendor

from ..utilities.models import BaseEntity


class Cluster(BaseEntity):
    __tablename__ = "clusters"

    name: Mapped[str] = mapped_column(String, nullable=True)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    workloads_base_url: Mapped[str] = mapped_column(String, nullable=True)
    kube_api_url: Mapped[str] = mapped_column(String, nullable=True)

    __table_args__ = (Index("clusters_name_organization_id_key", func.lower(name), organization_id, unique=True),)


class ClusterNode(BaseEntity):
    __tablename__ = "cluster_nodes"

    cluster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    cpu_milli_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ephemeral_storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    gpu_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    gpu_type: Mapped[str] = mapped_column(String, nullable=True)
    gpu_vendor: Mapped[GPUVendor] = mapped_column(
        SQLAlchemyEnum(GPUVendor, native_enum=False, values_callable=lambda obj: [str(e) for e in obj]), nullable=True
    )
    gpu_vram_bytes_per_device: Mapped[int] = mapped_column(BigInteger, nullable=True)
    gpu_product_name: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (Index("cluster_nodes_name_cluster_id_key", func.lower(name), cluster_id, unique=True),)
