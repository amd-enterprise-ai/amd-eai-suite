# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from prometheus_client.core import GaugeMetricFamily

from airm.messaging.schemas import ClusterQuotaAllocation, GPUVendor
from app.clusters.models import ClusterNode
from app.clusters.schemas import ClusterWithResources
from app.organizations.models import Organization
from app.quotas.models import Quota
from app.quotas.schemas import QuotaCreate
from app.quotas.utils import (
    does_quota_match_allocation,
    set_allocated_gpus_metric_samples,
    set_allocated_vram_metric_samples,
    validate_quota_against_available_cluster_resources,
)


@pytest.fixture
def quota_request():
    return QuotaCreate(
        name="test-quota",
        description="Test Description",
        cpu_milli_cores=1000,
        memory_bytes=1 * 1024**3,
        ephemeral_storage_bytes=10 * 1024**3,
        gpu_count=1,
        cluster_id=uuid4(),
        project_id=uuid4(),
    )


@pytest.fixture
def cluster_resources():
    available = MagicMock()
    available.cpu_milli_cores = 4000
    available.memory_bytes = 4 * 1024**3
    available.ephemeral_storage_bytes = 100 * 1024**3
    available.gpu_count = 2

    allocated = MagicMock()
    allocated.cpu_milli_cores = 2000
    allocated.memory_bytes = 2 * 1024**3
    allocated.ephemeral_storage_bytes = 50 * 1024**3
    allocated.gpu_count = 1

    resources = MagicMock(spec=ClusterWithResources)
    resources.available_resources = available
    resources.allocated_resources = allocated

    return resources


@pytest.fixture
def quota_to_update():
    return Quota(
        cpu_milli_cores=2000,
        memory_bytes=1 * 1024**1,
        ephemeral_storage_bytes=10 * 1024**2,
        gpu_count=2,
        cluster_id=uuid4(),
        project_id=uuid4(),
    )


def test_all_resources_within_limits_new_quota(quota_request, cluster_resources):
    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request)
    assert len(errors) == 0


def test_all_resources_within_limits_update_quota(quota_request, quota_to_update, cluster_resources):
    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request, quota_to_update)
    assert len(errors) == 0


def test_cpu_exceeds_limit_new_quota(quota_request, cluster_resources):
    quota_request.cpu_milli_cores = 3000
    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request)

    assert len(errors) == 1
    assert any("CPU" in error for error in errors)


def test_cpu_exceeds_limit_quota_to_update(quota_request, quota_to_update, cluster_resources):
    quota_request.cpu_milli_cores = 5000
    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request, quota_to_update)

    assert len(errors) == 1
    assert any("CPU" in error for error in errors)


def test_all_resources_exceed_limits_new_quota(quota_request, cluster_resources):
    quota_request.cpu_milli_cores = 3000
    quota_request.memory_bytes = 3 * 1024**3
    quota_request.ephemeral_storage_bytes = 60 * 1024**3
    quota_request.gpu_count = 2

    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request)

    assert len(errors) == 4
    assert any("CPU" in error for error in errors)
    assert any("memory" in error for error in errors)
    assert any("storage" in error for error in errors)
    assert any("GPU" in error for error in errors)


def test_all_resources_exceed_limits_quota_to_update(quota_request, quota_to_update, cluster_resources):
    quota_request.cpu_milli_cores = 5000
    quota_request.memory_bytes = 5 * 1024**3
    quota_request.ephemeral_storage_bytes = 60 * 1024**6
    quota_request.gpu_count = 24

    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request, quota_to_update)

    assert len(errors) == 4
    assert any("CPU" in error for error in errors)
    assert any("memory" in error for error in errors)
    assert any("storage" in error for error in errors)
    assert any("GPU" in error for error in errors)


def test_no_allocated_resources_new_quota(quota_request, cluster_resources):
    cluster_resources.allocated_resources.cpu_milli_cores = 0
    cluster_resources.allocated_resources.memory_bytes = 0
    cluster_resources.allocated_resources.ephemeral_storage_bytes = 0
    cluster_resources.allocated_resources.gpu_count = 0

    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request)
    assert len(errors) == 0

    quota_request.cpu_milli_cores = 5000
    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request)

    assert len(errors) == 1
    assert any("CPU" in error for error in errors)


def test_zero_available_resources(quota_request, cluster_resources):
    cluster_resources.available_resources.cpu_milli_cores = 0
    cluster_resources.available_resources.memory_bytes = 0
    cluster_resources.available_resources.ephemeral_storage_bytes = 0
    cluster_resources.available_resources.gpu_count = 0

    errors = validate_quota_against_available_cluster_resources(cluster_resources, quota_request)

    assert len(errors) == 4
    assert any("CPU" in error for error in errors)
    assert any("memory" in error for error in errors)
    assert any("storage" in error for error in errors)
    assert any("GPU" in error for error in errors)


existing_quota = Quota(
    id=uuid4(),
    cpu_milli_cores=200,
    memory_bytes=8 * (1024**3),
    ephemeral_storage_bytes=100 * (1024**3),
    gpu_count=1,
    cluster_id=uuid4(),
    project_id=uuid4(),
)


def test_does_quota_match_allocation_cpu_milli_cores():
    allocation = ClusterQuotaAllocation(
        quota_name="test-node",
        cpu_milli_cores=400,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_count=1,
        namespaces=["test-node"],
    )
    assert does_quota_match_allocation(existing_quota, allocation) is False


def test_does_quota_match_allocation_memory_bytes():
    allocation = ClusterQuotaAllocation(
        quota_name="test-node",
        cpu_milli_cores=200,
        memory_bytes=9 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_count=1,
        namespaces=["test-node"],
    )
    assert does_quota_match_allocation(existing_quota, allocation) is False


def test_does_quota_match_allocation_ephemeral_storage_bytes():
    allocation = ClusterQuotaAllocation(
        quota_name="test-node",
        cpu_milli_cores=200,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=90 * (1024**3),
        gpu_count=1,
        namespaces=["test-node"],
    )
    assert does_quota_match_allocation(existing_quota, allocation) is False


def test_does_quota_match_allocation_gpu_count():
    allocation = ClusterQuotaAllocation(
        quota_name="test-node",
        cpu_milli_cores=200,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_count=2,
        namespaces=["test-node"],
    )
    assert does_quota_match_allocation(existing_quota, allocation) is False


def test_has_node_changed_no_change():
    allocation = ClusterQuotaAllocation(
        quota_name="test-node",
        cpu_milli_cores=200,
        memory_bytes=8 * (1024**3),
        ephemeral_storage_bytes=100 * (1024**3),
        gpu_count=1,
        namespaces=["test-node"],
    )
    assert does_quota_match_allocation(existing_quota, allocation) is True


def test_set_allocated_gpus_metric_samples():
    allocated_gpus_metric = GaugeMetricFamily("allocated_gpus", "Allocated GPUs")
    allocated_gpus_metric.add_sample(
        "allocated_gpus",
        labels={"project_id": "123", "cluster_id": "3456", "org_name": "Org", "cluster_name": "cluster"},
        value=9,
    )

    project1 = MagicMock()
    project1.id = 1
    project1.cluster_id = 1
    project1.organization_id = 1
    project1.quota = Quota(gpu_count=10)
    project1.cluster = MagicMock()
    project1.cluster.name = "Cluster1"

    project2 = MagicMock()
    project2.id = 2
    project2.cluster_id = 2
    project2.organization_id = 1
    project2.quota = Quota(gpu_count=20)
    project2.cluster = MagicMock()
    project2.cluster.name = "Cluster2"

    projects = [project1, project2]

    organizations = [
        Organization(id=1, name="Org1", keycloak_organization_id="123"),
        Organization(id=2, name="Org2", keycloak_organization_id="456"),
    ]

    result = set_allocated_gpus_metric_samples(allocated_gpus_metric, projects, organizations)

    assert len(result.samples) == 2
    assert result.samples[0].value == 10
    assert result.samples[1].value == 20


def test_set_allocated_vram_metric_samples():
    allocated_gpu_vram_metric = GaugeMetricFamily("allocated_gpu_vram", "Allocated GPU VRAM")
    allocated_gpu_vram_metric.add_sample(
        "allocated_gpu_vram",
        labels={"project_id": "123", "cluster_id": "3456", "org_name": "Org", "cluster_name": "cluster"},
        value=12,
    )

    project = MagicMock()
    project.organization_id = 1
    project.cluster_id = 1
    project.id = 1
    project.quota = Quota(project_id=1, cluster_id=1, gpu_count=2)
    project.cluster = MagicMock()
    project.cluster.name = "Cluster1"

    projects = [project]
    organizations = [
        Organization(id=1, name="Org1", keycloak_organization_id="123"),
    ]
    cluster_nodes = [
        ClusterNode(
            cluster_id=1,
            gpu_vendor=GPUVendor.AMD,
            gpu_type="74a1",
            gpu_count=2,
            gpu_vram_bytes_per_device=192 * 1024**3,
        )
    ]

    result = set_allocated_vram_metric_samples(allocated_gpu_vram_metric, projects, organizations, cluster_nodes)

    assert len(result.samples) == 1
    assert result.samples[0].value == 2 * 192 * 1024  # Assuming 2 GPUs with 192GB each, in MB
