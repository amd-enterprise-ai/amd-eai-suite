# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from ..utilities.database import get_session
from ..utilities.exceptions import NotFoundException, ValidationException
from ..utilities.schema import DeleteOverlaysBatchRequest
from ..utilities.security import ensure_super_administrator, get_user_email
from .repository import delete_overlays, list_overlays
from .schemas import OverlayResponse, OverlaysResponse, OverlayUpdate
from .service import create_overlay, delete_overlay_by_id_service, get_overlay_by_id, parse_overlay_file, update_overlay

router = APIRouter(tags=["Overlays"])


@router.post(
    "/overlays",
    response_model=OverlayResponse,
    summary="Create model deployment overlay",
    description="""
        Create YAML overlay for customizing AI model deployments on Helm charts.
        Requires super administrator role. Defines model-specific configurations,
        resource requirements, and environment variables for standardized deployments.
    """,
)
async def create_overlay_endpoint(
    chart_id: UUID = Form(description="The ID of an existing Chart."),
    overlay_file: UploadFile = File(description="YAML file containing the model overlay"),
    canonical_name: str | None = Form(
        None,
        description="Optional canonical name to associate the overlay with a model type, for example 'meta-llama/Llama-3.1-8B'.",
        examples=["meta-llama/Llama-3.1-8B"],
    ),
    session: Session = Depends(get_session),
    creator: str = Depends(get_user_email),
    _: None = Depends(ensure_super_administrator),
) -> OverlayResponse:
    overlay_data = await parse_overlay_file(overlay_file)
    overlay = await create_overlay(
        session=session,
        chart_id=chart_id,
        overlay_data=overlay_data,
        canonical_name=canonical_name,
        creator=creator,
    )
    return overlay


@router.put(
    "/overlays/{overlay_id}",
    response_model=OverlayResponse,
    summary="Update deployment overlay",
    description="""
        Modify existing YAML overlay for AI model deployment customization.
        Requires super administrator role. Updates model-specific configurations
        and deployment parameters for improved workload management.
    """,
)
async def update_overlay_endpoint(
    overlay_id: UUID,
    chart_id: UUID = Form(None, description="The ID of an existing Chart."),
    overlay_file: UploadFile | None = File(None, description="YAML file containing the model overlay"),
    canonical_name: str | None = Form(
        None,
        description="Optional canonical name to associate the overlay with a model type, for example 'meta-llama/Llama-3.1-8B'.",
        examples=["meta-llama/Llama-3.1-8B"],
    ),
    session: Session = Depends(get_session),
    updater: str = Depends(get_user_email),
    _: None = Depends(ensure_super_administrator),
) -> OverlayResponse:
    overlay_data = None
    if overlay_file:
        overlay_data = await parse_overlay_file(overlay_file)
    if not overlay_data and not chart_id and not canonical_name:
        raise ValidationException("Either 'overlay_file' or 'chart_id' or 'canonical_name' must be provided")
    overlay_update = OverlayUpdate(
        chart_id=chart_id, overlay=overlay_data, canonical_name=canonical_name, updated_by=updater
    )

    overlay = await update_overlay(
        session=session,
        overlay_id=overlay_id,
        overlay_update=overlay_update,
    )
    return overlay


@router.get(
    "/overlays",
    response_model=OverlaysResponse,
    summary="List deployment overlays",
    description="""
        List all available YAML overlays for AI model deployment customization.
        Used for discovering available model configurations and deployment patterns
        across different AI model types and use cases.
    """,
)
async def list_overlays_endpoint(
    chart_id: UUID | None = Query(None, description="Optionally filter by chart ID"),
    canonical_name: str | None = Query(
        None,
        description="Optionally filter by overlays compatible to models with a specific canonical name. This also includes overlays with no canonical name specified.",
    ),
    session: Session = Depends(get_session),
    _: str = Depends(get_user_email),
) -> OverlaysResponse:
    """
    List all model overlays.
    """
    items = await list_overlays(
        session=session,
        chart_id=chart_id,
        canonical_name=canonical_name,
    )
    return OverlaysResponse(data=items)


@router.get(
    "/overlays/{overlay_id}",
    response_model=OverlayResponse,
    summary="Get deployment overlay details",
    description="""
        Retrieve detailed information about a specific YAML overlay including
        configuration content and associated model metadata. Used for understanding
        deployment specifications before model workload submission.
    """,
)
async def get_overlay_endpoint(
    overlay_id: UUID,
    session: Session = Depends(get_session),
    _: str = Depends(get_user_email),
) -> OverlayResponse:
    overlay = await get_overlay_by_id(session, overlay_id)
    return overlay


@router.delete(
    "/overlays/{overlay_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete deployment overlay",
    description="""
        Remove YAML overlay from system permanently. Requires super administrator
        role. Affects future model deployments that depend on this overlay
        configuration - use with caution in production environments.
    """,
)
async def delete_overlay_endpoint(
    overlay_id: UUID,
    session: Session = Depends(get_session),
    _: str = Depends(get_user_email),
    __: None = Depends(ensure_super_administrator),
) -> None:
    await delete_overlay_by_id_service(session, overlay_id)


@router.post(
    "/overlays/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bulk delete deployment overlays",
    description="""
        Atomic bulk deletion of multiple YAML overlays. Requires super administrator
        role. All-or-nothing operation ensures consistency - fails completely if
        any overlay ID is invalid or currently in use.
    """,
)
async def batch_delete_overlays(
    data: DeleteOverlaysBatchRequest,
    session: Session = Depends(get_session),
    _: str = Depends(get_user_email),
    __: None = Depends(ensure_super_administrator),
) -> None:
    deleted_ids = await delete_overlays(session=session, ids=data.ids)
    missing_ids = set(data.ids) - set(deleted_ids)
    if missing_ids:
        raise NotFoundException(f"Overlays with IDs {list(missing_ids)} not found")
