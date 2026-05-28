# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from app.namespaces.utils import _build_namespace_manifest
from app.projects.enums import GpuPreemptionPolicy
from app.projects.schemas import GpuPreemptionConfig
from app.workloads.constants import KUEUE_MANAGED_LABEL, PROJECT_ID_LABEL


def test_build_namespace_manifest_no_preemption() -> None:
    """Without a preemption config the manifest has no annotations."""
    project_id = uuid4()
    manifest = _build_namespace_manifest("my-ns", project_id)

    assert manifest.metadata.name == "my-ns"
    assert manifest.metadata.labels[PROJECT_ID_LABEL] == str(project_id)
    assert manifest.metadata.labels[KUEUE_MANAGED_LABEL] == "true"
    assert manifest.metadata.annotations is None


def test_build_namespace_manifest_preemption_disabled() -> None:
    """A disabled preemption config produces no annotations."""
    manifest = _build_namespace_manifest("my-ns", uuid4(), GpuPreemptionConfig(enabled=False))
    assert manifest.metadata.annotations is None


def test_build_namespace_manifest_preemption_enabled_all_fields() -> None:
    """All four Kaiwo annotation keys are present with correct formatted values."""
    config = GpuPreemptionConfig(enabled=True, threshold=10, grace_period=1800, policy=GpuPreemptionPolicy.ON_PRESSURE)
    manifest = _build_namespace_manifest("my-ns", uuid4(), config)

    annotations = manifest.metadata.annotations
    assert annotations is not None
    assert annotations["kaiwo.silogen.ai/gpu-preemption.enabled"] == "true"
    assert annotations["kaiwo.silogen.ai/gpu-preemption.threshold"] == "10"
    assert annotations["kaiwo.silogen.ai/gpu-preemption.grace-period"] == "1800s"
    assert annotations["kaiwo.silogen.ai/gpu-preemption.policy"] == "OnPressure"


def test_build_namespace_manifest_preemption_enabled_partial_fields() -> None:
    """Only non-None optional fields appear in annotations."""
    config = GpuPreemptionConfig(enabled=True, threshold=None, grace_period=None, policy=None)
    manifest = _build_namespace_manifest("my-ns", uuid4(), config)

    annotations = manifest.metadata.annotations
    assert annotations is not None
    assert "kaiwo.silogen.ai/gpu-preemption.enabled" in annotations
    assert "kaiwo.silogen.ai/gpu-preemption.threshold" not in annotations
    assert "kaiwo.silogen.ai/gpu-preemption.grace-period" not in annotations
    assert "kaiwo.silogen.ai/gpu-preemption.policy" not in annotations


def test_build_namespace_manifest_grace_period_formatted_with_s_suffix() -> None:
    """grace_period (seconds) is formatted as a Go-compatible duration with an 's' suffix."""
    config = GpuPreemptionConfig(enabled=True, grace_period=2700)
    manifest = _build_namespace_manifest("my-ns", uuid4(), config)

    assert manifest.metadata.annotations["kaiwo.silogen.ai/gpu-preemption.grace-period"] == "2700s"
