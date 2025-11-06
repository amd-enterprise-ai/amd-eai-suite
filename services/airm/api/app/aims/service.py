# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from uuid import UUID

import yaml
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import WorkloadStatus

from ..apikeys.cluster_auth_client import ClusterAuthClient
from ..managed_workloads.repository import insert_workload
from ..managed_workloads.schemas import AIMWorkloadCreate, AIMWorkloadResponse
from ..projects.models import Project
from ..utilities.exceptions import ConflictException, NotFoundException, NotReadyException
from ..workloads.enums import WorkloadType
from ..workloads.service import extract_components_and_submit_workload, submit_delete_workload
from .constants import AMD_CANONICAL_NAME
from .repository import select_aim, select_aim_workload, select_aims_with_workload
from .schemas import AIMDeployRequest, AIMResponse
from .utils import generate_aim_service_manifest, generate_aim_workload_urls


async def get_aim(session: AsyncSession, aim_id: UUID) -> AIMResponse:
    """Get a single AIM by its ID."""
    aim = await select_aim(session, aim_id)
    if not aim:
        raise NotFoundException(f"AIM with ID '{aim_id}' not found")
    return AIMResponse.model_validate(aim)


async def list_aims(session: AsyncSession, project: Project) -> list[AIMResponse]:
    """List all AIMs with their active workload deployment in the specified project."""

    aims_with_workload = await select_aims_with_workload(session, project.id)

    return [
        AIMResponse.model_validate(aim).model_copy(
            update={"workload": AIMWorkloadResponse.model_validate(workload) if workload else None}
        )
        for aim, workload in aims_with_workload
    ]


async def deploy_aim(
    session: AsyncSession,
    aim_id: UUID,
    deploy_request: AIMDeployRequest,
    project: Project,
    creator: str,
    token: str,
    cluster_auth_client: ClusterAuthClient,
    display_name: str | None = None,
) -> AIMWorkloadResponse:
    """Deploy an AIM using direct AIMService CRD creation."""

    aim = await select_aim(session, aim_id)
    if not aim:
        raise NotFoundException(f"AIM with ID '{aim_id}' not found")

    # Check if this AIM is already deployed in this project
    existing_workload = await select_aim_workload(
        session=session,
        aim_id=aim.id,
        project_id=project.id,
        type=[WorkloadType.INFERENCE],
        status=[WorkloadStatus.RUNNING, WorkloadStatus.PENDING],
    )
    if existing_workload:
        raise ConflictException(
            f"AIM '{aim.image_name}:{aim.image_tag}' is already deployed in project '{project.name}'"
        )

    canonical_name = aim.labels.get(AMD_CANONICAL_NAME, None)
    if not canonical_name:
        raise NotReadyException("AIM does not have canonical name configured. Please contact your administrator.")

    workload = await insert_workload(
        session=session,
        creator=creator,
        project=project,
        workload_data=AIMWorkloadCreate(
            type=WorkloadType.INFERENCE,
            display_name=display_name,
            aim_id=aim.id,
            user_inputs={"canonical_name": canonical_name},
        ),
    )
    workload.output = generate_aim_workload_urls(project, workload)
    await session.flush()  # Save the name and output

    # Create cluster-auth group for this AIM deployment when enabled
    group_id = None
    group_name = f"aim-{aim.image_name}-{aim.image_tag}-{workload.name}"
    try:
        group_result = await cluster_auth_client.create_group(name=group_name)
        group_id = group_result["id"]
        workload.cluster_auth_group_id = group_id
        logger.info(f"Created cluster-auth group {group_id} for AIM deployment {workload.name}")
    except Exception as e:
        logger.warning(f"Failed to create cluster-auth group for AIM deployment {workload.name}: {e}")
        # Continue with deployment without group - workload will still be accessible via other auth methods

    await session.flush()  # Save the name, output, and group_id (if set)

    manifest = generate_aim_service_manifest(aim, deploy_request, workload, project, group_id)

    await extract_components_and_submit_workload(
        session=session,
        workload=workload,
        project=project,
        manifest=list(yaml.safe_load_all(manifest)),
        creator=creator,
        token=token,
    )

    return AIMWorkloadResponse.model_validate(workload)


async def undeploy_aim(
    session: AsyncSession, aim_id: UUID, project: Project, user: str, cluster_auth_client: ClusterAuthClient
) -> bool:
    """Undeploy an AIM by finding and deleting its workload."""
    aim = await select_aim(session, aim_id)
    if not aim:
        raise NotFoundException(f"AIM with ID '{aim_id}' not found")

    workload = await select_aim_workload(
        session=session, aim_id=aim.id, project_id=project.id, status=[WorkloadStatus.RUNNING, WorkloadStatus.PENDING]
    )
    if not workload:
        raise NotFoundException(
            f"No active workload found for AIM '{aim.image_name}:{aim.image_tag}' in project '{project.name}'"
        )

    # Clean up cluster-auth group if it exists
    if workload.cluster_auth_group_id:
        try:
            await cluster_auth_client.delete_group(workload.cluster_auth_group_id)
            logger.info(
                f"Deleted cluster-auth group {workload.cluster_auth_group_id} for AIM deployment {workload.name}"
            )
        except Exception as e:
            logger.warning(f"Failed to delete cluster-auth group {workload.cluster_auth_group_id}: {e}")
            # Continue with workload deletion even if group cleanup fails

    return await submit_delete_workload(session=session, workload=workload, user=user)
