# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest


@pytest.fixture(scope="session")
def docker_setup():
    return ["up --build -d --wait"]


@pytest.fixture
def rabbitmq_service(docker_ip, docker_services):
    """Ensure that RabbitMQ service is up and responsive."""
    port = docker_services.port_for("rabbitmq", 5672)

    return docker_ip, port
