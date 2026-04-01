# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AIMs database models."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.aims.enums import AIMServiceStatus, OptimizationMetric
from tests.factory import create_aim_service_db


async def test_aim_service_creation(db_session: AsyncSession) -> None:
    """Test AIMService model creation and field access."""
    svc = await create_aim_service_db(
        db_session,
        model="llama3-8b",
        status=AIMServiceStatus.RUNNING,
        metric=OptimizationMetric.LATENCY,
    )

    assert svc.id is not None
    assert svc.namespace == "test-namespace"
    assert svc.model == "llama3-8b"
    assert svc.status == AIMServiceStatus.RUNNING.value
    assert svc.metric == OptimizationMetric.LATENCY.value
    assert svc.created_at is not None
    assert svc.updated_at is not None


async def test_aim_service_without_metric(db_session: AsyncSession) -> None:
    """Test AIMService creation without metric."""
    svc = await create_aim_service_db(db_session, metric=None)
    assert svc.metric is None


async def test_aim_service_status_update(db_session: AsyncSession) -> None:
    """Test updating AIMService status."""
    svc = await create_aim_service_db(db_session, status=AIMServiceStatus.PENDING)
    assert svc.status == AIMServiceStatus.PENDING.value

    svc.status = AIMServiceStatus.RUNNING.value
    await db_session.flush()
    await db_session.refresh(svc)
    assert svc.status == AIMServiceStatus.RUNNING.value


async def test_multiple_aim_services_in_different_namespaces(db_session: AsyncSession) -> None:
    """Test creating AIMServices in different namespaces."""
    svc1 = await create_aim_service_db(db_session, namespace="ns-1")
    svc2 = await create_aim_service_db(db_session, namespace="ns-2")

    assert svc1.namespace != svc2.namespace
    assert svc1.id != svc2.id
