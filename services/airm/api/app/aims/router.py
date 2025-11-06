# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..apikeys.cluster_auth_client import get_cluster_auth_client
from ..managed_workloads.schemas import AIMWorkloadResponse
from ..utilities.checks import ensure_cluster_healthy
from ..utilities.database import get_session
from ..utilities.security import BearerToken, get_user_email, validate_and_get_project_from_query
from .schemas import AIMDeployRequest, AIMResponse
from .service import deploy_aim, get_aim, list_aims, undeploy_aim

router = APIRouter(prefix="/aims", tags=["AIMs"])


@router.get(
    "/{aim_id}",
    response_model=AIMResponse,
    summary="Get AIM by ID",
    description="""Get a specific AIM by its ID.""",
)
async def get_aim_endpoint(
    aim_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AIMResponse:
    return await get_aim(session=session, aim_id=aim_id)


@router.get(
    "",
    response_model=list[AIMResponse],
    summary="List AIMs with deployment info",
    description="""List all available AIMs with their active workload deployment in the specified project.
    The workload field will be null if the AIM is not currently deployed (RUNNING/PENDING).""",
)
async def list_aims_endpoint(
    project=Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
) -> list[AIMResponse]:
    return await list_aims(session=session, project=project)


@router.post(
    "/{aim_id}/deploy",
    response_model=AIMWorkloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Deploy an AIM",
    description="""Deploy an AIM by providing its ID""",
)
async def deploy_aim_endpoint(
    aim_id: UUID,
    deploy_request: AIMDeployRequest,
    project=Depends(validate_and_get_project_from_query),
    creator=Depends(get_user_email),
    token: str = Depends(BearerToken),
    session: AsyncSession = Depends(get_session),
    cluster_auth_client=Depends(get_cluster_auth_client),
) -> AIMWorkloadResponse:
    ensure_cluster_healthy(project)
    workload = await deploy_aim(
        session=session,
        aim_id=aim_id,
        deploy_request=deploy_request,
        project=project,
        creator=creator,
        token=token,
        cluster_auth_client=cluster_auth_client,
    )

    return AIMWorkloadResponse.model_validate(workload)


@router.post(
    "/{aim_id}/undeploy",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Undeploy an AIM",
    description="""Undeploy an AIM by finding and removing its active workload.""",
)
async def undeploy_aim_endpoint(
    aim_id: UUID,
    project=Depends(validate_and_get_project_from_query),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_user_email),
    cluster_auth_client=Depends(get_cluster_auth_client),
):
    ensure_cluster_healthy(project)
    await undeploy_aim(
        session=session, aim_id=aim_id, project=project, user=user, cluster_auth_client=cluster_auth_client
    )
