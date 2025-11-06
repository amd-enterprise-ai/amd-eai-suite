# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.aims.schemas import AIMDeployRequest
from app.aims.utils import (
    generate_aim_service_manifest,
    generate_aim_workload_urls,
    get_workload_internal_host,
    kubernetes_name,
)
from tests.factory import create_aim, create_aim_workload, create_basic_test_environment


@pytest.mark.asyncio
async def test_generate_aim_service_manifest(db_session: AsyncSession):
    """Test AIM service manifest generation."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session, image_name="aim", image_tag="0.1.0-test-model-20251002")
    workload = await create_aim_workload(db_session, project=env.project, aim=aim, creator=env.creator)
    deploy_request = AIMDeployRequest()

    manifest_str = generate_aim_service_manifest(aim, deploy_request, workload, env.project)
    manifest = yaml.safe_load(manifest_str)

    assert manifest["apiVersion"] == "aim.silogen.ai/v1alpha1"
    assert manifest["kind"] == "AIMService"

    # Verify metadata
    metadata = manifest["metadata"]
    assert metadata["name"] == workload.name

    spec = manifest["spec"]
    assert spec["model"]["ref"] == kubernetes_name(aim.image_name, aim.image_tag)
    assert spec["cacheModel"] is True
    assert spec["replicas"] == 1

    # Verify routing is enabled by default
    assert "routing" in spec
    assert spec["routing"]["enabled"] is True
    # No group annotation when group_id is not provided
    assert "annotations" not in spec["routing"]


@pytest.mark.asyncio
async def test_generate_aim_service_manifest_with_all_options(db_session: AsyncSession):
    """Test AIM service manifest generation with all optional fields."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session, image_name="aim", image_tag="0.1.0-test-model-20251002")
    workload = await create_aim_workload(db_session, project=env.project, aim=aim, creator=env.creator)
    deploy_request = AIMDeployRequest(
        cache_model=True,
        replicas=3,
        image_pull_secrets=["regcred", "ghcr-secret"],
        hf_token="hf_test123456789",
    )

    manifest_str = generate_aim_service_manifest(aim, deploy_request, workload, env.project)
    manifest = yaml.safe_load(manifest_str)

    # Verify structure
    assert manifest["apiVersion"] == "aim.silogen.ai/v1alpha1"
    assert manifest["kind"] == "AIMService"

    # Verify metadata
    metadata = manifest["metadata"]
    assert metadata["name"] == workload.name

    # Verify spec fields
    spec = manifest["spec"]
    assert spec["model"]["ref"] == kubernetes_name(aim.image_name, aim.image_tag)
    assert spec["cacheModel"] is True
    assert spec["replicas"] == 3

    # Verify image pull secrets
    assert len(spec["imagePullSecrets"]) == 2
    assert spec["imagePullSecrets"][0] == {"name": "regcred"}
    assert spec["imagePullSecrets"][1] == {"name": "ghcr-secret"}

    # Verify environment variables for HF token
    assert "env" in spec
    assert len(spec["env"]) == 1
    assert spec["env"][0]["name"] == "HF_TOKEN"
    assert "valueFrom" in spec["env"][0]
    assert spec["env"][0]["valueFrom"]["secretKeyRef"]["name"] == "hf_test123456789"
    assert spec["env"][0]["valueFrom"]["secretKeyRef"]["key"] == "token"

    # Verify routing is enabled by default
    assert "routing" in spec
    assert spec["routing"]["enabled"] is True
    # No group annotation when group_id is not provided
    assert "annotations" not in spec["routing"]


@pytest.mark.asyncio
async def test_generate_aim_service_manifest_with_group_id(db_session: AsyncSession):
    """Test AIM service manifest generation with group_id."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session, image_name="aim", image_tag="0.1.0-test-model-20251002")
    workload = await create_aim_workload(db_session, project=env.project, aim=aim, creator=env.creator)
    deploy_request = AIMDeployRequest()

    group_id = "test-group-123"
    manifest_str = generate_aim_service_manifest(aim, deploy_request, workload, env.project, group_id=group_id)
    manifest = yaml.safe_load(manifest_str)

    # Verify routing includes group annotation
    spec = manifest["spec"]
    assert "routing" in spec
    assert spec["routing"]["enabled"] is True
    assert "annotations" in spec["routing"]
    assert spec["routing"]["annotations"]["cluster-auth/allowed-group"] == group_id


@pytest.mark.asyncio
async def test_generate_aim_workload_urls(db_session: AsyncSession):
    """Test AIM workload URL generation."""
    env = await create_basic_test_environment(db_session)
    aim = await create_aim(db_session, image_name="aim", image_tag="0.1.0-test-model-20251002")
    workload = await create_aim_workload(
        db_session, project=env.project, aim=aim, creator=env.creator, name="test-workload"
    )

    urls = generate_aim_workload_urls(env.project, workload)

    # Verify the URLs are generated correctly
    assert "internal_host" in urls
    assert "external_host" in urls
    # Internal host uses get_workload_internal_host which may truncate
    expected_internal = get_workload_internal_host(workload.name, env.project.name)
    assert urls["internal_host"] == expected_internal
    assert urls["external_host"] == f"{env.project.cluster.base_url}/{env.project.name}/{workload.id}"


def test_get_workload_internal_host_max_namespace():
    """Test hostname generation with maximum 41-char namespace."""
    workload_name = "mw-abcd1234"  # 11-char: mw-{8-char-hash}
    namespace = "a" * 41  # Max length

    result = get_workload_internal_host(workload_name, namespace)

    expected = f"{workload_name}-predictor.{namespace}.svc.cluster.local"
    assert result == expected

    # Verify DNS label constraints are met
    # First label: {workload_name}-predictor = 11 + 10 = 21 chars (< 63)
    first_label = f"{workload_name}-predictor"
    assert len(first_label) == 21
    assert len(first_label) < 63

    # Second label: namespace = 41 chars (< 63)
    assert len(namespace) == 41
    assert len(namespace) < 63


def test_get_workload_internal_host_original_issue():
    """Test the original issue case from qa-test-project (now fixed with short names)."""
    workload_name = "mw-1d103f8c"  # 11-char: mw-{8-char-hash} (shortened from mw-2f58e277-b811-4dff-a72f-8eaf2206a6fa)
    namespace = "qa-test-project"  # 15 chars

    result = get_workload_internal_host(workload_name, namespace)

    expected = f"{workload_name}-predictor.{namespace}.svc.cluster.local"
    assert result == expected

    # Verify this fits within DNS constraints
    first_label = f"{workload_name}-predictor"
    assert len(first_label) == 21  # 11 + 10
    assert len(first_label) < 63
