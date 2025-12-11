# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import hashlib
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.charts.models import Chart
from app.managed_workloads.models import ManagedWorkload
from app.managed_workloads.utils import (
    generate_display_name,
    generate_workload_name,
    get_workload_host_from_HTTPRoute_manifest,
    render_helm_template,
    workload_directory,
)
from app.models.models import InferenceModel
from app.utilities.exceptions import InconsistentStateException
from tests import factory


@pytest.fixture
def mock_chart():
    chart = MagicMock(spec=Chart)
    chart.files = [
        MagicMock(path="Chart.yaml", content="name: test-chart\nversion: 1.0.0"),
        MagicMock(path="values.yaml", content="key: value"),
        MagicMock(path="templates/deployment.yaml", content="kind: Deployment\nmetadata:\n  name: {{ .Release.Name }}"),
    ]
    return chart


def test_workload_directory(mock_chart):
    with workload_directory(mock_chart) as temp_dir:
        # Verify files were created
        assert os.path.exists(os.path.join(temp_dir, "Chart.yaml"))
        assert os.path.exists(os.path.join(temp_dir, "values.yaml"))
        assert os.path.exists(os.path.join(temp_dir, "templates/deployment.yaml"))

        # Verify file contents
        with open(os.path.join(temp_dir, "Chart.yaml")) as f:
            assert f.read() == "name: test-chart\nversion: 1.0.0"

        with open(os.path.join(temp_dir, "values.yaml")) as f:
            assert f.read() == "key: value"

        with open(os.path.join(temp_dir, "templates/deployment.yaml")) as f:
            assert f.read() == "kind: Deployment\nmetadata:\n  name: {{ .Release.Name }}"

    # Verify directory was cleaned up
    assert not os.path.exists(temp_dir)


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_render_helm_template(mock_subprocess, mock_chart):
    # Setup mock process
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"rendered template", b"")
    mock_process.returncode = 0
    mock_subprocess.return_value = mock_process

    result = await render_helm_template(
        mock_chart,
        "test-workload",
        "test-namespace",
        overlays_values=[{"key1": "value1"}, {"key2": "value2"}],
    )

    # Verify result
    assert result == "rendered template"

    # Verify subprocess was called with correct arguments
    mock_subprocess.assert_called_once()
    args, _ = mock_subprocess.call_args

    # Check that the command includes the expected arguments
    assert "helm" in args
    assert "template" in args
    assert "--namespace" in args
    assert "test-namespace" in args
    assert "--name-template" in args
    assert "test-workload" in args


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_render_helm_template_error(mock_subprocess, mock_chart):
    # Setup mock process with error
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"error message")
    mock_process.returncode = 1
    mock_subprocess.return_value = mock_process

    # Call the function and expect an error
    with pytest.raises(RuntimeError) as exc_info:
        await render_helm_template(mock_chart, "test-workload", "test-namespace")

    # Verify error message
    assert "Failed to render Helm template" in str(exc_info.value)
    assert "error message" in str(exc_info.value)


def test_get_workload_host_from_HTTPRoute_manifest():
    manifest = """
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: test-route
spec:
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /test-path
"""
    cluster_base_url = "https://example.com"
    host = get_workload_host_from_HTTPRoute_manifest(manifest=manifest, cluster_base_url=cluster_base_url)
    assert host == cluster_base_url + "/test-path"

    manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test
"""
    host = get_workload_host_from_HTTPRoute_manifest(manifest=manifest, cluster_base_url=cluster_base_url)
    assert host is None

    manifest = """
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: test-route
spec:
  rules:
  - matches:
    - headers:
        type: Exact
        name: test-header
        value: test-value
"""
    host = get_workload_host_from_HTTPRoute_manifest(manifest=manifest, cluster_base_url=cluster_base_url)
    assert host is None


@pytest.fixture
def mock_model():
    model = MagicMock(spec=InferenceModel)
    model.name = "test-model"
    return model


@pytest.mark.asyncio
@patch("app.managed_workloads.utils.time.time")
async def test_generate_workload_name_chart_workload(mock_time, db_session):
    """Test generate_workload_name with chart workload."""
    # Setup
    mock_time.return_value = 1715000000  # Fixed timestamp for testing
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    # Test 1: Basic chart workload
    chart_workload = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=env.chart,
        model_id=env.model.id,
        status="Pending",
        display_name="Test Chart Workload",
    )

    name = generate_workload_name(chart_workload)
    uuid_prefix = str(chart_workload.id)[:4]
    expected_chart_name = env.chart.name.replace(" ", "-").replace("_", "-")
    assert name == f"mw-{expected_chart_name}-1715000000-{uuid_prefix}"
    assert len(name) <= 53  # Kubernetes name length limit
    assert name.startswith("mw-")

    # Test 2: Chart with spaces and underscores in name
    chart_with_spaces = await factory.create_chart(db_session, name="test chart_with spaces_and_underscores")
    chart_workload_spaces = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=chart_with_spaces,
        model_id=env.model.id,
        status="Pending",
        display_name="Test Spaces",
    )

    name_spaces = generate_workload_name(chart_workload_spaces)
    assert "test-chart-with-spaces" in name_spaces
    assert len(name_spaces) <= 53

    # Test 3: Very long chart name (truncation test)
    long_chart = await factory.create_chart(db_session, name="a" * 100)
    chart_workload_long = await factory.create_chart_workload(
        db_session, env.project, chart=long_chart, model_id=env.model.id, status="Pending", display_name="Test Long"
    )

    name_long = generate_workload_name(chart_workload_long)
    assert name_long.startswith("mw-" + ("a" * 33))
    assert len(name_long) <= 53


@pytest.mark.asyncio
async def test_generate_workload_name_aim_workload(db_session):
    """Test generate_workload_name with AIM workload."""

    env = await factory.create_basic_test_environment(db_session)
    aim = await factory.create_aim(
        db_session,
        resource_name="test-aim-v1-0-0",
        image_reference="docker.io/amdenterpriseai/test-aim:v1.0.0",
    )

    aim_workload = await factory.create_aim_workload(
        db_session,
        env.project,
        aim=aim,
        status="Pending",
        display_name="Test AIM Workload",
    )

    name = generate_workload_name(aim_workload)

    # For AIM workloads, name should be mw-{8-char-hash} (11 chars total)
    # Prefix ensures name starts with letter (KServe requirement)
    expected_hash = hashlib.sha256(str(aim_workload.id).encode()).hexdigest()[:8]
    expected_name = f"mw-{expected_hash}"
    assert name == expected_name
    assert len(name) == 11  # mw- prefix + 8-char hash
    assert name.startswith("mw-")  # Must start with letter for KServe validation


@pytest.mark.asyncio
async def test_generate_display_name_chart_workload(db_session):
    """Test generate_display_name with chart workload."""
    env = await factory.create_full_test_environment(db_session, with_chart=True, with_model=True)

    # Test 1: Chart workload with model
    chart_workload_with_model = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=env.chart,
        model_id=env.model.id,
        status="Pending",
        display_name="Test Chart Workload",
    )

    display_name = generate_display_name(chart_workload_with_model)
    uuid_prefix = str(chart_workload_with_model.id)[:8]
    assert display_name == f"{env.chart.name}-{env.model.name}-{uuid_prefix}"

    # Test 2: Chart workload without model
    chart_workload_no_model = await factory.create_chart_workload(
        db_session, env.project, chart=env.chart, status="Pending", display_name="Test Chart Workload No Model"
    )

    display_name = generate_display_name(chart_workload_no_model)
    uuid_prefix = str(chart_workload_no_model.id)[:8]
    assert display_name == f"{env.chart.name}-{uuid_prefix}"

    # Test 3: Different chart name
    another_chart = await factory.create_chart(db_session, name="another-chart")
    chart_workload_different = await factory.create_chart_workload(
        db_session,
        env.project,
        chart=another_chart,
        model_id=env.model.id,
        status="Pending",
        display_name="Test Different Chart",
    )

    display_name = generate_display_name(chart_workload_different)
    uuid_prefix = str(chart_workload_different.id)[:8]
    assert display_name == f"another-chart-{env.model.name}-{uuid_prefix}"


@pytest.mark.asyncio
async def test_generate_display_name_aim_workload(db_session):
    """Test generate_display_name with AIM workload."""
    env = await factory.create_basic_test_environment(db_session)
    aim = await factory.create_aim(
        db_session,
        resource_name="test-aim-v1-0-0",
        image_reference="docker.io/amdenterpriseai/test-aim:v1.0.0",
    )

    aim_workload = await factory.create_aim_workload(
        db_session,
        env.project,
        aim=aim,
        status="Pending",
        display_name="Test AIM Workload",
    )

    display_name = generate_display_name(aim_workload)
    uuid_prefix = str(aim_workload.id)[:8]
    assert display_name == f"{aim.resource_name}-{uuid_prefix}"


@pytest.mark.asyncio
async def test_generate_workload_name_invalid_workload(db_session):
    """Test generate_workload_name raises InconsistentStateException for workload without chart or AIM."""
    # Create a workload mock without chart or AIM
    invalid_workload = MagicMock(spec=ManagedWorkload)
    invalid_workload.id = uuid4()
    invalid_workload.aim = None
    invalid_workload.chart = None

    with pytest.raises(InconsistentStateException) as exc_info:
        generate_workload_name(invalid_workload)

    assert "Cannot generate workload name" in exc_info.value.message
    assert "must have either a chart or AIM reference" in exc_info.value.detail


@pytest.mark.asyncio
async def test_generate_display_name_invalid_workload(db_session):
    """Test generate_display_name raises InconsistentStateException for workload without chart or AIM."""
    # Create a workload mock without chart or AIM
    invalid_workload = MagicMock(spec=ManagedWorkload)
    invalid_workload.id = uuid4()
    invalid_workload.aim = None
    invalid_workload.chart = None

    with pytest.raises(InconsistentStateException) as exc_info:
        generate_display_name(invalid_workload)

    assert "Cannot generate display name" in exc_info.value.message
    assert "must have either a chart or AIM reference" in exc_info.value.detail
