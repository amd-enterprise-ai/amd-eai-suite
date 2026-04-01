# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.namespaces.models import Namespace
from app.namespaces.repository import (
    create_namespace,
    delete_namespace,
    get_namespace_by_name_and_cluster,
    get_namespace_by_project_and_cluster,
    update_namespace_status,
)
from tests import factory  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_create_namespace_for_project(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)
    namespace = Namespace(
        name="test-namespace",
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Active",
        status_reason=None,
        created_by="test_creator",
        updated_by="test_creator",
    )
    created = await create_namespace(db_session, namespace)
    assert created.id is not None
    assert created.name == "test-namespace"
    assert created.cluster_id == env.cluster.id
    assert created.project_id == env.project.id
    assert created.status == "Active"
    assert created.status_reason is None


@pytest.mark.asyncio
async def test_get_namespace_by_project_and_cluster_found(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    await factory.create_namespace(db_session, env.cluster, env.project, name="test-namespace", creator="creator")

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)

    assert found_namespace is not None
    assert found_namespace.name == "test-namespace"
    assert found_namespace.cluster_id == env.cluster.id
    assert found_namespace.project_id == env.project.id


@pytest.mark.asyncio
async def test_get_namespace_by_project_and_cluster_different_cluster(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    await factory.create_namespace(db_session, env.cluster, env.project, name="test-namespace", creator="creator")

    other_cluster = await factory.create_cluster(db_session, name="Other Cluster")

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, other_cluster.id)

    assert found_namespace is None


@pytest.mark.asyncio
async def test_update_namespace_status(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    created_namespace = await factory.create_namespace(
        db_session,
        env.cluster,
        env.project,
        name="test-namespace",
        status="Pending",
        status_reason="creating",
        creator="creator",
    )

    updated_namespace = await update_namespace_status(
        db_session, created_namespace, "Active", "namespace is ready", "system"
    )

    assert updated_namespace.status == "Active"
    assert updated_namespace.status_reason == "namespace is ready"
    assert updated_namespace.id == created_namespace.id
    assert updated_namespace.name == "test-namespace"


@pytest.mark.asyncio
async def test_delete_namespace(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    created_namespace = await factory.create_namespace(
        db_session, env.cluster, env.project, name="test-namespace", creator="creator"
    )

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)
    assert found_namespace is not None

    await delete_namespace(db_session, created_namespace)

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)
    assert found_namespace is None


@pytest.mark.asyncio
async def test_get_namespace_by_name_and_cluster_found(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    created_namespace = await factory.create_namespace(
        db_session, env.cluster, env.project, name="test-namespace", creator="creator"
    )

    found_namespace = await get_namespace_by_name_and_cluster(db_session, env.cluster.id, "test-namespace")
    assert found_namespace is not None
    assert found_namespace.id == created_namespace.id
    assert found_namespace.name == "test-namespace"
    assert found_namespace.cluster_id == env.cluster.id


@pytest.mark.asyncio
async def test_get_namespace_by_name_and_cluster_not_found(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    found_namespace = await get_namespace_by_name_and_cluster(db_session, env.cluster.id, "nonexistent-namespace")
    assert found_namespace is None


@pytest.mark.asyncio
async def test_get_namespace_by_name_and_cluster_unmanaged(db_session: AsyncSession) -> None:
    env = await factory.create_basic_test_environment(db_session)

    created_namespace = await factory.create_namespace(
        db_session,
        env.cluster,
        project=None,
        name="unmanaged-namespace",
        status_reason="Unmanaged namespace",
        creator="system",
    )

    found_namespace = await get_namespace_by_name_and_cluster(db_session, env.cluster.id, "unmanaged-namespace")
    assert found_namespace is not None
    assert found_namespace.id == created_namespace.id
    assert found_namespace.project_id is None
