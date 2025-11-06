# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import uuid4

from app.aims.schemas import AIMBase, AIMDeployRequest, AIMResponse


def test_aim_base_validation():
    """Test AIMBase schema validation."""
    data = {
        "id": str(uuid4()),
        "image_name": "test-model",
        "image_tag": "v1.0",
        "image": "docker.io/amdenterpriseai/test-model:v1.0",
        "labels": {"type": "inference"},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
    }

    aim = AIMBase.model_validate(data)
    assert aim.image_name == "test-model"
    assert aim.image_tag == "v1.0"
    assert aim.labels == {"type": "inference"}


def test_aim_response_validation():
    """Test AIMResponse schema validation."""
    data = {
        "id": str(uuid4()),
        "image_name": "response-model",
        "image_tag": "v2.0",
        "image": "docker.io/amdenterpriseai/response-model:v2.0",
        "labels": {"framework": "pytorch"},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
        "workload": None,
    }

    response = AIMResponse.model_validate(data)
    assert response.image_name == "response-model"
    assert response.image_tag == "v2.0"
    assert response.workload is None


def test_aim_response_with_workload():
    """Test AIMResponse schema with workload data."""

    aim_id = uuid4()
    now = datetime.now(UTC)

    workload_data = {
        "id": uuid4(),
        "display_name": "Test Workload",
        "name": "test-workload",
        "project": {
            "id": "789e0123-e89b-12d3-a456-426614174000",
            "name": "test-project",  # Valid kubernetes name pattern
            "description": "Test Description",
            "cluster_id": "012e3456-e89b-12d3-a456-426614174000",
            "status": "Ready",
            "created_at": now,
            "updated_at": now,
            "created_by": "test@example.com",
            "updated_by": "test@example.com",
        },
        "status": "Running",
        "type": "CUSTOM",
        "user_inputs": {},
        "output": None,
        "allocated_resources": None,
        "aim_id": aim_id,
        "created_at": now,
        "updated_at": now,
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }

    data = {
        "id": aim_id,
        "image_name": "test-model",
        "image_tag": "v1",
        "image": "docker.io/amdenterpriseai/test-model:v1",
        "labels": {},
        "workload": workload_data,
        "created_at": now,
        "updated_at": now,
        "created_by": "test@example.com",
        "updated_by": "test@example.com",
    }

    response = AIMResponse(**data)
    assert response.workload is not None
    assert response.workload.display_name == "Test Workload"


def test_aim_deploy_request_schema():
    """Test AIMDeployRequest schema creation."""
    # PLACEHOLDER (as it has no required fields currently)
    request = AIMDeployRequest()
    assert request is not None

    # Test from dict
    request = AIMDeployRequest.model_validate({})
    assert request is not None
