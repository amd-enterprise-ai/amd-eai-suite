# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for cluster service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from kubernetes_asyncio.client import V1Node, V1NodeList, V1NodeStatus

from app.cluster.service import (
    get_aim_image_families,
    get_cluster_accelerators,
    get_cluster_gpu_device_ids,
    get_cluster_resources,
    parse_cpu_value,
    parse_memory_value,
)
from app.cluster.utils import parse_container_image_repository_and_tag
from app.custom_models.constants import DEFAULT_AIM_DEPLOYMENT_IMAGE_REF


def test_parse_cpu_value():
    """Test CPU value parsing."""
    assert parse_cpu_value("1") == 1000
    assert parse_cpu_value("500m") == 500
    assert parse_cpu_value("2.5") == 2500
    assert parse_cpu_value("") == 0


def test_parse_memory_value():
    """Test memory value parsing."""
    assert parse_memory_value("1024Ki") == 1024 * 1024
    assert parse_memory_value("1Mi") == 1024 * 1024
    assert parse_memory_value("1Gi") == 1024 * 1024 * 1024
    assert parse_memory_value("1000") == 1000
    assert parse_memory_value("") == 0


@pytest.mark.parametrize(
    ("image_ref", "expected_repository", "expected_tag_or_digest"),
    [
        ("amdenterpriseai/aim-base:0.11", "amdenterpriseai/aim-base", "0.11"),
        ("localhost:5000/aim-base:latest", "localhost:5000/aim-base", "latest"),
        (
            "amdenterpriseai/aim-base@sha256:abcdef0123456789",
            "amdenterpriseai/aim-base",
            "sha256:abcdef0123456789",
        ),
        (
            "amdenterpriseai/aim-base:0.11@sha256:abcdef0123456789",
            "amdenterpriseai/aim-base",
            "sha256:abcdef0123456789",
        ),
        (
            "localhost:5000/aim-base:latest@sha256:abcdef0123456789",
            "localhost:5000/aim-base",
            "sha256:abcdef0123456789",
        ),
    ],
)
def test_parse_container_image_repository_and_tag(
    image_ref: str,
    expected_repository: str,
    expected_tag_or_digest: str,
) -> None:
    repository, tag_or_digest = parse_container_image_repository_and_tag(image_ref)
    assert repository == expected_repository
    assert tag_or_digest == expected_tag_or_digest


@pytest.mark.parametrize(
    "image_ref",
    [
        "",
        "repo-only",
        "repo@",
        "@sha256:abc",
        "repo@sha256:",
    ],
)
def test_parse_container_image_repository_and_tag_rejects_invalid(image_ref: str) -> None:
    with pytest.raises(ValueError):
        parse_container_image_repository_and_tag(image_ref)


def test_get_aim_image_families_includes_automatic_first():
    families = get_aim_image_families()
    assert len(families) == 2
    assert families[0].family_id == "automatic"
    assert families[0].repository is None
    assert families[0].tags == []


def test_get_aim_image_families_includes_aim_base_from_default_deployment_ref():
    families = get_aim_image_families()
    by_id = {family.family_id: family for family in families}
    assert set(by_id) == {"automatic", "aim-base"}
    repository, default_tag = parse_container_image_repository_and_tag(DEFAULT_AIM_DEPLOYMENT_IMAGE_REF)
    assert by_id["aim-base"].repository == repository
    assert by_id["aim-base"].tags == [default_tag]


def test_get_aim_image_families_is_idempotent():
    first = get_aim_image_families()
    second = get_aim_image_families()
    assert [f.model_dump() for f in first] == [f.model_dump() for f in second]


def test_get_aim_image_families_stable_order():
    ids = [family.family_id for family in get_aim_image_families()]
    assert ids == ["automatic", "aim-base"]


def test_get_aim_image_families_returns_independent_copies():
    families = get_aim_image_families()
    families[1].tags.append("mutated-tag")

    fresh = get_aim_image_families()
    _, default_tag = parse_container_image_repository_and_tag(DEFAULT_AIM_DEPLOYMENT_IMAGE_REF)
    assert fresh[1].tags == [default_tag]


def make_node(
    device_id: str | None = None,
    ready: bool = True,
    allocatable: dict | None = None,
    beta_device_id: str | None = None,
    product_name: str | None = None,
    beta_product_name: str | None = None,
) -> Mock:
    """Build a mock V1Node.

    Args:
        device_id: Value for the amd.com/gpu.device-id label.
        ready: Whether the node has a Ready=True condition.
        allocatable: Dict of allocatable resources (cpu, memory, etc.).
        beta_device_id: Value for the beta.amd.com/gpu.device-id label.
        product_name: Value for the amd.com/gpu.product-name label.
        beta_product_name: Value for the beta.amd.com/gpu.product-name label.
    """
    node = Mock(spec=V1Node)
    node.status = Mock(spec=V1NodeStatus)

    condition = Mock()
    condition.type = "Ready"
    condition.status = "True" if ready else "False"
    node.status.conditions = [condition]

    labels: dict[str, str] = {}
    if device_id:
        labels["amd.com/gpu.device-id"] = device_id
    if beta_device_id:
        labels["beta.amd.com/gpu.device-id"] = beta_device_id
    if product_name:
        labels["amd.com/gpu.product-name"] = product_name
    if beta_product_name:
        labels["beta.amd.com/gpu.product-name"] = beta_product_name
    metadata = Mock()
    metadata.labels = labels
    node.metadata = metadata

    if allocatable is not None:
        node.status.allocatable = allocatable
        node.to_dict = Mock(return_value={"status": {"allocatable": allocatable}})

    return node


@pytest.mark.asyncio
async def test_get_cluster_resources():
    allocatable = {"cpu": "4", "memory": "8Gi", "ephemeral-storage": "100Gi", "amd.com/gpu": "2"}
    result = await get_cluster_resources(make_kube_client([make_node(allocatable=allocatable)]))

    assert result.data.total_node_count == 1
    assert result.data.available_resources.cpu_milli_cores == 4000
    assert result.data.available_resources.memory_bytes == 8 * 1024 * 1024 * 1024
    assert result.data.available_resources.ephemeral_storage_bytes == 100 * 1024 * 1024 * 1024
    assert result.data.available_resources.gpu_count == 2


@pytest.mark.asyncio
async def test_get_cluster_resources_multiple_nodes():
    allocatable = {"cpu": "8", "memory": "16Gi", "ephemeral-storage": "200Gi", "amd.com/gpu": "4"}
    nodes = [make_node(allocatable=allocatable), make_node(allocatable=allocatable)]
    result = await get_cluster_resources(make_kube_client(nodes))

    assert result.data.total_node_count == 2
    assert result.data.available_resources.cpu_milli_cores == 16000
    assert result.data.available_resources.memory_bytes == 32 * 1024 * 1024 * 1024
    assert result.data.available_resources.ephemeral_storage_bytes == 400 * 1024 * 1024 * 1024
    assert result.data.available_resources.gpu_count == 8


def make_kube_client(nodes: list[Mock]) -> Mock:
    """Build a mock KubernetesClient whose list_node returns the given nodes."""
    mock_response = Mock(spec=V1NodeList)
    mock_response.items = nodes

    mock_kube_client = Mock()
    mock_kube_client.core_v1 = Mock()
    mock_kube_client.core_v1.list_node = AsyncMock(return_value=mock_response)
    return mock_kube_client


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_returns_device_ids():
    result = await get_cluster_gpu_device_ids(make_kube_client([make_node("74a1"), make_node("74a9")]))

    assert result == {"74a1", "74a9"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_deduplicates():
    result = await get_cluster_gpu_device_ids(
        make_kube_client([make_node("74a1"), make_node("74a1"), make_node("74a1")])
    )

    assert result == {"74a1"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_no_label_returns_empty():
    result = await get_cluster_gpu_device_ids(make_kube_client([make_node(device_id=None), make_node(device_id=None)]))

    assert result == set()


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_excludes_not_ready_nodes():
    result = await get_cluster_gpu_device_ids(
        make_kube_client([make_node("74a1", ready=True), make_node("74b0", ready=False)])
    )

    assert result == {"74a1"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_falls_back_to_beta_label():
    result = await get_cluster_gpu_device_ids(make_kube_client([make_node("74a1"), make_node(beta_device_id="74b0")]))

    assert result == {"74a1", "74b0"}


@pytest.mark.asyncio
async def test_get_cluster_gpu_device_ids_propagates_kube_error():
    mock_kube_client = Mock()
    mock_kube_client.core_v1 = Mock()
    mock_kube_client.core_v1.list_node = AsyncMock(side_effect=RuntimeError("kube unavailable"))

    with patch("app.cluster.service.logger") as mock_logger:
        with pytest.raises(RuntimeError, match="kube unavailable"):
            await get_cluster_gpu_device_ids(mock_kube_client)

    mock_logger.exception.assert_called_once()


def _gpu_allocatable(count: int) -> dict:
    return {"amd.com/gpu": str(count)}


@pytest.mark.asyncio
async def test_get_cluster_accelerators_single_node():
    node = make_node(
        "74a1",
        allocatable=_gpu_allocatable(4),
        product_name="AMD_Instinct_MI300X",
    )
    result = await get_cluster_accelerators(make_kube_client([node]))
    assert len(result) == 1
    assert result[0].device_id == "74a1"
    assert result[0].product_name == "AMD Instinct MI300X"
    assert result[0].allocatable_count == 4


@pytest.mark.asyncio
async def test_get_cluster_accelerators_prefers_labeled_product_name_over_device_id_fallback():
    nodes = [
        make_node("74a1", allocatable=_gpu_allocatable(2)),
        make_node("74a1", allocatable=_gpu_allocatable(4), product_name="AMD_Instinct_MI300X"),
    ]
    result = await get_cluster_accelerators(make_kube_client(nodes))
    assert len(result) == 1
    assert result[0].product_name == "AMD Instinct MI300X"
    assert result[0].allocatable_count == 6


@pytest.mark.asyncio
async def test_get_cluster_accelerators_keeps_labeled_product_name_when_later_node_lacks_label():
    nodes = [
        make_node("74a1", allocatable=_gpu_allocatable(2), product_name="AMD_Instinct_MI300X"),
        make_node("74a1", allocatable=_gpu_allocatable(4)),
    ]
    result = await get_cluster_accelerators(make_kube_client(nodes))
    assert len(result) == 1
    assert result[0].product_name == "AMD Instinct MI300X"
    assert result[0].allocatable_count == 6


@pytest.mark.asyncio
async def test_get_cluster_accelerators_sums_across_nodes():
    nodes = [
        make_node("74a1", allocatable=_gpu_allocatable(4), product_name="AMD_Instinct_MI300X"),
        make_node("74a1", allocatable=_gpu_allocatable(8), product_name="AMD_Instinct_MI300X"),
    ]
    result = await get_cluster_accelerators(make_kube_client(nodes))
    assert len(result) == 1
    assert result[0].allocatable_count == 12


@pytest.mark.asyncio
async def test_get_cluster_accelerators_multiple_device_ids():
    nodes = [
        make_node("74a1", allocatable=_gpu_allocatable(2), product_name="AMD_Instinct_MI300X"),
        make_node("74a9", allocatable=_gpu_allocatable(1), product_name="AMD_Instinct_MI250X"),
    ]
    result = await get_cluster_accelerators(make_kube_client(nodes))
    by_id = {entry.device_id: entry for entry in result}
    assert by_id["74a1"].allocatable_count == 2
    assert by_id["74a9"].allocatable_count == 1


@pytest.mark.asyncio
async def test_get_cluster_accelerators_excludes_not_ready_nodes():
    nodes = [
        make_node("74a1", allocatable=_gpu_allocatable(4), product_name="AMD_Instinct_MI300X"),
        make_node("74b0", ready=False, allocatable=_gpu_allocatable(8), product_name="Other"),
    ]
    result = await get_cluster_accelerators(make_kube_client(nodes))
    assert len(result) == 1
    assert result[0].device_id == "74a1"


@pytest.mark.asyncio
async def test_get_cluster_accelerators_no_gpu_label_returns_empty():
    result = await get_cluster_accelerators(make_kube_client([make_node(device_id=None), make_node(device_id=None)]))
    assert result == []


@pytest.mark.asyncio
async def test_get_cluster_accelerators_falls_back_to_beta_device_id():
    node = make_node(beta_device_id="74b0", allocatable=_gpu_allocatable(2), beta_product_name="AMD_GPU")
    result = await get_cluster_accelerators(make_kube_client([node]))
    assert len(result) == 1
    assert result[0].device_id == "74b0"
    assert result[0].product_name == "AMD GPU"


@pytest.mark.asyncio
async def test_get_cluster_accelerators_missing_product_name_uses_device_id():
    node = make_node("74a1", allocatable=_gpu_allocatable(1))
    result = await get_cluster_accelerators(make_kube_client([node]))
    assert result[0].product_name == "74a1"


@pytest.mark.asyncio
async def test_get_cluster_accelerators_counts_only_amd_gpus_when_nvidia_present():
    allocatable = {"nvidia.com/gpu": "8", "amd.com/gpu": "2"}
    node = make_node("74a1", allocatable=allocatable, product_name="AMD_Instinct_MI300X")
    result = await get_cluster_accelerators(make_kube_client([node]))
    assert len(result) == 1
    assert result[0].allocatable_count == 2


@pytest.mark.asyncio
async def test_get_cluster_accelerators_zero_allocatable_on_labeled_node():
    node = make_node("74a1", allocatable=_gpu_allocatable(0), product_name="AMD_Instinct_MI300X")
    result = await get_cluster_accelerators(make_kube_client([node]))
    assert len(result) == 1
    assert result[0].allocatable_count == 0


@pytest.mark.asyncio
async def test_get_cluster_accelerators_empty_node_list():
    result = await get_cluster_accelerators(make_kube_client([]))
    assert result == []


@pytest.mark.asyncio
async def test_get_cluster_accelerators_propagates_kube_error():
    mock_kube_client = Mock()
    mock_kube_client.core_v1 = Mock()
    mock_kube_client.core_v1.list_node = AsyncMock(side_effect=RuntimeError("kube unavailable"))

    with patch("app.cluster.service.logger") as mock_logger:
        with pytest.raises(RuntimeError, match="kube unavailable"):
            await get_cluster_accelerators(mock_kube_client)

    mock_logger.exception.assert_called_once()
