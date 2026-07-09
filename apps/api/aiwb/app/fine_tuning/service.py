# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api_common.collections import PaginatedResult, paginate_list
from api_common.exceptions import NotFoundException

from ..aims.crds import AIMModelResource
from ..dispatch.kube_client import KubernetesClient
from ..models.service import get_aim_model, list_aim_models
from ..workloads.constants import WORKLOAD_TYPE_LABEL
from ..workloads.enums import WorkloadType
from ..workloads.repository import get_workload_by_id
from ..workloads.service import delete_workload_components


def _is_fine_tuning_model(model: AIMModelResource) -> bool:
    labels = model.metadata.labels or {}
    return labels.get(WORKLOAD_TYPE_LABEL) == WorkloadType.FINE_TUNING


async def list_fine_tuning_models(
    kube_client: KubernetesClient,
    namespace: str,
    page: int = 1,
    page_size: int = 10,
) -> PaginatedResult[AIMModelResource]:
    # K8s label selector restricts the LIST to fine-tuning AIMModels, so
    # `total` naturally reflects only that subset.
    models = await list_aim_models(
        kube_client=kube_client,
        namespace=namespace,
        label_selector=f"{WORKLOAD_TYPE_LABEL}={WorkloadType.FINE_TUNING}",
    )
    return paginate_list(models, page=page, page_size=page_size)


async def get_fine_tuning_model(
    kube_client: KubernetesClient,
    namespace: str,
    model_id: str,
) -> AIMModelResource:
    model = await get_aim_model(kube_client, namespace, model_id)
    if not _is_fine_tuning_model(model):
        # 404 not 422 because the endpoint is type-scoped to fine-tuning models
        raise NotFoundException(f"Fine-tuning model {model_id} not found")
    return model


async def delete_fine_tuning_job(
    session: AsyncSession,
    namespace: str,
    workload_id: UUID,
) -> None:
    workload = await get_workload_by_id(session=session, workload_id=workload_id, namespace=namespace)
    if not workload or workload.type != WorkloadType.FINE_TUNING:
        # 404 not 422 because the endpoint is type-scoped to fine-tuning jobs
        raise NotFoundException(f"Fine-tuning job {workload_id} not found")

    await delete_workload_components(namespace, workload_id, session, workload=workload)
