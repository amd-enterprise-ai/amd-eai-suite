# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs repository functions."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.aims.enums import AIMServiceStatus, OptimizationMetric
from app.aims.repository import (
    create_aim_service,
    get_aim_service_by_id,
    list_aim_services_history,
    update_aim_service_status,
)
from tests.factory import create_aim_service_db


@pytest.mark.asyncio
async def test_create_aim_service(db_session: AsyncSession) -> None:
    """Test repository create function."""
    svc = await create_aim_service(
        session=db_session,
        namespace="my-ns",
        model="llama3-8b",
        status=AIMServiceStatus.PENDING,
        metric=OptimizationMetric.THROUGHPUT,
        submitter="user@test.com",
    )
    await db_session.flush()

    assert svc.namespace == "my-ns"
    assert svc.status == AIMServiceStatus.PENDING
    assert svc.metric == OptimizationMetric.THROUGHPUT


@pytest.mark.asyncio
async def test_create_aim_service_with_explicit_id(db_session: AsyncSession) -> None:
    """Test creating with explicit ID."""
    explicit_id = uuid4()
    svc = await create_aim_service(
        session=db_session,
        namespace="ns",
        model="llama3-8b",
        status=AIMServiceStatus.RUNNING,
        metric=None,
        submitter="test",
        id=explicit_id,
    )
    await db_session.flush()
    assert svc.id == explicit_id


@pytest.mark.asyncio
async def test_get_aim_service_by_id(db_session: AsyncSession) -> None:
    """Test retrieving by ID."""
    svc = await create_aim_service_db(db_session)
    result = await get_aim_service_by_id(db_session, svc.id)
    assert result is not None
    assert result.id == svc.id


@pytest.mark.asyncio
async def test_get_aim_service_by_id_with_namespace(db_session: AsyncSession) -> None:
    """Test retrieving with namespace filter."""
    svc = await create_aim_service_db(db_session, namespace="correct-ns")

    assert await get_aim_service_by_id(db_session, svc.id, namespace="correct-ns") is not None
    assert await get_aim_service_by_id(db_session, svc.id, namespace="wrong-ns") is None


@pytest.mark.asyncio
async def test_get_aim_service_by_id_not_found(db_session: AsyncSession) -> None:
    """Test not found returns None."""
    assert await get_aim_service_by_id(db_session, uuid4()) is None


@pytest.mark.asyncio
async def test_list_aim_services_history(db_session: AsyncSession) -> None:
    """Test listing services."""
    await create_aim_service_db(db_session, namespace="ns1")
    await create_aim_service_db(db_session, namespace="ns1")
    await create_aim_service_db(db_session, namespace="ns2")

    all_svcs = await list_aim_services_history(db_session)
    assert len(all_svcs) == 3

    ns1_svcs = await list_aim_services_history(db_session, namespace="ns1")
    assert len(ns1_svcs) == 2


@pytest.mark.asyncio
async def test_list_aim_services_history_by_status(db_session: AsyncSession) -> None:
    """Test filtering by status."""
    await create_aim_service_db(db_session, status=AIMServiceStatus.RUNNING)
    await create_aim_service_db(db_session, status=AIMServiceStatus.PENDING)

    running = await list_aim_services_history(db_session, status=AIMServiceStatus.RUNNING)
    assert len(running) == 1


@pytest.mark.asyncio
async def test_list_aim_services_history_includes_deleted(db_session: AsyncSession) -> None:
    """Test that DELETED services are returned from repository (filtering at service layer)."""
    await create_aim_service_db(db_session, namespace="ns1", status=AIMServiceStatus.RUNNING)
    await create_aim_service_db(db_session, namespace="ns1", status=AIMServiceStatus.FAILED)
    await create_aim_service_db(db_session, namespace="ns1", status=AIMServiceStatus.DELETED)
    await create_aim_service_db(db_session, namespace="ns1", status=AIMServiceStatus.DELETED)

    # Repository returns all services including DELETED (filtering happens at service layer)
    all_svcs = await list_aim_services_history(db_session, namespace="ns1")
    assert len(all_svcs) == 4


@pytest.mark.asyncio
async def test_list_aim_services_history_can_query_deleted_explicitly(db_session: AsyncSession) -> None:
    """Test that DELETED services can be queried explicitly."""
    await create_aim_service_db(db_session, status=AIMServiceStatus.RUNNING)
    await create_aim_service_db(db_session, status=AIMServiceStatus.DELETED)
    await create_aim_service_db(db_session, status=AIMServiceStatus.DELETED)

    # Explicitly requesting DELETED status should return them
    deleted = await list_aim_services_history(db_session, status=AIMServiceStatus.DELETED)
    assert len(deleted) == 2
    assert all(svc.status == AIMServiceStatus.DELETED for svc in deleted)


@pytest.mark.asyncio
async def test_update_aim_service_status(db_session: AsyncSession) -> None:
    """Test status update."""
    svc = await create_aim_service_db(db_session, status=AIMServiceStatus.PENDING)
    updated = await update_aim_service_status(db_session, svc, AIMServiceStatus.RUNNING, "updater")

    assert updated.status == AIMServiceStatus.RUNNING
    assert updated.updated_by == "updater"
