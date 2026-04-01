# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api_common.exceptions import ConflictException, DeletionConflictException, NotFoundException
from api_common.models import set_updated_fields

from ..workloads.enums import WorkloadStatus
from ..workloads.models import Workload
from .models import InferenceModel, OnboardingStatus


def workload_status_to_model_status(status: WorkloadStatus) -> OnboardingStatus:
    """Convert workload status to model onboarding status."""
    match status:
        case WorkloadStatus.COMPLETE:
            return OnboardingStatus.ready
        case WorkloadStatus.FAILED:
            return OnboardingStatus.failed
        case _:
            return OnboardingStatus.pending


async def select_model(
    session: AsyncSession,
    model_id: UUID,
    namespace: str,
) -> InferenceModel | None:
    query = select(InferenceModel).where(InferenceModel.id == model_id, InferenceModel.namespace == namespace)
    result = await session.execute(query)
    model = result.scalar_one_or_none()
    return model


async def select_models(
    session: AsyncSession,
    namespace: str,
    selected_model_ids: list[UUID] | None = None,
    onboarding_status: OnboardingStatus | None = None,
    name: str | None = None,
) -> list[InferenceModel]:
    query = select(InferenceModel).where(InferenceModel.namespace == namespace)
    if selected_model_ids:
        query = query.where(InferenceModel.id.in_(selected_model_ids))
    if onboarding_status:
        query = query.where(InferenceModel.onboarding_status == onboarding_status)
    if name:
        query = query.where(InferenceModel.name == name)
    result = await session.execute(query)
    return result.scalars().all()


async def insert_model(
    session: AsyncSession,
    name: str,
    submitter: str,
    namespace: str,
    onboarding_status: OnboardingStatus,
    canonical_name: str,
    model_weights_path: str | None = None,
) -> InferenceModel:
    model = InferenceModel(
        name=name,
        created_by=submitter,
        updated_by=submitter,
        namespace=namespace,
        onboarding_status=onboarding_status,
        model_weights_path=model_weights_path,
        canonical_name=canonical_name,
    )
    session.add(model)
    try:
        await session.flush()
        return model
    except IntegrityError as e:
        error_message = str(e)
        if "inference_models_name_namespace_key" in error_message:
            raise ConflictException(f"A model with name '{name}' already exists in this namespace")
        raise e


async def can_delete_model(session: AsyncSession, model: InferenceModel | None, model_id: UUID) -> None:
    if not model:
        raise NotFoundException(f"Model with ID {model_id} not found in this namespace")
    if model.onboarding_status in {OnboardingStatus.pending, OnboardingStatus.ready}:
        query_workloads = select(Workload).where(
            Workload.model_id == model.id,
            Workload.status.in_(
                {
                    WorkloadStatus.DELETING,
                    WorkloadStatus.PENDING,
                    WorkloadStatus.RUNNING,
                    WorkloadStatus.UNKNOWN,
                }
            ),
        )
        result = await session.execute(query_workloads)
        if result.first() is not None:
            match model.onboarding_status:
                case OnboardingStatus.ready:
                    raise DeletionConflictException("Cannot delete model that is currently being used by a workload")
                case OnboardingStatus.pending:
                    raise DeletionConflictException("Cannot delete model that is currently being onboarded")


async def delete_model_by_id(session: AsyncSession, model_id: UUID, namespace: str) -> None:
    """Delete a model with weights, raising NotFoundException if not found and DeletionConflictException if ready."""
    model = await select_model(session, model_id, namespace=namespace)
    await can_delete_model(session, model, model_id)
    await session.delete(model)
    await session.flush()


# TODO: if we have time, we could move this to a syncer
async def update_onboarding_statuses(session: AsyncSession, namespace: str) -> None:
    pending_models = await select_models(session, namespace=namespace, onboarding_status=OnboardingStatus.pending)
    if not pending_models:
        return

    model_ids = [model.id for model in pending_models]

    pending_workloads = await session.execute(select(Workload).where(Workload.model_id.in_(model_ids)))
    pending_workloads = pending_workloads.unique().scalars().all()

    related_workloads = {}
    for workload in pending_workloads:
        if workload.model_id not in related_workloads:
            related_workloads[workload.model_id] = workload

    for model in pending_models:
        if model.id in related_workloads:
            latest_workload_for_model: Workload = related_workloads[model.id]
            model.onboarding_status = workload_status_to_model_status(latest_workload_for_model.status)
        else:
            model.onboarding_status = OnboardingStatus.failed
        set_updated_fields(model, "system")

    await session.flush()
