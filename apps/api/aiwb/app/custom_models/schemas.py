# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Pydantic schemas for custom model preview and onboard."""

from typing import Any

from pydantic import Field, model_validator

from api_common.schemas import BaseModel

from ..aims.crds import AIMModelResource, AIMProfileResource
from ..secrets.constants import SECRET_NAME_MAX_LENGTH, SECRET_NAME_MIN_LENGTH, SECRET_NAME_PATTERN
from .enums import OnboardPhase


class PreviewRequest(BaseModel):
    """Request body for the model source preview endpoint."""

    source: str = Field(
        ...,
        description=(
            "HF repo id or URL; normalized server-side. A revision may be "
            "embedded in the URL (e.g. /tree/<rev> or /blob/<rev>/...); "
            "otherwise the Hub's default branch is used and its SHA is reported."
        ),
        examples=[
            "meta-llama/Llama-3.1-8B-Instruct",
            "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        ],
    )
    hf_token_secret_name: str | None = Field(
        None,
        description="K8s secret name in the namespace containing an HF token under the 'token' key.",
        min_length=SECRET_NAME_MIN_LENGTH,
        max_length=SECRET_NAME_MAX_LENGTH,
        pattern=SECRET_NAME_PATTERN,
        examples=["hf-token"],
    )


class OnboardRequest(BaseModel):
    """Request body for the custom model onboard endpoint.

    Carries the Hub-validated fields returned by preview (possibly edited by
    the user) plus the container image selected in the UI. The server
    re-fetches Hub on every onboard and rejects the request if the supplied
    sha does not match what Hub currently resolves `(repoId, revision)` to,
    so stale or forged Hub fields fail at the API boundary rather than
    landing on the persisted CR.
    """

    repo_id: str = Field(..., min_length=1, description="Canonical repo id from preview.")
    revision: str = Field(..., min_length=1, description="Resolved revision label or SHA from preview.")
    sha: str = Field(..., min_length=1, description="Pinned commit SHA from preview.")
    display_name: str = Field(
        ...,
        min_length=1,
        description=(
            "Display title for the model; may differ from preview suggestion. "
            "Non-empty so the sanitized DISPLAY_NAME_LABEL is non-empty: an empty "
            "label value yields a `display-name=` selector that matches every "
            "AIMModel missing the label, corrupting conflict detection."
        ),
    )
    description: str = Field(default="", description="Catalog description from preview; may be empty.")
    tags: list[str] = Field(default_factory=list, description="HuggingFace Hub tags from preview.")
    image: str = Field(
        ...,
        min_length=1,
        description="Container image reference chosen by the user for the onboarded model.",
    )
    hf_token_secret_name: str | None = Field(
        None,
        description="K8s secret name in the namespace containing an HF token under the 'token' key.",
        min_length=SECRET_NAME_MIN_LENGTH,
        max_length=SECRET_NAME_MAX_LENGTH,
        pattern=SECRET_NAME_PATTERN,
    )
    custom_profile: dict[str, Any] | None = Field(
        None,
        description=(
            "Optional opaque profile overrides written verbatim to "
            "`AIMModel.spec.profiles.overrides`. aim-engine consumes this block at "
            "admission and bakes the values (engine, engineArgs, engineEnv, "
            "containerEnv, metric, precision, accelerator settings, etc.) into each "
            "emitted AIMProfile.spec. `engineEnv` is supplied as `[{name, value}]` "
            "entries (env var names are UPPER_SNAKE_CASE, so they ride as values to "
            "stay outside the camelCase contract); its entry shape is validated and "
            "collapsed to a `map[string]string` server-side. Other fields pass through "
            "verbatim — the API does not validate their shape, and aim-engine rejects "
            "unknown keys at admission. If `customProfile.image` "
            "is supplied it must agree with the top-level `image` field, otherwise "
            "the two image references would disagree once the profile is emitted."
        ),
    )

    @model_validator(mode="after")
    def _reject_conflicting_image_refs(self) -> "OnboardRequest":
        """Reject disagreeing image refs so the deployment image stays unambiguous (422 from FastAPI)."""
        if not self.custom_profile:
            return self
        profile_image = self.custom_profile.get("image")
        if profile_image is None:
            return self
        if profile_image == "":
            raise ValueError(
                "customProfile.image must not be an empty string. "
                "Either omit customProfile.image so the top-level image is used, "
                "or set it to the same non-empty image reference."
            )
        if profile_image == self.image:
            return self
        raise ValueError(
            f"customProfile.image '{profile_image}' conflicts with the top-level "
            f"image '{self.image}'. Either omit customProfile.image so the top-level "
            "image is used, or set them to the same reference."
        )


class CustomModelOnboardStatus(BaseModel):
    """Composed lifecycle status for a custom (BYOM) model.

    Aggregates three independent Kubernetes resources into a single object
    so clients never need to perform their own multi-resource joins:

    * ``state`` — derived lifecycle state spanning the full arc from import
      to deployment (see ``OnboardPhase``).
    * ``status`` — raw AIMModel.status.status string from the controller.
    * ``templateReady`` — whether at least one AIMProfile has been emitted
      by aim-engine for this model. Necessary but not sufficient for
      deployability: profiles derive from the base image, so this can be True
      while the weight import is still Importing or has Failed. Gate deploy on
      ``state == Ready``, not on this flag.
    * ``artifact_phase`` / ``artifact_last_error`` — weight-import signal,
      read primarily from the workbench-owned import annotations on the CR;
      the AIMArtifact is only a fallback for models onboarded before
      annotation-based import existed. Null when neither source is available.

    ``state`` composition rule:
    * ``Ready``     — AIMModel is Ready *and* templateReady is True.
    * ``Failed``    — AIMModel status indicates failure, or AIMArtifact is Failed.
    * ``Importing`` — AIMArtifact exists and is not yet terminal (state not Ready/Failed).
    * ``Pending``   — none of the above; the CR exists and the engine has not yet reacted.

    Display metadata (title, tags, description) is stored in
    ``metadata.annotations`` on the parent ``CustomModelResponse`` rather than
    in a dedicated sub-object, so UI parsers must read annotations directly.
    """

    state: OnboardPhase = Field(
        OnboardPhase.PENDING,
        description="Derived lifecycle state spanning import → ready → deployed.",
    )
    status: str = Field("", description="Raw AIMModel.status.status string from the controller.")
    template_ready: bool = Field(
        False,
        description="True when at least one AIMProfile has been emitted by aim-engine for this model.",
    )
    artifact_phase: str | None = Field(
        None,
        description=(
            "Weight-import phase, read primarily from the workbench-owned import annotations on the CR; "
            "falls back to AIMArtifact.status.phase for models onboarded before annotation-based import. "
            "Null when neither source is available."
        ),
    )
    artifact_last_error: str | None = Field(None, description="Last import error; null when no error.")


class CustomModelResponse(AIMModelResource):
    """Custom (BYOM) model onboarded via the preview endpoint.

    Extends AIMModelResource (namespace-scoped v1alpha2) so the spec reflects
    the actual CR shape — including spec.profiles, modelSources, and image —
    rather than the cluster-scoped AIMClusterModelResource projection that only
    carries spec.image.  Extra fields carry custom-model-specific data that has
    no equivalent in the base CR shape.
    """

    # lifecycle phase that aggregates AIMModel, AIMProfile, and AIMArtifact.
    phase: CustomModelOnboardStatus = Field(
        default_factory=lambda: CustomModelOnboardStatus(state=OnboardPhase.PENDING)
    )
    profile: AIMProfileResource | None = Field(None, description="AIMProfile resource.")


class WeightFile(BaseModel):
    """A single candidate weight file from the Hub repository."""

    path: str = Field(
        ...,
        description="Relative path from the repo root (rfilename from Hub siblings).",
        examples=["model-00001-of-00004.safetensors"],
    )
    size_bytes: int | None = Field(
        None,
        description="File size in bytes; None when Hub did not report it.",
        examples=[4831838208],
    )
    role: str | None = Field(
        None,
        description="Coarse role classification: primary, shard, or config.",
        examples=["primary", "shard", "config"],
    )


class PreviewResponse(BaseModel):
    """Response body for the model source preview endpoint.

    Contains Hub metadata and candidate weight files for UI selection.
    Preview is read-only; persist the model via POST .../models/onboard.
    """

    repo_id: str = Field(
        ...,
        description="Canonical repo id after normalization.",
        examples=["meta-llama/Llama-3.1-8B-Instruct"],
    )
    revision: str = Field(
        ...,
        description=(
            "Resolved revision label or SHA for import. Equal to the revision "
            "label extracted from the source URL (branch, tag, or SHA) when one "
            "was provided; otherwise equal to the SHA of the Hub's default branch."
        ),
        examples=["main"],
    )
    sha: str = Field(
        ...,
        description="Resolved commit SHA from Hub; use this to pin the import.",
        examples=["8ab3a4c1b2d4e5f6789012345678901234567890"],
    )
    display_name: str = Field(
        ...,
        description="Suggested display title derived from Hub card data or repo name.",
        examples=["Llama 3.1 8B Instruct"],
    )
    description: str = Field(
        ...,
        description="Catalog description from Hub card data; may be empty.",
    )
    tags: list[str] = Field(
        ...,
        description="Hub and card tags associated with the model.",
        examples=[["text-generation", "llama", "meta"]],
    )
    pipeline_tag: str | None = Field(
        None,
        description="Hub pipeline tag (e.g. text-generation).",
        examples=["text-generation"],
    )
    gated: bool = Field(
        ...,
        description="True when the Hub model requires license acceptance to download.",
    )
    hf_token_recommended: bool = Field(
        ...,
        description="True when an HF token is required or strongly recommended.",
    )
    weight_files: list[WeightFile] = Field(
        ...,
        description=(
            "All candidate files from the Hub repo. Entries with role 'primary' "
            "or 'shard' are selectable weight blobs; entries with role 'config' "
            "(tokenizer files, README, config.json, etc.) are included for "
            "context and should not be presented as selectable weights."
        ),
    )
    layout_hint: str | None = Field(
        None,
        description=(
            "Coarse layout hint: 'safetensors', 'gguf', 'mixed' when both "
            "formats are present, or null when no recognised weight files "
            "were found."
        ),
        examples=["safetensors"],
    )


class CustomModelPatchRequest(BaseModel):
    """Partial update body for a custom-onboarded model.

    All fields are optional; supply only the fields to change. At least one
    field must be present — enforced in the service layer after
    ``model_dump(exclude_unset=True)``.

    Two groups of edits are supported and may be combined in one request:

    * **Display metadata** (``display_name`` / ``description`` / ``tags``) —
      written to the AIMModel annotations.
    * **Runtime profile** (``image`` / ``custom_profile``) — rewrites
      ``AIMModel.spec.profiles.overrides`` and repatches the live AIMProfile so
      the change takes effect without waiting for a controller reconcile.

    Runtime-profile edits use JSON merge-patch semantics on the overrides block,
    so the client must send the *complete* desired profile: a present key is
    set, a key sent as ``null`` is deleted (reset to the aim-engine default),
    and an omitted key is left unchanged. A profile edit requires the model to
    already have a derived AIMProfile (i.e. be past import); the service rejects
    it otherwise.
    """

    display_name: str | None = Field(
        None,
        min_length=1,
        description="Updated display title for the model card and detail surfaces.",
    )
    description: str | None = Field(
        None,
        description="Updated catalog description; pass an empty string to clear.",
    )
    tags: list[str] | None = Field(
        None,
        description="Replacement tag list; pass an empty list to clear all tags.",
    )
    image: str | None = Field(
        None,
        min_length=1,
        description=(
            "Updated runtime container image reference. Supplying this — alone or "
            "alongside customProfile — triggers a runtime-profile edit: the "
            "AIMModel overrides image and the live AIMProfile deployment-image-ref "
            "annotation are repointed. Requires a derived AIMProfile to exist."
        ),
    )
    custom_profile: dict[str, Any] | None = Field(
        None,
        description=(
            "Complete runtime profile overrides written verbatim to "
            "`AIMModel.spec.profiles.overrides` and merged onto the live "
            "`AIMProfile.spec`. Merge-patch semantics apply: send every field to "
            "keep, send `null` to reset a field to the aim-engine default. The API "
            "does not validate field shape — aim-engine rejects unknown keys at "
            "admission. If `customProfile.image` is supplied it must agree with the "
            "top-level `image`, otherwise the two image references would disagree "
            "once the profile is re-emitted."
        ),
    )

    @model_validator(mode="after")
    def _reject_conflicting_image_refs(self) -> "CustomModelPatchRequest":
        """Reject disagreeing image refs so the deployment image stays unambiguous (422 from FastAPI)."""
        if not self.custom_profile:
            return self
        profile_image = self.custom_profile.get("image")
        if profile_image is None:
            return self
        if profile_image == "":
            raise ValueError(
                "customProfile.image must not be an empty string. "
                "Either omit customProfile.image so the top-level image is used, "
                "or set it to the same non-empty image reference."
            )
        if self.image is not None and profile_image != self.image:
            raise ValueError(
                f"customProfile.image '{profile_image}' conflicts with the top-level "
                f"image '{self.image}'. Either omit customProfile.image so the top-level "
                "image is used, or set them to the same reference."
            )
        return self


class CustomModelPatchResponse(BaseModel):
    """Post-patch display metadata for a custom-onboarded AIMModel."""

    name: str = Field(..., description="AIMModel CR resource name in the namespace.")
    display_name: str = Field(..., description="Current display title.")
    description: str = Field(default="", description="Current catalog description.")
    tags: list[str] = Field(default_factory=list, description="Current tag list.")


class RuntimeProfileOptions(BaseModel):
    """Runtime options a custom model will support, derived from the namespace's base-image profiles.

    A BYOM model inherits its runtime matrix from the base-image model's
    base-role AIMProfiles, so these distinct values are what the onboard wizard
    should offer (and preset) — the onboard-time analogue of the deploy wizard's
    Ready-profile selectors. Empty lists mean the base model has not emitted
    profiles yet; the client should fall back to its static defaults.
    """

    accelerator_models: list[str] = Field(
        default_factory=list,
        description="Distinct acceleratorModel values (e.g. 'MI300X') aim-engine resolves against.",
    )
    precisions: list[str] = Field(
        default_factory=list,
        description="Distinct precisions the base template emits (e.g. 'fp16'); precision is base-determined, not freely chosen.",
    )
    accelerator_counts: list[int] = Field(
        default_factory=list,
        description="Distinct accelerator (GPU) counts per profile, ascending (e.g. [1, 2, 4, 8]).",
    )
    optimization_classes: list[str] = Field(
        default_factory=list,
        description="Distinct optimization tiers (AIMProfile.spec.type, e.g. 'general', 'optimized').",
    )
