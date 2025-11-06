# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from fastapi import APIRouter, Depends, status

from ..utilities.database import get_session
from ..utilities.security import ensure_platform_administrator, get_user_organization
from .schemas import ClustersWithNamespaces
from .service import get_namespaces_by_cluster_for_organization

router = APIRouter(tags=["Namespaces"])


@router.get(
    "/namespaces",
    operation_id="get_namespaces",
    summary="Get all namespaces for an organization, grouped by cluster",
    status_code=status.HTTP_200_OK,
    response_model=ClustersWithNamespaces,
)
async def get_namespaces(
    _=Depends(ensure_platform_administrator),
    organization=Depends(get_user_organization),
    session=Depends(get_session),
) -> ClustersWithNamespaces:
    return await get_namespaces_by_cluster_for_organization(session, organization)
