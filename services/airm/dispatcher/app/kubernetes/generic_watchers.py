# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


from collections.abc import Callable, Coroutine

from kubernetes import client

from ..kubernetes.watcher import start_kubernetes_watcher


def start_generic_configmap_watcher(callback: Callable, component_name: str, label_selector: str = "") -> Coroutine:
    return start_kubernetes_watcher(
        f"{component_name}_configmap_watcher",
        client.CoreV1Api().list_config_map_for_all_namespaces,
        callback,
        label_selector=label_selector,
    )
