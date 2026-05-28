# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from ..projects.schemas import GpuPreemptionConfig
from ..utilities.messaging import KubernetesMetadata
from ..workloads.constants import KUEUE_MANAGED_LABEL, PROJECT_ID_LABEL
from .constants import (
    KAIWO_PREEMPTION_ENABLED,
    KAIWO_PREEMPTION_GRACE_PERIOD,
    KAIWO_PREEMPTION_POLICY,
    KAIWO_PREEMPTION_THRESHOLD,
)
from .messaging import NamespaceManifest


def _build_namespace_manifest(
    name: str, project_id: UUID, gpu_preemption: GpuPreemptionConfig | None = None
) -> NamespaceManifest:
    annotations = _build_preemption_annotations(gpu_preemption)
    return NamespaceManifest(
        metadata=KubernetesMetadata(
            name=name,
            labels={
                PROJECT_ID_LABEL: str(project_id),
                KUEUE_MANAGED_LABEL: "true",
            },
            annotations=annotations,
        )
    )


def _build_preemption_annotations(gpu_preemption: GpuPreemptionConfig | None) -> dict[str, str] | None:
    if not gpu_preemption or not gpu_preemption.enabled:
        return None

    annotations: dict[str, str] = {KAIWO_PREEMPTION_ENABLED: "true"}

    if gpu_preemption.threshold is not None:
        annotations[KAIWO_PREEMPTION_THRESHOLD] = str(gpu_preemption.threshold)
    if gpu_preemption.grace_period is not None:
        annotations[KAIWO_PREEMPTION_GRACE_PERIOD] = f"{gpu_preemption.grace_period}s"
    if gpu_preemption.policy is not None:
        annotations[KAIWO_PREEMPTION_POLICY] = gpu_preemption.policy.value

    return annotations


def namespace_failure_message_preemption_mismatch(observed: GpuPreemptionConfig) -> str:
    return (
        f"Preemption config on cluster does not match configured value.\n"
        f"Observed on cluster: enabled={observed.enabled}, threshold={observed.threshold}, "
        f"grace_period={observed.grace_period}, policy={observed.policy}"
    )
