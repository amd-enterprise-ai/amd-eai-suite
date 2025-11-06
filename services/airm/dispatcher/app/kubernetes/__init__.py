# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from kubernetes import config as k8s_config

from .config import USE_LOCAL_KUBE_CONTEXT


def load_k8s_config():
    """
    Loads up Kubernetes configuration from the cluster for the K8s Python client.
    """
    if USE_LOCAL_KUBE_CONTEXT:
        k8s_config.load_kube_config("~/.kube/config")
    else:
        k8s_config.load_incluster_config()
