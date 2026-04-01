# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.workloads.enums import WorkloadType
from app.workloads.models import Workload
from app.workloads.utils import apply_manifest, get_dynamic_client


async def apply_test_manifest(manifest: str) -> tuple[list[dict], MagicMock]:
    """Call apply_manifest with mocked K8s clients. Returns (bodies, workload)."""
    workload = MagicMock(spec=Workload)
    workload.id = uuid4()
    workload.chart_id = uuid4()
    workload.type = WorkloadType.INFERENCE
    workload.display_name = "test-workload"
    workload.model_id = None
    workload.dataset_id = None

    api_resource = MagicMock(namespaced=True, create=MagicMock())
    dyn_client = MagicMock()
    dyn_client.resources.get.return_value = api_resource

    with patch("app.workloads.utils.get_dynamic_client", spec=get_dynamic_client, return_value=dyn_client):
        await apply_manifest(AsyncMock(), manifest, workload, "test-namespace", "test@example.com")

    bodies = [c.kwargs["body"] for c in api_resource.create.call_args_list]
    return bodies, workload


def make_condition(type: str, status: str, reason: str | None = None) -> MagicMock:
    cond = MagicMock()
    cond.type = type
    cond.status = status
    cond.reason = reason
    return cond


def make_deployment_status(
    conditions: list[MagicMock] | None = None,
    ready_replicas: int | None = None,
) -> MagicMock:
    status = MagicMock()
    status.conditions = conditions
    status.ready_replicas = ready_replicas
    return status


def make_job_status(
    conditions: list[MagicMock] | None = None,
    active: int | None = None,
    succeeded: int | None = None,
    failed: int | None = None,
) -> MagicMock:
    status = MagicMock()
    status.conditions = conditions
    status.active = active
    status.succeeded = succeeded
    status.failed = failed
    return status
