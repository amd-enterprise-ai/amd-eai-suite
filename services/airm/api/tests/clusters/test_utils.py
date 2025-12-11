# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from airm.messaging.schemas import ClusterNode, GPUInformation, GPUVendor
from app.clusters.models import Cluster as ClusterModel
from app.clusters.models import ClusterNode as ClusterNodeModel
from app.clusters.utils import build_cluster_kube_config, flatten_for_db_comparison, has_node_changed


def test_flatten_for_db_comparison_without_gpu():
    node = ClusterNode(
        name="node-1",
        cpu_milli_cores=2000,
        memory_bytes=8 * 1024**3,
        ephemeral_storage_bytes=50 * 1024**3,
        gpu_information=None,
        status="Ready",
        is_ready=True,
    )

    flattened = flatten_for_db_comparison(node)

    # Ensure GPU fields are not present
    assert "gpu_count" not in flattened
    assert "gpu_type" not in flattened
    assert flattened["name"] == "node-1"
    assert flattened["cpu_milli_cores"] == 2000
    assert flattened["memory_bytes"] == 8 * 1024**3
    assert flattened["ephemeral_storage_bytes"] == 50 * 1024**3
    assert flattened["status"] == "Ready"
    assert flattened["is_ready"] is True


def test_flatten_for_db_comparison_with_gpu():
    gpu_info = GPUInformation(
        count=2,
        type="gfx908",
        vendor=GPUVendor.AMD,
        vram_bytes_per_device=16 * 1024**3,
        product_name="MI100",
    )
    node = ClusterNode(
        name="node-2",
        cpu_milli_cores=1000,
        memory_bytes=4 * 1024**3,
        ephemeral_storage_bytes=0,
        gpu_information=gpu_info,
        status="NotReady",
        is_ready=False,
    )

    flattened = flatten_for_db_comparison(node)

    # Original ClusterNode fields still exist
    assert flattened["name"] == "node-2"
    assert flattened["cpu_milli_cores"] == 1000
    assert flattened["memory_bytes"] == 4 * 1024**3
    assert flattened["ephemeral_storage_bytes"] == 0
    assert flattened["status"] == "NotReady"
    assert flattened["is_ready"] is False

    # GPU fields are flattened with prefix
    assert flattened["gpu_count"] == 2
    assert flattened["gpu_type"] == "gfx908"
    assert flattened["gpu_vendor"] == GPUVendor.AMD
    assert flattened["gpu_vram_bytes_per_device"] == 16 * 1024**3
    assert flattened["gpu_product_name"] == "MI100"


existing_node = ClusterNodeModel(
    id=uuid4(),
    name="test-node",
    cpu_milli_cores=2000,
    memory_bytes=8 * (1024**3),
    ephemeral_storage_bytes=100 * (1024**3),
    gpu_count=1,
    gpu_type="740c",
    gpu_vendor=GPUVendor.AMD,
    gpu_vram_bytes_per_device=64 * (1024**3),
    gpu_product_name="Instinct MI250X",
    status="ready",
)


def test_has_node_changed_cpu_count():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=4000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="740c",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_memory_bytes():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=16 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="740c",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_ephemeral_storage_bytes():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=200 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="740c",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_gpu_count():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=2,
            type="740c",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_gpu_type():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="74a1",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_gpu_vram():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="74a1",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=128 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_gpu_name():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="74a1",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI300",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_status():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="740c",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="unavailable",
        is_ready=False,
    )
    assert has_node_changed(node, existing_node) is True


def test_has_node_changed_no_change():
    node = ClusterNode(
        name="test-node",
        cpu_milli_cores=2000,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_information=GPUInformation(
            count=1,
            type="740c",
            vendor=GPUVendor.AMD,
            vram_bytes_per_device=64 * (1024**3),
            product_name="Instinct MI250X",
        ),
        status="ready",
        is_ready=True,
    )
    assert has_node_changed(node, existing_node) is False


def test_build_cluster_kube_config():
    cluster = ClusterModel(
        id=uuid4(),
        name="test-cluster",
        organization_id=uuid4(),
        workloads_base_url="https://workloads.example.com",
        kube_api_url="https://k8s.example.com:6443",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    keycloak_issuer_url = "https://keycloak.example.com/realms/test"
    k8s_client_secret = "test-secret-123"

    result = build_cluster_kube_config(cluster, keycloak_issuer_url, k8s_client_secret)

    assert (
        result.kube_config
        == """apiVersion: v1
clusters:
- cluster:
    insecure-skip-tls-verify: true
    server: https://k8s.example.com:6443
  name: default
contexts:
- context:
    cluster: default
    user: default
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: default
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      args:
      - oidc-login
      - get-token
      - --oidc-issuer-url=https://keycloak.example.com/realms/test
      - --oidc-client-id=k8s
      - --oidc-client-secret=test-secret-123
      command: kubectl
      env: null
      interactiveMode: IfAvailable
      provideClusterInfo: false
"""
    )
