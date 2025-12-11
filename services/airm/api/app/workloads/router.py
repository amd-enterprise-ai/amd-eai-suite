# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import json
from datetime import datetime
from uuid import UUID

import httpx
import yaml
from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..clusters.schemas import ClusterResponse, ClusterStatus
from ..logs.schemas import LogDirectionLiteral, LogLevel, LogLevelLiteral, LogTypeLiteral, WorkloadLogsResponse
from ..logs.service import get_loki_client, get_workload_logs, stream_workload_logs
from ..messaging.sender import MessageSender, get_message_sender
from ..organizations.models import Organization
from ..projects.models import Project
from ..users.models import User
from ..utilities.database import get_session
from ..utilities.enums import Roles
from ..utilities.exceptions import NotFoundException, UnhealthyException, ValidationException
from ..utilities.security import (
    BearerToken,
    auth_token_claimset,
    ensure_platform_administrator,
    get_projects_accessible_to_user,
    get_user,
    get_user_email,
    get_user_organization,
    is_user_in_role,
    validate_and_get_project_from_query,
)
from .enums import WorkloadType
from .repository import get_workload_by_id_and_user_membership, get_workload_by_id_in_organization
from .schemas import WorkloadResponse, Workloads, WorkloadsStats, WorkloadWithComponents
from .service import create_and_submit_workload as submit_workload_to_cluster
from .service import (
    get_stats_for_workloads_in_organization,
    get_workload_with_components,
    get_workloads_accessible_to_user,
    get_workloads_by_project,
    submit_delete_workload,
)
from .utils import validate_and_parse_workload_manifest

router = APIRouter(tags=["Workloads"])


@router.post(
    "/workloads",
    operation_id="submit_workload",
    summary="Submit a new workload",
    description="""
        Deploy a containerized workload (training, inference, workspace, or custom) to a GPU cluster.
        Requires active project with available quota, valid Kubernetes YAML manifest (max 2MB),
        and healthy cluster. Workload will be queued and scheduled based on resource availability.
    """,
    status_code=status.HTTP_201_CREATED,
    response_model=WorkloadResponse,
)
async def submit_workload(
    user: str = Depends(get_user_email),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    token: str = Depends(BearerToken),
    project: Project = Depends(validate_and_get_project_from_query),
    manifest: UploadFile = File(..., description="The YAML file to be uploaded."),
    workload_type: WorkloadType = Query(WorkloadType.CUSTOM, description="Type of workload being submitted."),
    display_name: str = Query(
        ...,
        description="display name for the workload.",
        min_length=2,
        max_length=256,
        pattern=r"^[a-zA-Z0-9 _\-\.,:\(\)\[\]\+@#]+$",  # Allow alphanumeric, spaces, and some special characters
    ),
) -> WorkloadResponse:
    if manifest.size > 2 * 1024 * 1024:
        raise ValidationException("File size too large. Max size is 2 MB.")

    if ClusterResponse.model_validate(project.cluster).status is not ClusterStatus.HEALTHY:
        raise UnhealthyException(f"Cannot submit workload to cluster '{project.cluster.name}' - cluster is not healthy")

    try:
        yml_content = await validate_and_parse_workload_manifest(manifest)
    except yaml.YAMLError as ymlErr:
        raise ValidationException(f"Invalid YAML content in workload manifest: {ymlErr}")
    return await submit_workload_to_cluster(
        session, project, yml_content, user, token, workload_type, display_name, message_sender
    )


@router.delete(
    "/workloads/{workload_id}",
    operation_id="delete_workload",
    summary="Delete a submitted workload",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workload(
    user: User = Depends(get_user),
    message_sender: MessageSender = Depends(get_message_sender),
    session: AsyncSession = Depends(get_session),
    claimset: dict = Depends(auth_token_claimset),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    workload_id: UUID = Path(description="The ID of the workload to be deleted"),
) -> None:
    if is_user_in_role(claimset, Roles.PLATFORM_ADMINISTRATOR):
        workload = await get_workload_by_id_in_organization(session, workload_id, user.organization_id)
    else:
        workload = await get_workload_by_id_and_user_membership(session, workload_id, accessible_projects)

    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found or access denied")

    await submit_delete_workload(session, workload, user.email, message_sender)


@router.get(
    "/workloads/stats",
    operation_id="get_workload_stats",
    summary="Get workload stats",
    status_code=status.HTTP_200_OK,
    response_model=WorkloadsStats,
)
async def get_workload_stats(
    _: None = Depends(ensure_platform_administrator),
    organization: Organization = Depends(get_user_organization),
    session: AsyncSession = Depends(get_session),
) -> WorkloadsStats:
    return await get_stats_for_workloads_in_organization(session, organization.id)


@router.get(
    "/workloads/{workload_id}",
    operation_id="get_workload_by_id",
    summary="Get a workload by ID, including its components",
    status_code=status.HTTP_200_OK,
    response_model=WorkloadWithComponents,
)
async def get_workload(
    session: AsyncSession = Depends(get_session),
    workload_id: UUID = Path(description="The ID of the workload to be retrieved"),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
) -> WorkloadWithComponents:
    workload = await get_workload_by_id_and_user_membership(session, workload_id, accessible_projects)

    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found or access denied")

    return await get_workload_with_components(session, workload)


@router.get(
    "/workloads",
    operation_id="get_workloads",
    summary="Get all workloads accessible to the user, optionally scoped by the specified project",
    status_code=status.HTTP_200_OK,
    response_model=Workloads,
)
async def get_workloads(
    project_id: UUID | None = Query(None, description="The ID of the project for which to retrieve workloads"),
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
) -> Workloads:
    if project_id:
        await validate_and_get_project_from_query(accessible_projects, project_id)
        return await get_workloads_by_project(session, project_id)
    else:
        return await get_workloads_accessible_to_user(session, accessible_projects)


@router.get(
    "/workloads/{workload_id}/logs",
    operation_id="get_workload_logs",
    summary="Get logs for a workload",
    response_model=WorkloadLogsResponse,
)
async def workload_logs(
    workload_id: UUID = Path(description="The ID of the workload"),
    start_date: datetime = Query(
        default=None,
        description="Start date for logs (ISO format, defaults to 15 days ago for forward direction and now for backward direction). Can be used for pagination combined with information from the pagination object",
    ),
    end_date: datetime = Query(
        default=None,
        description="End date for logs (ISO format, defaults to now for forward direction, 15 days ago for backward direction)",
    ),
    page_token: datetime | None = Query(
        default=None,
        description="Pagination timestamp for the next page of logs. For direction forward, this is the start date; for backward, it is the end date.",
    ),
    limit: int = Query(default=1000, description="Max number of log entries"),
    level: LogLevelLiteral | None = Query(
        default=None, description="Log level to filter by - filters logs at this level and above"
    ),
    log_type: LogTypeLiteral = Query(
        default="workload",
        description="Type of logs to retrieve - 'workload' for workload logs, 'event' for Kubernetes events",
    ),
    direction: LogDirectionLiteral = Query(
        default="forward",
        description="Direction of log retrieval - 'forward' for older logs first, 'backward' for newer logs first",
    ),
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
    loki_client: httpx.AsyncClient = Depends(get_loki_client),
) -> WorkloadLogsResponse:
    """Get logs for a workload."""
    workload = await get_workload_by_id_and_user_membership(session, workload_id, accessible_projects)
    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found")

    workload_with_components = await get_workload_with_components(session, workload)

    # Convert string level to LogLevel enum if provided
    level_filter = LogLevel.from_label(level) if level else None

    try:
        workload_logs = await get_workload_logs(
            workload=workload_with_components,
            loki_client=loki_client,
            start_date=start_date,
            end_date=end_date,
            page_token=page_token,
            limit=limit,
            level_filter=level_filter,
            log_type=log_type,
            direction=direction,
        )

        return workload_logs
    except ValueError as ve:
        raise ValidationException(f"Invalid date range: {ve}")


@router.get(
    "/workloads/{workload_id}/logs/stream",
    operation_id="stream_workload_logs",
    summary="Stream logs for a workload in real-time",
    description="""
    Stream workload logs in real-time using Server-Sent Events (SSE).

    **Event Format:**
    ```
    data: {"timestamp": "2025-01-01T10:00:00Z", "level": "INFO", "message": "Log message"}

    ```

    **Connection Details:**
    - Media type: `text/event-stream`
    - Events sent every 1-30 seconds based on `delay` parameter
    - Connection stays open until client disconnects or error occurs
    - Errors are sent as JSON events with `error` field

    **Client Implementation:**
    Use EventSource API or equivalent SSE client library to consume the stream.
    """,
    responses={
        200: {
            "description": "SSE stream established successfully",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"timestamp": "2025-01-01T10:00:00Z", "level": "INFO", "message": "Application started"}\n\n'
                }
            },
        },
        404: {"description": "Workload not found or access denied"},
        422: {"description": "Invalid parameters (e.g., delay out of range)"},
    },
)
async def workload_logs_stream(
    workload_id: UUID = Path(description="The ID of the workload"),
    start_time: datetime | None = Query(
        default=None,
        description="Start time for streaming (ISO format, defaults to now)",
    ),
    level: LogLevelLiteral | None = Query(
        default=None, description="Log level to filter by - filters logs at this level and above"
    ),
    log_type: LogTypeLiteral = Query(
        default="workload",
        description="Type of logs to retrieve - 'workload' for workload logs, 'event' for Kubernetes events",
    ),
    delay: int = Query(
        default=1,
        ge=1,
        le=30,
        description="Delay between polling requests in seconds (1-30 seconds)",
    ),
    session: AsyncSession = Depends(get_session),
    accessible_projects: list[Project] = Depends(get_projects_accessible_to_user),
) -> StreamingResponse:
    """Stream workload logs in real-time via SSE."""
    workload = await get_workload_by_id_and_user_membership(session, workload_id, accessible_projects)
    if not workload:
        raise NotFoundException(f"Workload with ID {workload_id} not found")

    workload_with_components = await get_workload_with_components(session, workload)

    level_filter = LogLevel.from_label(level) if level else None

    async def log_stream_generator():
        """Generate SSE events for log streaming."""
        try:
            async for message in stream_workload_logs(
                workload=workload_with_components,
                start_time=start_time,
                level_filter=level_filter,
                log_type=log_type,
                delay_seconds=delay,
            ):
                yield f"data: {message}\n\n"

            # Send completion marker when stream ends gracefully
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            # Client disconnection - log and exit gracefully
            logger.info(f"Log stream for workload {workload_id} cancelled by client")
            return
        except Exception as e:
            logger.error(f"Log stream error for workload {workload_id}: {e}")
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        log_stream_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
