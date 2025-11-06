# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any
from uuid import UUID

import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from airm.messaging.schemas import WorkloadStatus

from ..charts.models import Chart
from ..datasets.models import Dataset
from ..models.models import InferenceModel
from ..models.repository import select_model
from ..projects.models import Project
from ..utilities.capabilities import get_model_capabilities_from_overlays
from ..utilities.checks import ensure_base_url_configured
from ..utilities.exceptions import NotFoundException
from ..workloads.enums import WorkloadType
from ..workloads.service import extract_components_and_submit_workload, submit_delete_workload
from ..workloads.utils import validate_and_parse_workload_manifest
from .config import CHAT_STREAM_HTTP_TIMEOUT
from .models import ManagedWorkload
from .repository import insert_workload, select_workload, select_workloads
from .schemas import AIMWorkloadResponse, ChartWorkloadCreate, ChartWorkloadResponse
from .utils import (
    does_workload_need_cluster_base_url,
    get_workload_host_from_HTTPRoute_manifest,
    get_workload_internal_host,
    render_helm_template,
)


async def get_workload(
    session: AsyncSession,
    accessible_projects: list[Project],
    workload_id: UUID,
    require_aim: bool = False,
) -> ChartWorkloadResponse | AIMWorkloadResponse:
    workload = await select_workload(session, workload_id, accessible_projects)
    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found")
    if require_aim and not workload.aim_id:
        raise NotFoundException(f"AIM Workload with ID {workload_id} not found")

    if workload.aim_id:
        return AIMWorkloadResponse.model_validate(workload)
    else:
        if workload.chart_id and workload.model_id:
            model = await select_model(session, workload.model_id, workload.project_id)
            if model:
                workload.__dict__["capabilities"] = await get_model_capabilities_from_overlays(session, model) or []
        return ChartWorkloadResponse.model_validate(workload)


async def list_workloads(
    session: AsyncSession,
    project_id: UUID,
    type: list[WorkloadType] | None = None,
    status: list[WorkloadStatus] | None = None,
) -> list[ChartWorkloadResponse | AIMWorkloadResponse]:
    workloads = await select_workloads(session, project_id, type, status)

    results = []
    for workload in workloads:
        if workload.aim_id:
            results.append(AIMWorkloadResponse.model_validate(workload))
        else:
            if workload.chart_id and workload.model_id:
                model = await select_model(session, workload.model_id, workload.project_id)
                if model:
                    workload.__dict__["capabilities"] = await get_model_capabilities_from_overlays(session, model) or []
            results.append(ChartWorkloadResponse.model_validate(workload))
    return results


async def submit_chart_workload(
    session: AsyncSession,
    creator: str,
    token: str,
    project: Project,
    chart: Chart,
    overlays_values: list[dict[str, Any]],
    user_inputs: dict[str, Any] = None,
    model: InferenceModel | None = None,
    dataset: Dataset | None = None,
    display_name: str | None = None,
) -> ChartWorkloadResponse:
    """
    Submit a new chart-base managed workload by creating database record, rendering Helm template, and submitting to cluster.

    Raises:
        ConflictException: If workload creation violates database constraints
        ValidationException: If Helm template rendering or manifest validation fails
        ExternalServiceError: If cluster submission fails
    """

    if does_workload_need_cluster_base_url(chart):
        ensure_base_url_configured(project)

    # Ensure user_inputs is always a dict and add canonical_name
    if user_inputs is None:
        user_inputs = {}

    # Add user inputs as the last overlay (highest priority)
    overlays_values.append(user_inputs)

    workload: ManagedWorkload = await insert_workload(
        session=session,
        creator=creator,
        project=project,
        workload_data=ChartWorkloadCreate(
            type=chart.type,
            user_inputs={**user_inputs, "canonical_name": model.canonical_name if model else None},
            display_name=display_name,
            chart_id=chart.id,
            model_id=model.id if model else None,
            dataset_id=dataset.id if dataset else None,
        ),
    )
    await session.flush()  # Save to get the name

    manifest = await render_helm_template(
        chart,
        workload.name,
        project.name,
        overlays_values,
    )
    workload.manifest = manifest
    await session.flush()  # Save the manifest

    # Extract host from manifest
    internal_host = None
    external_host = None
    if does_workload_need_cluster_base_url(chart):
        internal_host = get_workload_internal_host(workload.name, project.name)
        external_host = get_workload_host_from_HTTPRoute_manifest(
            manifest=manifest, cluster_base_url=project.cluster.base_url
        )
    workload.output = {
        "internal_host": internal_host,
        "external_host": external_host,
    }
    await session.flush()  # Save the output

    yml_content = await validate_and_parse_workload_manifest(manifest)

    logger.info(f"Submitting workload {workload.id}...")
    await extract_components_and_submit_workload(session, workload, project, yml_content, creator, token)

    logger.info(f"Successfully completed managed workload submission for {workload.id}. Returning object.")
    return workload


async def delete_workload(session: AsyncSession, id: UUID, accessible_projects: list[Project]) -> bool:
    """
    Delete a managed workload that the user has access to.

    Raises:
        NotFoundException: If workload not found or user lacks access
        ExternalServiceError: If cluster deletion submission fails
    """
    workload = await select_workload(session, id, accessible_projects)
    if workload is None:
        raise NotFoundException("Workload not found")

    await submit_delete_workload(session, workload, "system")

    return True


async def stream_downstream(base_url: str, request: Request, url_path: str | None = None, body=None):
    """Stream response from a downstream server.
    If body is not None, it is used instead of the body in the request object.
    Optionally provide a url_path to override the request path.
    """
    if body is None:
        body = await request.body()
    headers = dict(request.headers)
    # Remove content length from headers as the body might have been modified from original
    if "content-length" in headers:
        del headers["content-length"]
    client = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(CHAT_STREAM_HTTP_TIMEOUT, read=None))
    path = url_path or request.url.path
    url = httpx.URL(path=path, query=request.url.query.encode("utf-8"))
    downstream_request = client.build_request(request.method, url, headers=headers, content=body)
    try:
        downstream_response = await client.send(downstream_request, stream=True)
    except httpx.ConnectError:
        logger.error(f"Connect error while connecting {base_url}")
        raise
    return StreamingResponse(
        downstream_response.aiter_raw(),
        status_code=downstream_response.status_code,
        headers=downstream_response.headers,
        background=BackgroundTask(downstream_response.aclose),
    )
