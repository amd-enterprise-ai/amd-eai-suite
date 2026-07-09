# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Custom-model k8s helpers.

Helpers for the **AIMProfile** that aim-engine auto-derives from an onboarded
AIMModel — wait/find/list/patch. The AIMModel CRUD itself lives in the shared
``aims.gateway`` (now v1alpha2-wide); only this profile-orchestration layer,
which encodes onboard-specific behavior (the ``deployment-image-ref`` annotation
and the ``customProfile`` pass-through), stays local to the custom-model module.
"""

import asyncio
import time
from typing import Any

from kubernetes_asyncio.client import ApiException
from loguru import logger

from api_common.exceptions import ExternalServiceError, PreconditionNotMetException

from ..aims.constants import (
    AIM_API_GROUP,
    AIM_API_VERSION,
    AIM_MODEL_LABEL,
    AIM_PROFILE_PLURAL,
    AIM_PROFILE_ROLE_BASE,
    AIM_PROFILE_ROLE_LABEL,
)
from ..aims.crds import AIMProfileResource
from ..dispatch.kube_client import KubernetesClient
from .constants import (
    AIM_DEPLOYMENT_IMAGE_REF_ANNOTATION,
    AIM_PROFILE_POLL_INTERVAL_SECONDS,
    AIM_PROFILE_WAIT_TIMEOUT_SECONDS,
)


async def list_aim_profiles(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str | None = None,
) -> list[AIMProfileResource]:
    """List namespace-scoped AIMProfile resources (v1alpha2).

    Args:
        kube_client: Kubernetes client.
        namespace: Namespace to search in.
        model_name: Optional AIMModel CR name; when provided only profiles
            stamped with the ``aim.eai.amd.com/model.name=<model_name>``
            label are returned.

    Returns:
        List of AIMProfile resources; empty list on a 404 (CRD absent in
        older clusters that haven't picked up v1alpha2 yet) or any other
        error so callers degrade gracefully into a "profile not yet
        emitted" state instead of a 500.
    """
    label_selector = f"{AIM_MODEL_LABEL}={model_name}" if model_name else None
    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_PROFILE_PLURAL,
            label_selector=label_selector,
        )
    except ApiException as e:
        if e.status == 404:
            return []
        logger.exception(f"Failed to list AIMProfiles in namespace {namespace}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Failed to list AIMProfiles in namespace {namespace}: {e}")
        return []

    profiles: list[AIMProfileResource] = []
    for item in result.get("items", []):
        try:
            profiles.append(AIMProfileResource.model_validate(item))
        except Exception as e:
            logger.error(f"Failed to parse AIMProfile: {e}")
            continue
    logger.debug(f"Found {len(profiles)} AIMProfiles for model {model_name or 'all'} in {namespace}")
    return profiles


async def list_base_role_profiles(
    kube_client: KubernetesClient,
    namespace: str,
) -> list[AIMProfileResource]:
    """List the namespace's base-role AIMProfiles (emitted by the base-image model).

    A BYOM model derives its runtime profiles from these, so their distinct
    accelerator/precision/count values are the runtime options a custom model
    will actually support — the onboard-time analogue of the deploy wizard's
    Ready-profile options. Returns an empty list on 404 or any error so the
    wizard degrades to static defaults instead of failing.
    """
    label_selector = f"{AIM_PROFILE_ROLE_LABEL}={AIM_PROFILE_ROLE_BASE}"
    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_PROFILE_PLURAL,
            label_selector=label_selector,
        )
    except ApiException as e:
        if e.status == 404:
            return []
        logger.exception(f"Failed to list base-role AIMProfiles in namespace {namespace}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Failed to list base-role AIMProfiles in namespace {namespace}: {e}")
        return []

    profiles: list[AIMProfileResource] = []
    for item in result.get("items", []):
        try:
            profiles.append(AIMProfileResource.model_validate(item))
        except Exception as e:
            logger.error(f"Failed to parse base-role AIMProfile: {e}")
            continue
    logger.debug(f"Found {len(profiles)} base-role AIMProfiles in {namespace}")
    return profiles


async def find_aim_profile_for_model(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str,
) -> AIMProfileResource | None:
    """Return the namespace-scoped AIMProfile for ``model_name``, or ``None``.

    Looks up by the ``aim.eai.amd.com/model.name`` label aim-engine
    stamps on derived profiles rather than the profile name, which aim-engine
    owns and may change. Non-404 ``ApiException``s propagate.
    """
    label_selector = f"{AIM_MODEL_LABEL}={model_name}"
    try:
        result = await kube_client.custom_objects.list_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_PROFILE_PLURAL,
            label_selector=label_selector,
        )
    except ApiException as e:
        if e.status == 404:
            return None
        raise

    items = result.get("items", [])
    if not items:
        return None
    # aim-engine emits a single default profile per AIMModel; if multiple
    # show up (e.g. tooling pre-created one) any match works for the
    # image-ref annotation since they all reference the same model.
    return AIMProfileResource.model_validate(items[0])


async def wait_for_aim_profile(
    kube_client: KubernetesClient,
    namespace: str,
    model_name: str,
    timeout_seconds: float = AIM_PROFILE_WAIT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = AIM_PROFILE_POLL_INTERVAL_SECONDS,
) -> AIMProfileResource | None:
    """Poll until the AIMProfile for ``model_name`` appears, or timeout.

    Returns the profile once visible, ``None`` on timeout. Polls rather
    than watches because the wait window is short and a watch would
    require a long-lived connection that the rest of the request flow
    does not. First probe runs immediately so an already-present
    profile resolves without sleeping.
    """
    if timeout_seconds <= 0:
        raise ValueError(f"timeout_seconds must be positive, got {timeout_seconds}")
    if poll_interval_seconds <= 0:
        raise ValueError(f"poll_interval_seconds must be positive, got {poll_interval_seconds}")

    deadline = time.monotonic() + timeout_seconds
    while True:
        profile = await find_aim_profile_for_model(kube_client, namespace, model_name)
        if profile is not None:
            return profile

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            logger.warning(
                "AIMProfile for model {} in namespace {} did not appear within {}s",
                model_name,
                namespace,
                timeout_seconds,
            )
            return None
        await asyncio.sleep(min(poll_interval_seconds, remaining))


async def patch_aim_profile(
    kube_client: KubernetesClient,
    namespace: str,
    profile_name: str,
    image_ref: str,
    custom_profile_spec: dict[str, Any] | None = None,
) -> AIMProfileResource:
    """Set ``aim.eai.amd.com/deployment-image-ref`` on a namespace AIMProfile, and
    optionally merge a user-supplied ``custom_profile_spec`` onto its ``spec``.

    Merge-patch so unrelated annotations and any spec fields aim-engine
    populated (e.g. resolved resources, container env) are preserved. The
    annotation drives BYOM image selection even though v1alpha2 AIMProfile
    has a ``spec.image`` field; the annotation wins as an override.

    ``custom_profile_spec`` is forwarded verbatim — it is the opaque
    pass-through carried through ``OnboardRequest.custom_profile``. None or
    empty results in an annotation-only patch (callers that have no profile
    overrides pay no extra cost). Validation of the dict shape is the
    caller's responsibility; aim-engine rejects unknown keys at admission.

    A 404 is translated to :class:`PreconditionNotMetException` so a profile
    that disappears between the upstream wait and this patch (aim-engine
    re-reconciling under a different name) surfaces the same way as the
    "profile never appeared" timeout, instead of an opaque 500. Other
    :class:`ApiException` failures wrap as :class:`ExternalServiceError` so
    FastAPI maps them to HTTP 502 like other Kubernetes gateway calls (the app
    only registers a handler for the synchronous ``kubernetes.client`` API
    exception type today).
    """
    if not image_ref:
        raise ValueError("image_ref must be a non-empty image reference")

    patch_body: dict[str, Any] = {
        "metadata": {
            "annotations": {
                AIM_DEPLOYMENT_IMAGE_REF_ANNOTATION: image_ref,
            }
        }
    }
    if custom_profile_spec:
        # Shallow-copy so a caller mutating the dict post-call doesn't
        # retroactively change the patch body sent to the API server.
        patch_body["spec"] = dict(custom_profile_spec)

    logger.info(
        "Patching AIMProfile {}/{} with image-ref {} and {} custom profile fields",
        namespace,
        profile_name,
        image_ref,
        len(patch_body.get("spec", {})),
    )

    try:
        patched = await kube_client.custom_objects.patch_namespaced_custom_object(
            group=AIM_API_GROUP,
            version=AIM_API_VERSION,
            namespace=namespace,
            plural=AIM_PROFILE_PLURAL,
            name=profile_name,
            body=patch_body,
            _content_type="application/merge-patch+json",
        )
    except ApiException as e:
        if e.status == 404:
            raise PreconditionNotMetException(
                message=(
                    f"AIMProfile '{profile_name}' in namespace "
                    f"'{namespace}' was not found at patch time; aim-engine "
                    "may have re-reconciled it between the wait and patch "
                    "steps. Retry the onboard so the wait helper picks up "
                    "the new profile."
                )
            ) from e
        logger.error(
            "Failed to patch AIMProfile {}/{}: status={} reason={}",
            namespace,
            profile_name,
            e.status,
            e.reason,
        )
        raise ExternalServiceError(
            f"Failed to patch AIMProfile '{profile_name}' in namespace '{namespace}': {e.reason}"
        ) from e
    return AIMProfileResource.model_validate(patched)
