# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Shared pytest fixtures for all tests."""

import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_yaml_file(tmp_path: Path):
    """Create a temporary YAML file."""

    def _create_temp_yaml(content_dict):
        with tempfile.NamedTemporaryFile(dir=tmp_path, mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(content_dict, f)
            temp_file = Path(f.name)
            return temp_file

    yield _create_temp_yaml
