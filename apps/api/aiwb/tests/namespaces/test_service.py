# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for namespaces service layer."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.collections import SortDirection
from app.aims.crds import AIMServiceResource, AIMServiceSpec, AIMServiceStatusFields
from app.aims.enums import AIMServiceStatus
from app.dispatch.crds import K8sMetadata
from app.namespaces.crds import Namespace
from app.namespaces.service import (
    _process_aim_services_to_metrics,
    _process_workloads_to_metrics,
    get_chattable_resources,
    get_namespace_stats_counts,
    get_namespace_workload_metrics_paginated,
)
from app.namespaces.utils import AIM_TO_WORKLOAD_STATUS
from app.workloads.constants import WORKLOAD_ID_LABEL
from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.schemas import WorkloadResponse
from tests.factory import DEFAULT_TEST_MANIFEST, create_aim_service_db, create_workload, make_aim_service_k8s


# Tests for get_chattable_resources
@pytest.mark.asyncio
async def test_get_chattable_resources_returns_both_types(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test that get_chattable_resources returns both AIM services and workloads."""
    namespace = "test-namespace"

    mock_aim_services: list[Any] = []
    mock_workloads: list[Any] = []

    with (
        patch("app.namespaces.service.list_chattable_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.list_chattable_workloads", autospec=True) as mock_list_workloads,
    ):
        mock_list_aims.return_value = mock_aim_services
        mock_list_workloads.return_value = mock_workloads

        result = await get_chattable_resources(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
        )

        # Verify both services were called
        mock_list_aims.assert_called_once_with(mock_kube_client, namespace)
        mock_list_workloads.assert_called_once_with(db_session, namespace)

        # Verify response structure
        assert hasattr(result, "aim_services")
        assert hasattr(result, "workloads")
        assert result.aim_services == mock_aim_services
        assert result.workloads == mock_workloads


@pytest.mark.asyncio
async def test_get_chattable_resources_empty_results(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test get_chattable_resources with empty results from both sources."""
    namespace = "empty-namespace"

    with (
        patch("app.namespaces.service.list_chattable_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.list_chattable_workloads", autospec=True) as mock_list_workloads,
    ):
        mock_list_aims.return_value = []
        mock_list_workloads.return_value = []

        result = await get_chattable_resources(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
        )

        assert result.aim_services == []
        assert result.workloads == []


@pytest.mark.asyncio
async def test_get_chattable_resources_only_aim_services(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test get_chattable_resources with only AIM services available."""
    namespace = "test-namespace"
    mock_aim_services: list[Any] = []

    with (
        patch("app.namespaces.service.list_chattable_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.list_chattable_workloads", autospec=True) as mock_list_workloads,
    ):
        mock_list_aims.return_value = mock_aim_services
        mock_list_workloads.return_value = []

        result = await get_chattable_resources(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
        )

        assert len(result.aim_services) == 0
        assert len(result.workloads) == 0


@pytest.mark.asyncio
async def test_get_chattable_resources_only_workloads(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test get_chattable_resources with only workloads available."""
    namespace = "test-namespace"
    # Create mock workload responses (not DB models)
    mock_workloads = [
        MagicMock(spec=WorkloadResponse),
        MagicMock(spec=WorkloadResponse),
        MagicMock(spec=WorkloadResponse),
    ]

    with (
        patch("app.namespaces.service.list_chattable_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.list_chattable_workloads", autospec=True) as mock_list_workloads,
    ):
        mock_list_aims.return_value = []
        mock_list_workloads.return_value = mock_workloads

        result = await get_chattable_resources(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
        )

        assert len(result.aim_services) == 0
        assert len(result.workloads) == 3


# Tests for get_namespace_workload_metrics_paginated
@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_with_aim_services_and_workloads(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test get_namespace_workload_metrics_paginated with both AIM services and workloads."""
    # Create mock namespace
    namespace = MagicMock(spec=Namespace)
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create mock AIM service from K8s
    aim_service_id = uuid4()
    mock_aim_service = make_aim_service_k8s(
        namespace="test-namespace",
        workload_id=aim_service_id,
        status=AIMServiceStatus.RUNNING,
    )

    # Create real AIM service in DB
    mock_aim_db = await create_aim_service_db(
        db_session,
        id=aim_service_id,
        namespace="test-namespace",
        status=AIMServiceStatus.RUNNING,
        created_by="test-user",
    )

    # Create real workload in DB
    workload = await create_workload(
        db_session,
        name="test-workload",
        display_name="Test Workload",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        submitter="test-user-2",
    )

    # Mock GPU and VRAM data
    gpu_counts = {str(aim_service_id): 2, str(workload.id): 4}
    vram_usage = {str(aim_service_id): 16000.0, str(workload.id): 32000.0}

    with (
        patch("app.namespaces.service.list_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", autospec=True) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", autospec=True) as mock_vram,
    ):
        mock_list_aims.return_value = [mock_aim_service]
        mock_gpu.return_value = gpu_counts
        mock_vram.return_value = vram_usage

        result = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
        )

        # Verify service calls
        mock_list_aims.assert_called_once_with(
            mock_kube_client, namespace.name, status_filter=list(AIM_TO_WORKLOAD_STATUS.keys())
        )
        mock_gpu.assert_called_once()
        mock_vram.assert_called_once()

        # Verify response structure and pagination
        assert len(result.data) == 2
        assert result.total == 2
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 1

        # Verify AIM service metrics
        aim_metric = next(m for m in result.data if m.id == aim_service_id)
        assert aim_metric.name == mock_aim_service.metadata.name
        assert aim_metric.type == WorkloadType.INFERENCE
        assert aim_metric.status == WorkloadStatus.RUNNING
        assert aim_metric.gpu_count == 2
        assert aim_metric.vram == 16000.0
        assert aim_metric.created_by == "test-user"

        # Verify workload metrics
        workload_metric = next(m for m in result.data if m.id == workload.id)
        assert workload_metric.name == "test-workload"
        assert workload_metric.display_name == "Test Workload"
        assert workload_metric.type == WorkloadType.INFERENCE
        assert workload_metric.status == WorkloadStatus.RUNNING
        assert workload_metric.gpu_count == 4
        assert workload_metric.vram == 32000.0
        assert workload_metric.created_by == "test-user-2"


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_pagination(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test that get_namespace_workload_metrics_paginated correctly paginates results."""
    namespace = MagicMock(spec=Namespace)
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create 5 real workloads in database
    workloads = []
    for i in range(5):
        workload = await create_workload(
            db_session,
            name=f"workload-{i}",
            display_name=f"Workload {i}",
            namespace="test-namespace",
            workload_type=WorkloadType.INFERENCE,
            status=WorkloadStatus.RUNNING,
            submitter="test-user",
        )
        workloads.append(workload)

    with (
        patch("app.namespaces.service.list_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", autospec=True) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", autospec=True) as mock_vram,
    ):
        mock_list_aims.return_value = []
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        # Test first page with page_size=2
        result = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            page=1,
            page_size=2,
        )

        assert len(result.data) == 2
        assert result.total == 5
        assert result.page == 1
        assert result.page_size == 2
        assert result.total_pages == 3

        # Test second page
        result2 = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            page=2,
            page_size=2,
        )

        assert len(result2.data) == 2
        assert result2.page == 2

        # Test last page (partial)
        result3 = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            page=3,
            page_size=2,
        )

        assert len(result3.data) == 1
        assert result3.page == 3


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_empty_namespace(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test get_namespace_workload_metrics_paginated with empty namespace."""
    namespace = MagicMock(spec=Namespace)
    namespace.name = "empty-namespace"
    namespace.id = "empty-namespace-id"

    with (
        patch("app.namespaces.service.list_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", autospec=True) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", autospec=True) as mock_vram,
    ):
        mock_list_aims.return_value = []
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        result = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
        )

        # Verify empty results
        assert len(result.data) == 0
        assert result.total == 0
        assert result.page == 1
        assert result.total_pages == 1


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_filter_by_workload_type(
    mock_kube_client: MagicMock,
    mock_db_session: AsyncMock,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test get_namespace_workload_metrics_paginated filters by workload type."""
    namespace = MagicMock()
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create mock workloads of different types
    workload_inference = MagicMock()
    workload_inference.id = uuid4()
    workload_inference.name = "workload-inference"
    workload_inference.display_name = "Inference Workload"
    workload_inference.type = WorkloadType.INFERENCE
    workload_inference.status = WorkloadStatus.RUNNING
    workload_inference.manifest = DEFAULT_TEST_MANIFEST
    workload_inference.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    workload_inference.created_by = "test-user"

    workload_finetuning = MagicMock()
    workload_finetuning.id = uuid4()
    workload_finetuning.name = "workload-finetuning"
    workload_finetuning.display_name = "Fine-tuning Workload"
    workload_finetuning.type = WorkloadType.FINE_TUNING
    workload_finetuning.status = WorkloadStatus.RUNNING
    workload_finetuning.manifest = DEFAULT_TEST_MANIFEST
    workload_finetuning.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    workload_finetuning.created_by = "test-user"

    with (
        patch("app.namespaces.service.list_aim_services", new_callable=AsyncMock) as mock_list_aims,
        patch("app.namespaces.service.get_workloads", new_callable=AsyncMock) as mock_get_workloads,
        patch(
            "app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", new_callable=AsyncMock
        ) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", new_callable=AsyncMock) as mock_vram,
    ):
        # Return only fine-tuning workload when filtering by FINE_TUNING
        mock_list_aims.return_value = []  # AIM services are always INFERENCE, so not included
        mock_get_workloads.return_value = [workload_finetuning]
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        result = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            workload_types=[WorkloadType.FINE_TUNING],
        )

        # Both are fetched in parallel, AIM services returns empty
        mock_list_aims.assert_called_once()
        mock_get_workloads.assert_called_once()
        call_kwargs = mock_get_workloads.call_args.kwargs
        assert call_kwargs["workload_types"] == [WorkloadType.FINE_TUNING]

        # Only fine-tuning workload in result
        assert len(result.data) == 1
        assert result.data[0].type == WorkloadType.FINE_TUNING


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_filter_by_status(
    mock_kube_client: MagicMock,
    mock_db_session: AsyncMock,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test get_namespace_workload_metrics_paginated filters by status."""
    namespace = MagicMock()
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create mock AIM service with RUNNING status
    aim_service_id = uuid4()
    mock_aim_service = MagicMock()
    mock_aim_service.id = str(aim_service_id)
    mock_aim_service.metadata.name = "test-aim-service"
    mock_aim_service.spec.model = {"metadata": {"title": "Test Model"}}
    mock_aim_service.status.status = AIMServiceStatus.RUNNING

    # Create mock workload with PENDING status
    workload_pending = MagicMock()
    workload_pending.id = uuid4()
    workload_pending.name = "workload-pending"
    workload_pending.display_name = "Pending Workload"
    workload_pending.type = WorkloadType.INFERENCE
    workload_pending.status = WorkloadStatus.PENDING
    workload_pending.manifest = DEFAULT_TEST_MANIFEST
    workload_pending.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    workload_pending.created_by = "test-user"

    with (
        patch("app.namespaces.service.list_aim_services", new_callable=AsyncMock) as mock_list_aims,
        patch("app.namespaces.service.get_workloads", new_callable=AsyncMock) as mock_get_workloads,
        patch("app.namespaces.service.get_aim_service_by_id", new_callable=AsyncMock) as mock_get_aim_db,
        patch(
            "app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", new_callable=AsyncMock
        ) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", new_callable=AsyncMock) as mock_vram,
    ):
        mock_list_aims.return_value = [mock_aim_service]
        mock_get_workloads.return_value = []  # No RUNNING workloads
        mock_get_aim_db.return_value = None
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        # Filter for RUNNING status only
        result = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            status_filter=[WorkloadStatus.RUNNING],
        )

        # Should pass status_filter to get_workloads
        mock_get_workloads.assert_called_once()
        call_kwargs = mock_get_workloads.call_args.kwargs
        assert call_kwargs["status_filter"] == [WorkloadStatus.RUNNING]

        # Only the AIM service (RUNNING) should be in results
        assert len(result.data) == 1
        assert result.data[0].status == WorkloadStatus.RUNNING


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_filter_by_type_and_status(
    mock_kube_client: MagicMock,
    mock_db_session: AsyncMock,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test get_namespace_workload_metrics_paginated filters by both type and status."""
    namespace = MagicMock()
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create mock AIM service (INFERENCE, RUNNING)
    aim_service_id = uuid4()
    mock_aim_service = MagicMock()
    mock_aim_service.id = str(aim_service_id)
    mock_aim_service.metadata.name = "test-aim-service"
    mock_aim_service.spec.model = {"metadata": {"title": "Test Model"}}
    mock_aim_service.status.status = AIMServiceStatus.RUNNING

    # Create mock INFERENCE workload (RUNNING)
    workload_inference = MagicMock()
    workload_inference.id = uuid4()
    workload_inference.name = "workload-inference"
    workload_inference.display_name = "Inference Workload"
    workload_inference.type = WorkloadType.INFERENCE
    workload_inference.status = WorkloadStatus.RUNNING
    workload_inference.manifest = DEFAULT_TEST_MANIFEST
    workload_inference.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    workload_inference.created_by = "test-user"

    with (
        patch("app.namespaces.service.list_aim_services", new_callable=AsyncMock) as mock_list_aims,
        patch("app.namespaces.service.get_workloads", new_callable=AsyncMock) as mock_get_workloads,
        patch("app.namespaces.service.get_aim_service_by_id", new_callable=AsyncMock) as mock_get_aim_db,
        patch(
            "app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", new_callable=AsyncMock
        ) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", new_callable=AsyncMock) as mock_vram,
    ):
        mock_list_aims.return_value = [mock_aim_service]
        mock_get_workloads.return_value = [workload_inference]
        mock_get_aim_db.return_value = None
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        # Filter for INFERENCE type and RUNNING status
        result = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            workload_types=[WorkloadType.INFERENCE],
            status_filter=[WorkloadStatus.RUNNING],
        )

        # Verify correct calls
        mock_list_aims.assert_called_once()  # Should include AIM services (INFERENCE)
        mock_get_workloads.assert_called_once()
        call_kwargs = mock_get_workloads.call_args.kwargs
        assert call_kwargs["workload_types"] == [WorkloadType.INFERENCE]
        assert call_kwargs["status_filter"] == [WorkloadStatus.RUNNING]

        # Both RUNNING resources should be in results
        assert len(result.data) == 2
        assert all(m.status == WorkloadStatus.RUNNING for m in result.data)
        assert all(m.type == WorkloadType.INFERENCE for m in result.data)


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_sorting(
    mock_kube_client: MagicMock,
    mock_db_session: AsyncMock,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test that get_namespace_workload_metrics_paginated sorts results before pagination."""
    namespace = MagicMock()
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create workloads with different created_at dates
    workload_old = MagicMock()
    workload_old.id = uuid4()
    workload_old.name = "workload-old"
    workload_old.display_name = "Old Workload"
    workload_old.type = WorkloadType.INFERENCE
    workload_old.status = WorkloadStatus.RUNNING
    workload_old.manifest = DEFAULT_TEST_MANIFEST
    workload_old.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    workload_old.created_by = "test-user"

    workload_new = MagicMock()
    workload_new.id = uuid4()
    workload_new.name = "workload-new"
    workload_new.display_name = "New Workload"
    workload_new.type = WorkloadType.INFERENCE
    workload_new.status = WorkloadStatus.RUNNING
    workload_new.manifest = DEFAULT_TEST_MANIFEST
    workload_new.created_at = datetime(2025, 1, 10, tzinfo=UTC)
    workload_new.created_by = "test-user"

    workload_mid = MagicMock()
    workload_mid.id = uuid4()
    workload_mid.name = "workload-mid"
    workload_mid.display_name = "Mid Workload"
    workload_mid.type = WorkloadType.INFERENCE
    workload_mid.status = WorkloadStatus.RUNNING
    workload_mid.manifest = DEFAULT_TEST_MANIFEST
    workload_mid.created_at = datetime(2025, 1, 5, tzinfo=UTC)
    workload_mid.created_by = "test-user"

    with (
        patch("app.namespaces.service.list_aim_services", new_callable=AsyncMock) as mock_list_aims,
        patch("app.namespaces.service.get_workloads", new_callable=AsyncMock) as mock_get_workloads,
        patch(
            "app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", new_callable=AsyncMock
        ) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", new_callable=AsyncMock) as mock_vram,
    ):
        mock_list_aims.return_value = []
        # Return workloads in unsorted order
        mock_get_workloads.return_value = [workload_mid, workload_old, workload_new]
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        # Test descending sort by created_at
        result_desc = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            sort_by="created_at",
            sort_order=SortDirection.desc,
        )

        assert len(result_desc.data) == 3
        assert result_desc.data[0].name == "workload-new"
        assert result_desc.data[1].name == "workload-mid"
        assert result_desc.data[2].name == "workload-old"

        # Test ascending sort by created_at
        result_asc = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            sort_by="created_at",
            sort_order=SortDirection.asc,
        )

        assert len(result_asc.data) == 3
        assert result_asc.data[0].name == "workload-old"
        assert result_asc.data[1].name == "workload-mid"
        assert result_asc.data[2].name == "workload-new"


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_sorting_with_pagination(
    mock_kube_client: MagicMock,
    mock_db_session: AsyncMock,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test that sorting applies to full dataset before pagination."""
    namespace = MagicMock()
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create 5 workloads
    workloads = []
    for i in range(5):
        workload = MagicMock()
        workload.id = uuid4()
        workload.name = f"workload-{i}"
        workload.display_name = f"Workload {i}"
        workload.type = WorkloadType.INFERENCE
        workload.status = WorkloadStatus.RUNNING
        workload.manifest = DEFAULT_TEST_MANIFEST
        workload.created_at = datetime(2025, 1, i + 1, tzinfo=UTC)
        workload.created_by = "test-user"
        workloads.append(workload)

    with (
        patch("app.namespaces.service.list_aim_services", new_callable=AsyncMock) as mock_list_aims,
        patch("app.namespaces.service.get_workloads", new_callable=AsyncMock) as mock_get_workloads,
        patch(
            "app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", new_callable=AsyncMock
        ) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", new_callable=AsyncMock) as mock_vram,
    ):
        mock_list_aims.return_value = []
        mock_get_workloads.return_value = workloads
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        # Get page 1 with page_size=2 sorted descending
        result = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            page=1,
            page_size=2,
            sort_by="created_at",
            sort_order=SortDirection.desc,
        )

        # Should have newest 2 workloads (workload-4 and workload-3)
        assert len(result.data) == 2
        assert result.total == 5
        assert result.data[0].name == "workload-4"
        assert result.data[1].name == "workload-3"

        # Get page 2
        result2 = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            page=2,
            page_size=2,
            sort_by="created_at",
            sort_order=SortDirection.desc,
        )

        # Should have next 2 workloads (workload-2 and workload-1)
        assert len(result2.data) == 2
        assert result2.data[0].name == "workload-2"
        assert result2.data[1].name == "workload-1"


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_sorting_by_status_across_pages(
    mock_kube_client: MagicMock,
    mock_db_session: AsyncMock,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test sorting by status groups all items by status across pages.

    Scenario: Page 1 has 3 RUNNING + 1 FAILED, Page 2 has 1 RUNNING.
    When sorted by status ascending, page 1 should have 1 FAILED + 3 RUNNING,
    and page 2 should have 1 RUNNING.
    When sorted descending, page 1 should have 4 RUNNING, page 2 should have 1 FAILED.
    """
    namespace = MagicMock()
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create 5 workloads: 4 RUNNING, 1 FAILED
    workloads = []
    for i in range(4):
        workload = MagicMock()
        workload.id = uuid4()
        workload.name = f"running-{i}"
        workload.display_name = f"Running Workload {i}"
        workload.type = WorkloadType.INFERENCE
        workload.status = WorkloadStatus.RUNNING
        workload.manifest = DEFAULT_TEST_MANIFEST
        workload.created_at = datetime(2025, 1, i + 1, tzinfo=UTC)
        workload.created_by = "test-user"
        workloads.append(workload)

    failed_workload = MagicMock()
    failed_workload.id = uuid4()
    failed_workload.name = "failed-0"
    failed_workload.display_name = "Failed Workload"
    failed_workload.type = WorkloadType.INFERENCE
    failed_workload.status = WorkloadStatus.FAILED
    failed_workload.manifest = DEFAULT_TEST_MANIFEST
    failed_workload.created_at = datetime(2025, 1, 5, tzinfo=UTC)
    failed_workload.created_by = "test-user"
    workloads.append(failed_workload)

    with (
        patch("app.namespaces.service.list_aim_services", new_callable=AsyncMock) as mock_list_aims,
        patch("app.namespaces.service.get_workloads", new_callable=AsyncMock) as mock_get_workloads,
        patch(
            "app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", new_callable=AsyncMock
        ) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", new_callable=AsyncMock) as mock_vram,
    ):
        mock_list_aims.return_value = []
        mock_get_workloads.return_value = workloads
        mock_gpu.return_value = {}
        mock_vram.return_value = {}

        # Sort by status descending (RUNNING > FAILED alphabetically reversed)
        # Page 1 (page_size=4) should have all 4 RUNNING
        result_page1 = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            page=1,
            page_size=4,
            sort_by="status",
            sort_order=SortDirection.desc,
        )

        # Page 2 should have the FAILED workload
        result_page2 = await get_namespace_workload_metrics_paginated(
            kube_client=mock_kube_client,
            session=mock_db_session,
            namespace=namespace,
            prometheus_client=mock_prometheus_client,
            page=2,
            page_size=4,
            sort_by="status",
            sort_order=SortDirection.desc,
        )

        # Verify total is 5 across both pages
        assert result_page1.total == 5
        assert result_page2.total == 5

        # Page 1: 4 items, all should be RUNNING (sorted desc, R > F)
        assert len(result_page1.data) == 4
        assert all(m.status == WorkloadStatus.RUNNING for m in result_page1.data)

        # Page 2: 1 item, should be FAILED
        assert len(result_page2.data) == 1
        assert result_page2.data[0].status == WorkloadStatus.FAILED


# Tests for get_namespace_stats_counts
@pytest.mark.asyncio
async def test_get_namespace_stats_counts_with_resources(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test get_namespace_stats_counts with both AIM services and workloads."""
    namespace = MagicMock(spec=Namespace)
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create mock AIM service from K8s
    aim_service_id = uuid4()
    mock_aim_service = make_aim_service_k8s(
        namespace="test-namespace",
        workload_id=aim_service_id,
        status=AIMServiceStatus.RUNNING,
    )

    # Create real workloads in DB with different statuses
    workload_running = await create_workload(
        db_session,
        name="workload-running",
        display_name="Workload Running",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        submitter="test-user-2",
    )

    workload_pending = await create_workload(
        db_session,
        name="workload-pending",
        display_name="Workload Pending",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        submitter="test-user-2",
    )

    with (
        patch("app.namespaces.service.list_aim_services", autospec=True) as mock_list_aims,
    ):
        mock_list_aims.return_value = [mock_aim_service]

        result = await get_namespace_stats_counts(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
        )

        # Verify response structure
        assert result.namespace == "test-namespace"
        assert result.total == 3

        # Verify status counts
        status_dict = {count.status: count.count for count in result.status_counts}
        assert status_dict[WorkloadStatus.RUNNING] == 2
        assert status_dict[WorkloadStatus.PENDING] == 1


@pytest.mark.asyncio
async def test_get_namespace_stats_counts_empty_namespace(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test get_namespace_stats_counts with empty namespace."""
    namespace = MagicMock(spec=Namespace)
    namespace.name = "empty-namespace"
    namespace.id = "empty-namespace-id"

    with (
        patch("app.namespaces.service.list_aim_services", autospec=True) as mock_list_aims,
    ):
        mock_list_aims.return_value = []

        result = await get_namespace_stats_counts(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
        )

        # Verify empty results
        assert result.namespace == "empty-namespace"
        assert result.total == 0
        assert len(result.status_counts) == 0


@pytest.mark.asyncio
async def test_get_namespace_stats_counts_all_statuses(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test get_namespace_stats_counts with resources in all statuses."""
    namespace = MagicMock(spec=Namespace)
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create real workloads in DB with different statuses
    workload_running = await create_workload(
        db_session,
        name="workload-running",
        display_name="Workload Running",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        submitter="test-user",
    )

    workload_pending = await create_workload(
        db_session,
        name="workload-pending",
        display_name="Workload Pending",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        submitter="test-user",
    )

    workload_failed = await create_workload(
        db_session,
        name="workload-failed",
        display_name="Workload Failed",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.FAILED,
        submitter="test-user",
    )

    workload_complete = await create_workload(
        db_session,
        name="workload-complete",
        display_name="Workload Complete",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.COMPLETE,
        submitter="test-user",
    )

    with (
        patch("app.namespaces.service.list_aim_services", autospec=True) as mock_list_aims,
    ):
        mock_list_aims.return_value = []

        result = await get_namespace_stats_counts(
            kube_client=mock_kube_client,
            session=db_session,
            namespace=namespace,
        )

        # Verify totals
        assert result.namespace == "test-namespace"
        assert result.total == 4

        # Verify all statuses are represented
        status_dict = {count.status: count.count for count in result.status_counts}
        assert status_dict[WorkloadStatus.RUNNING] == 1
        assert status_dict[WorkloadStatus.PENDING] == 1
        assert status_dict[WorkloadStatus.FAILED] == 1
        assert status_dict[WorkloadStatus.COMPLETE] == 1


# Tests for _process_aim_services_to_metrics
@pytest.mark.asyncio
async def test_process_aim_services_to_metrics(db_session: AsyncSession) -> None:
    """Test _process_aim_services_to_metrics converts AIM services correctly."""
    aim_service_id = uuid4()

    # Create mock AIM service from K8s
    mock_aim_service = make_aim_service_k8s(
        namespace="test-namespace",
        workload_id=aim_service_id,
        status=AIMServiceStatus.RUNNING,
    )

    # Create real AIM service in DB
    mock_aim_db = await create_aim_service_db(
        db_session,
        id=aim_service_id,
        namespace="test-namespace",
        status=AIMServiceStatus.RUNNING,
        created_by="test-user",
    )

    gpu_counts = {str(aim_service_id): 4}
    vram_usage = {str(aim_service_id): 24000.0}

    result = await _process_aim_services_to_metrics(
        aim_services_k8s=[mock_aim_service],
        session=db_session,
        namespace_name="test-namespace",
        gpu_counts=gpu_counts,
        vram_usage=vram_usage,
    )

    assert len(result) == 1
    metric = result[0]
    assert metric.id == aim_service_id
    assert metric.name == mock_aim_service.metadata.name
    assert metric.type == WorkloadType.INFERENCE
    assert metric.status == WorkloadStatus.RUNNING
    assert metric.gpu_count == 4
    assert metric.vram == 24000.0
    assert metric.created_by == "test-user"


@pytest.mark.asyncio
async def test_process_aim_services_to_metrics_no_db_record(db_session: AsyncSession) -> None:
    """Test _process_aim_services_to_metrics when AIM service has no DB record."""
    aim_service_id = uuid4()

    # Create mock AIM service from K8s (no DB record)
    mock_aim_service = make_aim_service_k8s(
        namespace="test-namespace",
        workload_id=aim_service_id,
        status=AIMServiceStatus.RUNNING,
    )

    result = await _process_aim_services_to_metrics(
        aim_services_k8s=[mock_aim_service],
        session=db_session,
        namespace_name="test-namespace",
        gpu_counts={},
        vram_usage={},
    )

    assert len(result) == 1
    metric = result[0]
    assert metric.created_at is None
    assert metric.created_by is None


@pytest.mark.asyncio
async def test_process_aim_services_to_metrics_skips_invalid_workload_id(db_session: AsyncSession) -> None:
    """Test _process_aim_services_to_metrics skips AIM services with invalid workload IDs."""
    # Service with no workload ID label
    mock_aim_service_no_uid = MagicMock(spec=AIMServiceResource)
    mock_aim_service_no_uid.metadata = K8sMetadata(name="test-aim-service-1", labels={})
    # Mock the id property to return None
    mock_aim_service_no_uid.id = None

    # Service with invalid UUID in workload ID label
    mock_aim_service_invalid_uuid = MagicMock(spec=AIMServiceResource)
    mock_aim_service_invalid_uuid.metadata = K8sMetadata(
        name="test-aim-service-2",
        labels={WORKLOAD_ID_LABEL: "invalid-uuid"},
    )
    # Mock the id property to return the invalid UUID
    mock_aim_service_invalid_uuid.id = "invalid-uuid"

    result = await _process_aim_services_to_metrics(
        aim_services_k8s=[mock_aim_service_no_uid, mock_aim_service_invalid_uuid],
        session=db_session,
        namespace_name="test-namespace",
        gpu_counts={},
        vram_usage={},
    )

    assert len(result) == 0


@pytest.mark.asyncio
async def test_process_aim_services_to_metrics_fallback_display_name(db_session: AsyncSession) -> None:
    """Test _process_aim_services_to_metrics falls back to name when title not available."""
    aim_service_id = uuid4()

    # Create mock AIM service from K8s with non-dict model spec
    mock_aim_service = MagicMock(spec=AIMServiceResource)
    mock_aim_service.metadata = K8sMetadata(
        name="test-aim-service",
        labels={WORKLOAD_ID_LABEL: str(aim_service_id)},
    )
    mock_aim_service.id = str(aim_service_id)
    # Configure spec and status as MagicMocks
    mock_spec = MagicMock(spec=AIMServiceSpec)
    # spec.model is not a dict with metadata
    mock_spec.model = "some-model-string"
    mock_aim_service.spec = mock_spec
    mock_status = MagicMock(spec=AIMServiceStatusFields)
    mock_status.status = AIMServiceStatus.RUNNING
    mock_aim_service.status = mock_status

    result = await _process_aim_services_to_metrics(
        aim_services_k8s=[mock_aim_service],
        session=db_session,
        namespace_name="test-namespace",
        gpu_counts={},
        vram_usage={},
    )

    assert len(result) == 1
    metric = result[0]
    assert metric.display_name == "test-aim-service"


# Tests for _process_workloads_to_metrics
@pytest.mark.asyncio
async def test_process_workloads_to_metrics(db_session: AsyncSession) -> None:
    """Test _process_workloads_to_metrics converts workloads correctly."""
    # Create real workload in database
    workload = await create_workload(
        db_session,
        name="test-workload",
        display_name="Test Workload",
        namespace="test-namespace",
        workload_type=WorkloadType.FINE_TUNING,
        status=WorkloadStatus.RUNNING,
        submitter="test-user",
    )

    gpu_counts = {str(workload.id): 8}
    vram_usage = {str(workload.id): 48000.0}

    result = await _process_workloads_to_metrics(
        workloads_db=[workload],
        gpu_counts=gpu_counts,
        vram_usage=vram_usage,
    )

    assert len(result) == 1
    metric = result[0]
    assert metric.id == workload.id
    assert metric.name == "test-workload"
    assert metric.display_name == "Test Workload"
    assert metric.type == WorkloadType.FINE_TUNING
    assert metric.status == WorkloadStatus.RUNNING
    assert metric.gpu_count == 8
    assert metric.vram == 48000.0
    assert metric.created_by == "test-user"


@pytest.mark.asyncio
async def test_process_workloads_to_metrics_no_gpu_metrics(db_session: AsyncSession) -> None:
    """Test _process_workloads_to_metrics when GPU metrics are not available."""
    # Create real workload in database
    workload = await create_workload(
        db_session,
        name="test-workload",
        display_name="Test Workload",
        namespace="test-namespace",
        workload_type=WorkloadType.WORKSPACE,
        status=WorkloadStatus.PENDING,
        submitter="test-user",
    )

    result = await _process_workloads_to_metrics(
        workloads_db=[workload],
        gpu_counts={},
        vram_usage={},
    )

    assert len(result) == 1
    metric = result[0]
    assert metric.gpu_count is None
    assert metric.vram is None


@pytest.mark.asyncio
async def test_process_workloads_to_metrics_multiple_workloads(db_session: AsyncSession) -> None:
    """Test _process_workloads_to_metrics with multiple workloads."""
    # Create real workloads in database
    workloads = []
    for i in range(3):
        workload = await create_workload(
            db_session,
            name=f"workload-{i}",
            display_name=f"Workload {i}",
            namespace="test-namespace",
            workload_type=WorkloadType.INFERENCE,
            status=WorkloadStatus.RUNNING,
            submitter=f"user-{i}",
        )
        workloads.append(workload)

    result = await _process_workloads_to_metrics(
        workloads_db=workloads,
        gpu_counts={},
        vram_usage={},
    )

    assert len(result) == 3
    for i, metric in enumerate(result):
        assert metric.name == f"workload-{i}"
        assert metric.display_name == f"Workload {i}"
        assert metric.created_by == f"user-{i}"


@pytest.mark.asyncio
async def test_get_namespace_workload_metrics_paginated_prometheus_errors(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
    mock_prometheus_client: MagicMock,
) -> None:
    """Test get_namespace_workload_metrics_paginated when Prometheus queries fail."""
    namespace = MagicMock(spec=Namespace)
    namespace.name = "test-namespace"
    namespace.id = "test-namespace-id"

    # Create real workload in database
    workload = await create_workload(
        db_session,
        name="test-workload",
        display_name="Test Workload",
        namespace="test-namespace",
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        submitter="test-user",
    )

    with (
        patch("app.namespaces.service.list_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.get_gpu_utilization_by_workload_in_namespace", autospec=True) as mock_gpu,
        patch("app.namespaces.service.get_gpu_vram_by_workload_in_namespace", autospec=True) as mock_vram,
    ):
        mock_list_aims.return_value = []
        mock_gpu.side_effect = RuntimeError("Prometheus connection failed")
        mock_vram.return_value = {}

        with pytest.raises(RuntimeError, match="Prometheus connection failed"):
            await get_namespace_workload_metrics_paginated(
                kube_client=mock_kube_client,
                session=db_session,
                namespace=namespace,
                prometheus_client=mock_prometheus_client,
            )


@pytest.mark.asyncio
async def test_get_chattable_resources_aim_service_error(
    mock_kube_client: MagicMock,
    db_session: AsyncSession,
) -> None:
    """Test get_chattable_resources when AIM service listing fails."""
    namespace = "test-namespace"

    with (
        patch("app.namespaces.service.list_chattable_aim_services", autospec=True) as mock_list_aims,
        patch("app.namespaces.service.list_chattable_workloads", autospec=True) as mock_list_workloads,
    ):
        mock_list_aims.side_effect = RuntimeError("Kubernetes API unavailable")
        mock_list_workloads.return_value = []

        with pytest.raises(RuntimeError, match="Kubernetes API unavailable"):
            await get_chattable_resources(
                kube_client=mock_kube_client,
                session=db_session,
                namespace=namespace,
            )

        mock_list_aims.assert_called_once_with(mock_kube_client, namespace)
