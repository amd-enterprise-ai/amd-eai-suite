# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Fixtures for secrets tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_kube_api_client() -> MagicMock:
    """Create a mock Kubernetes API client with async methods."""
    mock_client = MagicMock()
    # Make core_v1 methods async
    mock_client.core_v1.list_namespaced_secret = AsyncMock()
    mock_client.core_v1.read_namespaced_secret = AsyncMock()
    mock_client.core_v1.create_namespaced_secret = AsyncMock()
    mock_client.core_v1.delete_namespaced_secret = AsyncMock()
    return mock_client
