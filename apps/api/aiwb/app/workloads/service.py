# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workload service for creation, deletion, and management."""

from uuid import UUID

import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from api_common.exceptions import NotFoundException, ValidationException

from ..overlays.repository import list_overlays
from .config import CHAT_TIMEOUT, DEFAULT_CHAT_PATH
from .enums import WorkloadStatus, WorkloadType
from .gateway import delete_workload_resources
from .models import Workload
from .repository import get_workload_by_id, get_workloads, update_workload_status
from .schemas import WorkloadResponse
from .utils import get_workload_internal_url


async def delete_workload_components(namespace: str, workload_id: UUID, session: AsyncSession) -> None:
    """Delete all Kubernetes components associated with a workload.

    Raises:
        RuntimeError: If Kubernetes resource deletion fails. Database changes are rolled back.
    """
    logger.info(f"Deleting workload {workload_id}")

    workload = await get_workload_by_id(session, workload_id)
    if not workload:
        logger.warning(f"Workload {workload_id} not found in database")
        return

    await update_workload_status(session, workload.id, WorkloadStatus.DELETING, workload.updated_by)
    await delete_workload_resources(namespace, str(workload.id))
    await update_workload_status(session, workload.id, WorkloadStatus.DELETED, workload.updated_by)
    logger.info(f"Workload {workload.id} marked as DELETED")


async def is_workload_chattable(session: AsyncSession, workload: Workload) -> bool:
    """Check if a workload can be used for chat.

    A workload is chattable if it's running and has a model with chat capability
    defined in its overlays (metadata.labels.chat: true).
    """
    if workload.status != WorkloadStatus.RUNNING:
        return False

    # Must have an associated model
    if not workload.model_id:
        return False

    # Get canonical name from the joined model relationship
    canonical_name = workload.model.canonical_name if workload.model else None
    if not canonical_name:
        return False

    # Check overlays for chat capability
    overlays = await list_overlays(session, chart_id=workload.chart_id, canonical_name=canonical_name)

    for overlay in overlays:
        if not overlay.overlay or not isinstance(overlay.overlay, dict):
            continue

        metadata = overlay.overlay.get("metadata", {})
        if not isinstance(metadata, dict):
            continue

        labels = metadata.get("labels", {})
        if not isinstance(labels, dict):
            continue

        chat_value = labels.get("chat")
        if chat_value == "true" or chat_value is True:
            return True

    return False


async def list_chattable_workloads(
    session: AsyncSession,
    namespace: str,
) -> list[WorkloadResponse]:
    """Get all RUNNING Inference workloads that support chat."""
    workloads = await get_workloads(
        session=session,
        namespace=namespace,
        workload_types=[WorkloadType.INFERENCE],
        status_filter=[WorkloadStatus.RUNNING],
    )
    chattable_workloads = []

    for workload in workloads:
        if await is_workload_chattable(session, workload):
            chattable_workloads.append(WorkloadResponse.model_validate(workload))

    return chattable_workloads


async def chat_with_workload(
    session: AsyncSession,
    namespace: str,
    workload_id: UUID,
    request: Request,
) -> StreamingResponse:
    """Chat with a deployed workload.

    Raises:
        NotFoundException: If workload is not found
        ValidationException: If workload is not available for chat
    """
    workload = await get_workload_by_id(session=session, workload_id=workload_id, namespace=namespace)
    if not workload:
        raise NotFoundException(f"Workload {workload_id} not found")

    if not await is_workload_chattable(session, workload):
        raise ValidationException(
            f"Workload {workload_id} is not available for chat "
            f"(status: {workload.status}, model may not support chat capability)"
        )

    base_url = get_workload_internal_url(workload.name, namespace)

    try:
        return await stream_downstream(base_url=base_url, request=request)
    except Exception as e:
        logger.error(f"Error streaming from endpoint {base_url}: {e}")
        raise ValidationException(f"Error connecting to model endpoint: {str(e)}")


async def stream_downstream(base_url: str, request: Request, body: bytes | None = None) -> StreamingResponse:
    """Stream response from a downstream server.

    Args:
        base_url: Base URL of the downstream server
        request: The incoming FastAPI request
        body: Optional body to use instead of the request body

    Returns:
        StreamingResponse that proxies the downstream response
    """
    if body is None:
        body = await request.body()
    headers = dict(request.headers)
    # Remove content length from headers as the body might have been modified from original
    if "content-length" in headers:
        del headers["content-length"]

    # Timeout is set here as safety for long-lived connections
    # but API and UI timeouts are set at gateway level in helm charts
    timeout = httpx.Timeout(CHAT_TIMEOUT)

    client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
    url = httpx.URL(path=DEFAULT_CHAT_PATH, query=request.url.query.encode("utf-8"))
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
