# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import json

from kubernetes import client

from .config import METRICS_CONFIG_MAP_NAME, METRICS_CONFIG_MAP_NAMESPACE


async def __get_configmap_data(namespace=METRICS_CONFIG_MAP_NAMESPACE, configmap_name=METRICS_CONFIG_MAP_NAME):
    # Create a Kubernetes API client
    v1 = client.CoreV1Api()

    # Get the ConfigMap
    configmap = v1.read_namespaced_config_map(configmap_name, namespace)

    # Extract the `config.json` data
    config_json = configmap.data.get("config.json", "{}")
    return json.loads(config_json)  # Parse the JSON string


async def get_metrics_cluster_info(namespace=METRICS_CONFIG_MAP_NAMESPACE, configmap_name=METRICS_CONFIG_MAP_NAME):
    # Get the ConfigMap data
    config_data = await __get_configmap_data(namespace, configmap_name)

    # Extract ORG_NAME and KUBE_CLUSTER_NAME
    org_name = config_data.get("GPUConfig", {}).get("CustomLabels", {}).get("ORG_NAME")
    cluster_name = config_data.get("GPUConfig", {}).get("CustomLabels", {}).get("KUBE_CLUSTER_NAME")

    return org_name, cluster_name
