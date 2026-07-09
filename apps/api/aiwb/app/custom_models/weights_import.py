# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Asynchronous HuggingFace-to-S3 weight import for onboarded custom models.

Onboarding records an ``s3://.../weights/`` ``sourceUri`` on the AIMModel CR but
does not populate it. This module fills that prefix by streaming every file in
the HuggingFace repo into S3, in a detached background task so the onboard call
returns immediately. State is recorded as annotations on the AIMModel CR
(``import-state``/``import-error``), which the onboard status composition reads
back.

Import tasks are tracked in a per-process registry so a delete can cancel an
in-flight import. The importer also re-checks that the AIMModel still exists
before each upload, so a deleted model never keeps writing objects even if the
cancellation lands a moment late or the import runs on another replica.
"""

import asyncio
import contextlib
import os
from dataclasses import dataclass, field

import urllib3
from huggingface_hub import HfApi
from huggingface_hub.file_download import hf_hub_url
from huggingface_hub.utils import filter_repo_objects
from loguru import logger

from ..aims import gateway as aims_gateway
from ..dispatch.kube_client import KubernetesClient
from ..minio.client import MinioClient
from ..minio.config import MINIO_BUCKET
from ..models.utils import get_custom_model_weights_path
from .constants import (
    IMPORT_ERROR_ANNOTATION,
    IMPORT_STATE_ANNOTATION,
    WEIGHT_IMPORT_IGNORE_PATTERNS,
)
from .enums import OnboardPhase

# Caps how many weight files stream concurrently. Bounds peak memory (each
# in-flight transfer holds one _STREAM_PART_SIZE buffer) and the thread-pool
# slots used by the blocking stream-to-MinIO calls.
# Clamped to >= 1: a non-positive value would build asyncio.Semaphore(0) and
# deadlock the importer, and a non-numeric value would crash API startup.
_weight_import_concurrency_raw = os.getenv("WEIGHT_IMPORT_MAX_CONCURRENCY", "4")
try:
    WEIGHT_IMPORT_MAX_CONCURRENCY = max(1, int(_weight_import_concurrency_raw))
except ValueError:
    logger.warning(f"WEIGHT_IMPORT_MAX_CONCURRENCY={_weight_import_concurrency_raw!r} is not an integer; using 4")
    WEIGHT_IMPORT_MAX_CONCURRENCY = 4

# ``asyncio.gather`` builds one Task per file; large HF repos can have tens of
# thousands of paths — materializing all of those tasks at once spikes RSS
# even though the semaphore only allows WEIGHT_IMPORT_MAX_CONCURRENCY active
# downloads. Process files in chunks so peak pending Task count stays bounded.
_WEIGHT_IMPORT_GATHER_CHUNK = 512

# In-process registry of running imports, keyed by (namespace, resource).
# Single-process by design: it mirrors the detached-task model, and the per-file
# AIMModel-existence re-check is the cross-replica/late-cancellation backstop.
_import_tasks: dict[tuple[str, str], "_RunningImport"] = {}


@dataclass(frozen=True)
class _RunningImport:
    """A scheduled import plus the event used to stop it cooperatively.

    Cancellation is cooperative (set ``cancel_event``) rather than
    ``task.cancel()`` because the download and upload run in worker threads via
    ``asyncio.to_thread``, which a coroutine cancel cannot interrupt — cancelling
    would return while a thread is still writing to S3, defeating the
    delete-then-cleanup guarantee. Setting the event lets the importer stop at a
    safe boundary (it skips the upload of any file whose download is still in
    flight), so awaiting ``task`` proves no worker thread is still running.
    """

    task: asyncio.Task
    cancel_event: asyncio.Event


@dataclass(frozen=True)
class _ImportJob:
    """Immutable inputs for one weight import.

    Bundles the clients, the source/target identity, and the cooperative
    cancellation signal so the import helpers take a single ``job`` argument
    instead of threading the same parameters through every function.
    """

    kube_client: KubernetesClient
    minio_client: MinioClient
    namespace: str
    resource_name: str
    repo_id: str
    revision: str
    token: str | None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def weights_prefix(self) -> str:
        return get_custom_model_weights_path(self.namespace, self.resource_name)


class _ImportAborted(Exception):
    """Raised internally when the AIMModel disappears mid-import.

    Signals a clean stop (the model was deleted) rather than a failure, so the
    importer neither marks the model Failed nor keeps uploading.
    """


def schedule_import(
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    resource_name: str,
    repo_id: str,
    revision: str,
    token: str | None,
) -> None:
    """Start (or restart) the detached weight import for a model.

    A re-onboard supersedes any in-flight import for the same model: the prior
    import is signalled to stop and the new task waits for it to drain before
    writing, so two imports never write the same prefix concurrently.
    """
    key = (namespace, resource_name)
    cancel_event = asyncio.Event()

    previous = _import_tasks.get(key)
    previous_task: asyncio.Task | None = None
    if previous is not None and not previous.task.done():
        previous.cancel_event.set()
        previous_task = previous.task

    task = asyncio.create_task(
        import_custom_model_weights(
            kube_client=kube_client,
            minio_client=minio_client,
            namespace=namespace,
            resource_name=resource_name,
            repo_id=repo_id,
            revision=revision,
            token=token,
            cancel_event=cancel_event,
            previous_task=previous_task,
        )
    )
    _import_tasks[key] = _RunningImport(task=task, cancel_event=cancel_event)
    task.add_done_callback(lambda finished: _discard_task(key, finished))


def _discard_task(key: tuple[str, str], task: asyncio.Task) -> None:
    """Drop a finished task from the registry unless it was already superseded."""
    running = _import_tasks.get(key)
    if running is not None and running.task is task:
        _import_tasks.pop(key, None)


async def cancel_import(namespace: str, resource_name: str) -> None:
    """Signal and await any in-flight import for a model.

    Cancellation is cooperative: the importer's downloads and uploads run in
    worker threads that a coroutine cancel cannot interrupt, so we set the
    cancel event and await the task. The importer stops launching new files and
    skips the upload of any file still downloading, so when this returns no
    worker thread is writing to S3 — the caller can then sweep the S3 tree
    without an upload racing the cleanup. A no-op when nothing is running.
    """
    key = (namespace, resource_name)
    running = _import_tasks.get(key)
    if running is None:
        return
    running.cancel_event.set()
    try:
        await running.task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"In-flight import for {resource_name} in {namespace} ended with error during cancel: {e}")
    finally:
        # Identity-check before removing: a re-onboard during the await above may
        # have registered a fresh task under this key, and that newcomer must not
        # be dropped (which would orphan it — running, but no longer cancellable).
        current = _import_tasks.get(key)
        if current is not None and current.task is running.task:
            _import_tasks.pop(key, None)


async def import_custom_model_weights(
    kube_client: KubernetesClient,
    minio_client: MinioClient,
    namespace: str,
    resource_name: str,
    repo_id: str,
    revision: str,
    token: str | None,
    cancel_event: asyncio.Event | None = None,
    previous_task: asyncio.Task | None = None,
) -> None:
    """Import a custom model's HuggingFace weights into its S3 prefix.

    Marks the model Importing, mirrors the repo to S3, then marks it Ready.
    A download/upload failure is recorded as Failed; a model deleted or an
    import cancelled mid-flight stops silently (no Ready/Failed state).

    When ``previous_task`` is set (a re-onboard superseding an in-flight import),
    waits for it to drain first so the two never write the same prefix at once.
    """
    if cancel_event is None:
        cancel_event = asyncio.Event()
    if previous_task is not None:
        with contextlib.suppress(BaseException):
            await previous_task

    job = _ImportJob(
        kube_client=kube_client,
        minio_client=minio_client,
        namespace=namespace,
        resource_name=resource_name,
        repo_id=repo_id,
        revision=revision,
        token=token,
        cancel_event=cancel_event,
    )
    try:
        await _mark_import(job, state=OnboardPhase.IMPORTING)
        await _clear_weights_prefix(job)
        completed = await _mirror_repo_to_s3(job)
        if not completed:
            logger.info(
                f"Weight import for {resource_name} in {namespace} stopped before completion (deleted or cancelled)."
            )
            return
        await _mark_import(job, state=OnboardPhase.READY)
        logger.info(f"Imported weights for {resource_name} in {namespace} to s3://{MINIO_BUCKET}/{job.weights_prefix}")
    except asyncio.CancelledError:
        logger.info(f"Weight import for {resource_name} in {namespace} was cancelled.")
        raise
    except Exception as error:
        await _record_failure(job, error)


async def _clear_weights_prefix(job: _ImportJob) -> None:
    """Remove any objects already under the model's S3 weights prefix.

    Re-onboard and retry reuse the same resource name, hence the same prefix.
    Resuming a partial import is out of scope, so every import starts clean: a
    prior revision's files or a failed attempt's leftovers are deleted up front,
    leaving the prefix with exactly the current import's files rather than a
    union of old and new.
    """
    await asyncio.to_thread(job.minio_client.delete_objects, MINIO_BUCKET, job.weights_prefix)


async def _mirror_repo_to_s3(job: _ImportJob) -> bool:
    """Copy every file in the HF repo into the model's S3 weights prefix.

    Files are copied with bounded concurrency. Returns True when all files
    imported, False when the import was aborted because the AIMModel was deleted
    mid-flight. Raises on a download/upload failure (the caller records it as
    Failed).
    """
    files = await _fetch_repo_files(job)
    if not files:
        raise ValueError(f"Hugging Face repo '{job.repo_id}' (revision '{job.revision}') has no files to import.")

    aborted = False
    semaphore = asyncio.Semaphore(WEIGHT_IMPORT_MAX_CONCURRENCY)

    async def _copy_one(path: str) -> None:
        nonlocal aborted
        async with semaphore:
            if aborted or job.cancel_event.is_set():
                return
            if not await _model_exists(job):
                aborted = True
                raise _ImportAborted()
            # A skipped upload (model deleted during the in-thread download, before
            # the pre-upload re-check) means the file never reached S3, so the import
            # is incomplete and must abort rather than fall through to Ready.
            if not await _download_and_upload(job, path):
                aborted = True
                raise _ImportAborted()

    for i in range(0, len(files), _WEIGHT_IMPORT_GATHER_CHUNK):
        chunk = files[i : i + _WEIGHT_IMPORT_GATHER_CHUNK]
        part = await asyncio.gather(*(_copy_one(path) for path in chunk), return_exceptions=True)
        if aborted or job.cancel_event.is_set() or any(isinstance(r, _ImportAborted) for r in part):
            return False
        errors = [r for r in part if isinstance(r, Exception)]
        if errors:
            raise errors[0]
    return True


async def _record_failure(job: _ImportJob, error: Exception) -> None:
    """Mark the import Failed — unless the model was deleted mid-import.

    A model deleted mid-import must not be resurrected with a Failed
    annotation, so the state is only written when the CR still exists.
    """
    logger.exception(f"Weight import for {job.resource_name} in {job.namespace} failed: {error}")
    try:
        if await _model_exists(job):
            await _mark_import(job, state=OnboardPhase.FAILED, error=str(error))
    except Exception as patch_error:
        logger.warning(f"Failed to record import failure for {job.resource_name} in {job.namespace}: {patch_error}")


async def _fetch_repo_files(job: _ImportJob) -> list[str]:
    """Return the repo files to import: every path minus non-runtime cruft.

    Starts from ``list_repo_files`` (the raw list, not the preview-curated
    weights) so runtime files the preview's allow-list would drop —
    ``*.safetensors.index.json``, ``.bin`` weights, custom ``modeling_*.py``,
    unusually named tokenizer assets — are kept. Then applies an exclude-list
    (``WEIGHT_IMPORT_IGNORE_PATTERNS``) to skip documentation/license/VCS/media
    files inference never loads.
    """
    files = await asyncio.to_thread(HfApi().list_repo_files, job.repo_id, revision=job.revision, token=job.token)
    return list(filter_repo_objects(files, ignore_patterns=list(WEIGHT_IMPORT_IGNORE_PATTERNS)))


_STREAM_PART_SIZE = 10 * 1024 * 1024  # 10 MiB per MinIO multipart part


async def _download_and_upload(job: _ImportJob, path: str) -> bool:
    """Stream one file directly from HuggingFace into MinIO without touching local disk.

    ``hf_hub_url`` resolves the canonical HuggingFace URL; urllib3 follows the
    CDN redirect and streams the response body straight into ``put_object``.
    Only a single part buffer (``_STREAM_PART_SIZE``) lives in memory at any
    one time, regardless of file size, which keeps peak memory bounded when
    importing large shards concurrently.

    Returns True when the file was uploaded, False when the upload was skipped
    because the import was cancelled or the model was deleted.
    """
    object_name = f"{job.weights_prefix}{path}"
    if job.cancel_event.is_set() or not await _model_exists(job):
        return False
    await asyncio.to_thread(_stream_hf_to_minio, job, path, object_name)
    return True


def _stream_hf_to_minio(job: _ImportJob, path: str, object_name: str) -> None:
    """Blocking helper that pipes one HuggingFace file into MinIO.

    Runs inside ``asyncio.to_thread`` so the event loop stays responsive.
    The Bearer token is sent to the HuggingFace origin; the CDN redirect URL
    is pre-signed, so auth does not need to follow the redirect.
    """
    url = hf_hub_url(job.repo_id, path, revision=job.revision)
    headers = {"Authorization": f"Bearer {job.token}"} if job.token else {}
    http = urllib3.PoolManager()
    response = http.request("GET", url, headers=headers, preload_content=False, redirect=True)
    try:
        if response.status >= 400:
            raise OSError(f"HuggingFace returned HTTP {response.status} for {path}")
        content_length = int(response.headers.get("content-length", -1))
        job.minio_client.client.put_object(
            MINIO_BUCKET,
            object_name,
            response,
            length=content_length,
            part_size=_STREAM_PART_SIZE,
        )
    finally:
        response.release_conn()


async def _model_exists(job: _ImportJob) -> bool:
    return await aims_gateway.get_aim_model(job.kube_client, job.namespace, job.resource_name) is not None


async def _mark_import(job: _ImportJob, *, state: OnboardPhase, error: str = "") -> None:
    """Patch the import-state annotations the onboard status composition reads."""
    annotations: dict[str, str] = {IMPORT_STATE_ANNOTATION: str(state), IMPORT_ERROR_ANNOTATION: error}
    await _patch_annotations(job, annotations)


async def _patch_annotations(job: _ImportJob, annotations: dict[str, str]) -> None:
    await aims_gateway.patch_aim_model(
        job.kube_client, job.namespace, job.resource_name, {"metadata": {"annotations": annotations}}
    )
