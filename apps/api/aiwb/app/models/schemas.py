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
    gpu_count: int | None = Field(
        None,
        description="Number of GPUs required for finetuning, or null if unspecified.",
        examples=[1, 2, 4, 8],
    )
    compatible_accelerators: list[str] = Field(
        default_factory=list,
        description="AMD GPU device IDs this recipe is compatible with.",
        examples=[["0x74a1"]],
    )
    compatible_accelerator_names: list[str] = Field(
        default_factory=list,
        description="Display names for the compatible AMD GPUs, resolved from cluster node labels.",
        examples=[["AMD Instinct MI300X"]],
    )
    hf_token_required: bool | None = Field(
        None,
        description="Whether this base model is gated on Hugging Face and requires a token to download. "
        "Read from the recipe overlay's top-level `hfTokenRequired` field. Null when the overlay does "
        "not declare it.",
        examples=[True, False],
    )


class FinetuneJobResponse(BaseModel):
    """Response returned when a finetuning job is submitted.

    Represents the pending job, not yet an AIMModel CR (which is created upon completion).
    """

    workload_id: UUID = Field(
        description="AIWB workload ID to track the job.",
        examples=["7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"],
    )
    display_name: str = Field(
        description="Name of the finetuned model to be produced.",
        examples=["imdb-classifier-v3"],
    )
    base_model: str = Field(
        description="Canonical name of the base model being finetuned.",
        examples=["meta-llama/Llama-3.1-8B"],
    )
    namespace: str = Field(
        description="Namespace where the job runs.",
        examples=["acme-summarizer"],
    )
    status: str = Field(default="Pending", description="Initial job status.", examples=["Pending"])


class FinetuneCreate(BaseModel):
    display_name: str = Field(
        min_length=1,
        description="The user-visible name for the finetuning job and the resulting finetuned model. Any characters are allowed.",
        examples=["imdb-classifier-v3"],
    )
    dataset_id: UUID = Field(
        description="The ID of the dataset to be used for finetuning",
        examples=["7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"],
    )
    epochs: int | None = Field(
        description="The number of epochs to train the model for",
        default=1,
        ge=1,
        examples=[1, 3, 10],
    )
    learning_rate: float | None = Field(
        description="The learning rate for the training process",
        default=1.41421,
        gt=0,
        examples=[1.41421, 0.0001],
    )
    batch_size: int | None = Field(
        description="The batch size for the training process",
        default=2,
        ge=1,
        examples=[2, 4, 8],
    )
    hf_token_secret_name: str | None = Field(
        description="Optional HuggingFace token secret name for downloading private models",
        default=None,
        examples=["hf-token"],
    )
