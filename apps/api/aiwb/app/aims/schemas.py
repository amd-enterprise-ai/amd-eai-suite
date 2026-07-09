# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from typing import Any

from pydantic import Field, computed_field, model_validator

from api_common.schemas import BaseModel

from .constants import (
    AIM_CHATTABLE_CONDITIONS,
    CLUSTER_AUTH_GROUP_ANNOTATION,
)
from .crds import AIMModelResource, AIMServiceResource, HTTPRouteResource
from .enums import AIMModelStatus, OptimizationMetric
from .utils import extract_endpoints, is_condition_true


class ScalingPolicyMixin(BaseModel):
    """Mixin for scaling policy fields.

    For autoscaling, all three fields (minReplicas, maxReplicas, autoScaling) must be
    provided together. For fixed replicas, use only the 'replicas' field instead.

    NOTE: aim-engine enables KEDA when minReplicas/maxReplicas are set, so these fields
    should only be used with a valid autoScaling configuration containing KEDA metrics.
    """

    min_replicas: int | None = Field(
        None,
        ge=1,
        description="Minimum number of replicas for autoscaling. Requires autoScaling config.",
        examples=[1],
    )
    max_replicas: int | None = Field(
        None,
        ge=1,
        description="Maximum number of replicas for autoscaling. Requires autoScaling config.",
        examples=[5],
    )
    auto_scaling: dict[str, Any] | None = Field(
        None,
        description=(
            "KEDA autoscaling configuration with custom metrics. Required when using minReplicas/maxReplicas. "
            "Example: {'metrics': [{'type': 'PodMetric', 'podmetric': {'metric': {...}, 'target': {...}}}]}"
        ),
    )

    @model_validator(mode="after")
    def validate_scaling_policy(self) -> "ScalingPolicyMixin":
        """Validate that autoscaling fields are provided together."""
        fields = [self.min_replicas, self.max_replicas, self.auto_scaling]
        fields_set = sum(1 for f in fields if f is not None)

        # All three must be provided together or none at all
        # This prevents accidentally enabling KEDA without valid triggers in aim-engine
        if fields_set > 0 and fields_set < 3:
            raise ValueError(
                "Autoscaling requires all three fields: minReplicas, maxReplicas, and autoScaling. "
                "For fixed replicas, use only the 'replicas' field instead."
            )

        # Validate max_replicas >= min_replicas
        if self.min_replicas is not None and self.max_replicas is not None:
            if self.max_replicas < self.min_replicas:
                raise ValueError(f"maxReplicas ({self.max_replicas}) must be >= minReplicas ({self.min_replicas})")

        # autoScaling must not be empty (would cause KEDA errors)
        if self.auto_scaling is not None and self.auto_scaling == {}:
            raise ValueError("autoScaling cannot be empty - provide valid KEDA metrics configuration")

        return self


class ListAimsQuery(BaseModel):
    status_filter: list[AIMModelStatus] | None = Field(default=None, description="Filter by status(es)")


class AIMResponse(AIMModelResource):
    """AIMResponse API response schema.

    Pure pass-through of the ``AIMModelResource`` CRD shape, which backs both
    cluster-scoped ``AIMClusterModel`` and namespace-scoped ``AIMModel``
    resources. AIWB performs no enrichment or formatting on the response —
    consumers read accelerator metadata directly from
    ``status.discoveredProfiles.byHardware[]`` on the resource, mirroring what
    the aim-engine controller publishes.
    """


class AIMDeployRequest(ScalingPolicyMixin):
    """Schema for deploying an AIM with optional scaling policy configuration.

    The `model` field can reference either a cluster-scoped AIMClusterModel or a
    namespace-scoped AIMModel (fine-tuned). The API auto-detects which type it is.
    """

    model: str = Field(
        ...,
        description=(
            "Model resource name. Either an AIMClusterModel name (e.g., 'meta-llama-3-8b') "
            "or a namespace-scoped AIMModel name (fine-tuned model UUID). "
            "The API auto-detects which type it is."
        ),
        examples=["meta-llama-3-8b", "7f3b6c8e-2a1d-4b9f-9c12-1a2b3c4d5e6f"],
    )
    replicas: int = Field(
        1,
        description="Number of replicas for this service.",
        examples=[1, 3],
    )
    image_pull_secrets: list[str] | None = Field(
        None,
        description=(
            "Names of the secrets for pulling AIM container images. "
            "Honored only on cluster-scoped AIMClusterModel deployments; "
            "rejected with 400 when sent for custom-onboarded/fine-tuned models."
        ),
        examples=[["registry-credentials"]],
    )
    hf_token: str | None = Field(
        None,
        description=(
            "Hugging Face token for accessing private models (if required). "
            "Honored only on cluster-scoped AIMClusterModel deployments; "
            "rejected with 400 when sent for custom-onboarded/fine-tuned models."
        ),
        examples=["hf_xxxxxxxxxxxx"],
    )
    metric: OptimizationMetric | None = Field(
        None,
        description=(
            "Profile-selector field written to spec.profile.selector.metric "
            "(latency or throughput). Ignored when profileName is set."
        ),
    )
    precision: str | None = Field(
        None,
        description=(
            "Profile-selector field written to spec.profile.selector.precision "
            "(e.g. fp8, fp16). Ignored when profileName is set."
        ),
        examples=["fp8", "fp16"],
    )
    gpu_model: str | None = Field(
        None,
        description=(
            "Profile-selector field written to spec.profile.selector.acceleratorModel "
            "(e.g. MI300X). Ignored when profileName is set."
        ),
        examples=["MI300X"],
    )
    gpu_count: int | None = Field(
        None,
        ge=1,
        description=(
            "Number of GPUs per replica. Not a profile selector — per ADR 006b §3 "
            "the selector picks profiles by hardware model. When set, written to "
            "``spec.profileOverrides.acceleratorCount`` as a per-service override "
            "on top of the resolved profile."
        ),
        examples=[1, 8],
    )
    engine_args: dict[str, Any] | None = Field(
        None,
        description="Engine launch arguments (e.g. vLLM flags). Forwarded to AIMService.spec.profileOverrides.engineArgs.",
        examples=[{"max-model-len": 8192}],
    )
    engine_env: list[dict[str, Any]] | None = Field(
        None,
        description=(
            "Engine-process environment variables as name/value entries. "
            "Converted to AIMService.spec.profileOverrides.engineEnv."
        ),
        examples=[[{"name": "VLLM_LOGGING_LEVEL", "value": "DEBUG"}]],
    )
    container_env: list[dict[str, Any]] | None = Field(
        None,
        description="Container env entries (K8s EnvVar shape). Forwarded to AIMService.spec.profileOverrides.containerEnv.",
    )
    profile_name: str | None = Field(
        None,
        description=(
            "Explicit AIMProfile/AIMClusterProfile name. When set, "
            "spec.profile.name is written. When unset, the engine resolves "
            "the profile via the model's aimId. Rejected with 400 when sent "
            "for fine-tuned models."
        ),
        examples=["mi300x-throughput-fp8"],
    )
    display_name: str | None = Field(
        None,
        description="User-visible display name for this AIM deployment. Stored as a K8s annotation; any characters are allowed.",
    )


class AIMServicePatchRequest(ScalingPolicyMixin):
    """Request schema for patching an AIMService.

    All fields are optional. Include only the fields you want to update.
    For scaling policy, all three fields (minReplicas, maxReplicas, autoScaling) must be provided together.
    """


class AIMServiceResponse(AIMServiceResource):
    """AIMService API response schema.

    Inherits all fields from AIMServiceResource (metadata, spec, status).
    This is the live K8s CRD data with namespace already in metadata.
    """

    httproute: HTTPRouteResource | None = Field(None, exclude=True)
    inference_service_name: str | None = Field(None, exclude=True)

    @computed_field
    def status_value(self) -> str:
        return self.status.status.value

    @computed_field
    def endpoints(self) -> dict[str, str]:
        # Endpoints require both routing and inference service to be ready.
        # We check both conditions because endpoints represent inference service URLs
        # and should only be shown when the full stack is functional.
        if not all(is_condition_true(self.status.conditions, c) for c in AIM_CHATTABLE_CONDITIONS):
            return {}
        return extract_endpoints(self, httproute=self.httproute, inference_service_name=self.inference_service_name)

    @computed_field
    def cluster_auth_group_id(self) -> str | None:
        """Extract cluster-auth group ID from routing annotations."""
        if not self.spec.routing:
            return None
        routing_annotations = self.spec.routing.get("annotations", {})
        return routing_annotations.get(CLUSTER_AUTH_GROUP_ANNOTATION)
