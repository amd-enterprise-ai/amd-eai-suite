# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from textwrap import dedent

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.auth.security import get_user_email
from api_common.database import get_session

from ..dispatch.kube_client import KubernetesClient, get_kube_client
from ..namespaces.security import ensure_access_to_workbench_namespace
from ..workloads.schemas import WorkloadResponse
from .enums import WorkspaceType
from .schemas import DevelopmentWorkspaceRequest
from .service import create_development_workspace

router = APIRouter(tags=["Workspaces"])


@router.post(
    "/namespaces/{namespace}/workspaces/{workspace_type}",
    response_model=WorkloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create development workspace",
    description=dedent("""
        Create interactive development workspace (Jupyter, VS Code, MLflow, ComfyUI) for AI/ML development.
        Provisions containerized environment with optional GPU access for model development and experimentation.

        **Workspace Types:**
        - **jupyterlab**: Interactive notebook environment for data science
        - **vscode**: Browser-based Visual Studio Code with full IDE features
        - **comfyui**: Visual interface for AI image generation workflows
        - **mlflow**: Experiment tracking and model registry (namespace-scoped)

        **Workspace Limitations:**
        - MLflow workspaces are limited to one active instance per namespace
        - JupyterLab, VS Code, and ComfyUI workspaces are user-scoped and limited to one active instance per user per namespace

        Returns 409 Conflict if attempting to create a workspace of a given type when an instance
        with the same scope (namespace for MLflow; user and namespace for other types) is already
        running or pending.
    """),
)
async def create_workspace_endpoint(
    request: DevelopmentWorkspaceRequest,
    workspace_type: WorkspaceType = Path(..., description="Type of workspace to create"),
    display_name: str | None = Query(None, description="User-friendly display name for the workspace"),
    namespace: str = Depends(ensure_access_to_workbench_namespace),
    session: AsyncSession = Depends(get_session),
    submitter: str = Depends(get_user_email),
    kube_client: KubernetesClient = Depends(get_kube_client),
) -> WorkloadResponse:
    """Create and deploy a new development workspace."""

    workload = await create_development_workspace(
        session=session,
        kube_client=kube_client,
        submitter=submitter,
        namespace=namespace,
        request=request,
        workspace_type=workspace_type,
        display_name=display_name,
    )

    return WorkloadResponse.model_validate(workload)
