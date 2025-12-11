# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import NamespaceStatus, ProjectNamespaceCreateMessage, ProjectNamespaceStatusMessage
from app.clusters.models import Cluster
from app.namespaces.models import Namespace
from app.namespaces.schemas import ClustersWithNamespaces
from app.namespaces.service import (
    create_namespace_for_project,
    delete_namespace_in_cluster,
    get_namespaces_by_cluster_for_organization,
    update_project_namespace_status,
)
from app.projects.models import Project
from app.utilities.exceptions import NotFoundException


@pytest.mark.asyncio
@patch("app.namespaces.service.create_namespace")
async def test_create_namespace_for_project_success(mock_create_namespace):
    project = Project(
        id=uuid4(),
        name="test-project",
        cluster_id=uuid4(),
        organization_id=uuid4(),
        description="A test project",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    cluster_id = uuid4()
    user = "test_user@example.com"

    # Create mock message sender
    mock_message_sender = AsyncMock()

    namespace = await create_namespace_for_project(
        AsyncMock(spec=AsyncSession), project, cluster_id, user, mock_message_sender
    )

    assert namespace.project_id == project.id
    assert namespace.name == project.name
    assert namespace.cluster_id == cluster_id
    assert namespace.status == NamespaceStatus.PENDING
    assert namespace.status_reason == "creating"
    assert namespace.created_by == user
    assert namespace.updated_by == user

    mock_create_namespace.assert_awaited_once()
    mock_message_sender.enqueue.assert_awaited_once()
    args, kwargs = mock_message_sender.enqueue.call_args
    assert args[0] == project.cluster_id
    assert isinstance(args[1], ProjectNamespaceCreateMessage)
    assert args[1].message_type == "project_namespace_create"
    assert args[1].name == namespace.name


@pytest.mark.asyncio
@patch("app.namespaces.service.create_namespace")
async def test_create_namespace_for_project_db_error(mock_create_namespace):
    project = Project(
        id=uuid4(),
        name="test-project",
        cluster_id=uuid4(),
        organization_id=uuid4(),
        description="A test project",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )
    cluster_id = uuid4()
    user = "test_user@example.com"

    mock_create_namespace.side_effect = Exception("Database error")
    mock_message_sender = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await create_namespace_for_project(AsyncMock(spec=AsyncSession), project, cluster_id, user, mock_message_sender)

    assert "Database error" in str(exc_info.value)
    mock_create_namespace.assert_awaited_once()
    mock_message_sender.enqueue.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.projects.service.update_project_status_from_components")
@patch("app.namespaces.service.get_project_in_organization")
@patch("app.namespaces.service.get_namespace_by_project_and_cluster")
@patch("app.namespaces.service.update_namespace_status")
async def test_update_project_namespace_status_success(
    mock_update_namespace, mock_get_namespace, mock_get_project, mock_update_project_status
):
    session_mock = AsyncMock(spec=AsyncSession)

    cluster = Cluster(
        id=uuid4(),
        name="test-cluster",
        organization_id=uuid4(),
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    namespace = Namespace(
        id=uuid4(),
        name="test-namespace",
        cluster_id=cluster.id,
        project_id=uuid4(),
        status=NamespaceStatus.PENDING,
        status_reason="creating",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    message = ProjectNamespaceStatusMessage(
        message_type="project_namespace_status",
        project_id=namespace.project_id,
        status=NamespaceStatus.ACTIVE,
        status_reason="namespace is ready",
        updated_at=datetime.now(UTC),
    )

    # Create a mock project
    mock_project = Project(
        id=uuid4(),
        name="test-project",
        cluster_id=cluster.id,
        organization_id=cluster.organization_id,
        description="A test project",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_namespace.return_value = namespace
    mock_get_project.return_value = mock_project

    dummy_kc_admin = object()
    await update_project_namespace_status(dummy_kc_admin, session_mock, cluster, message)

    mock_get_namespace.assert_awaited_once_with(session_mock, message.project_id, cluster.id)
    mock_update_namespace.assert_awaited_once_with(
        session_mock, namespace, NamespaceStatus.ACTIVE, "namespace is ready", "system"
    )
    mock_get_project.assert_awaited_once_with(session_mock, cluster.organization_id, namespace.project_id)
    mock_update_project_status.assert_awaited_once_with(dummy_kc_admin, session_mock, mock_project)


@pytest.mark.asyncio
@patch("app.projects.service.update_project_status_from_components")
@patch("app.namespaces.service.get_project_in_organization")
@patch("app.namespaces.service.get_namespace_by_project_and_cluster")
@patch("app.namespaces.service.update_namespace_status")
async def test_update_project_namespace_status_namespace_not_found(
    mock_update_namespace, mock_get_namespace, mock_get_project, mock_update_project_status
):
    session_mock = AsyncMock(spec=AsyncSession)

    cluster = Cluster(
        id=uuid4(),
        name="test-cluster",
        organization_id=uuid4(),
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    message = ProjectNamespaceStatusMessage(
        message_type="project_namespace_status",
        project_id=uuid4(),
        status=NamespaceStatus.ACTIVE,
        status_reason="namespace is ready",
        updated_at=datetime.now(UTC),
    )

    dummy_kc_admin = object()
    mock_get_namespace.return_value = None

    with pytest.raises(NotFoundException) as exc_info:
        await update_project_namespace_status(dummy_kc_admin, session_mock, cluster, message)

    assert f"Namespace for project {message.project_id} not found in cluster {cluster.id}." in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.projects.service.update_project_status_from_components")
@patch("app.namespaces.service.get_project_in_organization")
@patch("app.namespaces.service.get_namespace_by_project_and_cluster")
@patch("app.namespaces.service.update_namespace_status")
async def test_update_project_namespace_status_project_not_found(
    mock_update_namespace, mock_get_namespace, mock_get_project, mock_update_project_status
):
    session_mock = AsyncMock(spec=AsyncSession)

    cluster = Cluster(
        id=uuid4(),
        name="test-cluster",
        organization_id=uuid4(),
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    namespace = Namespace(
        id=uuid4(),
        name="test-namespace",
        cluster_id=cluster.id,
        project_id=uuid4(),
        status=NamespaceStatus.PENDING,
        status_reason="creating",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    message = ProjectNamespaceStatusMessage(
        message_type="project_namespace_status",
        project_id=namespace.project_id,
        status=NamespaceStatus.ACTIVE,
        status_reason="namespace is ready",
        updated_at=datetime.now(UTC),
    )

    dummy_kc_admin = object()
    mock_get_namespace.return_value = namespace
    mock_get_project.return_value = None  # Project not found

    with pytest.raises(NotFoundException) as exc_info:
        await update_project_namespace_status(dummy_kc_admin, session_mock, cluster, message)

    assert f"Project {namespace.project_id} not found in organization {cluster.organization_id}." in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.namespaces.service.get_namespaces_by_organisation")
async def test_get_namespaces_by_cluster_for_organization(mock_get_namespaces_by_organisation):
    org_id = uuid4()
    cluster1_id = uuid4()
    cluster2_id = uuid4()
    project1_id = uuid4()
    project2_id = uuid4()

    org = MagicMock()
    org.id = org_id

    ns1 = Namespace(
        id=uuid4(),
        name="ns1",
        cluster_id=cluster1_id,
        project_id=project1_id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )
    ns2 = Namespace(
        id=uuid4(),
        name="ns2",
        cluster_id=cluster1_id,
        project_id=project1_id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )
    ns3 = Namespace(
        id=uuid4(),
        name="ns3",
        cluster_id=cluster2_id,
        project_id=project2_id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )

    mock_get_namespaces_by_organisation.return_value = [ns1, ns2, ns3]

    result = await get_namespaces_by_cluster_for_organization(AsyncMock(), org)

    assert isinstance(result, ClustersWithNamespaces)

    clusters = {c.cluster_id: c.namespaces for c in result.clusters_namespaces}
    assert set(clusters.keys()) == {cluster1_id, cluster2_id}

    ns_names_cluster1 = {ns.name for ns in clusters[cluster1_id]}
    ns_names_cluster2 = {ns.name for ns in clusters[cluster2_id]}
    assert ns_names_cluster1 == {"ns1", "ns2"}
    assert ns_names_cluster2 == {"ns3"}

    mock_get_namespaces_by_organisation.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.namespaces.service.get_namespace_by_project_and_cluster")
@patch("app.namespaces.service.update_namespace_status")
async def test_delete_namespace_in_cluster_success(mock_update_namespace_status, mock_get_namespace):
    session_mock = AsyncMock(spec=AsyncSession)

    project = Project(
        id=uuid4(),
        name="test-project",
        cluster_id=uuid4(),
        organization_id=uuid4(),
        description="A test project",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    namespace = Namespace(
        id=uuid4(),
        name="test-namespace",
        cluster_id=project.cluster_id,
        project_id=project.id,
        status=NamespaceStatus.ACTIVE,
        status_reason="namespace is ready",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_namespace.return_value = namespace
    updater = "test_user@example.com"
    mock_message_sender = AsyncMock()

    await delete_namespace_in_cluster(session_mock, project, updater, mock_message_sender)

    mock_get_namespace.assert_awaited_once_with(session_mock, project.id, project.cluster_id)
    mock_update_namespace_status.assert_awaited_once_with(
        session_mock, namespace, NamespaceStatus.TERMINATING, "Namespace is being deleted", updater
    )
    mock_message_sender.enqueue.assert_awaited_once()

    args, kwargs = mock_message_sender.enqueue.call_args
    assert args[0] == project.cluster_id
    assert args[1].message_type == "project_namespace_delete"
    assert args[1].name == project.name
    assert args[1].project_id == project.id


@pytest.mark.asyncio
@patch("app.namespaces.service.get_namespace_by_project_and_cluster")
@patch("app.namespaces.service.update_namespace_status")
async def test_delete_namespace_in_cluster_namespace_not_found(mock_update_namespace_status, mock_get_namespace):
    session_mock = AsyncMock(spec=AsyncSession)

    project = Project(
        id=uuid4(),
        name="test-project",
        cluster_id=uuid4(),
        organization_id=uuid4(),
        description="A test project",
        created_at=datetime(2023, 1, 1, tzinfo=UTC),
        updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    mock_get_namespace.return_value = None  # Namespace not found
    updater = "test_user@example.com"
    mock_message_sender = AsyncMock()

    with pytest.raises(NotFoundException) as exc_info:
        await delete_namespace_in_cluster(session_mock, project, updater, mock_message_sender)

    assert f"Namespace for project {project.id} not found in cluster {project.cluster_id}." in str(exc_info.value)
    mock_get_namespace.assert_awaited_once_with(session_mock, project.id, project.cluster_id)
    mock_update_namespace_status.assert_not_awaited()
    mock_message_sender.enqueue.assert_not_awaited()
