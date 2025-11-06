# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..aims.models import AIM
from ..charts.models import Chart
from ..datasets.models import Dataset
from ..models.models import InferenceModel
from ..workloads.models import Workload


class ManagedWorkload(Workload):
    # Many fields are nullable because of polymorphic inheritance: (generic) Workloads will not contain these fields
    project = relationship("Project")
    name: Mapped[str] = mapped_column(String, nullable=True)
    chart_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("charts.id", ondelete="CASCADE"), index=True, nullable=True
    )
    chart: Mapped[Chart | None] = relationship(lazy="joined")
    model_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inference_models.id", ondelete="CASCADE"), index=True, nullable=True
    )
    model: Mapped[InferenceModel | None] = relationship(lazy="joined")
    dataset_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    dataset: Mapped[Dataset | None] = relationship(lazy="joined")
    aim_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("aims.id", ondelete="SET NULL"), index=True, nullable=True
    )
    aim: Mapped[AIM | None] = relationship(lazy="joined")

    user_inputs: Mapped[dict] = mapped_column(JSONB, nullable=True)
    manifest: Mapped[str | None] = mapped_column(nullable=True)
    output: Mapped[dict] = mapped_column(JSONB, nullable=True)
    cluster_auth_group_id: Mapped[str | None] = mapped_column(String, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "managed",
        "polymorphic_on": "kind",
    }
