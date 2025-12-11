# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..managed_workloads.enums import WorkloadStatus, workload_status_to_model_status
from ..managed_workloads.models import ManagedWorkload
from ..models.schemas import ModelEdit
from ..utilities.exceptions import ConflictException, DeletionConflictException, NotFoundException
from ..utilities.models import set_updated_fields
from .models import InferenceModel, OnboardingStatus


async def select_model(
    session: AsyncSession,
    model_id: UUID,
    project_id: UUID,
) -> InferenceModel | None:
    query = select(InferenceModel).where(InferenceModel.id == model_id, InferenceModel.project_id == project_id)
    result = await session.execute(query)
    model = result.scalar_one_or_none()
    return model


async def select_models(
    session: AsyncSession,
    project_id: UUID,
    selected_model_ids: list[UUID] | None = None,
    onboarding_status: OnboardingStatus | None = None,
    name: str | None = None,
) -> list[InferenceModel]:
    query = select(InferenceModel).where(InferenceModel.project_id == project_id)
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
    creator: str,
    project_id: UUID,
    onboarding_status: OnboardingStatus,
    canonical_name: str,
    model_weights_path: str | None = None,
) -> InferenceModel:
    model = InferenceModel(
        name=name,
        created_by=creator,
        updated_by=creator,
        project_id=project_id,
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
        if "inference_models_name_project_id_key" in error_message:
            raise ConflictException(f"A model with name '{name}' already exists in this project")
        raise e


async def update_model(
    session: AsyncSession,
    model: InferenceModel,
    update_data: ModelEdit,
    updater: str,
) -> InferenceModel:
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(model, field, value)
    set_updated_fields(model, updater)
    await session.flush()
    return model


async def can_delete_model(session: AsyncSession, model: InferenceModel | None, model_id: UUID) -> None:
    if not model:
        raise NotFoundException(f"Model with ID {model_id} not found in this project")
    if model.onboarding_status in {OnboardingStatus.pending, OnboardingStatus.ready}:
        # Check if there are active workloads for this specific model
        query_workloads = select(ManagedWorkload).where(
            ManagedWorkload.model_id == model.id,
            ManagedWorkload.status.in_(
                {
                    WorkloadStatus.DELETING,
                    WorkloadStatus.DELETE_FAILED,
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


async def delete_model_by_id(session: AsyncSession, model_id: UUID, project_id: UUID) -> None:
    """Delete a model with weights, raising NotFoundException if not found and DeletionConflictException if ready."""
    model = await select_model(session, model_id, project_id=project_id)
    await can_delete_model(session, model, model_id)
    await session.delete(model)
    await session.flush()


async def delete_models(session: AsyncSession, existing_ids: list[UUID], project_id: UUID) -> list[UUID]:
    """Delete models by existing IDs. Returns list of IDs that were actually deleted."""
    if not existing_ids:
        return []

    deletable_model_ids = []
    deletion_errors = []

    # Check each requested model ID
    for model_id in existing_ids:
        try:
            model = await select_model(session, model_id, project_id=project_id)
            await can_delete_model(session, model, model_id)
            deletable_model_ids.append(model_id)
        except (NotFoundException, DeletionConflictException) as e:
            deletion_errors.append(e)

    # Delete as many models as possible
    if deletable_model_ids:
        query = delete(InferenceModel).where(InferenceModel.id.in_(deletable_model_ids))
        await session.execute(query)
        await session.flush()

    # If there were any deletion errors, raise them as an ExceptionGroup AFTER successful deletions
    if deletion_errors:
        raise ExceptionGroup("Some models could not be deleted", deletion_errors)

    return deletable_model_ids


async def update_onboarding_statuses(session: AsyncSession, project_id: UUID) -> None:
    pending_models = await select_models(session, project_id=project_id, onboarding_status=OnboardingStatus.pending)
    if not pending_models:
        return

    model_ids = [model.id for model in pending_models]

    pending_workloads = await session.execute(select(ManagedWorkload).where(ManagedWorkload.model_id.in_(model_ids)))
    pending_workloads = pending_workloads.unique().scalars().all()

    related_workloads = {}
    for workload in pending_workloads:
        if workload.model_id not in related_workloads:
            related_workloads[workload.model_id] = workload

    for model in pending_models:
        if model.id in related_workloads:
            latest_workload_for_model: ManagedWorkload = related_workloads[model.id]
            model.onboarding_status = workload_status_to_model_status(latest_workload_for_model.status)
            set_updated_fields(model, f"Workload: {latest_workload_for_model.id}")

    await session.flush()
