# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from app.workspaces.schemas import DevelopmentWorkspaceRequest


def test_development_workspace_request_defaults():
    """Test that DevelopmentWorkspaceRequest has expected defaults."""
    request = DevelopmentWorkspaceRequest()

    assert request.image == "rocm/pytorch:rocm6.4_ubuntu24.04_py3.12_pytorch_release_2.6.0"
    assert request.imagePullSecrets == []
    assert request.gpus == 1
    assert request.memory_per_gpu == 128
    assert request.cpu_per_gpu == 4
