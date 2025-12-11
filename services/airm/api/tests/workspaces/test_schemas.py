# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from app.workspaces.schemas import DevelopmentWorkspaceRequest


def test_development_workspace_request_defaults():
    """Test that DevelopmentWorkspaceRequest has expected defaults."""
    request = DevelopmentWorkspaceRequest()

    assert request.image is None
    assert request.imagePullSecrets == []
    assert request.gpus == 1
    assert request.memory_per_gpu == 128
    assert request.cpu_per_gpu == 4
