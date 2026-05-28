# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs router endpoints using FastAPI TestClient with dependency overrides."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from api_common.exceptions import NotFoundException
from app import app  # type: ignore[attr-defined]
from app.metrics.schemas import MetricsScalar
from tests.dependency_overrides import (
    BASE_OVERRIDES,
    CLUSTER_AUTH_OVERRIDES,
    PROMETHEUS_OVERRIDES,
    SESSION_OVERRIDES,
    override_dependencies,
)
from tests.factory import make_aim_cluster_model, make_aim_cluster_service_template, make_aim_service_k8s


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.list_aims")
def test_list_aim_cluster_models(mock_list: MagicMock) -> None:
    """Test GET /v1/cluster/aims/models returns 200."""
    mock_list.return_value = [make_aim_cluster_model(as_response=True)]
    with TestClient(app) as client:
        response = client.get("/v1/cluster/aims/models")
    assert response.status_code == status.HTTP_200_OK
    assert "data" in response.json()


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.get_aim_by_resource_name")
def test_get_aim_cluster_model(mock_get: MagicMock) -> None:
    """Test GET /v1/cluster/aims/models/{resource_name} returns 200."""
    mock_get.return_value = make_aim_cluster_model(as_response=True)
    with TestClient(app) as client:
        response = client.get("/v1/cluster/aims/models/llama3-8b")
    assert response.status_code == status.HTTP_200_OK


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.get_aim_by_resource_name")
def test_get_aim_cluster_model_not_found(mock_get: MagicMock) -> None:
    """Test GET /v1/cluster/aims/models/{resource_name} returns 404."""
    mock_get.side_effect = NotFoundException("Not found")
    with TestClient(app) as client:
        response = client.get("/v1/cluster/aims/models/missing")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.list_aim_services")
def test_list_aim_services(mock_list: MagicMock) -> None:
    """Test GET /v1/namespaces/{ns}/aims/services returns 200."""
    mock_list.return_value = [make_aim_service_k8s(as_response=True)]
    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/aims/services")
    assert response.status_code == status.HTTP_200_OK
    assert "data" in response.json()


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
@patch("app.aims.router.deploy_aim")
def test_deploy_aim(mock_deploy: MagicMock) -> None:
    """Test POST /v1/namespaces/{ns}/aims/services returns 202."""
    mock_deploy.return_value = make_aim_service_k8s(as_response=True)
    with TestClient(app) as client:
        response = client.post(
            "/v1/namespaces/test-namespace/aims/services",
            json={"model": "docker.io/amd/llama3:8b"},
        )
    assert response.status_code == status.HTTP_202_ACCEPTED


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
@patch("app.aims.router.deploy_aim")
def test_deploy_aim_rejects_snake_case_field_names(mock_deploy: MagicMock) -> None:
    """API must reject snake_case field names with 422; only camelCase is accepted."""
    mock_deploy.return_value = make_aim_service_k8s(as_response=True)
    with TestClient(app) as client:
        snake_resp = client.post(
            "/v1/namespaces/test-ns/aims/services",
            json={
                "model": "llama3-8b",
                "hf_token": "secret-xyz",
                "image_pull_secrets": ["s1", "s2"],
                "allow_unoptimized": True,
                "min_replicas": 2,
                "max_replicas": 10,
                "auto_scaling": {"metrics": []},
            },
        )
        camel_resp = client.post(
            "/v1/namespaces/test-ns/aims/services",
            json={
                "model": "llama3-8b",
                "hfToken": "secret-xyz",
                "imagePullSecrets": ["s1", "s2"],
                "allowUnoptimized": True,
                "minReplicas": 2,
                "maxReplicas": 10,
                "autoScaling": {"metrics": []},
            },
        )

    assert snake_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert camel_resp.status_code == status.HTTP_202_ACCEPTED


@override_dependencies(CLUSTER_AUTH_OVERRIDES)
@patch("app.aims.router.undeploy_aim")
def test_undeploy_aim(mock_undeploy: MagicMock) -> None:
    """Test DELETE /v1/namespaces/{ns}/aims/services/{id} returns 204."""
    mock_undeploy.return_value = None
    with TestClient(app) as client:
        response = client.delete(f"/v1/namespaces/test-namespace/aims/services/{uuid4()}")
    assert response.status_code == status.HTTP_204_NO_CONTENT


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.get_aim_service")
def test_get_aim_service(mock_get: MagicMock) -> None:
    """Test GET /v1/namespaces/{ns}/aims/services/{id} returns 200."""
    mock_get.return_value = make_aim_service_k8s(as_response=True)
    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/aims/services/{uuid4()}")
    assert response.status_code == status.HTTP_200_OK


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.get_aim_service")
def test_get_aim_service_not_found(mock_get: MagicMock) -> None:
    """Test GET /v1/namespaces/{ns}/aims/services/{id} returns 404."""
    mock_get.side_effect = NotFoundException("Not found")
    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/aims/services/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@override_dependencies(SESSION_OVERRIDES)
@patch("app.aims.router.list_aim_services_history")
def test_list_aim_services_history(mock_list: MagicMock) -> None:
    """Test GET /v1/namespaces/{ns}/aims/services/history returns 200."""
    mock_list.return_value = []
    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/aims/services/history")
    assert response.status_code == status.HTTP_200_OK


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.update_aim_scaling_policy")
def test_patch_aim_service_scaling(mock_update: MagicMock) -> None:
    """Test PATCH /v1/namespaces/{ns}/aims/services/{id} with scaling returns 200."""
    mock_update.return_value = make_aim_service_k8s(min_replicas=2, max_replicas=10, as_response=True)
    with TestClient(app) as client:
        response = client.patch(
            f"/v1/namespaces/test-namespace/aims/services/{uuid4()}",
            json={"minReplicas": 2, "maxReplicas": 10, "autoScaling": {"metrics": []}},
        )
    assert response.status_code == status.HTTP_200_OK


@override_dependencies(BASE_OVERRIDES)
def test_patch_aim_service_no_fields() -> None:
    """Test PATCH with no fields returns 400."""
    with TestClient(app) as client:
        response = client.patch(f"/v1/namespaces/test-namespace/aims/services/{uuid4()}", json={})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.list_chattable_aim_services")
def test_list_chattable_aim_services(mock_list: MagicMock) -> None:
    """Test GET /v1/namespaces/{ns}/aims/services/chattable returns 200."""
    mock_list.return_value = []
    with TestClient(app) as client:
        response = client.get("/v1/namespaces/test-namespace/aims/services/chattable")
    assert response.status_code == status.HTTP_200_OK


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.list_aim_service_replicas")
def test_get_aim_service_replicas(mock_replicas: MagicMock) -> None:
    """Test GET /v1/namespaces/{ns}/aims/services/{id}/replicas returns 200."""
    mock_replicas.return_value = [
        {"metadata": {"name": "pod-1"}, "status": {"phase": "Running"}},
        {"metadata": {"name": "pod-2"}, "status": {"phase": "Pending"}},
    ]
    with TestClient(app) as client:
        response = client.get(f"/v1/namespaces/test-namespace/aims/services/{uuid4()}/replicas")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["data"]) == 2


@override_dependencies(PROMETHEUS_OVERRIDES)
@patch("app.aims.router.get_metric_by_workload_id")
def test_get_aim_metric_passes_pod_name_to_service(mock_metric: MagicMock) -> None:
    """podName query param is forwarded to the metrics service as pod_name."""
    mock_metric.return_value = MetricsScalar(data=42.0)
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    with TestClient(app) as client:
        response = client.get(
            f"/v1/namespaces/test-namespace/aims/services/{uuid4()}/metrics/total_tokens",
            params={"start": start.isoformat(), "end": end.isoformat(), "podName": "pod-abc123"},
        )
    assert response.status_code == status.HTTP_200_OK
    assert mock_metric.call_args.kwargs["pod_name"] == "pod-abc123"


@override_dependencies(BASE_OVERRIDES)
@patch("app.aims.router.list_aim_cluster_service_templates")
def test_list_aim_cluster_service_templates(mock_list: MagicMock) -> None:
    """Test GET /v1/cluster/aims/templates returns 200."""
    mock_list.return_value = [make_aim_cluster_service_template()]
    with TestClient(app) as client:
        response = client.get("/v1/cluster/aims/templates?aimResourceName=llama3-8b")
    assert response.status_code == status.HTTP_200_OK
