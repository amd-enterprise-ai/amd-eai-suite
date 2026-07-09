# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from ..dispatch.kube_client import KubernetesClient
from .crds import Namespace
from .gateway import get_namespaces
from .security import is_valid_workbench_namespace


async def get_accessible_namespaces(
    kube_client: KubernetesClient,
    user_groups: list[str],
) -> list[Namespace]:
    """Get workbench namespaces accessible to the user.

    Single API call, in-memory filtering.
    """
    all_namespaces = await get_namespaces(kube_client)
    return [ns for ns in all_namespaces if is_valid_workbench_namespace(ns, user_groups)]
