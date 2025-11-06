# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest

from app.namespaces.models import Namespace
from app.namespaces.repository import (
    create_namespace,
    delete_namespace,
    get_namespace_by_project_and_cluster,
    get_namespaces_by_organisation,
    update_namespace_status,
)
from tests import factory


@pytest.mark.asyncio
async def test_create_namespace_for_project(db_session):
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
async def test_get_namespace_by_project_and_cluster_found(db_session):
    env = await factory.create_basic_test_environment(db_session)

    namespace = Namespace(
        name="test-namespace",
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )
    await create_namespace(db_session, namespace)

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)

    assert found_namespace is not None
    assert found_namespace.name == "test-namespace"
    assert found_namespace.cluster_id == env.cluster.id
    assert found_namespace.project_id == env.project.id


@pytest.mark.asyncio
async def test_get_namespace_by_project_and_cluster_different_cluster(db_session):
    env = await factory.create_basic_test_environment(db_session)

    namespace = Namespace(
        name="test-namespace",
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )
    await create_namespace(db_session, namespace)

    other_cluster = await factory.create_cluster(db_session, env.organization, name="Other Cluster")

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, other_cluster.id)

    assert found_namespace is None


@pytest.mark.asyncio
async def test_update_namespace_status(db_session):
    env = await factory.create_basic_test_environment(db_session)

    namespace = Namespace(
        name="test-namespace",
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Pending",
        status_reason="creating",
        created_by="creator",
        updated_by="creator",
    )
    created_namespace = await create_namespace(db_session, namespace)

    updated_namespace = await update_namespace_status(
        db_session, created_namespace, "Active", "namespace is ready", "system"
    )

    assert updated_namespace.status == "Active"
    assert updated_namespace.status_reason == "namespace is ready"
    assert updated_namespace.id == created_namespace.id
    assert updated_namespace.name == "test-namespace"


@pytest.mark.asyncio
async def test_get_namespaces_by_organisation(db_session):
    env = await factory.create_basic_test_environment(db_session)

    ns1 = Namespace(
        name="org-ns1",
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )
    ns2 = Namespace(
        name="org-ns2",
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )
    await create_namespace(db_session, ns1)
    await create_namespace(db_session, ns2)

    result = await get_namespaces_by_organisation(db_session, env.organization.id)
    names = {ns.name for ns in result}
    assert "org-ns1" in names
    assert "org-ns2" in names
    assert all(ns.project_id == env.project.id for ns in result)


@pytest.mark.asyncio
async def test_delete_namespace(db_session):
    env = await factory.create_basic_test_environment(db_session)

    namespace = Namespace(
        name="test-namespace",
        cluster_id=env.cluster.id,
        project_id=env.project.id,
        status="Active",
        status_reason=None,
        created_by="creator",
        updated_by="creator",
    )
    created_namespace = await create_namespace(db_session, namespace)

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)
    assert found_namespace is not None

    await delete_namespace(db_session, created_namespace)

    found_namespace = await get_namespace_by_project_and_cluster(db_session, env.project.id, env.cluster.id)
    assert found_namespace is None
