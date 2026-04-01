# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api_common.models import BaseEntity

from ..charts.models import Chart
from ..datasets.models import Dataset
from ..models.models import InferenceModel
from .enums import WorkloadStatus, WorkloadType


class Workload(BaseEntity):
    __tablename__ = "workloads"

    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[WorkloadType] = mapped_column(String, nullable=False)
    status: Mapped[WorkloadStatus] = mapped_column(String, nullable=False)
    chart_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("charts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chart: Mapped[Chart] = relationship(lazy="joined")
    model_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inference_models.id", ondelete="SET NULL"), index=True, nullable=True
    )
    model: Mapped["InferenceModel | None"] = relationship(lazy="joined")
    dataset_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    dataset: Mapped["Dataset | None"] = relationship(lazy="joined")
    manifest: Mapped[str] = mapped_column(String, nullable=False, default="")
