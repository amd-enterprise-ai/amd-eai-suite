# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from app.projects.enums import GpuPreemptionPolicy
from app.projects.schemas import GpuPreemptionConfig
from app.projects.utils import flatten_gpu_preemption


def test_gpu_preemption_config_defaults():
    config = GpuPreemptionConfig()
    assert config.enabled is False
    assert config.threshold is None
    assert config.grace_period is None
    assert config.policy is None


def test_gpu_preemption_config_full():
    config = GpuPreemptionConfig(enabled=True, threshold=80, grace_period=900, policy=GpuPreemptionPolicy.ON_PRESSURE)
    assert config.enabled is True
    assert config.threshold == 80
    assert config.grace_period == 900
    assert config.policy == GpuPreemptionPolicy.ON_PRESSURE


def test_gpu_preemption_config_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GpuPreemptionConfig(enabled=True, threshhold=80)


def test_gpu_preemption_config_threshold_range():
    with pytest.raises(ValidationError):
        GpuPreemptionConfig(threshold=-1)
    with pytest.raises(ValidationError):
        GpuPreemptionConfig(threshold=101)


def test_gpu_preemption_config_grace_period_minimum():
    with pytest.raises(ValidationError):
        GpuPreemptionConfig(grace_period=0)
    with pytest.raises(ValidationError):
        GpuPreemptionConfig(grace_period=899)
    GpuPreemptionConfig(grace_period=900)


def test_gpu_preemption_config_grace_period_multiple_of_sixty_seconds():
    with pytest.raises(ValidationError):
        GpuPreemptionConfig(grace_period=901)
    GpuPreemptionConfig(grace_period=960)


def test_flatten_gpu_preemption():
    config = GpuPreemptionConfig(enabled=True, threshold=75, grace_period=1800, policy=GpuPreemptionPolicy.ALWAYS)
    assert flatten_gpu_preemption(config) == {
        "gpu_preemption_enabled": True,
        "gpu_preemption_threshold": 75,
        "gpu_preemption_grace_period": 1800,
        "gpu_preemption_policy": GpuPreemptionPolicy.ALWAYS,
    }
