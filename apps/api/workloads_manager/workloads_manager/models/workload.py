# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workload-related models."""

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import yaml
from loguru import logger
from pydantic import BaseModel, Field, StringConstraints, ValidationError

from .. import config
from ..core.utils import normalize_metadata_keys
from .base import FileProcessingResult, ProcessingStats


class WorkloadMetadata(BaseModel):
    """Metadata for a workload."""

    id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
        Field(..., description="Unique identifier for the workload"),
    ]
    type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="Type of the workload")
    ]
    name: str | None = Field(None, description="Display name for the workload")
    slug: str | None = Field(None, description="Slug identifier for the workload")
    description: str | None = Field(None, description="Description of the workload")
    version: str | None = Field(None, description="Version of the workload")
    long_description: str | None = Field(None, description="Long description of the workload")
    category: str | None = Field(None, description="Category of the workload")
    tags: list[str] | None = Field(None, description="Tags associated with the workload")
    featured_image: str | None = Field(None, description="Featured image URL")
    required_resources: dict | None = Field(None, description="Required resources specification")
    external_url: str | None = Field(None, description="External URL for the workload")


@dataclass
class Workload:
    """Workload class to encapsulate workload properties."""

    path: Path
    metadata: WorkloadMetadata | None = None
    has_patch: bool = False
    has_changes: bool = False

    @property
    def dir_name(self) -> str:
        """Get the directory name from the path."""
        return self.path.name

    def __post_init__(self):
        """Initialize metadata."""
        self.metadata = self.load_metadata()

    @property
    def is_changed(self) -> bool:
        """Return True if workload has changes not covered by a patch."""
        return self.has_changes

    def load_metadata(self) -> WorkloadMetadata | None:
        """Load metadata from _metadata.yaml file."""
        metadata_file = self.metadata_path
        if not metadata_file.exists():
            return None

        try:
            content = metadata_file.read_text()
            raw_metadata = yaml.safe_load(content)
            if not raw_metadata:
                return None

            if isinstance(raw_metadata, dict) and "id" in raw_metadata and "type" in raw_metadata:
                return WorkloadMetadata(**normalize_metadata_keys(raw_metadata))

            return None
        except ValidationError as e:
            logger.error(f"Invalid metadata format in {metadata_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading metadata file: {e}")
            return None

    @property
    def chart_name(self) -> str | None:
        """Chart name from metadata."""
        try:
            if self.metadata:
                return self.metadata.id
            return None
        except Exception as e:
            logger.exception(f"Error getting chart name: {e}")
            return None

    @property
    def type(self) -> str | None:
        """Workload type from metadata."""
        try:
            if self.metadata:
                return self.metadata.type
            return None
        except Exception as e:
            logger.exception(f"Error getting workload type: {e}")
            return None

    @property
    def chart_path(self) -> Path:
        """Path to the helm chart directory."""
        return self.path / "helm"

    @property
    def metadata_path(self) -> Path:
        """Path to _metadata.yaml."""
        return self.chart_path / "overrides" / "dev-center" / "_metadata.yaml"

    @property
    def signature_path(self) -> Path:
        """Path to signature.yaml."""
        return self.chart_path / "overrides" / "dev-center" / "signature.yaml"

    def __str__(self) -> str:
        return self.dir_name

    @property
    def is_registerable(self) -> bool:
        """Check if registerable."""
        has_meta = bool(self.metadata)
        has_chart = self.chart_name is not None
        has_type = self.type is not None
        return has_meta and has_chart and has_type

    def _iter_files(self) -> Iterator[tuple[Path, str]]:
        """Iterate over all files in the chart directory.

        Yields:
            Tuple of (file_path, relative_path_str) for each file
        """
        if not self.chart_path.exists():
            return

        for root, _, filenames in os.walk(self.chart_path):
            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.chart_path)
                yield file_path, str(rel_path)

    def _is_allowed_file(self, rel_path: str | Path) -> bool:
        """Check if a file should be included based on ALLOWED_CHART_PATHS."""
        path_obj = Path(rel_path)
        rel_path_str = str(path_obj)
        rel_dir = str(path_obj.parent) if path_obj.parent != Path(".") else ""

        for allowed_path in config.ALLOWED_CHART_PATHS:
            # Exact file match
            if allowed_path == rel_path_str:
                return True
            # Directory match - normalize paths by removing trailing slashes
            allowed_path_normalized = allowed_path.rstrip("/")
            if allowed_path_normalized and (
                rel_dir == allowed_path_normalized or rel_path_str.startswith(f"{allowed_path_normalized}/")
            ):
                return True

        return False

    def get_chart_files(self) -> list[Path]:
        """Get list of chart files for upload (excludes overlays)."""
        chart_files: list[Path] = []
        for file_path, rel_path_str in self._iter_files():
            # Skip overrides directory (handled separately as overlays)
            if rel_path_str.startswith("overrides/"):
                continue
            # Check if file should be included based on allowed paths
            if self._is_allowed_file(rel_path_str):
                chart_files.append(file_path)
        return chart_files

    def get_overlay_files(self) -> list[tuple[Path, str]]:
        """Get list of overlay files for processing (YAML files in allowed overlay directories)."""
        overlay_files = []
        for file_path, rel_path_str in self._iter_files():
            # Only include overlay files that are allowed and YAML
            if (
                self._is_allowed_file(rel_path_str)
                and rel_path_str.startswith("overrides/")
                and not rel_path_str.startswith("overrides/dev-center/")
                and rel_path_str.endswith((".yaml", ".yml"))
            ):
                overlay_files.append((file_path, rel_path_str))
        return overlay_files

    def get_chart_upload_data(self) -> dict[str, list[Path]] | None:
        """Get files data for chart upload in the format expected by make_api_request."""
        if not self.signature_path.exists():
            logger.error(f"Signature file not found at {self.signature_path}")
            return None

        chart_files = self.get_chart_files()
        if not chart_files:
            logger.error("No chart files found")
            return None

        return {"signature": [self.signature_path], "files": chart_files}

    def get_metadata_for_api(self) -> dict[str, str | list | dict | None]:
        """Get metadata fields for API submission.

        Returns:
            Dict with metadata fields using API field names (snake_case)
        """
        if not self.metadata:
            return {}

        # Map metadata fields to API field names
        metadata_dict = {
            "slug": self.metadata.slug or self.metadata.id,  # Use slug if available, fallback to id
            "display_name": self.metadata.name,
            "description": self.metadata.description,
            "long_description": self.metadata.long_description,
            "category": self.metadata.category,
            "tags": json.dumps(self.metadata.tags) if self.metadata.tags else None,
            "featured_image": self.metadata.featured_image,
            "required_resources": (
                json.dumps(self.metadata.required_resources) if self.metadata.required_resources else None
            ),
            "external_url": self.metadata.external_url,
        }

        # Remove None values to avoid overwriting existing data
        return {k: v for k, v in metadata_dict.items() if v is not None}


class WorkloadRegistrationResult(BaseModel):
    """Result of workload registration operation."""

    success: bool = Field(..., description="Whether the registration was successful")
    chart_id: str | None = Field(None, description="ID of the registered chart")
    chart_name: str | None = Field(None, description="Name of the chart")
    files: list[FileProcessingResult] = Field(default_factory=list, description="Results for individual files")
    stats: ProcessingStats = Field(default_factory=ProcessingStats, description="Processing statistics")
    error: str | None = Field(None, description="Error message if registration failed")
