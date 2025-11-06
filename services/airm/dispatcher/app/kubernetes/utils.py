# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from collections.abc import Awaitable, Callable
from typing import Any

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic import DynamicClient
from loguru import logger


async def delete_resources_by_label(
    dynamic_client: DynamicClient,
    label_selector: str,
    allowed_kinds: list[str],
    on_delete_error: Callable[[Any, ApiException, Any], Awaitable[None]],
    targeted_namespace: str | None = None,
    *,
    api_version_for_kind: dict[str, str] | None = None,
) -> bool:
    deleted_any = False

    resources = dynamic_client.resources

    for api_resource in resources.search():
        if api_resource.kind not in allowed_kinds:
            continue

        if not api_resource.namespaced:
            continue

        if api_version_for_kind and api_resource.kind in api_version_for_kind:
            if api_resource.api_version != api_version_for_kind[api_resource.kind]:
                continue

        instances = api_resource.get(body=None, label_selector=label_selector)
        for item in getattr(instances, "items", []):
            try:
                deleted_any = True
                name = getattr(item.metadata, "name")
                namespace = getattr(item.metadata, "namespace")

                if targeted_namespace is None or namespace == targeted_namespace:
                    logger.info(f"Deleting {api_resource.kind} '{name}' in '{namespace}'")

                    api_resource.delete(
                        name=name,
                        namespace=namespace,
                        body=client.V1DeleteOptions(propagation_policy="Foreground"),
                    )
            except (ApiException, AttributeError) as delete_err:
                await on_delete_error(api_resource, delete_err, item)

    return deleted_any
