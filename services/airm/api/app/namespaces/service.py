# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import itertools
from uuid import UUID

from keycloak import KeycloakAdmin
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from airm.messaging.schemas import (
    NamespaceStatus,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceDeleteMessage,
    ProjectNamespaceStatusMessage,
)

from ..clusters.models import Cluster
from ..messaging.sender import MessageSender
from ..organizations.models import Organization
from ..projects.models import Project
from ..projects.repository import get_project_in_organization
from ..utilities.exceptions import NotFoundException
from .models import Namespace
from .repository import (
    create_namespace,
    get_namespace_by_project_and_cluster,
    get_namespaces_by_organisation,
    update_namespace_status,
)
from .schemas import ClusterNamespaces, ClustersWithNamespaces, NamespaceResponse


async def get_namespaces_by_cluster_for_organization(
    session: AsyncSession, organization: Organization
) -> ClustersWithNamespaces:
    namespaces = await get_namespaces_by_organisation(session, organization.id)

    clusters = [
        ClusterNamespaces(cluster_id=cluster_id, namespaces=[NamespaceResponse.model_validate(ns) for ns in ns_group])
        for cluster_id, ns_group in itertools.groupby(namespaces, key=lambda ns: ns.cluster_id)
    ]
    return ClustersWithNamespaces(clusters_namespaces=clusters)


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

    message = ProjectNamespaceCreateMessage(
        message_type="project_namespace_create", name=namespace.name, project_id=namespace.project_id
    )
    await message_sender.enqueue(project.cluster_id, message)

    return namespace


async def update_project_namespace_status(
    kc_admin: KeycloakAdmin, session: AsyncSession, cluster: Cluster, message: ProjectNamespaceStatusMessage
) -> None:
    from ..projects.service import update_project_status_from_components

    namespace = await get_namespace_by_project_and_cluster(session, message.project_id, cluster.id)

    if not namespace:
        raise NotFoundException(f"Namespace for project {message.project_id} not found in cluster {cluster.id}.")

    await update_namespace_status(session, namespace, message.status, message.status_reason, "system")

    project = await get_project_in_organization(session, cluster.organization_id, namespace.project_id)
    if not project:
        raise NotFoundException(f"Project {namespace.project_id} not found in organization {cluster.organization_id}.")

    await update_project_status_from_components(kc_admin, session, project)

    logger.info(f"Updated namespace {project.name} status to {message.status}.")


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
