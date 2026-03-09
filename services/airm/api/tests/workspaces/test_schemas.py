# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from app.workspaces.schemas import DevelopmentWorkspaceRequest


def test_development_workspace_request_defaults():
    """Test that DevelopmentWorkspaceRequest has expected defaults."""
    request = DevelopmentWorkspaceRequest()

    assert request.image is None
    assert request.image_pull_secrets == []
    assert request.gpus == 1
    assert request.memory_per_gpu == 128
    assert request.cpu_per_gpu == 4


def test_development_workspace_request_with_image_pull_secrets():
    """Test that image_pull_secrets are properly set when provided."""
    request = DevelopmentWorkspaceRequest(image_pull_secrets=["secret1", "secret2"])

    assert request.image_pull_secrets == ["secret1", "secret2"]


def test_development_workspace_request_empty_image_pull_secrets():
    """Test that empty image_pull_secrets list is handled correctly."""
    request = DevelopmentWorkspaceRequest(image_pull_secrets=[])

    assert request.image_pull_secrets == []


def test_development_workspace_request_with_snake_case_alias():
    """Test that snake_case field name (image_pull_secrets) works."""
    # Test that the model accepts snake_case field name (as sent by UI)
    request = DevelopmentWorkspaceRequest.model_validate({"image_pull_secrets": ["secret1", "secret2"], "gpus": 2})

    assert request.image_pull_secrets == ["secret1", "secret2"]
    assert request.gpus == 2


def test_development_workspace_request_camel_and_snake_case():
    """Test that snake_case field works in different contexts."""
    # When using model_validate with snake_case (UI format)
    request_from_ui = DevelopmentWorkspaceRequest.model_validate(
        {"image_pull_secrets": ["ui-secret"], "memory_per_gpu": 64.0}
    )
    assert request_from_ui.image_pull_secrets == ["ui-secret"]

    # When using direct instantiation with snake_case
    request_from_api = DevelopmentWorkspaceRequest(image_pull_secrets=["api-secret"], memory_per_gpu=64.0)
    assert request_from_api.image_pull_secrets == ["api-secret"]
