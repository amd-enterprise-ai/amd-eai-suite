# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for BYOM onboarding: manifest builder and upsert orchestration.

These tests target the upsert orchestration in `onboard_custom_model_source`
and the manifest builder `_build_custom_aim_model_manifest`. The Hub-fetch +
preview shape are covered in test_service.py; here we exercise AIMModel CR
creation/patch, conflict detection, and the k8s-first ordering guarantee:
the CR is the source of truth and is written before the S3 manifest mirror.
"""

import re
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import tenacity
import yaml
from kubernetes_asyncio.client import ApiException
from minio.error import S3Error
from pydantic import ValidationError

from api_common.exceptions import ConflictException, ExternalServiceError, ForbiddenException, ValidationException
from app.aims.crds import AIMModelResource
from app.custom_models.constants import (
    AIM_BASE_MODEL_NAME,
    CANONICAL_REPO_ID_ANNOTATION,
    COMPONENT_ID_ANNOTATION,
    DEFAULT_AIM_DEPLOYMENT_IMAGE_REF,
    MINIO_CREDENTIALS_ACCESS_KEY_KEY,
    MINIO_CREDENTIALS_SECRET_KEY_KEY,
    MINIO_CREDENTIALS_SECRET_NAME,
    MODEL_DISPLAY_NAME_ANNOTATION,
    REVISION_ANNOTATION,
    SOURCE_DESCRIPTION_ANNOTATION,
    SOURCE_SHA_ANNOTATION,
    SOURCE_URI_ANNOTATION,
)
from app.custom_models.manifest import write_manifest_to_s3
from app.custom_models.schemas import OnboardRequest, PreviewRequest
from app.custom_models.service import (
    _build_aim_base_model_manifest,
    _build_custom_aim_model_manifest,
    _verify_minio_credentials_secret,
    ensure_namespace_aim_base_model,
    onboard_custom_model_source,
    preview_model_source,
)
from app.dispatch.crds import K8sMetadata
from app.minio.config import MINIO_URL
from app.workloads.constants import (
    CANONICAL_NAME_LABEL,
    DISPLAY_NAME_ANNOTATION,
    MODEL_NAME_LABEL,
)


@pytest.fixture(autouse=True)
def _disable_write_manifest_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Short-circuit the tenacity retry on the shared manifest writer.

    Onboard tests exercise the upsert orchestration around the S3 write
    (read → upsert → write), not the retry timing itself. Without this
    fixture, an S3-failure test would block on three exponential-backoff
    sleeps before the exception surfaces to the assertion.
    """
    monkeypatch.setattr(write_manifest_to_s3.retry, "wait", tenacity.wait_none())
    monkeypatch.setattr(write_manifest_to_s3.retry, "stop", tenacity.stop_after_attempt(1))


HUB_RESPONSE = {
    "id": "meta-llama/Meta-Llama-3-8B-Instruct",
    "sha": "abc123",
    "tags": [],
    "pipeline_tag": "text-generation",
    "gated": False,
    "private": False,
    "cardData": {"model_name": "Llama 3 8B", "description": "An open model."},
    "siblings": [],
}

TEST_IMAGE = "docker.io/amd/tinyllama:1.0.0"
TEST_SUBMITTER = "alice@example.com"

# Sha used by the default `_make_request` payload and by the autouse Hub
# re-verify mock; keep these aligned so the happy path stays a no-op.
_DEFAULT_REQUEST_SHA = "abc123"


@pytest.fixture(autouse=True)
def stub_onboard_hub_reverify() -> Iterator[dict[str, AsyncMock]]:
    """Stub the onboard Hub re-verify path so existing tests stay focused on
    the K8s/S3 orchestration rather than the Hub fetch.

    Defaults match the sha used in `_make_request` so the verify step is a
    no-op on the happy path. Tests covering the verify failure modes (sha
    mismatch, Hub auth, Hub 404, etc.) override `return_value`/`side_effect`
    on the yielded mocks (or re-patch inside the test body); either way the
    fixture's defaults are restored once the test exits.
    """
    with (
        patch("app.custom_models.service._fetch_hub_model") as fetch_mock,
        patch("app.custom_models.service._get_hf_token") as token_mock,
    ):
        fetch_mock.return_value = {"sha": _DEFAULT_REQUEST_SHA}
        token_mock.return_value = "fake-hf-token"
        yield {"fetch": fetch_mock, "token": token_mock}


@pytest.fixture(autouse=True)
def stub_schedule_import() -> Iterator[MagicMock]:
    """Stop onboard from spawning the real detached weight-import task.

    These tests cover the CR/S3 orchestration, not the import itself; without
    this stub each onboard would fire a background task hitting the network.
    The dedicated import tests in test_weights_import.py exercise the importer.
    """
    with patch("app.custom_models.service.schedule_import") as schedule_mock:
        yield schedule_mock


def _no_such_key_s3_error() -> S3Error:
    """Synthetic ``NoSuchKey`` for the default "no prior manifest" state."""
    return S3Error(
        code="NoSuchKey",
        message="no such key",
        resource="key",
        request_id="r",
        host_id="h",
        response=MagicMock(status=404),
    )


@pytest.fixture
def mock_minio_client() -> MagicMock:
    """Local MinioClient mock; the global fixture in tests/conftest.py is broken.

    ``download_object`` defaults to raising ``NoSuchKey`` so a first-onboard
    test exercises the realistic "no prior manifest" branch in
    ``read_manifest_from_s3`` without needing per-test setup. Tests that
    want to exercise re-onboard append semantics override this to return
    the bytes of a prior manifest.
    """
    mock = MagicMock()
    mock.download_object.side_effect = _no_such_key_s3_error()
    return mock


_CREATED_AIM_MODEL_STUB = {
    "apiVersion": "aim.eai.amd.com/v1alpha2",
    "kind": "AIMModel",
    "metadata": {"name": "llama-3-8b-abc12345", "namespace": "test-namespace"},
    "spec": {},
}

_AIM_BASE_STUB = _build_aim_base_model_manifest(
    namespace="test-namespace",
    image_ref=DEFAULT_AIM_DEPLOYMENT_IMAGE_REF,
)


@pytest.fixture
def mock_kube_client() -> AsyncMock:
    """Local kube client mock with the custom_objects API surface populated."""
    mock = AsyncMock()
    mock.custom_objects = AsyncMock()
    mock.custom_objects.list_namespaced_custom_object = AsyncMock(return_value={"items": []})

    async def get_namespaced_custom_object(*_args: Any, name: str, **_kwargs: Any) -> dict:
        if name == AIM_BASE_MODEL_NAME:
            return _AIM_BASE_STUB
        raise ApiException(status=404, reason="Not Found")

    mock.custom_objects.get_namespaced_custom_object = AsyncMock(side_effect=get_namespaced_custom_object)
    # Gateway helpers parse the server response into AIMModelResource, so we
    # default to a valid-shaped payload; individual tests override as needed.
    mock.custom_objects.create_namespaced_custom_object = AsyncMock(return_value=_CREATED_AIM_MODEL_STUB)
    mock.custom_objects.patch_namespaced_custom_object = AsyncMock(return_value=_CREATED_AIM_MODEL_STUB)
    return mock


_EXISTING_COMPONENT_ID = "11111111-2222-3333-4444-555555555555"


def _make_existing_aim_model(
    *,
    name: str = "llama-3-8b-import-12345678",
    display_name: str = "Llama 3 8B",
    repo_id: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    source_uri: str | None = None,
    component_id: str | None = _EXISTING_COMPONENT_ID,
) -> AIMModelResource:
    # sourceUri is normally the s3:// prefix where the import lands; tests rarely
    # care about its exact shape, so it defaults to a placeholder unless overridden.
    # component_id defaults to a stable value so patch-path tests can assert it's
    # preserved across idempotent calls; pass None to simulate a legacy CR.
    annotations: dict[str, str] = {}
    if component_id is not None:
        annotations[COMPONENT_ID_ANNOTATION] = component_id
    # v1alpha2 shape: identity + weights live under spec.profiles.overrides, not
    # the legacy flat spec.modelSources. Conflict detection reads the repo id
    # back from overrides, so the fixture must mirror what the builder emits.
    return AIMModelResource(
        metadata=K8sMetadata(
            name=name,
            namespace="test-namespace",
            labels={MODEL_NAME_LABEL: display_name.replace(" ", "-")},
            annotations=annotations,
        ),
        spec={
            "profiles": {
                "derivedFrom": {"selector": {"role": "base", "modelRef": {"name": "aim-base", "scope": "Namespace"}}},
                "versionPolicy": "all",
                "overrides": {
                    "aimId": repo_id,
                    "modelId": repo_id,
                    "image": TEST_IMAGE,
                    "modelSources": [
                        {
                            "modelId": repo_id,
                            "sourceUri": source_uri or f"s3://test-bucket/test-namespace/custom-models/{name}/weights/",
                        }
                    ],
                },
            }
        },
    )


# --- OnboardRequest schema validation ---


@pytest.mark.parametrize("field", ["repo_id", "revision", "sha", "display_name"])
def test_onboard_request_rejects_empty_required_string(field: str) -> None:
    """Required identifier fields must be non-empty. An empty ``display_name``
    in particular sanitizes to an empty ``DISPLAY_NAME_LABEL`` value, which
    turns conflict detection into a ``display-name=`` selector that matches
    every AIMModel missing the label — the schema must fail-fast at the
    boundary so service code never sees that state."""
    payload: dict[str, Any] = {
        "repo_id": "meta-llama/Llama-3-8B",
        "revision": "main",
        "sha": "abc123",
        "display_name": "Llama 3 8B",
        "image": TEST_IMAGE,
    }
    payload[field] = ""

    with pytest.raises(ValidationError) as exc_info:
        OnboardRequest(**payload)
    assert any(err["loc"] == (field,) for err in exc_info.value.errors())


# --- _build_custom_aim_model_manifest ---


_RESOURCE_NAME = "llama-3-8b-import-abc12345"
_SOURCE_URI = f"s3://test-bucket/test-namespace/custom-models/{_RESOURCE_NAME}/weights/"
_BUILDER_COMPONENT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _make_request(**overrides: Any) -> OnboardRequest:
    """Default OnboardRequest used across builder and orchestrator tests.

    Centralizing defaults here means future fields on `OnboardRequest` only
    touch this factory, not every test body.
    """
    defaults: dict = {
        "repo_id": "meta-llama/Llama-3-8B",
        "revision": "main",
        "sha": "abc123",
        "display_name": "Llama 3 8B",
        "description": "A great model.",
        "image": TEST_IMAGE,
        "hf_token_secret_name": None,
    }
    defaults.update(overrides)
    return OnboardRequest(**defaults)


def _build_manifest(source: OnboardRequest | None = None, **overrides: Any) -> dict:
    return _build_custom_aim_model_manifest(
        namespace=overrides.pop("namespace", "test-namespace"),
        resource_name=overrides.pop("resource_name", _RESOURCE_NAME),
        source=source if source is not None else _make_request(),
        source_uri=overrides.pop("source_uri", _SOURCE_URI),
        submitter=overrides.pop("submitter", TEST_SUBMITTER),
        component_id=overrides.pop("component_id", _BUILDER_COMPONENT_ID),
    )


def test_manifest_carries_required_kind_and_api_version() -> None:
    manifest = _build_manifest()

    assert manifest["apiVersion"] == "aim.eai.amd.com/v1alpha2"
    assert manifest["kind"] == "AIMModel"
    assert manifest["metadata"]["name"] == _RESOURCE_NAME
    assert manifest["metadata"]["namespace"] == "test-namespace"


def test_manifest_emits_only_profiles_spec_no_flat_fields() -> None:
    """v1alpha2 CEL forbids spec.image / spec.modelSources / spec.env /
    spec.imageMetadata alongside spec.profiles. The builder must emit a
    profiles-only spec so the manifest is admissible."""
    manifest = _build_manifest(_make_request(description="", hf_token_secret_name="my-hf-secret"))

    spec = manifest["spec"]
    assert set(spec.keys()) == {"profiles"}
    for forbidden in ("image", "modelSources", "env", "imageMetadata"):
        assert forbidden not in spec


def test_manifest_derives_from_base_image_model() -> None:
    """The custom model derives from base-role profiles emitted by the
    configured base-image AIMModel; identity filters are forbidden by CEL
    when role=base, so the selector carries only role + modelRef."""
    manifest = _build_manifest(_make_request(description=""))

    profiles = manifest["spec"]["profiles"]
    selector = profiles["derivedFrom"]["selector"]
    assert selector["role"] == "base"
    assert selector["modelRef"]["name"] == "aim-base"
    assert selector["modelRef"]["scope"] == "Namespace"
    # versionPolicy=all copies every matched base version; pinned would require
    # a concrete source version we do not have, and CEL forbids version here.
    assert profiles["versionPolicy"] == "all"
    assert "version" not in profiles
    assert "aimId" not in selector and "modelId" not in selector


def test_manifest_overrides_stamp_identity_required_for_base_role() -> None:
    """role=base requires overrides.aimId and overrides.modelId (base profiles
    carry no identity of their own); the builder sets both to the repo id."""
    manifest = _build_manifest(_make_request(description=""))

    overrides = manifest["spec"]["profiles"]["overrides"]
    assert overrides["aimId"] == "meta-llama/Llama-3-8B"
    assert overrides["modelId"] == "meta-llama/Llama-3-8B"


def test_manifest_stamps_display_and_canonical_labels_only() -> None:
    """Labels carry only sanitised model-name and canonical-name for selector
    queries. The human-readable display name lives in DISPLAY_NAME_ANNOTATION.
    No WORKLOAD_ID_LABEL since a BYOM import is not a workload."""
    manifest = _build_manifest(_make_request(description=""))

    labels = manifest["metadata"]["labels"]
    assert labels[MODEL_NAME_LABEL] == "Llama-3-8B"
    assert labels[CANONICAL_NAME_LABEL] == "meta-llama-Llama-3-8B"
    assert DISPLAY_NAME_ANNOTATION not in labels  # annotation, not label
    # Workload-id has no meaning for BYOM and must not be stamped.
    workload_id_label_key = "apps.eai.amd.com/workload-id"
    assert workload_id_label_key not in labels

    annotations = manifest["metadata"]["annotations"]
    assert annotations[DISPLAY_NAME_ANNOTATION] == "Llama 3 8B"


def test_manifest_carries_source_annotations() -> None:
    """Revision, sha, and description live in annotations because they aren't
    first-class spec fields on the AIMModel CR — but we still want to round-trip
    them between preview calls."""
    manifest = _build_manifest(_make_request(revision="dev-branch", description="An open model."))

    annotations = manifest["metadata"]["annotations"]
    assert annotations[REVISION_ANNOTATION] == "dev-branch"
    assert annotations[SOURCE_SHA_ANNOTATION] == "abc123"
    assert annotations[SOURCE_DESCRIPTION_ANNOTATION] == "An open model."


def test_manifest_carries_airm_provenance_annotations() -> None:
    """component-id, source-uri, and revision live under the airm.silogen.ai
    prefix as a cross-app contract: AIRM-side tooling reads these to identify
    the BYOM source independently of AIWB internals."""
    manifest = _build_manifest(_make_request(revision="dev-branch", description=""))

    annotations = manifest["metadata"]["annotations"]
    assert annotations[COMPONENT_ID_ANNOTATION] == _BUILDER_COMPONENT_ID
    assert annotations[SOURCE_URI_ANNOTATION] == _SOURCE_URI
    assert annotations[REVISION_ANNOTATION] == "dev-branch"


def test_manifest_keeps_raw_display_name_and_repo_id_on_dedicated_annotation_keys() -> None:
    """Raw display name and repo id live on dedicated annotation keys distinct
    from the label keys. Mixing the two maps under the same key would let a
    downstream reader pick up the sanitized label value when it wanted the
    raw string (or vice versa) depending on which map it grabs first."""
    manifest = _build_manifest(_make_request(description=""))

    annotations = manifest["metadata"]["annotations"]
    labels = manifest["metadata"]["labels"]
    assert annotations[MODEL_DISPLAY_NAME_ANNOTATION] == "Llama 3 8B"
    assert annotations[CANONICAL_REPO_ID_ANNOTATION] == "meta-llama/Llama-3-8B"
    # The MODEL_NAME_LABEL / CANONICAL_NAME_LABEL keys must remain label-only —
    # never carry an annotation entry with the same key but a different value.
    assert MODEL_NAME_LABEL not in annotations
    assert CANONICAL_NAME_LABEL not in annotations
    assert labels[MODEL_NAME_LABEL] != annotations[MODEL_DISPLAY_NAME_ANNOTATION]


def test_manifest_stamps_description_annotation_even_when_blank() -> None:
    """Always stamped so a re-onboard with a cleared description merge-patches the
    annotation back to empty rather than leaving a stale value behind."""
    manifest = _build_manifest(_make_request(description=""))

    assert manifest["metadata"]["annotations"][SOURCE_DESCRIPTION_ANNOTATION] == ""


def test_manifest_pins_source_in_model_sources() -> None:
    """overrides.modelSources is the engine's source of truth for where to load
    the BYO weights from. modelId is the logical HF id; sourceUri is the s3://
    prefix the importer writes to."""
    manifest = _build_manifest(_make_request(description=""))

    sources = manifest["spec"]["profiles"]["overrides"]["modelSources"]
    assert len(sources) == 1
    assert sources[0]["modelId"] == "meta-llama/Llama-3-8B"
    assert sources[0]["sourceUri"].startswith("s3://")
    assert sources[0]["sourceUri"].endswith("/weights/")


def test_manifest_sets_user_provided_image() -> None:
    manifest = _build_manifest(_make_request(description="", image="registry.example.com/byom:v2"))

    assert manifest["spec"]["profiles"]["overrides"]["image"] == "registry.example.com/byom:v2"


def test_manifest_always_injects_s3_credentials() -> None:
    """aim-engine's check-size job requires AWS_* env vars to authenticate to
    MinIO regardless of whether the model is gated — inject them unconditionally."""
    manifest = _build_manifest(_make_request(description=""))

    env = manifest["spec"]["profiles"]["overrides"]["modelSources"][0]["env"]
    env_names = [e["name"] for e in env]
    assert "AWS_ACCESS_KEY_ID" in env_names
    assert "AWS_SECRET_ACCESS_KEY" in env_names
    assert "AWS_ENDPOINT_URL" in env_names


def test_manifest_s3_credentials_reference_minio_secret() -> None:
    """AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must reference the
    platform-provisioned minio-credentials secret so aim-engine can
    authenticate without the API ever handling the raw credential values."""
    manifest = _build_manifest(_make_request(description=""))

    env = manifest["spec"]["profiles"]["overrides"]["modelSources"][0]["env"]
    env_by_name = {e["name"]: e for e in env}

    access_key = env_by_name["AWS_ACCESS_KEY_ID"]
    assert access_key["valueFrom"]["secretKeyRef"]["name"] == MINIO_CREDENTIALS_SECRET_NAME
    assert access_key["valueFrom"]["secretKeyRef"]["key"] == MINIO_CREDENTIALS_ACCESS_KEY_KEY

    secret_key = env_by_name["AWS_SECRET_ACCESS_KEY"]
    assert secret_key["valueFrom"]["secretKeyRef"]["name"] == MINIO_CREDENTIALS_SECRET_NAME
    assert secret_key["valueFrom"]["secretKeyRef"]["key"] == MINIO_CREDENTIALS_SECRET_KEY_KEY


def test_manifest_s3_endpoint_uses_minio_url_config() -> None:
    """AWS_ENDPOINT_URL must match MINIO_URL so aim-engine talks to the
    platform's MinIO instance and not a default public S3 endpoint."""
    manifest = _build_manifest(_make_request(description=""))

    env = manifest["spec"]["profiles"]["overrides"]["modelSources"][0]["env"]
    env_by_name = {e["name"]: e for e in env}

    assert env_by_name["AWS_ENDPOINT_URL"]["value"] == MINIO_URL


def test_manifest_wires_hf_token_when_secret_name_given() -> None:
    """Gated/private models need HF_TOKEN appended after the S3 credentials
    so aim-engine sees all required env vars on the weights source."""
    manifest = _build_manifest(_make_request(description="", hf_token_secret_name="my-hf-secret"))

    env = manifest["spec"]["profiles"]["overrides"]["modelSources"][0]["env"]
    env_names = [e["name"] for e in env]

    assert env_names[:3] == ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ENDPOINT_URL"]
    assert env_names[-1] == "HF_TOKEN"

    hf_entry = next(e for e in env if e["name"] == "HF_TOKEN")
    assert hf_entry == {
        "name": "HF_TOKEN",
        "valueFrom": {"secretKeyRef": {"name": "my-hf-secret", "key": "token"}},
    }


def test_manifest_omits_hf_token_when_no_secret_name_given() -> None:
    """Public models do not need HF_TOKEN — the env stanza should contain
    only the three S3 credential vars."""
    manifest = _build_manifest(_make_request(description=""))

    env = manifest["spec"]["profiles"]["overrides"]["modelSources"][0]["env"]
    env_names = [e["name"] for e in env]

    assert env_names == ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ENDPOINT_URL"]


# --- _verify_minio_credentials_secret ---


@pytest.mark.asyncio
async def test_verify_minio_credentials_secret_passes_when_present(mock_kube_client: AsyncMock) -> None:
    """No exception is raised when the platform-provisioned secret exists."""
    mock_kube_client.core_v1.read_namespaced_secret.return_value = MagicMock()

    await _verify_minio_credentials_secret(mock_kube_client, "test-namespace")

    mock_kube_client.core_v1.read_namespaced_secret.assert_called_once_with(
        name=MINIO_CREDENTIALS_SECRET_NAME, namespace="test-namespace"
    )


@pytest.mark.asyncio
async def test_verify_minio_credentials_secret_raises_400_when_missing(mock_kube_client: AsyncMock) -> None:
    """A missing MinIO credentials secret raises ValidationException (400) with
    an actionable message so the caller knows exactly what to provision."""
    mock_kube_client.core_v1.read_namespaced_secret.side_effect = ApiException(status=404)

    with pytest.raises(ValidationException, match=MINIO_CREDENTIALS_SECRET_NAME):
        await _verify_minio_credentials_secret(mock_kube_client, "test-namespace")


@pytest.mark.asyncio
async def test_verify_minio_credentials_secret_wraps_non_404_errors_as_external_service_error(
    mock_kube_client: AsyncMock,
) -> None:
    """Non-404 Kubernetes errors must surface as ExternalServiceError (502) so they
    are handled consistently at the service layer instead of leaking the async
    ApiException type that AIWB's exception handler does not recognise."""
    api_error = ApiException(status=403, reason="Forbidden")
    mock_kube_client.core_v1.read_namespaced_secret.side_effect = api_error

    with pytest.raises(ExternalServiceError) as exc_info:
        await _verify_minio_credentials_secret(mock_kube_client, "test-namespace")

    assert exc_info.value.__cause__ is api_error


# --- derivedFrom bootstrap (aim-base) ---


def test_aim_base_manifest_uses_configured_image() -> None:
    manifest = _build_aim_base_model_manifest(namespace="test-namespace", image_ref=DEFAULT_AIM_DEPLOYMENT_IMAGE_REF)

    assert manifest["apiVersion"] == "aim.eai.amd.com/v1alpha2"
    assert manifest["kind"] == "AIMModel"
    assert manifest["metadata"]["name"] == AIM_BASE_MODEL_NAME
    assert manifest["metadata"]["namespace"] == "test-namespace"
    assert manifest["spec"] == {"image": DEFAULT_AIM_DEPLOYMENT_IMAGE_REF}


@pytest.mark.asyncio
async def test_ensure_namespace_aim_base_model_creates_when_missing(mock_kube_client: AsyncMock) -> None:
    mock_kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404)

    await ensure_namespace_aim_base_model(mock_kube_client, "test-namespace")

    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_called_once()
    create_kwargs = mock_kube_client.custom_objects.create_namespaced_custom_object.call_args.kwargs
    body = create_kwargs["body"]
    assert body["metadata"]["name"] == AIM_BASE_MODEL_NAME
    assert body["spec"]["image"] == DEFAULT_AIM_DEPLOYMENT_IMAGE_REF


@pytest.mark.asyncio
async def test_ensure_namespace_aim_base_model_skips_when_present(mock_kube_client: AsyncMock) -> None:
    await ensure_namespace_aim_base_model(mock_kube_client, "test-namespace")

    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_namespace_aim_base_model_honors_custom_image_ref(mock_kube_client: AsyncMock) -> None:
    custom_image = "docker.io/amd/custom-base:9.9"
    mock_kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404)

    await ensure_namespace_aim_base_model(mock_kube_client, "test-namespace", image_ref=custom_image)

    body = mock_kube_client.custom_objects.create_namespaced_custom_object.call_args.kwargs["body"]
    assert body["spec"]["image"] == custom_image


@pytest.mark.asyncio
async def test_ensure_namespace_aim_base_model_tolerates_create_race_conflict(mock_kube_client: AsyncMock) -> None:
    mock_kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404)
    mock_kube_client.custom_objects.create_namespaced_custom_object.side_effect = ApiException(status=409)

    await ensure_namespace_aim_base_model(mock_kube_client, "test-namespace")


@pytest.mark.asyncio
async def test_ensure_namespace_aim_base_model_noop_when_scope_not_namespace(mock_kube_client: AsyncMock) -> None:
    with patch("app.custom_models.service.AIM_BASE_MODEL_SCOPE", "Cluster"):
        await ensure_namespace_aim_base_model(mock_kube_client, "test-namespace")

    mock_kube_client.custom_objects.get_namespaced_custom_object.assert_not_called()
    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_not_called()


@pytest.mark.asyncio
async def test_onboard_provisions_aim_base_before_custom_model_create(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    create_calls: list[dict] = []
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
    mock_kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404)

    def record_create(*_args: Any, body: dict, **_kwargs: Any) -> dict:
        create_calls.append(body)
        return body

    mock_kube_client.custom_objects.create_namespaced_custom_object.side_effect = record_create

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Llama-3-8B"),
    )

    assert len(create_calls) == 2
    assert create_calls[0]["metadata"]["name"] == AIM_BASE_MODEL_NAME
    assert "profiles" in create_calls[1]["spec"]


@pytest.mark.asyncio
async def test_onboard_skips_aim_base_create_when_already_present(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    async def get_namespaced_custom_object(*_args: Any, name: str, **_kwargs: Any) -> dict:
        if name == AIM_BASE_MODEL_NAME:
            return _AIM_BASE_STUB
        raise ApiException(status=404)

    mock_kube_client.custom_objects.get_namespaced_custom_object = AsyncMock(side_effect=get_namespaced_custom_object)

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Llama-3-8B"),
    )

    create_call = mock_kube_client.custom_objects.create_namespaced_custom_object.await_args
    assert create_call is not None
    created_body = create_call.kwargs.get("body") or create_call.args[-1]
    assert created_body["metadata"]["name"] != AIM_BASE_MODEL_NAME


@pytest.mark.asyncio
async def test_onboard_repatches_existing_model_after_ensuring_aim_base(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """Re-onboard must still provision aim-base when missing, then patch the custom AIMModel."""
    existing = _make_existing_aim_model()
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404)
    mock_kube_client.custom_objects.patch_namespaced_custom_object.return_value = existing.model_dump(by_alias=True)

    create_calls: list[dict] = []

    def record_create(*_args: Any, body: dict, **_kwargs: Any) -> dict:
        create_calls.append(body)
        return body

    mock_kube_client.custom_objects.create_namespaced_custom_object.side_effect = record_create

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Meta-Llama-3-8B-Instruct", description="An open model."),
    )

    assert len(create_calls) == 1
    assert create_calls[0]["metadata"]["name"] == AIM_BASE_MODEL_NAME
    mock_kube_client.custom_objects.patch_namespaced_custom_object.assert_called_once()
    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_called_once()


# --- onboard_custom_model_source ---


@pytest.mark.asyncio
async def test_onboard_rejects_malformed_repo_id_before_touching_k8s_or_s3(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock, stub_onboard_hub_reverify: dict[str, AsyncMock]
) -> None:
    """Repo id validation runs at the service boundary so a malformed value never
    reaches the K8s API (where it would otherwise produce a malformed label and a
    confusing admission error). It also fails before the Hub re-verify fetch so
    we don't burn a Hub call on a request we already know is bad."""
    with pytest.raises(ValidationException, match="not a valid Hugging Face repo id"):
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(repo_id="not-a-valid-repo"),
        )

    stub_onboard_hub_reverify["fetch"].assert_not_called()
    mock_kube_client.custom_objects.list_namespaced_custom_object.assert_not_called()
    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_not_called()
    mock_kube_client.custom_objects.patch_namespaced_custom_object.assert_not_called()
    mock_minio_client.upload_object.assert_not_called()


@pytest.mark.asyncio
async def test_onboard_accepts_custom_profile_without_warning(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """customProfile is now wired end-to-end; the legacy "wiring not implemented" warning must not fire."""
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    with patch("app.custom_models.service.logger") as mock_logger:
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(repo_id="meta-llama/Llama-3-8B", custom_profile={"precision": "fp16"}),
        )

    warning_messages = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert not any("customProfile" in msg and "profile wiring" in msg for msg in warning_messages)


def test_manifest_writes_custom_profile_to_aim_model_overrides() -> None:
    """customProfile lands on AIMModel.spec.profiles.overrides so aim-engine bakes it into each AIMProfile."""
    manifest = _build_manifest(
        _make_request(
            description="",
            custom_profile={
                "precision": "fp16",
                "engine": "vllm",
                "engineArgs": {"max-model-len": 4096},
            },
        )
    )

    overrides = manifest["spec"]["profiles"]["overrides"]
    assert overrides["precision"] == "fp16"
    assert overrides["engine"] == "vllm"
    assert overrides["engineArgs"] == {"max-model-len": 4096}


def test_manifest_persists_runtime_profile_fields_from_onboard_wizard() -> None:
    """The onboard wizard's customProfile (canonical acceleratorModel, precision, engineArgs/engineEnv) must persist verbatim onto overrides."""
    manifest = _build_manifest(
        _make_request(
            description="",
            custom_profile={
                "imageFamilyId": "aim-base",
                "acceleratorType": "gpu",
                "acceleratorModel": "MI300X",
                "acceleratorCount": 1,
                "precision": "fp16",
                "engineArgs": {"max-model-len": 4096, "attention-backend": "TRITON_ATTN"},
                # Env vars arrive as name/value entries (UPPER_SNAKE_CASE names ride as
                # values to clear the camelCase contract) and collapse to a map on write.
                "engineEnv": [{"name": "VLLM_ROCM_USE_AITER", "value": "1"}],
            },
        )
    )

    overrides = manifest["spec"]["profiles"]["overrides"]
    # Precision and the canonical model name (not a device id) reach the spec.
    assert overrides["acceleratorModel"] == "MI300X"
    assert overrides["precision"] == "fp16"
    # Engine args / env vars persist as structured maps, not empty.
    assert overrides["engineArgs"] == {"max-model-len": 4096, "attention-backend": "TRITON_ATTN"}
    assert overrides["engineEnv"] == {"VLLM_ROCM_USE_AITER": "1"}


def test_manifest_stamped_fields_win_over_conflicting_custom_profile_keys() -> None:
    """customProfile must not override system-stamped aimId, modelId, image, or modelSources."""
    manifest = _build_manifest(
        _make_request(
            custom_profile={
                "aimId": "evil/evil",
                "modelId": "evil/evil",
                "image": TEST_IMAGE,
                "modelSources": [{"modelId": "evil", "sourceUri": "s3://evil/weights/"}],
                "precision": "fp16",
            },
        )
    )

    overrides = manifest["spec"]["profiles"]["overrides"]
    assert overrides["aimId"] == "meta-llama/Llama-3-8B"
    assert overrides["modelId"] == "meta-llama/Llama-3-8B"
    assert overrides["image"] == TEST_IMAGE
    assert overrides["modelSources"][0]["modelId"] == "meta-llama/Llama-3-8B"
    assert overrides["modelSources"][0]["sourceUri"] == _SOURCE_URI
    assert overrides["precision"] == "fp16"


def test_manifest_without_custom_profile_omits_runtime_override_keys() -> None:
    """v1alpha2 always emits spec.profiles; customProfile only adds extra override keys."""
    manifest = _build_manifest(_make_request(description=""))

    overrides = manifest["spec"]["profiles"]["overrides"]
    assert overrides["aimId"] == "meta-llama/Llama-3-8B"
    assert "precision" not in overrides
    assert "engine" not in overrides


def test_manifest_treats_empty_custom_profile_as_no_extra_overrides() -> None:
    """Empty customProfile ({}) must not add runtime override keys beyond the base stamp."""
    manifest = _build_manifest(_make_request(description="", custom_profile={}))

    overrides = manifest["spec"]["profiles"]["overrides"]
    assert overrides["aimId"] == "meta-llama/Llama-3-8B"
    assert "precision" not in overrides


def test_manifest_preserves_non_identifier_override_keys() -> None:
    """customProfile is an opaque pass-through: keys that aren't valid Python identifiers must round-trip."""
    manifest = _build_manifest(
        _make_request(
            description="",
            custom_profile={"engine-args": {"max-model-len": 4096}, "foo.bar": "baz"},
        )
    )

    overrides = manifest["spec"]["profiles"]["overrides"]
    assert overrides["engine-args"] == {"max-model-len": 4096}
    assert overrides["foo.bar"] == "baz"


def test_onboard_request_rejects_conflicting_image_in_custom_profile() -> None:
    """Top-level and customProfile images must agree to avoid two image refs on the emitted profile."""
    with pytest.raises(ValidationError) as exc_info:
        OnboardRequest(
            repo_id="meta-llama/Llama-3-8B",
            revision="main",
            sha="abc123",
            display_name="Llama 3 8B",
            image="docker.io/amd/tinyllama:1.0.0",
            custom_profile={"image": "docker.io/other/image:v9"},
        )

    message = str(exc_info.value)
    assert "docker.io/other/image:v9" in message
    assert "docker.io/amd/tinyllama:1.0.0" in message


def test_onboard_request_allows_matching_image_in_custom_profile() -> None:
    """The matching-image case is a no-op redundancy from the UI and must pass."""
    request = OnboardRequest(
        repo_id="meta-llama/Llama-3-8B",
        revision="main",
        sha="abc123",
        display_name="Llama 3 8B",
        image="docker.io/amd/tinyllama:1.0.0",
        custom_profile={"image": "docker.io/amd/tinyllama:1.0.0", "precision": "fp16"},
    )
    assert request.custom_profile == {"image": "docker.io/amd/tinyllama:1.0.0", "precision": "fp16"}


def test_onboard_request_allows_omitted_image_in_custom_profile() -> None:
    """customProfile without an ``image`` key inherits the top-level image."""
    request = OnboardRequest(
        repo_id="meta-llama/Llama-3-8B",
        revision="main",
        sha="abc123",
        display_name="Llama 3 8B",
        image="docker.io/amd/tinyllama:1.0.0",
        custom_profile={"precision": "fp16"},
    )
    assert request.custom_profile == {"precision": "fp16"}


def test_onboard_request_rejects_empty_image_in_custom_profile() -> None:
    """Empty customProfile.image must 422 — same rule as the required top-level image field."""
    with pytest.raises(ValidationError) as exc_info:
        OnboardRequest(
            repo_id="meta-llama/Llama-3-8B",
            revision="main",
            sha="abc123",
            display_name="Llama 3 8B",
            image="docker.io/amd/tinyllama:1.0.0",
            custom_profile={"image": ""},
        )

    assert "empty string" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_repatch_clears_custom_override_keys_when_custom_profile_omitted(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
) -> None:
    """Re-onboard without customProfile must rewrite the v1alpha2 profiles block without prior override keys."""
    existing = _make_existing_aim_model()
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.patch_namespaced_custom_object.return_value = existing.model_dump(by_alias=True)

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Meta-Llama-3-8B-Instruct"),
    )

    patch_call = mock_kube_client.custom_objects.patch_namespaced_custom_object.await_args
    assert patch_call is not None
    patch_body = patch_call.kwargs.get("body") or patch_call.args[-1]
    profiles = patch_body["spec"]["profiles"]
    assert profiles["derivedFrom"]["selector"]["role"] == "base"
    overrides = profiles["overrides"]
    assert overrides["aimId"] == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert "precision" not in overrides


@pytest.mark.asyncio
async def test_repatch_merges_custom_profile_into_profiles_overrides(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
) -> None:
    """Re-onboard with customProfile must merge runtime keys into the v1alpha2 overrides stamp."""
    existing = _make_existing_aim_model()
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.patch_namespaced_custom_object.return_value = existing.model_dump(by_alias=True)

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(
            repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
            custom_profile={"precision": "bf16"},
        ),
    )

    patch_call = mock_kube_client.custom_objects.patch_namespaced_custom_object.await_args
    assert patch_call is not None
    patch_body = patch_call.kwargs.get("body") or patch_call.args[-1]
    overrides = patch_body["spec"]["profiles"]["overrides"]
    assert overrides["precision"] == "bf16"
    assert overrides["aimId"] == "meta-llama/Meta-Llama-3-8B-Instruct"


@pytest.mark.asyncio
async def test_onboard_creates_cr_then_uploads_manifest_when_absent(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """First call onboards: provisions aim-base when absent, creates the custom AIMModel CR, then mirrors to S3."""
    call_order: list[str] = []
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
    mock_kube_client.custom_objects.get_namespaced_custom_object.side_effect = ApiException(status=404)

    def record_k8s_create(*_args: Any, **_kwargs: Any) -> dict:
        call_order.append("k8s_create")
        return _CREATED_AIM_MODEL_STUB

    def record_s3_upload(**_kwargs: Any) -> None:
        call_order.append("s3_upload")

    mock_kube_client.custom_objects.create_namespaced_custom_object.side_effect = record_k8s_create
    mock_minio_client.upload_object.side_effect = record_s3_upload

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Llama-3-8B", description="An open model."),
    )

    assert call_order == ["k8s_create", "k8s_create", "s3_upload"]

    mock_minio_client.upload_object.assert_called_once()
    upload_kwargs = mock_minio_client.upload_object.call_args.kwargs
    assert upload_kwargs["object_name"].startswith("test-namespace/custom-models/")
    assert upload_kwargs["object_name"].endswith("/manifest.yaml")
    payload = upload_kwargs["data"].decode("utf-8")
    assert payload.startswith("---"), "Manifest must start with a YAML document marker"
    documents = list(yaml.safe_load_all(payload))
    assert len(documents) == 1
    assert documents[0]["kind"] == "AIMModel"

    assert mock_kube_client.custom_objects.create_namespaced_custom_object.await_count == 2


@pytest.mark.asyncio
async def test_onboard_stamps_fresh_component_id_on_create(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """Each new onboarded CR gets a freshly generated component-id UUID stamped
    under the AIRM-prefixed annotation."""
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Llama-3-8B", description=""),
    )

    create_kwargs = mock_kube_client.custom_objects.create_namespaced_custom_object.call_args.kwargs
    body = create_kwargs["body"]
    assert "profiles" in body["spec"]
    component_id = body["metadata"]["annotations"][COMPONENT_ID_ANNOTATION]
    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    assert uuid_pattern.match(component_id), f"Expected UUID-shaped component-id, got {component_id!r}"


@pytest.mark.asyncio
async def test_onboard_is_idempotent_on_same_display_name_and_source(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """Second call with same (display name, repo) patches the CR and overwrites the manifest."""
    existing = _make_existing_aim_model()
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.patch_namespaced_custom_object.return_value = existing.model_dump(by_alias=True)

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Meta-Llama-3-8B-Instruct", description="An open model."),
    )

    mock_minio_client.upload_object.assert_called_once()
    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_not_called()
    mock_kube_client.custom_objects.patch_namespaced_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_onboard_re_submission_preserves_appended_aim_profile(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """Re-onboarding must not erase an AIMProfile document already in the manifest.

    The upsert path replaces the AIMModel document by ``(kind, name)`` identity
    while leaving sibling documents (e.g. an AIMProfile appended separately)
    intact.
    """
    existing = _make_existing_aim_model()
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.patch_namespaced_custom_object.return_value = existing.model_dump(by_alias=True)

    aim_profile_doc = {
        "apiVersion": "aim.eai.amd.com/v1alpha2",
        "kind": "AIMProfile",
        "metadata": {
            "name": f"{existing.metadata.name}-default",
            "namespace": "test-namespace",
            "annotations": {"aim.eai.amd.com/deployment-image-ref": "amdenterpriseai/aim-base:0.11"},
        },
        "spec": {"aimId": existing.metadata.name, "image": "amdenterpriseai/aim-base:0.11"},
    }
    prior_aim_model_doc = {
        "apiVersion": "aim.eai.amd.com/v1alpha1",
        "kind": "AIMModel",
        "metadata": {"name": existing.metadata.name, "namespace": "test-namespace"},
        "spec": {"modelSources": [{"modelId": "meta-llama/Meta-Llama-3-8B-Instruct", "sourceUri": "s3://prior"}]},
    }
    prior_manifest = yaml.safe_dump_all(
        [prior_aim_model_doc, aim_profile_doc], sort_keys=False, explicit_start=True
    ).encode("utf-8")
    mock_minio_client.download_object.side_effect = None
    mock_minio_client.download_object.return_value = prior_manifest

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Meta-Llama-3-8B-Instruct", description="An open model."),
    )

    mock_minio_client.upload_object.assert_called_once()
    upload_kwargs = mock_minio_client.upload_object.call_args.kwargs
    written_documents = list(yaml.safe_load_all(upload_kwargs["data"]))

    kinds_in_order = [doc["kind"] for doc in written_documents]
    assert kinds_in_order == ["AIMModel", "AIMProfile"], (
        "Re-onboard must replace the AIMModel document in place and leave sibling documents untouched."
    )
    assert written_documents[1] == aim_profile_doc, (
        "AIMProfile document was modified by re-onboard; only its sibling AIMModel doc may change on re-submission."
    )


@pytest.mark.asyncio
async def test_onboard_preserves_component_id_on_patch(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """An idempotent re-submission must reuse the existing CR's component-id so
    the stable identity survives across patches."""
    existing = _make_existing_aim_model()
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.patch_namespaced_custom_object.return_value = existing.model_dump(by_alias=True)

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Meta-Llama-3-8B-Instruct", description=""),
    )

    patch_kwargs = mock_kube_client.custom_objects.patch_namespaced_custom_object.call_args.kwargs
    annotations = patch_kwargs["body"]["metadata"]["annotations"]
    assert annotations[COMPONENT_ID_ANNOTATION] == _EXISTING_COMPONENT_ID


@pytest.mark.asyncio
async def test_onboard_backfills_component_id_for_legacy_cr_on_patch(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """Legacy CRs predating the AIRM annotation must get a freshly stamped
    component-id on first patch so subsequent calls have something to preserve."""
    existing = _make_existing_aim_model(component_id=None)
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.patch_namespaced_custom_object.return_value = existing.model_dump(by_alias=True)

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(repo_id="meta-llama/Meta-Llama-3-8B-Instruct", description=""),
    )

    patch_kwargs = mock_kube_client.custom_objects.patch_namespaced_custom_object.call_args.kwargs
    annotations = patch_kwargs["body"]["metadata"]["annotations"]
    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    assert uuid_pattern.match(annotations[COMPONENT_ID_ANNOTATION])


@pytest.mark.asyncio
async def test_onboard_conflict_on_same_display_name_different_repo(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """Same display name but a different HF repo must raise so the FE prompts for a new name.
    The conflict key is modelId (the HF repo), not sourceUri (the s3:// path the system assigns)."""
    existing = _make_existing_aim_model(repo_id="meta-llama/Meta-Llama-3-8B-Instruct")
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }

    with pytest.raises(ConflictException, match="already exists"):
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(repo_id="other/Model", description=""),
        )

    mock_minio_client.upload_object.assert_not_called()
    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_not_called()
    mock_kube_client.custom_objects.patch_namespaced_custom_object.assert_not_called()


@pytest.mark.asyncio
async def test_onboard_skips_s3_when_k8s_create_fails(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """k8s-first ordering: when the CR create fails, S3 is never touched — so there's
    nothing to compensate and the next retry starts from a clean slate."""
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}
    mock_kube_client.custom_objects.create_namespaced_custom_object.side_effect = RuntimeError("kube boom")

    with pytest.raises(RuntimeError, match="kube boom"):
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(repo_id="meta-llama/Llama-3-8B", description=""),
        )

    mock_minio_client.upload_object.assert_not_called()
    mock_minio_client.delete_object.assert_not_called()


@pytest.mark.asyncio
async def test_onboard_skips_s3_when_k8s_patch_fails(mock_kube_client: AsyncMock, mock_minio_client: MagicMock) -> None:
    """k8s-first ordering: when the CR patch fails, S3 is never overwritten — so the
    existing mirror is unchanged and the next idempotent call retries cleanly.
    """
    existing = _make_existing_aim_model()
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {
        "items": [existing.model_dump(by_alias=True)]
    }
    mock_kube_client.custom_objects.patch_namespaced_custom_object.side_effect = ApiException(
        status=500, reason="Internal Server Error"
    )

    with pytest.raises(ExternalServiceError, match="Failed to patch AIMModel"):
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(repo_id="meta-llama/Meta-Llama-3-8B-Instruct", description=""),
        )

    mock_minio_client.upload_object.assert_not_called()
    mock_minio_client.delete_object.assert_not_called()


@pytest.mark.asyncio
async def test_onboard_rolls_back_cr_when_s3_upload_fails(
    mock_kube_client: AsyncMock, mock_minio_client: MagicMock
) -> None:
    """A failed S3 manifest sync deletes the just-created CR so the next call
    can retry from a clean slate instead of finding a CR without a manifest."""
    mock_kube_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    with patch(
        "app.custom_models.service.write_manifest_to_s3",
        side_effect=RuntimeError("s3 down"),
    ):
        with pytest.raises(RuntimeError, match="s3 down"):
            await onboard_custom_model_source(
                mock_kube_client,
                mock_minio_client,
                "test-namespace",
                TEST_SUBMITTER,
                _make_request(repo_id="meta-llama/Llama-3-8B", description=""),
            )

    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_called_once()
    mock_kube_client.custom_objects.delete_namespaced_custom_object.assert_called_once()


# --- onboard Hub re-verify ---


@pytest.mark.asyncio
async def test_onboard_reverifies_sha_with_hub_before_touching_k8s(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
    stub_onboard_hub_reverify: dict[str, AsyncMock],
) -> None:
    """Onboard re-fetches Hub with the request's (repo_id, revision) before any
    K8s read/write so a stale or forged sha is caught at the API boundary, not
    after a partial CR write."""
    call_order: list[str] = []

    def record_hub_fetch(*_args: Any, **_kwargs: Any) -> dict:
        call_order.append("hub_fetch")
        return {"sha": _DEFAULT_REQUEST_SHA}

    stub_onboard_hub_reverify["fetch"].side_effect = record_hub_fetch

    def record_list(*_args: Any, **_kwargs: Any) -> dict:
        call_order.append("k8s_list")
        return {"items": []}

    mock_kube_client.custom_objects.list_namespaced_custom_object.side_effect = record_list

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(),
    )

    assert call_order[:2] == ["hub_fetch", "k8s_list"]
    stub_onboard_hub_reverify["fetch"].assert_called_once()
    # Hub is asked about exactly what the client claims, so the verification can
    # actually detect a mismatch — passing canonicalised values here would mask
    # the very forgery we're guarding against.
    fetch_args = stub_onboard_hub_reverify["fetch"].call_args.args
    assert fetch_args[0] == "meta-llama/Llama-3-8B"
    assert fetch_args[1] == "main"


@pytest.mark.asyncio
async def test_onboard_resolves_hf_token_and_forwards_to_hub_reverify(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
    stub_onboard_hub_reverify: dict[str, AsyncMock],
) -> None:
    """When the request names an HF token secret, the re-verify Hub call must
    use that token — otherwise gated repos would 401/403 on re-verify even
    when the user supplied valid credentials."""
    stub_onboard_hub_reverify["token"].return_value = "hf_real_token"

    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(hf_token_secret_name="my-hf-secret"),
    )

    stub_onboard_hub_reverify["token"].assert_called_once()
    token_call_args = stub_onboard_hub_reverify["token"].call_args.args
    assert token_call_args[1] == "test-namespace"
    assert token_call_args[2] == "my-hf-secret"
    fetch_args = stub_onboard_hub_reverify["fetch"].call_args.args
    assert fetch_args[2] == "hf_real_token"


@pytest.mark.asyncio
async def test_onboard_skips_token_fetch_when_no_secret_supplied(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
    stub_onboard_hub_reverify: dict[str, AsyncMock],
) -> None:
    """A public repo onboard must not read any secret, and must call Hub
    anonymously — both for least-privilege and so the Hub 401-without-token
    message is the one users see."""
    await onboard_custom_model_source(
        mock_kube_client,
        mock_minio_client,
        "test-namespace",
        TEST_SUBMITTER,
        _make_request(hf_token_secret_name=None),
    )

    stub_onboard_hub_reverify["token"].assert_not_called()
    assert stub_onboard_hub_reverify["fetch"].call_args.args[2] is None


@pytest.mark.asyncio
async def test_onboard_rejects_when_hub_sha_differs_from_request_sha(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
    stub_onboard_hub_reverify: dict[str, AsyncMock],
) -> None:
    """The named revision moved between preview and onboard (or the caller
    forged a sha). Reject as 400-mapped ValidationException naming both shas
    so the FE can prompt the user to re-preview."""
    stub_onboard_hub_reverify["fetch"].return_value = {"sha": "deadbeef_current_hub_sha"}

    with pytest.raises(ValidationException) as exc_info:
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(sha="abc123_stale_sha"),
        )

    message = str(exc_info.value)
    assert "abc123_stale_sha" in message
    assert "deadbeef_current_hub_sha" in message
    assert "Re-preview" in message

    mock_kube_client.custom_objects.list_namespaced_custom_object.assert_not_called()
    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_not_called()
    mock_kube_client.custom_objects.patch_namespaced_custom_object.assert_not_called()
    mock_minio_client.upload_object.assert_not_called()


@pytest.mark.asyncio
async def test_onboard_rejects_when_hub_returns_no_sha(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
    stub_onboard_hub_reverify: dict[str, AsyncMock],
) -> None:
    """Mirrors the preview semantics: an unpinnable Hub response is an upstream
    error, not a client error."""
    stub_onboard_hub_reverify["fetch"].return_value = {"sha": ""}

    with pytest.raises(ExternalServiceError, match="did not return a SHA"):
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(),
        )

    mock_kube_client.custom_objects.list_namespaced_custom_object.assert_not_called()


@pytest.mark.asyncio
async def test_onboard_propagates_hub_forbidden_unchanged(
    mock_kube_client: AsyncMock,
    mock_minio_client: MagicMock,
    stub_onboard_hub_reverify: dict[str, AsyncMock],
) -> None:
    """ForbiddenException from the re-verify fetch must propagate so the global
    handler surfaces 403 — same mapping preview uses. Re-wrapping would mask
    a gated-repo failure as a generic onboard error."""
    stub_onboard_hub_reverify["fetch"].side_effect = ForbiddenException("Hub denied access")

    with pytest.raises(ForbiddenException):
        await onboard_custom_model_source(
            mock_kube_client,
            mock_minio_client,
            "test-namespace",
            TEST_SUBMITTER,
            _make_request(),
        )

    mock_kube_client.custom_objects.list_namespaced_custom_object.assert_not_called()


# --- preview side-effect guard ---


@pytest.mark.asyncio
async def test_preview_does_not_onboard(mock_kube_client: AsyncMock, mock_minio_client: MagicMock) -> None:
    """Preview remains read-only and does not touch k8s or S3."""
    with patch("app.custom_models.service._fetch_hub_model", return_value=HUB_RESPONSE):
        result = await preview_model_source(
            kube_client=mock_kube_client,
            namespace="test-namespace",
            request=PreviewRequest(source="meta-llama/Meta-Llama-3-8B-Instruct"),
        )

    assert result.display_name == "Llama 3 8B"
    mock_minio_client.upload_object.assert_not_called()
    mock_kube_client.custom_objects.create_namespaced_custom_object.assert_not_called()
