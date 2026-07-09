# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for deleting onboarded custom models (service layer)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import tenacity
from kubernetes_asyncio.client import ApiException, CustomObjectsApi

from api_common.exceptions import ConflictException, ExternalServiceError, NotFoundException
from app.aims.crds import AIMModelResource
from app.custom_models.constants import REVISION_ANNOTATION, SOURCE_URI_ANNOTATION
from app.custom_models.service import delete_onboarded_model
from app.dispatch.crds import K8sMetadata
from app.dispatch.kube_client import KubernetesClient
from app.minio import MinioClient
from app.models.utils import delete_from_s3
from app.workloads.constants import MODEL_NAME_LABEL, MODEL_SOURCE_TYPE_LABEL
from app.workloads.enums import ModelSourceType

_NAMESPACE = "test-namespace"
_MODEL_NAME = "llama-3-8b-import-12345678"


@pytest.fixture(autouse=True)
def _disable_delete_from_s3_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    # delete_from_s3 retries with exponential backoff; collapse it so the
    # S3-failure path raises immediately instead of sleeping through retries.
    monkeypatch.setattr(delete_from_s3.retry, "wait", tenacity.wait_none())
    monkeypatch.setattr(delete_from_s3.retry, "stop", tenacity.stop_after_attempt(1))


def _custom_model(name: str = _MODEL_NAME) -> AIMModelResource:
    return AIMModelResource(
        metadata=K8sMetadata(
            name=name,
            namespace=_NAMESPACE,
            labels={
                MODEL_NAME_LABEL: "llama-3-8b",
                MODEL_SOURCE_TYPE_LABEL: ModelSourceType.CUSTOM,
            },
            annotations={
                REVISION_ANNOTATION: "main",
                SOURCE_URI_ANNOTATION: f"s3://bucket/{_NAMESPACE}/custom-models/{name}/weights/",
            },
        ),
        spec={"modelSources": []},
    )


def _aim_service_item(name: str, model_name: str = _MODEL_NAME) -> dict:
    return {
        "metadata": {"name": name, "namespace": _NAMESPACE},
        "spec": {"model": {"name": model_name}},
    }


@pytest.fixture
def mock_minio_client() -> MagicMock:
    return MagicMock(spec=MinioClient)


@pytest.fixture
def mock_kube_client() -> MagicMock:
    mock = MagicMock(spec=KubernetesClient)
    mock.custom_objects = MagicMock(spec=CustomObjectsApi)
    mock.custom_objects.get_namespaced_custom_object = AsyncMock(return_value=_custom_model().model_dump(by_alias=True))
    mock.custom_objects.list_namespaced_custom_object = AsyncMock(return_value={"items": []})
    mock.custom_objects.delete_namespaced_custom_object = AsyncMock(return_value=None)
    return mock


async def test_delete_with_no_deployments_deletes_cr_then_s3(
    mock_kube_client: MagicMock,
    mock_minio_client: MagicMock,
) -> None:
    call_order: list[str] = []
    mock_kube_client.custom_objects.delete_namespaced_custom_object.side_effect = lambda *a, **k: call_order.append(
        "cr"
    )
    mock_minio_client.delete_objects.side_effect = lambda *a, **k: call_order.append("s3")

    await delete_onboarded_model(
        kube_client=mock_kube_client,
        minio_client=mock_minio_client,
        namespace=_NAMESPACE,
        name=_MODEL_NAME,
    )

    mock_kube_client.custom_objects.delete_namespaced_custom_object.assert_called_once()
    mock_minio_client.delete_objects.assert_called_once()
    # Ordering contract: the live CR delete must precede S3 cleanup.
    assert call_order == ["cr", "s3"]
    delete_kwargs = mock_kube_client.custom_objects.delete_namespaced_custom_object.call_args.kwargs
    assert delete_kwargs["name"] == _MODEL_NAME
    s3_kwargs = mock_minio_client.delete_objects.call_args.kwargs
    assert s3_kwargs["prefix"].endswith(f"custom-models/{_MODEL_NAME}/")


async def test_delete_blocked_by_active_deployment_raises_conflict(
    mock_kube_client: MagicMock,
    mock_minio_client: MagicMock,
) -> None:
    mock_kube_client.custom_objects.list_namespaced_custom_object = AsyncMock(
        return_value={"items": [_aim_service_item("svc-alpha"), _aim_service_item("svc-beta")]}
    )

    with pytest.raises(ConflictException) as exc_info:
        await delete_onboarded_model(
            kube_client=mock_kube_client,
            minio_client=mock_minio_client,
            namespace=_NAMESPACE,
            name=_MODEL_NAME,
        )

    message = str(exc_info.value)
    assert "svc-alpha" in message
    assert "svc-beta" in message
    mock_kube_client.custom_objects.delete_namespaced_custom_object.assert_not_called()
    mock_minio_client.delete_objects.assert_not_called()


async def test_delete_missing_model_raises_not_found(
    mock_kube_client: MagicMock,
    mock_minio_client: MagicMock,
) -> None:
    mock_kube_client.custom_objects.get_namespaced_custom_object = AsyncMock(side_effect=ApiException(status=404))

    with pytest.raises(NotFoundException, match="not found"):
        await delete_onboarded_model(
            kube_client=mock_kube_client,
            minio_client=mock_minio_client,
            namespace=_NAMESPACE,
            name="no-such-model",
        )

    mock_kube_client.custom_objects.delete_namespaced_custom_object.assert_not_called()
    mock_minio_client.delete_objects.assert_not_called()


async def test_delete_non_custom_model_raises_not_found(
    mock_kube_client: MagicMock,
    mock_minio_client: MagicMock,
) -> None:
    # A model without the custom-onboard revision annotation (e.g. a fine-tuned
    # AIMModel) must not be deletable through the custom-model endpoint.
    non_custom = AIMModelResource(
        metadata=K8sMetadata(name="finetuned-model", namespace=_NAMESPACE),
        spec={"modelSources": []},
    )
    mock_kube_client.custom_objects.get_namespaced_custom_object = AsyncMock(
        return_value=non_custom.model_dump(by_alias=True)
    )

    with pytest.raises(NotFoundException, match="not found"):
        await delete_onboarded_model(
            kube_client=mock_kube_client,
            minio_client=mock_minio_client,
            namespace=_NAMESPACE,
            name="finetuned-model",
        )

    mock_kube_client.custom_objects.delete_namespaced_custom_object.assert_not_called()
    mock_minio_client.delete_objects.assert_not_called()


async def test_delete_swallows_s3_failure_after_cr_deleted(
    mock_kube_client: MagicMock,
    mock_minio_client: MagicMock,
) -> None:
    # Once the CR is gone the live intent is fulfilled; an S3 cleanup failure is
    # logged and recovered out-of-band rather than failing the request.
    mock_minio_client.delete_objects.side_effect = RuntimeError("S3 unavailable")

    await delete_onboarded_model(
        kube_client=mock_kube_client,
        minio_client=mock_minio_client,
        namespace=_NAMESPACE,
        name=_MODEL_NAME,
    )

    mock_kube_client.custom_objects.delete_namespaced_custom_object.assert_called_once()
    mock_minio_client.delete_objects.assert_called_once()


async def test_delete_non_404_read_error_raises_external_service_error(
    mock_kube_client: MagicMock,
    mock_minio_client: MagicMock,
) -> None:
    # A non-404 ApiException from the async k8s client is not caught by the app's
    # sync-ApiException handler, so the service must translate it into a
    # ExternalServiceError (502) to honour the documented contract.
    mock_kube_client.custom_objects.get_namespaced_custom_object = AsyncMock(
        side_effect=ApiException(status=500, reason="etcd unavailable")
    )

    with pytest.raises(ExternalServiceError):
        await delete_onboarded_model(
            kube_client=mock_kube_client,
            minio_client=mock_minio_client,
            namespace=_NAMESPACE,
            name=_MODEL_NAME,
        )

    mock_kube_client.custom_objects.delete_namespaced_custom_object.assert_not_called()
    mock_minio_client.delete_objects.assert_not_called()


async def test_delete_non_404_delete_error_raises_external_service_error(
    mock_kube_client: MagicMock,
    mock_minio_client: MagicMock,
) -> None:
    # A non-404 failure on the CR delete itself must also surface as 502, and the
    # S3 cleanup must not run since the live record was not removed.
    mock_kube_client.custom_objects.delete_namespaced_custom_object = AsyncMock(
        side_effect=ApiException(status=503, reason="apiserver overloaded")
    )

    with pytest.raises(ExternalServiceError):
        await delete_onboarded_model(
            kube_client=mock_kube_client,
            minio_client=mock_minio_client,
            namespace=_NAMESPACE,
            name=_MODEL_NAME,
        )

    mock_minio_client.delete_objects.assert_not_called()
