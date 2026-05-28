# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from api_common.auth.security import get_user_email
from api_common.database import get_session
from api_common.exceptions import NotFoundException, ValidationException
from api_common.schemas import DeleteBatchRequest, ListResponse, QueryParam

from .repository import delete_overlays, list_overlays
from .schemas import OverlayListQuery, OverlayResponse, OverlayUpdate
from .service import create_overlay, delete_overlay_by_id_service, get_overlay_by_id, parse_overlay_file, update_overlay

router = APIRouter(tags=["Overlays"])


@router.post(
    "/overlays",
    response_model=OverlayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create model deployment overlay",
    description=dedent("""
        Create YAML overlay for customizing AI model deployments on Helm charts.
        Requires super administrator role. Defines model-specific configurations,
        resource requirements, and environment variables for standardized deployments.
    """),
)
async def create_overlay_endpoint(
    chart_id: UUID = Form(alias=to_camel("chart_id"), description="The ID of an existing Chart."),
    overlay_file: UploadFile = File(
        alias=to_camel("overlay_file"), description="YAML file containing the model overlay"
    ),
    canonical_name: str | None = Form(
        None,
        alias=to_camel("canonical_name"),
        description="Optional canonical name to associate the overlay with a model type, for example 'meta-llama/Llama-3.1-8B'.",
        examples=["meta-llama/Llama-3.1-8B"],
    ),
    session: Session = Depends(get_session),
    creator: str = Depends(get_user_email),
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
    description=dedent("""
        Modify existing YAML overlay for AI model deployment customization.
        Requires super administrator role. Updates model-specific configurations
        and deployment parameters for improved workload management.
    """),
)
async def update_overlay_endpoint(
    overlay_id: UUID,
    chart_id: UUID = Form(None, alias=to_camel("chart_id"), description="The ID of an existing Chart."),
    overlay_file: UploadFile | None = File(
        None, alias=to_camel("overlay_file"), description="YAML file containing the model overlay"
    ),
    canonical_name: str | None = Form(
        None,
        alias=to_camel("canonical_name"),
        description="Optional canonical name to associate the overlay with a model type, for example 'meta-llama/Llama-3.1-8B'.",
        examples=["meta-llama/Llama-3.1-8B"],
    ),
    session: Session = Depends(get_session),
    updater: str = Depends(get_user_email),
) -> OverlayResponse:
    overlay_data = None
    if overlay_file:
        overlay_data = await parse_overlay_file(overlay_file)
    if not overlay_data and not chart_id and not canonical_name:
        raise ValidationException("Either 'overlayFile' or 'chartId' or 'canonicalName' must be provided")

    update_kwargs: dict[str, Any] = {"updated_by": updater}
    if chart_id is not None:
        update_kwargs["chart_id"] = chart_id
    if overlay_data is not None:
        update_kwargs["overlay"] = overlay_data
    if canonical_name is not None:
        update_kwargs["canonical_name"] = canonical_name
    overlay_update = OverlayUpdate(**update_kwargs)

    overlay = await update_overlay(
        session=session,
        overlay_id=overlay_id,
        overlay_update=overlay_update,
    )
    return overlay


@router.get(
    "/overlays",
    response_model=ListResponse[OverlayResponse],
    summary="List deployment overlays",
    description=dedent("""
        List all available YAML overlays for AI model deployment customization.
        Used for discovering available model configurations and deployment patterns
        across different AI model types and use cases.
    """),
)
async def list_overlays_endpoint(
    query: QueryParam[OverlayListQuery],
    session: Session = Depends(get_session),
) -> ListResponse[OverlayResponse]:
    """
    List all model overlays.
    """
    items = await list_overlays(
        session=session,
        chart_id=query.chart_id,
        canonical_name=query.canonical_name,
    )
    return ListResponse(data=items)


@router.get(
    "/overlays/{overlay_id}",
    response_model=OverlayResponse,
    summary="Get deployment overlay details",
    description=dedent("""
        Retrieve detailed information about a specific YAML overlay including
        configuration content and associated model metadata. Used for understanding
        deployment specifications before model workload submission.
    """),
)
async def get_overlay_endpoint(
    overlay_id: UUID,
    session: Session = Depends(get_session),
) -> OverlayResponse:
    overlay = await get_overlay_by_id(session, overlay_id)
    return overlay


@router.delete(
    "/overlays/{overlay_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete deployment overlay",
    description=dedent("""
        Remove YAML overlay from system permanently. Requires super administrator
        role. Affects future model deployments that depend on this overlay
        configuration - use with caution in production environments.
    """),
)
async def delete_overlay_endpoint(
    overlay_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    await delete_overlay_by_id_service(session, overlay_id)


@router.post(
    "/overlays/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bulk delete deployment overlays",
    description=dedent("""
        Atomic bulk deletion of multiple YAML overlays. Requires super administrator
        role. All-or-nothing operation ensures consistency - fails completely if
        any overlay ID is invalid or currently in use.
    """),
)
async def batch_delete_overlays(
    data: DeleteBatchRequest,
    session: Session = Depends(get_session),
) -> None:
    deleted_ids = await delete_overlays(session=session, ids=data.ids)
    missing_ids = set(data.ids) - set(deleted_ids)
    if missing_ids:
        raise NotFoundException(f"Overlays with IDs {list(missing_ids)} not found")
