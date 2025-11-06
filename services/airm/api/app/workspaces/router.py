# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..managed_workloads.schemas import ChartWorkloadResponse
from ..utilities.checks import ensure_base_url_configured, ensure_cluster_healthy
from ..utilities.database import get_session
from ..utilities.security import (
    BearerToken,
    get_user,
    validate_and_get_project_from_query,
)
from .enums import WorkspaceType
from .schemas import DevelopmentWorkspaceRequest
from .service import create_development_workspace

router = APIRouter(tags=["Workspaces"])


@router.post(
    "/workspaces/{workspace_type}",
    response_model=ChartWorkloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create development workspace",
    description="""
        Create interactive development workspace (Jupyter, VS Code, MLflow) for AI/ML development.
        Requires project membership and healthy cluster status. Provisions containerized
        environment with GPU access for model development and experimentation.

        **Workspace Limitations:**
        - MLflow workspaces are limited to one active instance per project
        - Other workspace types (Jupyter, VS Code) have no such restrictions

        Returns 409 Conflict if attempting to create an MLflow workspace when one is already
        running or pending in the project.
    """,
)
async def create_workspace_endpoint(
    request: DevelopmentWorkspaceRequest,
    workspace_type: WorkspaceType = Path(..., description="Type of workspace to create"),
    display_name: str | None = Query(None, description="User-friendly display name for the workload"),
    project=Depends(validate_and_get_project_from_query),
    user=Depends(get_user),
    token: str = Depends(BearerToken),
    session: AsyncSession = Depends(get_session),
):
    ensure_cluster_healthy(project)
    ensure_base_url_configured(project)

    return await create_development_workspace(
        session=session,
        creator=user,
        project=project,
        request=request,
        token=token,
        workspace_type=workspace_type,
        display_name=display_name,
    )
