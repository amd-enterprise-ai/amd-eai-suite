# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import uuid4

from app.aims.schemas import AIMDeployRequest, AIMResponse


def test_aim_base_validation():
    """Test AIMBase schema validation."""
    data = {
        "id": str(uuid4()),
        "image_reference": "docker.io/amdenterpriseai/test-model:v1.0",
        "labels": {
            "com.amd.aim.model.canonicalName": "test/model",
            "com.amd.aim.hfToken.required": "False",
            "org.opencontainers.image.description": "Test model",
        },
        "status": "Ready",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
        "workload": None,
    }

    aim = AIMResponse.model_validate(data)
    assert aim.image_reference == "docker.io/amdenterpriseai/test-model:v1.0"
    assert aim.status == "Ready"
    # Computed fields from image_reference
    assert aim.image_name == "test-model"
    assert aim.image_tag == "v1.0"


def test_aim_response_validation():
    """Test AIMResponse schema validation."""
    data = {
        "id": str(uuid4()),
        "image_reference": "docker.io/amdenterpriseai/response-model:v2.0",
        "labels": {
            "com.amd.aim.model.canonicalName": "test/model",
            "com.amd.aim.hfToken.required": "True",
            "org.opencontainers.image.description": "Response model",
        },
        "status": "Ready",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
        "workload": None,
    }

    response = AIMResponse.model_validate(data)
    assert response.status == "Ready"
    assert response.workload is None
    # Computed fields
    assert response.image_name == "response-model"
    assert response.image_tag == "v2.0"


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
            "name": "test-project",
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
        "image_reference": "docker.io/amdenterpriseai/test-model:v1",
        "labels": {"com.amd.aim.model.canonicalName": "test/model"},
        "status": "Ready",
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
    request = AIMDeployRequest()
    assert request is not None

    request = AIMDeployRequest.model_validate({})
    assert request is not None


def test_aim_deploy_request_with_metric():
    """Test AIMDeployRequest schema with metric field."""
    request = AIMDeployRequest(metric="latency")
    assert request.metric == "latency"

    request = AIMDeployRequest(metric="throughput")
    assert request.metric == "throughput"

    request = AIMDeployRequest()
    assert request.metric is None


def test_aim_deploy_request_with_all_fields():
    """Test AIMDeployRequest schema with all optional fields."""
    request = AIMDeployRequest(
        cache_model=False,
        replicas=4,
        image_pull_secrets=["secret1", "secret2"],
        hf_token="hf_test_token",
        metric="throughput",
    )
    assert request.cache_model is False
    assert request.replicas == 4
    assert request.image_pull_secrets == ["secret1", "secret2"]
    assert request.hf_token == "hf_test_token"
    assert request.metric == "throughput"


def test_aim_response_recommended_deployments():
    """Test that AIMResponse extracts recommendedDeployments from labels."""
    data = {
        "id": str(uuid4()),
        "image_reference": "docker.io/amdenterpriseai/test-model:v1.0",
        "labels": {
            "com.amd.aim.model.canonicalName": "test/model",
            "com.amd.aim.model.recommendedDeployments": "[{'gpuModel': 'MI300X', 'gpuCount': 1, 'precision': 'fp8', 'metric': 'latency'}, {'gpuModel': 'MI300X', 'gpuCount': 1, 'precision': 'fp8', 'metric': 'throughput'}]",
        },
        "status": "Ready",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
        "workload": None,
    }

    response = AIMResponse.model_validate(data)
    assert len(response.recommended_deployments) == 2
    assert response.recommended_deployments[0]["metric"] == "latency"
    assert response.recommended_deployments[1]["metric"] == "throughput"


def test_aim_response_recommended_deployments_single():
    """Test parsing a single recommendedDeployment (not in array)."""
    data = {
        "id": str(uuid4()),
        "image_reference": "docker.io/amdenterpriseai/test-model:v1.0",
        "labels": {
            "com.amd.aim.model.canonicalName": "test/model",
            "com.amd.aim.model.recommendedDeployments": "{'gpuModel': 'MI300X', 'gpuCount': 1, 'precision': 'fp8', 'metric': 'latency', 'description': 'Optimized for latency'}",
        },
        "status": "Ready",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
        "workload": None,
    }

    response = AIMResponse.model_validate(data)
    assert len(response.recommended_deployments) == 1
    assert response.recommended_deployments[0]["metric"] == "latency"


def test_aim_response_recommended_deployments_empty():
    """Test that missing recommendedDeployments returns empty list."""
    data = {
        "id": str(uuid4()),
        "image_reference": "docker.io/amdenterpriseai/test-model:v1.0",
        "labels": {},
        "status": "Ready",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
        "workload": None,
    }

    response = AIMResponse.model_validate(data)
    assert response.recommended_deployments == []


def test_aim_base_image_name_tag_computed():
    """Test that image_name and image_tag are computed from image_reference."""
    # Full registry path
    data = {
        "id": str(uuid4()),
        "image_reference": "ghcr.io/amdenterpriseai/mixtral-8x22b:v1.2.3",
        "labels": {},
        "status": "Ready",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": "user@example.com",
        "updated_by": "user@example.com",
        "workload": None,
    }
    aim = AIMResponse.model_validate(data)
    assert aim.image_name == "mixtral-8x22b"
    assert aim.image_tag == "v1.2.3"

    # Simple name:tag format
    data["image_reference"] = "my-model:latest"
    aim = AIMResponse.model_validate(data)
    assert aim.image_name == "my-model"
    assert aim.image_tag == "latest"

    # No tag (should default to latest)
    data["image_reference"] = "registry.example.com/models/llama"
    aim = AIMResponse.model_validate(data)
    assert aim.image_name == "llama"
    assert aim.image_tag == "latest"
