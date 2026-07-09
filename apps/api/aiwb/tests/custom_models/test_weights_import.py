# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Unit tests for the HuggingFace-to-S3 weight import pipeline.

Covers the detached importer's state machine (Importing → Ready / Failed),
deletion-abort semantics, the per-file streaming helper, and the in-process
task registry used to supersede and cancel in-flight imports.
"""

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from minio import Minio
from minio.datatypes import Object

from app.custom_models import weights_import
from app.custom_models.constants import (
    IMPORT_ERROR_ANNOTATION,
    IMPORT_STATE_ANNOTATION,
)
from app.custom_models.enums import OnboardPhase
from app.custom_models.weights_import import (
    cancel_import,
    import_custom_model_weights,
    schedule_import,
)
from app.minio import MinioClient
from app.minio.config import MINIO_BUCKET

_NAMESPACE = "test-namespace"
_RESOURCE = "tinyllama-import-abc12345"
_REPO_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
_REVISION = "main"


@pytest.fixture(autouse=True)
async def _clear_registry() -> AsyncIterator[None]:
    """Isolate the module-global task registry between tests.

    Leftover tasks are cancelled and awaited so no pending task survives the
    test (the suite treats warnings, including 'Task was destroyed', as errors).
    """
    weights_import._import_tasks.clear()
    yield
    for running in list(weights_import._import_tasks.values()):
        running.cancel_event.set()
        running.task.cancel()
        try:
            await running.task
        except (asyncio.CancelledError, Exception):
            pass
    weights_import._import_tasks.clear()


def _state_patches(patch_mock: AsyncMock) -> list[dict]:
    """Extract the annotations dict from every patch_aim_model call."""
    return [call.args[3]["metadata"]["annotations"] for call in patch_mock.call_args_list]


def _states(patch_mock: AsyncMock) -> list[str]:
    return [ann[IMPORT_STATE_ANNOTATION] for ann in _state_patches(patch_mock) if IMPORT_STATE_ANNOTATION in ann]


# ---------------------------------------------------------------------------
# import_custom_model_weights — state machine
# ---------------------------------------------------------------------------


async def test_import_happy_path_marks_importing_then_ready() -> None:
    patch_mock = AsyncMock()
    download_mock = AsyncMock()
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", patch_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.safetensors", "config.json"])),
        patch.object(weights_import, "_download_and_upload", download_mock),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=MagicMock(),
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    states = _states(patch_mock)
    assert states[0] == OnboardPhase.IMPORTING
    assert states[-1] == OnboardPhase.READY
    assert download_mock.await_count == 2
    # Only the Importing and Ready transitions patch the CR, so a multi-file
    # repo still yields exactly two patches.
    assert patch_mock.await_count == 2


async def test_import_uploads_each_file_to_weights_prefix() -> None:
    download_mock = AsyncMock()
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", AsyncMock()),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.bin"])),
        patch.object(weights_import, "_download_and_upload", download_mock),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=MagicMock(),
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token="hf-token",
        )

    # _download_and_upload(job, path)
    assert download_mock.await_args is not None
    job, path = download_mock.await_args.args
    assert (job.repo_id, job.revision, job.token, path) == (_REPO_ID, _REVISION, "hf-token", "a.bin")
    assert job.weights_prefix.endswith(f"custom-models/{_RESOURCE}/weights/")


async def test_import_clears_weights_prefix_before_mirroring() -> None:
    """Each import starts clean: the weights prefix is swept before any file is
    downloaded, so a re-onboard/retry never leaves stale objects behind."""
    minio_mock = MagicMock()
    order: list[str] = []
    minio_mock.delete_objects.side_effect = lambda *a, **k: order.append("clear")

    async def _download(job: object, path: str) -> bool:
        order.append("download")
        return True

    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", AsyncMock()),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.safetensors"])),
        patch.object(weights_import, "_download_and_upload", _download),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=minio_mock,
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    assert order and order[0] == "clear"  # swept before the first download
    bucket, prefix = minio_mock.delete_objects.call_args.args
    assert bucket == MINIO_BUCKET
    assert prefix.endswith(f"custom-models/{_RESOURCE}/weights/")


async def test_import_over_existing_prefix_reaches_ready() -> None:
    """Re-import over a non-empty weights prefix must succeed, not fail.

    The underlying SDK's remove_objects returns a lazy generator that yields
    nothing on success. delete_objects must treat that as "no errors" rather
    than raising, otherwise clearing an existing prefix before re-mirroring
    spuriously marks the model Failed.
    """
    sdk_client = MagicMock(spec=Minio)
    sdk_client.list_objects.return_value = [Object(MINIO_BUCKET, "prefix/old.safetensors")]
    sdk_client.remove_objects.return_value = iter([])  # successful delete yields nothing
    minio_client = MinioClient(host="http://localhost:9000", access_key="access_key", secret_key="secret_key")
    minio_client.client = sdk_client

    patch_mock = AsyncMock()
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", patch_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.safetensors"])),
        patch.object(weights_import, "_download_and_upload", AsyncMock(return_value=True)),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=minio_client,
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    sdk_client.remove_objects.assert_called_once()
    assert _states(patch_mock)[-1] == OnboardPhase.READY


async def test_import_empty_repo_marks_failed() -> None:
    patch_mock = AsyncMock()
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", patch_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=[])),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=MagicMock(),
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    assert _states(patch_mock)[-1] == OnboardPhase.FAILED


async def test_import_download_failure_marks_failed_with_error() -> None:
    patch_mock = AsyncMock()
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", patch_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.bin"])),
        patch.object(weights_import, "_download_and_upload", AsyncMock(side_effect=RuntimeError("network down"))),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=MagicMock(),
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    failed = [ann for ann in _state_patches(patch_mock) if ann.get(IMPORT_STATE_ANNOTATION) == OnboardPhase.FAILED]
    assert failed
    assert "network down" in failed[-1][IMPORT_ERROR_ANNOTATION]


async def test_import_aborts_silently_when_model_deleted() -> None:
    """A model deleted mid-import never reaches Ready or Failed and stops uploading."""
    patch_mock = AsyncMock()
    download_mock = AsyncMock()
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", patch_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=False)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.bin", "b.bin"])),
        patch.object(weights_import, "_download_and_upload", download_mock),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=MagicMock(),
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    states = _states(patch_mock)
    assert OnboardPhase.READY not in states
    assert OnboardPhase.FAILED not in states
    download_mock.assert_not_awaited()


async def test_import_aborts_when_upload_skipped_mid_flight() -> None:
    """A skipped upload (model deleted during the in-thread download, after the
    per-file precheck) must abort the import, not fall through to Ready.

    Single-file repos are the trap: the file passes _model_exists, then
    _download_and_upload returns False because the model vanished before upload.
    Honouring that bool is what keeps the import from marking a deleted model Ready.
    """
    patch_mock = AsyncMock()
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", patch_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["model.safetensors"])),
        patch.object(weights_import, "_download_and_upload", AsyncMock(return_value=False)),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=MagicMock(),
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    states = _states(patch_mock)
    assert OnboardPhase.READY not in states
    assert OnboardPhase.FAILED not in states


async def test_import_failure_not_recorded_when_model_gone() -> None:
    """A failure that coincides with deletion must not resurrect the model with
    a Failed annotation."""
    patch_mock = AsyncMock()
    # Exists for the per-file precheck, gone by the time the failure is recorded.
    exists_mock = AsyncMock(side_effect=[True, False])
    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", patch_mock),
        patch.object(weights_import, "_model_exists", exists_mock),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.bin"])),
        patch.object(weights_import, "_download_and_upload", AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        await import_custom_model_weights(
            kube_client=MagicMock(),
            minio_client=MagicMock(),
            namespace=_NAMESPACE,
            resource_name=_RESOURCE,
            repo_id=_REPO_ID,
            revision=_REVISION,
            token=None,
        )

    assert OnboardPhase.FAILED not in _states(patch_mock)


# ---------------------------------------------------------------------------
# _download_and_upload — direct HF-to-MinIO streaming
# ---------------------------------------------------------------------------


async def test_download_and_upload_streams_to_minio() -> None:
    """Happy path: _stream_hf_to_minio is called with the right object name."""
    stream_mock = MagicMock()
    job = weights_import._ImportJob(
        kube_client=MagicMock(),
        minio_client=MagicMock(),
        namespace=_NAMESPACE,
        resource_name=_RESOURCE,
        repo_id=_REPO_ID,
        revision=_REVISION,
        token="hf-token",
    )
    path = "subdir/model.safetensors"
    with (
        patch.object(weights_import, "_stream_hf_to_minio", stream_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
    ):
        uploaded = await weights_import._download_and_upload(job, path)

    assert uploaded is True
    stream_mock.assert_called_once_with(job, path, f"{job.weights_prefix}{path}")


async def test_download_and_upload_skips_stream_when_model_deleted() -> None:
    """Model deleted before streaming starts: no stream, returns False."""
    stream_mock = MagicMock()
    job = weights_import._ImportJob(
        kube_client=MagicMock(),
        minio_client=MagicMock(),
        namespace=_NAMESPACE,
        resource_name=_RESOURCE,
        repo_id=_REPO_ID,
        revision=_REVISION,
        token=None,
    )
    with (
        patch.object(weights_import, "_stream_hf_to_minio", stream_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=False)),
    ):
        uploaded = await weights_import._download_and_upload(job, "model.safetensors")

    assert uploaded is False
    stream_mock.assert_not_called()


async def test_download_and_upload_skips_stream_when_cancel_requested() -> None:
    """Cancel set before streaming starts: no stream, _model_exists not consulted."""
    stream_mock = MagicMock()
    job = weights_import._ImportJob(
        kube_client=MagicMock(),
        minio_client=MagicMock(),
        namespace=_NAMESPACE,
        resource_name=_RESOURCE,
        repo_id=_REPO_ID,
        revision=_REVISION,
        token=None,
    )
    job.cancel_event.set()
    with (
        patch.object(weights_import, "_stream_hf_to_minio", stream_mock),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)) as exists_mock,
    ):
        uploaded = await weights_import._download_and_upload(job, "model.safetensors")

    assert uploaded is False
    stream_mock.assert_not_called()
    exists_mock.assert_not_awaited()


def test_stream_hf_to_minio_pipes_response_into_put_object() -> None:
    """_stream_hf_to_minio resolves the URL, streams from HF, and calls put_object."""
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.headers = {"content-length": "1024"}

    minio_client_mock = MagicMock()
    job = weights_import._ImportJob(
        kube_client=MagicMock(),
        minio_client=MagicMock(client=minio_client_mock),
        namespace=_NAMESPACE,
        resource_name=_RESOURCE,
        repo_id=_REPO_ID,
        revision=_REVISION,
        token="hf-token",
    )
    path = "model.safetensors"
    object_name = f"{job.weights_prefix}{path}"

    with (
        patch.object(
            weights_import,
            "hf_hub_url",
            return_value="https://huggingface.co/resolve/main/model.safetensors",
        ) as url_mock,
        patch.object(weights_import.urllib3, "PoolManager") as pool_mock,
    ):
        pool_mock.return_value.request.return_value = fake_response
        weights_import._stream_hf_to_minio(job, path, object_name)

    url_mock.assert_called_once_with(_REPO_ID, path, revision=_REVISION)
    pool_mock.return_value.request.assert_called_once_with(
        "GET",
        "https://huggingface.co/resolve/main/model.safetensors",
        headers={"Authorization": "Bearer hf-token"},
        preload_content=False,
        redirect=True,
    )
    minio_client_mock.put_object.assert_called_once_with(
        MINIO_BUCKET,
        object_name,
        fake_response,
        length=1024,
        part_size=weights_import._STREAM_PART_SIZE,
    )
    fake_response.release_conn.assert_called_once()


def test_stream_hf_to_minio_raises_on_http_error() -> None:
    """A 4xx/5xx from HuggingFace surfaces as OSError."""
    fake_response = MagicMock()
    fake_response.status = 404
    fake_response.headers = {}

    job = weights_import._ImportJob(
        kube_client=MagicMock(),
        minio_client=MagicMock(),
        namespace=_NAMESPACE,
        resource_name=_RESOURCE,
        repo_id=_REPO_ID,
        revision=_REVISION,
        token=None,
    )
    with (
        patch.object(
            weights_import,
            "hf_hub_url",
            return_value="https://huggingface.co/resolve/main/model.safetensors",
        ),
        patch.object(weights_import.urllib3, "PoolManager") as pool_mock,
    ):
        pool_mock.return_value.request.return_value = fake_response
        with pytest.raises(OSError, match="404"):
            weights_import._stream_hf_to_minio(job, "model.safetensors", "prefix/model.safetensors")

    fake_response.release_conn.assert_called_once()


async def test_fetch_repo_files_delegates_to_hf_api() -> None:
    api_mock = MagicMock()
    api_mock.list_repo_files.return_value = ["model.safetensors", "config.json"]

    job = weights_import._ImportJob(
        kube_client=MagicMock(),
        minio_client=MagicMock(),
        namespace=_NAMESPACE,
        resource_name=_RESOURCE,
        repo_id=_REPO_ID,
        revision=_REVISION,
        token="hf-token",
    )
    with patch.object(weights_import, "HfApi", return_value=api_mock):
        files = await weights_import._fetch_repo_files(job)

    assert files == ["model.safetensors", "config.json"]
    api_mock.list_repo_files.assert_called_once_with(_REPO_ID, revision=_REVISION, token="hf-token")


async def test_fetch_repo_files_drops_non_runtime_cruft_but_keeps_runtime_assets() -> None:
    api_mock = MagicMock()
    api_mock.list_repo_files.return_value = [
        # runtime assets a curated allow-list would risk dropping — must be kept
        "model.safetensors",
        "model.safetensors.index.json",
        "pytorch_model.bin",
        "config.json",
        "tokenizer.model",
        "generation_config.json",
        "modeling_custom.py",
        # non-runtime cruft — must be dropped
        "README.md",
        "docs/README.md",
        "LICENSE",
        ".gitattributes",
        ".github/workflows/ci.yml",
        "assets/logo.png",
    ]

    job = weights_import._ImportJob(
        kube_client=MagicMock(),
        minio_client=MagicMock(),
        namespace=_NAMESPACE,
        resource_name=_RESOURCE,
        repo_id=_REPO_ID,
        revision=_REVISION,
        token=None,
    )
    with patch.object(weights_import, "HfApi", return_value=api_mock):
        files = await weights_import._fetch_repo_files(job)

    assert files == [
        "model.safetensors",
        "model.safetensors.index.json",
        "pytorch_model.bin",
        "config.json",
        "tokenizer.model",
        "generation_config.json",
        "modeling_custom.py",
    ]


# ---------------------------------------------------------------------------
# Task registry — schedule / supersede / cancel
# ---------------------------------------------------------------------------


async def test_schedule_import_registers_then_clears_on_completion() -> None:
    async def _noop(**kwargs: object) -> None:
        return None

    with patch.object(weights_import, "import_custom_model_weights", _noop):
        schedule_import(MagicMock(), MagicMock(), _NAMESPACE, _RESOURCE, _REPO_ID, _REVISION, None)
        running = weights_import._import_tasks[(_NAMESPACE, _RESOURCE)]
        await running.task

    assert (_NAMESPACE, _RESOURCE) not in weights_import._import_tasks


async def test_schedule_import_supersedes_in_flight() -> None:
    """A re-onboard signals the prior import to stop (cooperatively) and registers
    a fresh task; the superseded import drains rather than being hard-cancelled."""
    started = asyncio.Event()

    async def _blocking(*, cancel_event: asyncio.Event, **kwargs: object) -> None:
        started.set()
        await cancel_event.wait()

    with patch.object(weights_import, "import_custom_model_weights", _blocking):
        schedule_import(MagicMock(), MagicMock(), _NAMESPACE, _RESOURCE, _REPO_ID, _REVISION, None)
        first = weights_import._import_tasks[(_NAMESPACE, _RESOURCE)].task
        await started.wait()

        schedule_import(MagicMock(), MagicMock(), _NAMESPACE, _RESOURCE, _REPO_ID, _REVISION, None)
        second = weights_import._import_tasks[(_NAMESPACE, _RESOURCE)].task

        assert first is not second
        # The superseded import was signalled and drains to a normal completion.
        await asyncio.wait_for(first, timeout=1)
        assert first.done() and not first.cancelled()


async def test_import_waits_for_superseded_import_before_writing() -> None:
    """A re-onboard's new import must not touch S3 until the prior import drains."""
    order: list[str] = []
    prev_can_finish = asyncio.Event()

    async def _previous() -> None:
        await prev_can_finish.wait()
        order.append("previous-finished")

    previous_task = asyncio.create_task(_previous())

    async def _download(job: object, path: str) -> bool:
        order.append("download")
        return True

    with (
        patch.object(weights_import.aims_gateway, "patch_aim_model", AsyncMock()),
        patch.object(weights_import, "_model_exists", AsyncMock(return_value=True)),
        patch.object(weights_import, "_fetch_repo_files", AsyncMock(return_value=["a.bin"])),
        patch.object(weights_import, "_download_and_upload", _download),
    ):
        import_task = asyncio.create_task(
            import_custom_model_weights(
                kube_client=MagicMock(),
                minio_client=MagicMock(),
                namespace=_NAMESPACE,
                resource_name=_RESOURCE,
                repo_id=_REPO_ID,
                revision=_REVISION,
                token=None,
                previous_task=previous_task,
            )
        )
        await asyncio.sleep(0)
        assert "download" not in order  # blocked on the superseded import
        prev_can_finish.set()
        await import_task

    assert order == ["previous-finished", "download"]


async def test_cancel_import_drains_and_clears() -> None:
    started = asyncio.Event()

    async def _blocking(*, cancel_event: asyncio.Event, **kwargs: object) -> None:
        started.set()
        await cancel_event.wait()

    with patch.object(weights_import, "import_custom_model_weights", _blocking):
        schedule_import(MagicMock(), MagicMock(), _NAMESPACE, _RESOURCE, _REPO_ID, _REVISION, None)
        task = weights_import._import_tasks[(_NAMESPACE, _RESOURCE)].task
        await started.wait()
        await cancel_import(_NAMESPACE, _RESOURCE)

    # Cooperative stop: the task drains to a normal completion (not cancelled),
    # which is what proves no worker thread is still running.
    assert task.done() and not task.cancelled()
    assert (_NAMESPACE, _RESOURCE) not in weights_import._import_tasks


async def test_cancel_import_keeps_task_registered_by_concurrent_reonboard() -> None:
    """A re-onboard landing while cancel_import is draining the old task must
    survive: cancel only clears the exact task it awaited, never a newer one
    registered under the same key in the meantime (which would orphan it)."""
    key = (_NAMESPACE, _RESOURCE)
    started = [asyncio.Event(), asyncio.Event()]
    releases = [asyncio.Event(), asyncio.Event()]
    index = 0

    async def _blocking(*, cancel_event: asyncio.Event, **kwargs: object) -> None:
        nonlocal index
        i = index
        index += 1
        started[i].set()
        await releases[i].wait()

    with patch.object(weights_import, "import_custom_model_weights", _blocking):
        schedule_import(MagicMock(), MagicMock(), _NAMESPACE, _RESOURCE, _REPO_ID, _REVISION, None)
        first = weights_import._import_tasks[key].task
        await started[0].wait()

        cancel_task = asyncio.create_task(cancel_import(_NAMESPACE, _RESOURCE))
        await asyncio.sleep(0)  # let cancel_import reach `await running.task`

        # Re-onboard supersedes while the old task is still draining.
        schedule_import(MagicMock(), MagicMock(), _NAMESPACE, _RESOURCE, _REPO_ID, _REVISION, None)
        second = weights_import._import_tasks[key].task
        await started[1].wait()
        assert first is not second

        releases[0].set()  # let the task cancel_import awaited drain
        await cancel_task

        # The newcomer is still registered (and therefore cancellable), not orphaned.
        assert weights_import._import_tasks[key].task is second

        releases[1].set()
        await second


async def test_cancel_import_noop_when_nothing_running() -> None:
    await cancel_import(_NAMESPACE, "does-not-exist")
