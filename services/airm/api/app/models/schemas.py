# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..utilities.config import MINIO_BUCKET
from ..utilities.schema import BaseEntityPublic
from .models import OnboardingStatus


class ModelCreate(BaseModel):
    canonical_name: str = Field(
        description="The canonical name of the model. Used to identify models of the same origin for training purposes.",
        examples=["meta-llama/Llama-3.1-8B"],
    )
    name: str | None = Field(
        None,
        description="An optional name for the model. If not defined, the canonical name is used.",
        examples=["meta-llama/Llama-3.1-8B"],
    )
    model_weights_path: str | None = Field(
        None,
        description="The path to the model weights. If not defined, the path is generated from the canonical name.",
        examples=[f"{MINIO_BUCKET}/my-project/models/meta-llama/Llama-3.1-8B"],
    )


class ModelEdit(BaseModel):
    """Schema for editing models with all fields optional"""

    name: str | None = None

    model_config = ConfigDict(extra="ignore")


class ModelResponse(BaseEntityPublic):
    """Schema for model responses"""

    canonical_name: str = Field(description="The canonical name of the model.", examples=["meta-llama/Llama-3.1-8B"])
    name: str = Field(description="The name of the model.", examples=["meta-llama/Llama-3.1-8B"])
    model_weights_path: str | None = Field(None, description="The path to the model weights.")
    onboarding_status: OnboardingStatus = Field(
        OnboardingStatus.pending, description="The current onboarding status of the model"
    )

    model_config = ConfigDict(from_attributes=True)


class FinetuneCreate(BaseModel):
    name: str = Field(description="The name of the finetuning job and the resulting finetuned model")
    dataset_id: UUID = Field(description="The ID of the dataset to be used for finetuning")
    epochs: int | None = Field(description="The number of epochs to train the model for", default=1)
    learning_rate: float | None = Field(description="The learning rate for the training process", default=1.41421)
    batch_size: int | None = Field(description="The batch size for the training process", default=2)
    hf_token_secret_id: UUID | None = Field(
        description="Optional HuggingFace token secret ID for downloading private models", default=None
    )


class DeleteModelsBatchRequest(BaseModel):
    ids: list[UUID]


class ModelDeployRequest(BaseModel):
    image: str | None = Field(default=None, description="Container image to use for the workspace")
    gpus: int | None = Field(default=None, description="Number of GPUs to allocate to the workspace", ge=0, le=8)
    memory_per_gpu: int | None = Field(default=None, description="Memory per GPU in Gi", ge=1)
    cpu_per_gpu: float | None = Field(default=None, description="CPU per GPU in vCPUs", ge=1)
    replicas: int | None = Field(default=None, description="Number of inference replicas to deploy", ge=1, le=10)


class FinetunableModelsResponse(BaseModel):
    data: list[str] = Field(description="List of canonical names of all finetunable models")


class ModelsResponse(BaseModel):
    data: list[ModelResponse] = Field(description="List of models")
