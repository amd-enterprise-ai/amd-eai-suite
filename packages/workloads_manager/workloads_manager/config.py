# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Configuration module for the workloads manager."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Look for .env file in the current directory, then parent directories
load_dotenv()
# Also look for .env in the package directory
load_dotenv(Path(__file__).parent / ".env")
# And in the user's home directory
load_dotenv(Path.home() / ".workloads-manager.env")


# Get package directory
PACKAGE_DIR = Path(__file__).parent

# Data is always inside the package
DATA_DIR = PACKAGE_DIR / "data"

# Repository configuration
WORKLOADS_REPO = os.environ.get("WM_WORKLOADS_REPO", "git@github.com:silogen/ai-workloads.git")
WORKLOADS_DIR = os.environ.get("WM_WORKLOADS_DIR", str(DATA_DIR / "ai-workloads"))
PATCHES_DIR = os.environ.get("WM_PATCHES_DIR", str(DATA_DIR / "patches"))
MAIN_BRANCH = os.environ.get("WM_MAIN_BRANCH", "main")

# API configuration
API_BASE_URL = os.environ.get("WM_API_URL", "http://127.0.0.1:8001")
TOKEN = os.environ.get("TOKEN")

# Deployment configuration
# Paths relative to helm directory that should be included in chart uploads
# Only these specific files and directories will be included, everything else will be skipped
_default_chart_paths = [
    "templates",
    "overrides/dev-center",
    "overrides/models",
    "overrides/extension-gallery",
    "mount",
    "Chart.yaml",
    "values.yaml",
    "values.schema.json",
]

# Get from environment or use default
_chart_paths_env = os.environ.get("WM_ALLOWED_CHART_PATHS", None)
if _chart_paths_env is not None:
    # Parse comma-separated string from environment variable
    ALLOWED_CHART_PATHS = [p.strip() for p in _chart_paths_env.split(",") if p.strip()]
else:
    ALLOWED_CHART_PATHS = _default_chart_paths
