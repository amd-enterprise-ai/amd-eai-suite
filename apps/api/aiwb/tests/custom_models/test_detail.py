# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Unit tests for the custom-model detail endpoint.

Covers:
* _compose_onboard_status — all phase transitions
* _resolve_image_metadata — status preference and annotation fallback
* extract_hf_token_secret_name — overrides.modelSources[].env extraction
* list_custom_models — bulk join, non-custom CR filtering
* get_custom_model — happy path, CR not found, non-custom CR
* Router: GET /projects/{project}/models/{model_name} — HTTP layer
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api_common.exceptions import NotFoundException
from app import app  # type: ignore[attr-defined]
from app.aims.constants import AIM_MODEL_LABEL
from app.aims.crds import (
    AIMArtifactResource,
    AIMArtifactStatus,
    AIMImageMetadata,
    AIMModelProfilesDerivedFrom,
    AIMModelProfilesSpec,
    AIMModelResource,
    AIMModelSource,
    AIMModelSpec,
    AIMModelStatusFields,
    AIMProfileResource,
    AIMProfileSpec,
    ProfileOverrides,
    ProfileSelector,
    ProfileSelectorModelRef,
)
from app.custom_models.constants import (
    AIM_DEPLOYMENT_IMAGE_REF_ANNOTATION,
    CANONICAL_REPO_ID_ANNOTATION,
    IMPORT_ERROR_ANNOTATION,
    IMPORT_STATE_ANNOTATION,
    MODEL_DISPLAY_NAME_ANNOTATION,
    REVISION_ANNOTATION,
    SOURCE_DESCRIPTION_ANNOTATION,
    SOURCE_SHA_ANNOTATION,
    SOURCE_TAGS_ANNOTATION,
    SOURCE_URI_ANNOTATION,
)
from app.custom_models.enums import OnboardPhase
from app.custom_models.schemas import CustomModelOnboardStatus, CustomModelResponse, RuntimeProfileOptions
from app.custom_models.service import (
    _compose_onboard_status,
    get_base_runtime_profile_options,
    get_custom_model,
    list_custom_models,
)
from app.custom_models.utils import extract_hf_token_secret_name
from app.dispatch.crds import K8sMetadata
from app.workloads.constants import MODEL_SOURCE_TYPE_LABEL
from app.workloads.enums import ModelSourceType
from tests.dependency_overrides import BASE_OVERRIDES, override_dependencies

# ---------------------------------------------------------------------------
# Shared fixtures / builders
# ---------------------------------------------------------------------------

_NAMESPACE = "test-namespace"
_MODEL_NAME = "tinyllama-import-abc12345"
_REPO_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def _make_profiles_spec(
    *,
    repo_id: str = _REPO_ID,
    image: str = "docker.io/amd/tinyllama:1.0.0",
    env: list | None = None,
) -> AIMModelProfilesSpec:
    """Build the v1alpha2 spec.profiles block an onboarded custom model carries.

    ``env`` (e.g. an HF_TOKEN entry) rides on the weights source it authorizes,
    matching what the onboard builder emits.
    """
    return AIMModelProfilesSpec(
        derived_from=AIMModelProfilesDerivedFrom(
            selector=ProfileSelector(
                role="base",
                model_ref=ProfileSelectorModelRef(name="aim-base", scope="Namespace"),
            ),
        ),
        version_policy="all",
        overrides=ProfileOverrides(
            aim_id=repo_id,
            model_id=repo_id,
            image=image,
            model_sources=[
                AIMModelSource(
                    model_id=repo_id,
                    source_uri=f"s3://bucket/{_NAMESPACE}/custom-models/weights/",
                    env=env,
                )
            ],
        ),
    )


def _make_cr(
    name: str = _MODEL_NAME,
    aim_model_status: str = "NotAvailable",  # maps to cr.status.status; must be a valid AIMModelStatus
    annotations: dict | None = None,
    env: list | None = None,
    image_metadata: AIMImageMetadata | None = None,
) -> AIMModelResource:
    """Build a minimal v1alpha2 (profiles-shaped) AIMModelResource for testing."""
    base_annotations = {
        REVISION_ANNOTATION: "main",
        SOURCE_SHA_ANNOTATION: "abc123",
        SOURCE_URI_ANNOTATION: f"s3://bucket/{_NAMESPACE}/custom-models/{name}/weights/",
        MODEL_DISPLAY_NAME_ANNOTATION: "TinyLlama Chat",
        CANONICAL_REPO_ID_ANNOTATION: _REPO_ID,
        SOURCE_DESCRIPTION_ANNOTATION: "A tiny model.",
        SOURCE_TAGS_ANNOTATION: json.dumps(["text-generation", "llama"]),
    }
    if annotations:
        base_annotations.update(annotations)

    return AIMModelResource(
        metadata=K8sMetadata(name=name, namespace=_NAMESPACE, annotations=base_annotations),
        spec=AIMModelSpec(profiles=_make_profiles_spec(env=env)),
        status=AIMModelStatusFields(
            status=aim_model_status,
            image_metadata=image_metadata or AIMImageMetadata(),
        ),
    )


def _make_profile(
    model_name: str = _MODEL_NAME,
    with_image_ref: bool = True,
) -> AIMProfileResource:
    """Build a minimal AIMProfileResource for testing."""
    annotations = {}
    if with_image_ref:
        annotations[AIM_DEPLOYMENT_IMAGE_REF_ANNOTATION] = "amdenterpriseai/aim-base:0.11"
    return AIMProfileResource(
        metadata=K8sMetadata(
            name=f"{model_name}-default",
            namespace=_NAMESPACE,
            labels={AIM_MODEL_LABEL: model_name},
            annotations=annotations,
        ),
        spec=AIMProfileSpec(aim_id=model_name, image="amdenterpriseai/aim-base:0.11"),
    )


def _make_artifact(
    model_name: str = _MODEL_NAME,
    phase: str = "Importing",
    progress: float | None = 42.0,
    last_error: str | None = None,
) -> AIMArtifactResource:
    """Build a minimal AIMArtifactResource for testing."""
    return AIMArtifactResource(
        metadata=K8sMetadata(
            name=f"{model_name}-artifact",
            namespace=_NAMESPACE,
            labels={AIM_MODEL_LABEL: model_name},
        ),
        status=AIMArtifactStatus(phase=phase, progress=progress, last_error=last_error),
    )


# ---------------------------------------------------------------------------
# _compose_onboard_status — phase transition rules
# ---------------------------------------------------------------------------


def test_compose_status_pending_when_no_profile_no_artifact() -> None:
    cr = _make_cr(aim_model_status="Progressing")
    result = _compose_onboard_status(cr, profile=None, artifact=None)
    assert result.state == OnboardPhase.PENDING
    assert result.status == "Progressing"
    assert result.template_ready is False
    assert result.artifact_phase is None


def test_compose_status_ready_when_aim_ready_and_profile_exists() -> None:
    """For v1alpha2 spec.profiles derivation, aim-engine does not stamp the legacy
    deployment-image-ref annotation — profile existence alone is the correct
    readiness signal."""
    cr = _make_cr(aim_model_status="Ready")
    profile = _make_profile(with_image_ref=False)
    result = _compose_onboard_status(cr, profile=profile, artifact=None)
    assert result.state == OnboardPhase.READY
    assert result.template_ready is True


def test_compose_status_ready_when_aim_ready_and_profile_annotated() -> None:
    cr = _make_cr(aim_model_status="Ready")
    profile = _make_profile(with_image_ref=True)
    result = _compose_onboard_status(cr, profile=profile, artifact=None)
    assert result.state == OnboardPhase.READY
    assert result.template_ready is True
    assert result.status == "Ready"


def test_compose_status_failed_when_aim_model_status_is_failed_variant() -> None:
    cr = _make_cr(aim_model_status="Failed")
    result = _compose_onboard_status(cr, profile=None, artifact=None)
    assert result.state == OnboardPhase.FAILED


def test_compose_status_failed_when_aim_model_status_is_error_variant() -> None:
    """``Error`` is the second failure-class status the engine can emit (alongside
    ``Failed``); ``resolve_onboard_phase`` recognises both via explicit
    ``AIMModelStatus`` membership rather than substring matching."""
    cr = _make_cr(aim_model_status="Error")
    result = _compose_onboard_status(cr, profile=None, artifact=None)
    assert result.state == OnboardPhase.FAILED


def test_compose_status_failed_when_artifact_phase_is_failed() -> None:
    cr = _make_cr(aim_model_status="Progressing")
    artifact = _make_artifact(phase="Failed", progress=None, last_error="disk full")
    result = _compose_onboard_status(cr, profile=None, artifact=artifact)
    assert result.state == OnboardPhase.FAILED
    assert result.artifact_last_error == "disk full"


def test_compose_status_importing_when_artifact_in_progress() -> None:
    cr = _make_cr(aim_model_status="Progressing")
    artifact = _make_artifact(phase="Importing", progress=65.0)
    result = _compose_onboard_status(cr, profile=None, artifact=artifact)
    assert result.state == OnboardPhase.IMPORTING
    assert result.artifact_phase == "Importing"


def test_compose_status_importing_gates_ready_model_and_profile() -> None:
    """An in-flight import gates readiness even when the AIMModel is Ready and a
    profile exists — the model is not deployable until the weights land."""
    cr = _make_cr(aim_model_status="Ready")
    profile = _make_profile(with_image_ref=True)
    artifact = _make_artifact(phase="Importing", progress=99.0)
    result = _compose_onboard_status(cr, profile=profile, artifact=artifact)
    assert result.state == OnboardPhase.IMPORTING


def test_compose_status_artifact_fields_propagated() -> None:
    cr = _make_cr(aim_model_status="Progressing")
    artifact = _make_artifact(phase="Importing", progress=30.5, last_error=None)
    result = _compose_onboard_status(cr, profile=None, artifact=artifact)
    assert result.artifact_phase == "Importing"
    assert result.artifact_last_error is None


def test_compose_status_no_artifact_fields_are_none() -> None:
    cr = _make_cr()
    result = _compose_onboard_status(cr, profile=None, artifact=None)
    assert result.artifact_phase is None
    assert result.artifact_last_error is None


def test_compose_status_pending_when_artifact_phase_is_ready_but_aim_not_ready() -> None:
    """AIMArtifact finished but AIMModel hasn't reached Ready+profile yet → Pending.

    This is the transition window where the weight import completed but
    aim-engine has not yet set the AIMModel status to Ready or emitted the
    AIMProfile.  Pending is the correct holding state.
    """
    cr = _make_cr(aim_model_status="Progressing")
    artifact = _make_artifact(phase="Ready", progress=100.0)
    result = _compose_onboard_status(cr, profile=None, artifact=artifact)
    assert result.state == OnboardPhase.PENDING


def test_compose_status_import_annotation_drives_importing() -> None:
    """The workbench-owned import annotations are the weight-import signal."""
    cr = _make_cr(
        aim_model_status="Progressing",
        annotations={IMPORT_STATE_ANNOTATION: "Importing"},
    )
    result = _compose_onboard_status(cr, profile=None, artifact=None)
    assert result.state == OnboardPhase.IMPORTING
    assert result.artifact_phase == "Importing"


def test_compose_status_import_annotation_failed_with_error() -> None:
    cr = _make_cr(
        aim_model_status="Progressing",
        annotations={
            IMPORT_STATE_ANNOTATION: "Failed",
            IMPORT_ERROR_ANNOTATION: "HF 401 unauthorized",
        },
    )
    result = _compose_onboard_status(cr, profile=None, artifact=None)
    assert result.state == OnboardPhase.FAILED
    assert result.artifact_last_error == "HF 401 unauthorized"


def test_compose_status_import_annotation_takes_precedence_over_artifact() -> None:
    """When both an import annotation and an AIMArtifact are present, the
    annotation (the onboard flow's own signal) wins."""
    cr = _make_cr(
        aim_model_status="Progressing",
        annotations={IMPORT_STATE_ANNOTATION: "Importing"},
    )
    artifact = _make_artifact(phase="Ready", progress=100.0)
    result = _compose_onboard_status(cr, profile=None, artifact=artifact)
    assert result.artifact_phase == "Importing"


def test_compose_status_import_annotation_ready_gates_on_model_and_profile() -> None:
    """Import done + model Ready + profile present → Ready."""
    cr = _make_cr(aim_model_status="Ready", annotations={IMPORT_STATE_ANNOTATION: "Ready"})
    profile = _make_profile(with_image_ref=False)
    result = _compose_onboard_status(cr, profile=profile, artifact=None)
    assert result.state == OnboardPhase.READY


# ---------------------------------------------------------------------------
# extract_hf_token_secret_name
# ---------------------------------------------------------------------------


def test_extract_hf_token_secret_name_returns_secret_name() -> None:
    env = [{"name": "HF_TOKEN", "valueFrom": {"secretKeyRef": {"name": "my-hf-secret", "key": "token"}}}]
    cr = _make_cr(env=env)
    assert extract_hf_token_secret_name(cr) == "my-hf-secret"


def test_extract_hf_token_secret_name_returns_none_when_no_hf_token_entry() -> None:
    env = [{"name": "SOME_OTHER_VAR", "value": "foo"}]
    cr = _make_cr(env=env)
    assert extract_hf_token_secret_name(cr) is None


def test_extract_hf_token_secret_name_returns_none_when_env_is_empty() -> None:
    cr = _make_cr(env=[])
    assert extract_hf_token_secret_name(cr) is None


def test_extract_hf_token_secret_name_returns_none_when_not_profiles_shaped() -> None:
    """A CR with no spec.profiles (e.g. a non-custom model) yields no secret."""
    cr = AIMModelResource(
        metadata=K8sMetadata(name=_MODEL_NAME, namespace=_NAMESPACE, annotations={}),
        spec=AIMModelSpec(),
    )
    assert extract_hf_token_secret_name(cr) is None


def test_extract_hf_token_secret_name_returns_none_when_hf_token_entry_lacks_value_from() -> None:
    """An HF_TOKEN env entry that uses a literal value instead of secretKeyRef returns None."""
    env = [{"name": "HF_TOKEN", "value": "hf_plaintext"}]
    cr = _make_cr(env=env)
    assert extract_hf_token_secret_name(cr) is None


# ---------------------------------------------------------------------------
# list_custom_models — async service function
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_custom_models_returns_only_custom_crs() -> None:
    """list_custom_models delegates filtering to the k8s label selector; the
    service includes whatever list_aim_models returns without re-filtering."""
    custom_cr = _make_cr(name="custom-model")
    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.list_aim_models", return_value=[custom_cr]),
        patch("app.custom_models.service.list_aim_profiles", return_value=[]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[]),
    ):
        results = await list_custom_models(kube, _NAMESPACE)

    assert len(results) == 1
    assert results[0].metadata.name == "custom-model"


@pytest.mark.asyncio
async def test_list_custom_models_passes_custom_label_selector_to_gateway() -> None:
    """The label selector that restricts results to custom-source models must be
    forwarded to the gateway so that non-custom CRs are excluded at the API
    server rather than filtered client-side."""
    kube = AsyncMock()
    mock_list = AsyncMock(return_value=[])
    with (
        patch("app.custom_models.service.aims_gateway.list_aim_models", mock_list),
        patch("app.custom_models.service.list_aim_profiles", return_value=[]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[]),
    ):
        await list_custom_models(kube, _NAMESPACE)

    expected_selector = f"{MODEL_SOURCE_TYPE_LABEL}={ModelSourceType.CUSTOM}"
    mock_list.assert_called_once_with(kube, _NAMESPACE, label_selector=expected_selector)


@pytest.mark.asyncio
async def test_list_custom_models_joins_profile_and_artifact_by_model_name() -> None:
    """Profile and artifact are matched to the CR by the model.name label."""
    cr = _make_cr(aim_model_status="Ready")
    profile = _make_profile(model_name=_MODEL_NAME, with_image_ref=True)
    artifact = _make_artifact(model_name=_MODEL_NAME, phase="Importing")

    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.list_aim_models", return_value=[cr]),
        patch("app.custom_models.service.list_aim_profiles", return_value=[profile]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[artifact]),
    ):
        results = await list_custom_models(kube, _NAMESPACE)

    assert len(results) == 1
    # The artifact matched by label (its Importing phase proves the join); the
    # in-flight import gates readiness even though the model is Ready + profiled.
    assert results[0].phase.state == OnboardPhase.IMPORTING
    assert results[0].phase.template_ready is True
    assert results[0].phase.artifact_phase == "Importing"


@pytest.mark.asyncio
async def test_list_custom_models_unmatched_profile_is_ignored() -> None:
    """A profile for a different model name does not affect composition."""
    cr = _make_cr(name="model-a", aim_model_status="Progressing")
    profile_for_other = _make_profile(model_name="model-b", with_image_ref=True)

    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.list_aim_models", return_value=[cr]),
        patch("app.custom_models.service.list_aim_profiles", return_value=[profile_for_other]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[]),
    ):
        results = await list_custom_models(kube, _NAMESPACE)

    assert results[0].phase.state == OnboardPhase.PENDING
    assert results[0].phase.template_ready is False


@pytest.mark.asyncio
async def test_list_custom_models_includes_composed_phase() -> None:
    """list_custom_models populates the phase field for every returned model."""
    cr = _make_cr(aim_model_status="Progressing")
    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.list_aim_models", return_value=[cr]),
        patch("app.custom_models.service.list_aim_profiles", return_value=[]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[]),
    ):
        results = await list_custom_models(kube, _NAMESPACE)

    assert results[0].phase is not None
    assert results[0].phase.state == OnboardPhase.PENDING


# ---------------------------------------------------------------------------
# get_custom_model — async service function
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_custom_model_returns_composed_response() -> None:
    cr = _make_cr(aim_model_status="Ready")
    profile = _make_profile(with_image_ref=True)

    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.get_aim_model", return_value=cr),
        patch("app.custom_models.service.list_aim_profiles", return_value=[profile]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[]),
    ):
        result = await get_custom_model(kube, _NAMESPACE, _MODEL_NAME)

    assert result.metadata.name == _MODEL_NAME
    assert result.phase.state == OnboardPhase.READY
    assert result.phase.template_ready is True


@pytest.mark.asyncio
async def test_get_custom_model_returns_persisted_runtime_overrides() -> None:
    """Runtime knobs persisted on spec.profiles.overrides must round-trip on GET so the edit form can prefill them."""
    cr = _make_cr(aim_model_status="Ready")
    cr.spec.profiles.overrides = ProfileOverrides.model_validate(
        {
            "aimId": _REPO_ID,
            "modelId": _REPO_ID,
            "image": "docker.io/amd/tinyllama:1.0.0",
            "acceleratorModel": "MI300X",
            "precision": "fp16",
            "engineArgs": {"max-model-len": 4096},
            "engineEnv": {"VLLM_ROCM_USE_AITER": "1"},
        }
    )
    profile = _make_profile(with_image_ref=True)

    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.get_aim_model", return_value=cr),
        patch("app.custom_models.service.list_aim_profiles", return_value=[profile]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[]),
    ):
        result = await get_custom_model(kube, _NAMESPACE, _MODEL_NAME)

    overrides = result.spec.profiles.overrides.model_dump(by_alias=True)
    assert overrides["acceleratorModel"] == "MI300X"
    assert overrides["precision"] == "fp16"
    assert overrides["engineArgs"] == {"max-model-len": 4096}
    assert overrides["engineEnv"] == {"VLLM_ROCM_USE_AITER": "1"}


@pytest.mark.asyncio
async def test_get_custom_model_raises_not_found_when_cr_absent() -> None:
    kube = AsyncMock()
    with patch("app.custom_models.service.aims_gateway.get_aim_model", return_value=None):
        with pytest.raises(NotFoundException):
            await get_custom_model(kube, _NAMESPACE, "nonexistent-model")


@pytest.mark.asyncio
async def test_get_custom_model_raises_not_found_for_non_custom_cr() -> None:
    """A CR without REVISION_ANNOTATION (e.g. fine-tuned) must not be returned."""
    non_custom_cr = AIMModelResource(
        metadata=K8sMetadata(name="fine-tuned-model", namespace=_NAMESPACE, annotations={}),
        spec=AIMModelSpec(),
        status=AIMModelStatusFields(),
    )
    kube = AsyncMock()
    with patch("app.custom_models.service.aims_gateway.get_aim_model", return_value=non_custom_cr):
        with pytest.raises(NotFoundException):
            await get_custom_model(kube, _NAMESPACE, "fine-tuned-model")


@pytest.mark.asyncio
async def test_get_custom_model_passes_model_name_to_gateway_fetches() -> None:
    """list_aim_profiles and list_aim_artifacts are called with the
    model_name kwarg so only that model's resources are fetched, not the whole namespace."""
    cr = _make_cr(aim_model_status="Ready")

    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.get_aim_model", return_value=cr) as mock_get,
        patch("app.custom_models.service.list_aim_profiles", return_value=[]) as mock_profiles,
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[]) as mock_artifacts,
    ):
        await get_custom_model(kube, _NAMESPACE, _MODEL_NAME)

    mock_get.assert_called_once_with(kube, _NAMESPACE, _MODEL_NAME)
    mock_profiles.assert_called_once_with(kube, _NAMESPACE, model_name=_MODEL_NAME)
    mock_artifacts.assert_called_once_with(kube, _NAMESPACE, model_name=_MODEL_NAME)


@pytest.mark.asyncio
async def test_get_custom_model_with_artifact_in_progress() -> None:
    cr = _make_cr(aim_model_status="Progressing")
    artifact = _make_artifact(phase="Importing", last_error=None)

    kube = AsyncMock()
    with (
        patch("app.custom_models.service.aims_gateway.get_aim_model", return_value=cr),
        patch("app.custom_models.service.list_aim_profiles", return_value=[]),
        patch("app.custom_models.service.aims_gateway.list_aim_artifacts", return_value=[artifact]),
    ):
        result = await get_custom_model(kube, _NAMESPACE, _MODEL_NAME)

    assert result.phase.state == OnboardPhase.IMPORTING
    assert result.phase.artifact_phase == "Importing"


# ---------------------------------------------------------------------------
# get_base_runtime_profile_options — base-template runtime options
# ---------------------------------------------------------------------------


def _make_base_profile(
    *,
    accelerator_model: str = "MI300X",
    precision: str = "fp16",
    accelerator_count: int = 1,
    profile_type: str = "general",
) -> AIMProfileResource:
    """Build a base-role AIMProfile carrying the runtime fields the wizard reads."""
    return AIMProfileResource(
        metadata=K8sMetadata(name=f"aim-base-{precision}-tp{accelerator_count}", namespace=_NAMESPACE),
        spec=AIMProfileSpec(
            aim_id="",
            accelerator_model=accelerator_model,
            precision=precision,
            accelerator_count=accelerator_count,
            type=profile_type,
        ),
    )


@pytest.mark.asyncio
async def test_base_runtime_profile_options_aggregates_distinct_sorted_values() -> None:
    """Distinct accelerator/precision/count/type values across base-role profiles are returned, deduped and sorted."""
    profiles = [
        _make_base_profile(accelerator_count=1),
        _make_base_profile(accelerator_count=2),
        _make_base_profile(accelerator_count=8),
        _make_base_profile(accelerator_count=4),
        _make_base_profile(accelerator_count=1),  # duplicate
    ]
    kube = AsyncMock()
    with patch("app.custom_models.service.list_base_role_profiles", return_value=profiles):
        options = await get_base_runtime_profile_options(kube, _NAMESPACE)

    assert options.accelerator_models == ["MI300X"]
    assert options.precisions == ["fp16"]
    assert options.accelerator_counts == [1, 2, 4, 8]
    assert options.optimization_classes == ["general"]


@pytest.mark.asyncio
async def test_base_runtime_profile_options_ignores_non_positive_accelerator_counts() -> None:
    """AIMProfile specs with zero or negative accelerator_count must not pollute the options list."""
    profiles = [
        _make_base_profile(accelerator_count=1),
        _make_base_profile(accelerator_count=0),
        _make_base_profile(accelerator_count=-2),
        _make_base_profile(accelerator_count=2),
    ]
    kube = AsyncMock()
    with patch("app.custom_models.service.list_base_role_profiles", return_value=profiles):
        options = await get_base_runtime_profile_options(kube, _NAMESPACE)

    assert options.accelerator_counts == [1, 2]


@pytest.mark.asyncio
async def test_base_runtime_profile_options_empty_when_no_base_profiles() -> None:
    """No base-role profiles (base model not emitted yet) yields empty option lists for client fallback."""
    kube = AsyncMock()
    with patch("app.custom_models.service.list_base_role_profiles", return_value=[]):
        options = await get_base_runtime_profile_options(kube, _NAMESPACE)

    assert options == RuntimeProfileOptions()
    assert options.precisions == []


# ---------------------------------------------------------------------------
# Router: GET /projects/{project}/models/{model_name}
# ---------------------------------------------------------------------------

_GET_URL = f"/v1/projects/{_NAMESPACE}/models/{_MODEL_NAME}"


def _make_detail_response():
    return CustomModelResponse(
        metadata=K8sMetadata(name=_MODEL_NAME, namespace=_NAMESPACE),
        spec=AIMModelSpec(image="docker.io/amd/tinyllama:1.0.0"),
        phase=CustomModelOnboardStatus(
            state=OnboardPhase.READY,
            status="Ready",
            template_ready=True,
        ),
    )


@override_dependencies(BASE_OVERRIDES)
@patch("app.projects.router.get_custom_model")
def test_get_custom_model_endpoint_returns_200(mock_get: MagicMock) -> None:
    mock_get.return_value = _make_detail_response()
    with TestClient(app) as client:
        response = client.get(_GET_URL)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["metadata"]["name"] == _MODEL_NAME
    assert body["phase"]["state"] == "Ready"
    assert body["phase"]["templateReady"] is True


@override_dependencies(BASE_OVERRIDES)
@patch("app.projects.router.get_custom_model")
def test_get_custom_model_endpoint_camel_case_status_fields(mock_get: MagicMock) -> None:
    mock_get.return_value = _make_detail_response()
    with TestClient(app) as client:
        response = client.get(_GET_URL)
    body = response.json()
    assert "state" in body["phase"]
    assert "templateReady" in body["phase"]
    assert "artifactPhase" in body["phase"]
    assert "artifactLastError" in body["phase"]
    assert "imageMetadata" in body["status"]


@override_dependencies(BASE_OVERRIDES)
@patch(
    "app.projects.router.get_custom_model",
    side_effect=NotFoundException("Custom model 'x' not found"),
)
def test_get_custom_model_endpoint_returns_404_when_not_found(mock_get: MagicMock) -> None:
    with TestClient(app) as client:
        response = client.get(_GET_URL)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_custom_model_endpoint_returns_401_without_auth() -> None:
    with TestClient(app) as client:
        response = client.get(_GET_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@override_dependencies(BASE_OVERRIDES)
@patch("app.projects.router.get_custom_model")
def test_get_custom_model_endpoint_top_level_fields_present(mock_get: MagicMock) -> None:
    """Top-level response fields are camelCase: phase, profile, spec, status, metadata."""
    mock_get.return_value = CustomModelResponse(
        metadata=K8sMetadata(name=_MODEL_NAME, namespace=_NAMESPACE),
        spec=AIMModelSpec(image="docker.io/amd/tinyllama:1.0.0"),
        phase=CustomModelOnboardStatus(state=OnboardPhase.READY, status="Ready"),
    )
    with TestClient(app) as client:
        response = client.get(_GET_URL)
    body = response.json()
    assert "phase" in body
    assert "profile" in body
    assert "spec" in body
    assert "status" in body
    assert "metadata" in body


_RUNTIME_OPTIONS_URL = f"/v1/projects/{_NAMESPACE}/models/runtime-profile-options"


@override_dependencies(BASE_OVERRIDES)
@patch("app.projects.router.get_base_runtime_profile_options")
def test_runtime_profile_options_endpoint_returns_camelcase_options(mock_options: MagicMock) -> None:
    """The runtime-options endpoint resolves ahead of the /{model_name} route and serializes camelCase."""
    mock_options.return_value = RuntimeProfileOptions(
        accelerator_models=["MI300X"],
        precisions=["fp16"],
        accelerator_counts=[1, 2, 4, 8],
        optimization_classes=["general"],
    )
    with TestClient(app) as client:
        response = client.get(_RUNTIME_OPTIONS_URL)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["acceleratorModels"] == ["MI300X"]
    assert body["precisions"] == ["fp16"]
    assert body["acceleratorCounts"] == [1, 2, 4, 8]
    assert body["optimizationClasses"] == ["general"]


def test_runtime_profile_options_endpoint_returns_401_without_auth() -> None:
    with TestClient(app) as client:
        response = client.get(_RUNTIME_OPTIONS_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@override_dependencies(BASE_OVERRIDES)
@patch("app.projects.router.get_custom_model")
def test_get_custom_model_endpoint_importing_phase_with_artifact(mock_get: MagicMock) -> None:
    """An in-progress import is represented correctly at the HTTP layer."""
    mock_get.return_value = CustomModelResponse(
        metadata=K8sMetadata(name=_MODEL_NAME, namespace=_NAMESPACE),
        spec=AIMModelSpec(image="docker.io/amd/tinyllama:1.0.0"),
        phase=CustomModelOnboardStatus(
            state=OnboardPhase.IMPORTING,
            status="Importing",
            template_ready=False,
            artifact_phase="Importing",
        ),
    )
    with TestClient(app) as client:
        response = client.get(_GET_URL)
    assert response.status_code == status.HTTP_200_OK
    s = response.json()["phase"]
    assert s["state"] == "Importing"
    assert s["templateReady"] is False
    assert s["artifactPhase"] == "Importing"
