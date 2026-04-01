# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from keycloak import KeycloakAdmin
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..clusters.models import Cluster
from ..messaging.schemas import (
    NamespaceDeletedMessage,
    NamespaceStatus,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceDeleteMessage,
    ProjectNamespaceStatusMessage,
    UnmanagedNamespaceMessage,
)
from ..messaging.sender import MessageSender
from ..projects.models import Project
from ..projects.repository import get_project_by_id
from ..utilities.exceptions import NotFoundException
from .models import Namespace
from .repository import (
    create_namespace,
    delete_namespace,
    get_namespace_by_name_and_cluster,
    get_namespace_by_project_and_cluster,
    update_namespace_status,
)
from .utils import _build_namespace_manifest


async def create_namespace_for_project(
    session: AsyncSession, project: Project, cluster_id: UUID, user: str, message_sender: MessageSender
) -> Namespace:
    namespace = Namespace(
        project_id=project.id,
        name=project.name,
        cluster_id=cluster_id,
        status=NamespaceStatus.PENDING,
        status_reason="creating",
        created_by=user,
        updated_by=user,
    )
    await create_namespace(session, namespace)

    manifest = _build_namespace_manifest(namespace.name, namespace.project_id)
    message = ProjectNamespaceCreateMessage(message_type="project_namespace_create", namespace_manifest=manifest)
    await message_sender.enqueue(project.cluster_id, message)

    return namespace


async def update_project_namespace_status(
    kc_admin: KeycloakAdmin, session: AsyncSession, cluster: Cluster, message: ProjectNamespaceStatusMessage
) -> None:
    namespace = await get_namespace_by_project_and_cluster(session, message.project_id, cluster.id)

    if not namespace:
        raise NotFoundException(f"Namespace for project {message.project_id} not found in cluster {cluster.id}.")

    await __update_project_namespace_status(kc_admin, session, namespace, message.status, message.status_reason)


async def __update_project_namespace_status(
    kc_admin: KeycloakAdmin,
    session: AsyncSession,
    namespace: Namespace,
    status: NamespaceStatus,
    status_reason: str | None,
) -> None:
    from ..projects.service import update_project_status_from_components  # noqa: PLC0415

    await update_namespace_status(session, namespace, status, status_reason, "system")

    project = await get_project_by_id(session, namespace.project_id)
    if not project:
        raise NotFoundException(f"Project {namespace.project_id} not found.")

    await update_project_status_from_components(kc_admin, session, project)

    logger.info(f"Updated namespace {project.name} status to {status}.")


async def delete_namespace_in_cluster(
    session: AsyncSession, project: Project, updater: str, message_sender: MessageSender
) -> None:
    namespace = await get_namespace_by_project_and_cluster(session, project.id, project.cluster_id)
    if not namespace:
        raise NotFoundException(f"Namespace for project {project.id} not found in cluster {project.cluster_id}.")

    await update_namespace_status(
        session, namespace, NamespaceStatus.TERMINATING, "Namespace is being deleted", updater
    )
    message = ProjectNamespaceDeleteMessage(
        message_type="project_namespace_delete",
        name=project.name,
        project_id=project.id,
    )
    await message_sender.enqueue(project.cluster_id, message)


async def record_unmanaged_namespace(
    session: AsyncSession, cluster: Cluster, message: UnmanagedNamespaceMessage
) -> None:
    namespace = await get_namespace_by_name_and_cluster(session, cluster.id, message.namespace_name)
    if namespace and namespace.project_id is None:
        await update_namespace_status(
            session,
            namespace,
            message.namespace_status,
            f"Unmanaged namespace status: {message.namespace_status.value}",
            updater="system",
        )
        logger.info(f"Updated unmanaged namespace '{message.namespace_name}' in cluster {cluster.name}")
    elif not namespace:
        namespace = Namespace(
            name=message.namespace_name,
            cluster_id=cluster.id,
            status=message.namespace_status,
            status_reason=f"Unmanaged namespace status: {message.namespace_status.value}",
            project_id=None,
            created_by="system",
            updated_by="system",
        )
        await create_namespace(session, namespace)
        logger.info(f"Created unmanaged namespace '{message.namespace_name}' in cluster {cluster.name}")


async def handle_namespace_deleted(
    kc_admin: KeycloakAdmin, session: AsyncSession, cluster: Cluster, message: NamespaceDeletedMessage
) -> None:
    namespace = await get_namespace_by_name_and_cluster(session, cluster.id, message.namespace_name)

    if not namespace:
        raise NotFoundException(f"Namespace {message.namespace_name} not found in cluster {cluster.id}.")

    if namespace.project_id is not None:
        await __update_project_namespace_status(
            kc_admin, session, namespace, NamespaceStatus.DELETED, "Namespace deleted"
        )
    else:
        await delete_namespace(session, namespace)
        logger.info(f"Deleted unmanaged namespace '{message.namespace_name}' from database")
