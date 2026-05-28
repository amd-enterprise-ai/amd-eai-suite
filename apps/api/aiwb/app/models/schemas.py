# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import Field

from api_common.schemas import BaseModel


class FinetunableModelResponse(BaseModel):
    canonical_name: str = Field(
        description="The canonical name of the finetunable model.", examples=["meta-llama/Llama-3.1-8B"]
    )
    gpu_count: int | None = Field(None, description="Number of GPUs required for finetuning, or null if unspecified.")
    compatible_accelerators: list[str] = Field(
        default_factory=list,
        description="AMD GPU device IDs this recipe is compatible with.",
    )
    compatible_accelerator_names: list[str] = Field(
        default_factory=list,
        description="Display names for the compatible AMD GPUs, resolved from cluster node labels.",
    )


class FinetuneJobResponse(BaseModel):
    """Response returned when a finetuning job is submitted.

    Represents the pending job, not yet an AIMModel CR (which is created upon completion).
    """

    workload_id: UUID = Field(description="AIWB workload ID to track the job.")
    model_name: str = Field(description="Name of the finetuned model to be produced.")
    base_model: str = Field(description="Canonical name of the base model being finetuned.")
    namespace: str = Field(description="Namespace where the job runs.")
    status: str = Field(default="Pending", description="Initial job status.")


class FinetuneCreate(BaseModel):
    name: str = Field(
        description="The name of the finetuning job and the resulting finetuned model. "
        "Must contain only letters, digits, dots, underscores, and hyphens (no spaces).",
        pattern=r"^[a-zA-Z0-9._-]+$",
    )
    dataset_id: UUID = Field(description="The ID of the dataset to be used for finetuning")
    epochs: int | None = Field(description="The number of epochs to train the model for", default=1, ge=1)
    learning_rate: float | None = Field(description="The learning rate for the training process", default=1.41421, gt=0)
    batch_size: int | None = Field(description="The batch size for the training process", default=2, ge=1)
    hf_token_secret_name: str | None = Field(
        description="Optional HuggingFace token secret name for downloading private models", default=None
    )
