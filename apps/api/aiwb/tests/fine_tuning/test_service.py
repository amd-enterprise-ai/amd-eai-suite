# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for fine_tuning service-layer type verification (404 for wrong type)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import NotFoundException
from app.aims.crds import AIMModelResource
from app.dispatch.kube_client import KubernetesClient
from app.fine_tuning.service import delete_fine_tuning_job, get_fine_tuning_model, list_fine_tuning_models
from app.workloads.constants import WORKLOAD_TYPE_LABEL
from app.workloads.enums import WorkloadType
from app.workloads.models import Workload


def _make_model(name: str, fine_tuning: bool) -> AIMModelResource:
    labels: dict[str, str] = {}
    if fine_tuning:
        labels[WORKLOAD_TYPE_LABEL] = WorkloadType.FINE_TUNING
    return AIMModelResource.model_validate(
        {
            "metadata": {"name": name, "labels": labels},
            "spec": {"image": "test-image:latest"},
            "status": {"status": "Ready", "imageMetadata": {"model": {}}},
        }
    )


@pytest.mark.asyncio
@patch("app.fine_tuning.service.list_aim_models", new_callable=AsyncMock)
async def test_list_fine_tuning_models_filters_by_label(mock_list: AsyncMock) -> None:
    kube_client = AsyncMock(spec=KubernetesClient)
    mock_list.return_value = [
        _make_model("ft-1", fine_tuning=True),
        _make_model("ft-2", fine_tuning=True),
    ]

    result = await list_fine_tuning_models(kube_client=kube_client, namespace="ns")

    assert [m.metadata.name for m in result.items] == ["ft-1", "ft-2"]
    assert result.total == 2
    assert result.page == 1
    assert result.page_size == 10
    mock_list.assert_awaited_once_with(
        kube_client=kube_client,
        namespace="ns",
        label_selector=f"{WORKLOAD_TYPE_LABEL}={WorkloadType.FINE_TUNING}",
    )


@pytest.mark.asyncio
@patch("app.fine_tuning.service.list_aim_models", new_callable=AsyncMock)
async def test_list_fine_tuning_models_paginates_results(mock_list: AsyncMock) -> None:
    # K8s already filters via label selector, so the LIST returns only
    # fine-tuning models. This test verifies the pagination math slices
    # those results correctly.
    kube_client = AsyncMock(spec=KubernetesClient)
    mock_list.return_value = [
        _make_model("ft-1", fine_tuning=True),
        _make_model("ft-2", fine_tuning=True),
        _make_model("ft-3", fine_tuning=True),
    ]

    result = await list_fine_tuning_models(kube_client=kube_client, namespace="ns", page=1, page_size=2)

    assert [m.metadata.name for m in result.items] == ["ft-1", "ft-2"]
    assert result.total == 3
    assert result.page == 1
    assert result.page_size == 2


@pytest.mark.asyncio
@patch("app.fine_tuning.service.get_aim_model", new_callable=AsyncMock)
async def test_get_fine_tuning_model_returns_when_fine_tuning(mock_get: AsyncMock) -> None:
    kube_client = AsyncMock(spec=KubernetesClient)
    mock_get.return_value = _make_model("ft-1", fine_tuning=True)

    result = await get_fine_tuning_model(kube_client, "ns", "ft-1")

    assert result.metadata.name == "ft-1"


@pytest.mark.asyncio
@patch("app.fine_tuning.service.get_aim_model", new_callable=AsyncMock)
async def test_get_fine_tuning_model_raises_404_when_not_fine_tuning(mock_get: AsyncMock) -> None:
    kube_client = AsyncMock(spec=KubernetesClient)
    mock_get.return_value = _make_model("inference-1", fine_tuning=False)

    with pytest.raises(NotFoundException):
        await get_fine_tuning_model(kube_client, "ns", "inference-1")


@pytest.mark.asyncio
@patch("app.fine_tuning.service.delete_workload_components", new_callable=AsyncMock)
@patch("app.fine_tuning.service.get_workload_by_id", new_callable=AsyncMock)
async def test_delete_fine_tuning_job_deletes_when_fine_tuning(
    mock_get_workload: AsyncMock, mock_delete: AsyncMock
) -> None:
    session = AsyncMock(spec=AsyncSession)
    job_id = uuid4()
    workload = MagicMock(spec=Workload)
    workload.type = WorkloadType.FINE_TUNING
    mock_get_workload.return_value = workload

    await delete_fine_tuning_job(session=session, namespace="ns", workload_id=job_id)

    mock_delete.assert_awaited_once_with("ns", job_id, session, workload=workload)


@pytest.mark.asyncio
@patch("app.fine_tuning.service.delete_workload_components", new_callable=AsyncMock)
@patch("app.fine_tuning.service.get_workload_by_id", new_callable=AsyncMock)
async def test_delete_fine_tuning_job_raises_404_when_workload_missing(
    mock_get_workload: AsyncMock, mock_delete: AsyncMock
) -> None:
    session = AsyncMock(spec=AsyncSession)
    mock_get_workload.return_value = None

    with pytest.raises(NotFoundException):
        await delete_fine_tuning_job(session=session, namespace="ns", workload_id=uuid4())

    mock_delete.assert_not_called()


@pytest.mark.asyncio
@patch("app.fine_tuning.service.delete_workload_components", new_callable=AsyncMock)
@patch("app.fine_tuning.service.get_workload_by_id", new_callable=AsyncMock)
async def test_delete_fine_tuning_job_raises_404_when_workload_wrong_type(
    mock_get_workload: AsyncMock, mock_delete: AsyncMock
) -> None:
    session = AsyncMock(spec=AsyncSession)
    workload = MagicMock(spec=Workload)
    workload.type = WorkloadType.INFERENCE
    mock_get_workload.return_value = workload

    with pytest.raises(NotFoundException):
        await delete_fine_tuning_job(session=session, namespace="ns", workload_id=uuid4())

    mock_delete.assert_not_called()
