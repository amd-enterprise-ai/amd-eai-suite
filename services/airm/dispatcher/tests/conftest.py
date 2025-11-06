# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import pytest


# Mock the startup event to prevent RabbitMQ connection attempts
@pytest.fixture(autouse=True, scope="session")
def mock_startup():
    with patch("app.startup_event") as mock_startup:
        yield mock_startup


@pytest.fixture(autouse=True, scope="session")
def mock_kubernetes_connections():
    with (
        patch("app.kubernetes.load_k8s_config"),
    ):
        yield
