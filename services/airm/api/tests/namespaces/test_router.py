# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import app  # type: ignore
from app.namespaces.schemas import ClusterNamespaces, ClustersWithNamespaces, NamespaceResponse
from app.organizations.models import Organization
from app.utilities.database import get_session
from app.utilities.security import ensure_platform_administrator, get_user_organization


@pytest.mark.asyncio
@patch(
    "app.namespaces.router.get_namespaces_by_cluster_for_organization",
    return_value=ClustersWithNamespaces(
        clusters_namespaces=[
            ClusterNamespaces(
                cluster_id="11111111-1111-1111-1111-111111111111",
                namespaces=[
                    NamespaceResponse(
                        id=uuid4(),
                        name="ns1",
                        cluster_id=uuid4(),
                        project_id=uuid4(),
                        status="Active",
                        status_reason=None,
                        created_by="creator",
                        updated_by="creator",
                        created_at="2025-01-01T12:00:00Z",
                        updated_at="2025-01-01T12:00:00Z",
                    ),
                    NamespaceResponse(
                        id=uuid4(),
                        name="ns2",
                        cluster_id=uuid4(),
                        project_id=uuid4(),
                        status="Active",
                        status_reason=None,
                        created_by="creator",
                        updated_by="creator",
                        created_at="2025-01-01T12:00:00Z",
                        updated_at="2025-01-01T12:00:00Z",
                    ),
                ],
            )
        ]
    ),
)
async def test_get_namespaces_success(mock_service):
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_get_user_organization = MagicMock()
    mock_get_user_organization.return_value = Organization(
        id="org-id", name="Organization1", keycloak_organization_id="123"
    )
    app.dependency_overrides[get_user_organization] = lambda: mock_get_user_organization()
    app.dependency_overrides[ensure_platform_administrator] = lambda: MagicMock()

    with TestClient(app) as client:
        response = client.get("/v1/namespaces")

    assert response.status_code == 200
    response_json = response.json()
    assert "clusters_namespaces" in response_json
    clusters = response_json["clusters_namespaces"]
    assert isinstance(clusters, list)
    assert clusters[0]["cluster_id"] == "11111111-1111-1111-1111-111111111111"
    ns_names = {ns["name"] for ns in clusters[0]["namespaces"]}
    assert ns_names == {"ns1", "ns2"}

    app.dependency_overrides = {}
