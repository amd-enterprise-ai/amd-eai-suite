# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for workload models."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

import workloads_manager.config as config
from workloads_manager.models import Workload, WorkloadMetadata


def test_workload_metadata_validation():
    """Test WorkloadMetadata validation."""
    # Valid metadata
    metadata = WorkloadMetadata(id="test-workload", type="training")
    assert metadata.id == "test-workload"
    assert metadata.type == "training"

    # Empty ID should fail
    with pytest.raises(ValidationError) as exc_info:
        WorkloadMetadata(id="", type="training")
    assert "String should have at least 1 character" in str(exc_info.value)

    # Empty type should fail
    with pytest.raises(ValidationError) as exc_info:
        WorkloadMetadata(id="test", type="")
    assert "String should have at least 1 character" in str(exc_info.value)

    # Whitespace should be trimmed
    metadata = WorkloadMetadata(id="  test  ", type="  training  ")
    assert metadata.id == "test"
    assert metadata.type == "training"


def test_workload_creation(tmp_path: Path) -> None:
    """Test Workload class creation and properties."""
    workload_path = tmp_path / "test-workload"
    workload_path.mkdir()

    # Create metadata directory structure
    metadata_dir = workload_path / "helm" / "overrides" / "dev-center"
    metadata_dir.mkdir(parents=True)

    # Create metadata file
    metadata_file = metadata_dir / "_metadata.yaml"
    metadata_content = {"id": "test-workload", "type": "application", "description": "Test workload"}
    with open(metadata_file, "w") as f:
        yaml.dump(metadata_content, f)

    # Create signature file
    signature_file = metadata_dir / "signature.yaml"
    signature_file.write_text("signature: test")

    # Create some chart files
    chart_dir = workload_path / "helm"
    (chart_dir / "Chart.yaml").write_text("name: test-chart")
    (chart_dir / "values.yaml").write_text("key: value")

    # Create workload instance
    workload = Workload(path=workload_path)

    assert workload.dir_name == "test-workload"
    assert workload.metadata is not None
    assert workload.metadata.id == "test-workload"
    assert workload.metadata.type == "application"
    assert workload.chart_name == "test-workload"
    assert workload.type == "application"
    assert workload.is_registerable
    assert str(workload) == "test-workload"

    # Test chart functionality
    assert workload.chart_path == workload_path / "helm"
    chart_files = workload.get_chart_files()
    assert len(chart_files) == 2  # Chart.yaml and values.yaml

    # Test chart upload data
    upload_data = workload.get_chart_upload_data()
    assert upload_data is not None
    assert "signature" in upload_data
    assert "files" in upload_data
    assert len(upload_data["files"]) == 2


@patch.object(config, "ALLOWED_CHART_PATHS", ["templates/", "Chart.yaml", "values.yaml", "overrides/models/"])
def test_workload_is_allowed_file(tmp_path):
    """Test Workload._is_allowed_file method."""
    # Create a temporary workload directory
    workload_dir = tmp_path / "test-workload"
    workload_dir.mkdir()

    # Create workload metadata
    metadata_file = workload_dir / "workload.yaml"
    metadata_file.write_text(
        """
name: test-workload
version: 1.0.0
description: Test workload
"""
    )

    workload = Workload(path=workload_dir)

    # Test exact file matches
    assert workload._is_allowed_file("Chart.yaml")
    assert workload._is_allowed_file("values.yaml")

    # Test directory matches
    assert workload._is_allowed_file("templates/deployment.yaml")
    assert workload._is_allowed_file("overrides/models/model1.yaml")

    # Test non-allowed files
    assert not workload._is_allowed_file("README.md")
    assert not workload._is_allowed_file("scripts/build.sh")


@patch.object(config, "ALLOWED_CHART_PATHS", ["overrides/models/"])
def test_workload_get_overlay_files(tmp_path):
    """Test Workload.get_overlay_files method."""
    # Create a temporary workload directory structure
    workload_dir = tmp_path / "test-workload"
    helm_dir = workload_dir / "helm"
    overrides_dir = helm_dir / "overrides"
    models_dir = overrides_dir / "models"
    dev_center_dir = overrides_dir / "dev-center"

    # Create directories
    models_dir.mkdir(parents=True)
    dev_center_dir.mkdir(parents=True)

    # Create workload metadata
    metadata_file = dev_center_dir / "_metadata.yaml"
    metadata_file.write_text(
        """
id: test-workload
type: inference
description: Test workload
"""
    )

    # Create overlay files
    model1_file = models_dir / "model1.yaml"
    model1_file.write_text("model: model1")

    model2_file = models_dir / "model2.yml"
    model2_file.write_text("model: model2")

    # Create non-YAML file (should be excluded)
    readme_file = models_dir / "README.md"
    readme_file.write_text("# Models")

    # Create dev-center file (should be excluded)
    dev_file = dev_center_dir / "config.yaml"
    dev_file.write_text("config: dev")

    workload = Workload(path=workload_dir)

    overlay_files = workload.get_overlay_files()

    # Should only include YAML files from overrides/models/
    assert len(overlay_files) == 2

    file_paths = [rel_path for _, rel_path in overlay_files]
    assert "overrides/models/model1.yaml" in file_paths
    assert "overrides/models/model2.yml" in file_paths

    # Should not include non-YAML or dev-center files
    assert "overrides/models/README.md" not in file_paths
    assert "overrides/dev-center/config.yaml" not in file_paths
    assert "overrides/dev-center/_metadata.yaml" not in file_paths


def test_load_metadata_success(tmp_path):
    """Test Workload.load_metadata with valid _metadata.yaml and key normalization."""
    workload_path = tmp_path / "test-workload"
    metadata_dir = workload_path / "helm" / "overrides" / "dev-center"
    metadata_dir.mkdir(parents=True)

    # Use camelCase and snake_case keys to test normalization
    metadata_content = {
        "id": "test-workload",
        "type": "application",
        "shortDescription": "Short desc",
        "longDescription": "Long desc",
        "category": "Test",
        "tags": ["tag1", "tag2"],
        "featuredImage": "http://image",
        "requiredResources": {"cpu": 2},
        "externalUrl": "http://external",
    }
    metadata_file = metadata_dir / "_metadata.yaml"
    with open(metadata_file, "w") as f:
        yaml.dump(metadata_content, f)

    workload = Workload(path=workload_path)
    loaded = workload.load_metadata()
    assert loaded is not None
    assert loaded.id == "test-workload"
    assert loaded.type == "application"
    assert loaded.description == "Short desc"
    assert loaded.long_description == "Long desc"
    assert loaded.category == "Test"
    assert loaded.tags == ["tag1", "tag2"]
    assert loaded.featured_image == "http://image"
    assert loaded.required_resources == {"cpu": 2}
    assert loaded.external_url == "http://external"


def test_load_metadata_missing_file(tmp_path):
    """Test Workload.load_metadata returns None if file is missing."""
    workload_path = tmp_path / "test-workload"
    workload = Workload(path=workload_path)
    assert workload.load_metadata() is None


def test_load_metadata_invalid_yaml(tmp_path):
    """Test Workload.load_metadata returns None on invalid YAML."""
    workload_path = tmp_path / "test-workload"
    metadata_dir = workload_path / "helm" / "overrides" / "dev-center"
    metadata_dir.mkdir(parents=True)
    metadata_file = metadata_dir / "_metadata.yaml"
    metadata_file.write_text(":::invalid yaml:::")
    workload = Workload(path=workload_path)
    assert workload.load_metadata() is None


def test_load_metadata_missing_required_keys(tmp_path):
    """Test Workload.load_metadata returns None if required keys are missing."""
    workload_path = tmp_path / "test-workload"
    metadata_dir = workload_path / "helm" / "overrides" / "dev-center"
    metadata_dir.mkdir(parents=True)
    metadata_file = metadata_dir / "_metadata.yaml"
    yaml.dump({"name": "no-id-or-type"}, metadata_file.open("w"))
    workload = Workload(path=workload_path)
    assert workload.load_metadata() is None
