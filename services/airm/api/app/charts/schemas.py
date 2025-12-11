# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import json
from pathlib import Path
from typing import Literal

import yaml
from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..utilities.schema import BaseEntityPublic
from ..workloads.enums import WorkloadType


async def _parse_signature_file(signature: UploadFile | Path) -> dict:
    """Parse signature YAML file."""
    try:
        if isinstance(signature, Path):
            with open(signature, encoding="utf-8") as f:
                signature_content = f.read()
        else:
            signature_content = (await signature.read()).decode()
        return yaml.safe_load(signature_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in signature file: {e}")


async def _parse_chart_files(files: list[UploadFile | Path]) -> list[dict]:
    """Parse chart files into dict objects."""
    files_data = []
    for file in files:
        if isinstance(file, Path):
            with open(file, encoding="utf-8") as f:
                content = f.read()
            file_name = file.name
            path_parts = file.parts
            if "helm" in path_parts:
                helm_idx = path_parts.index("helm")
                if helm_idx + 1 < len(path_parts):
                    # Get relative path from helm directory
                    rel_parts = path_parts[helm_idx + 1 :]
                    file_name = "/".join(rel_parts)
        else:
            content = (await file.read()).decode()
            file_name = file.filename
        files_data.append({"path": file_name, "content": content})
    return files_data


class ChartFile(BaseModel):
    path: str
    content: str


class ChartMetadata(BaseModel):
    """Chart metadata fields."""

    display_name: str | None = None
    slug: str | None = None
    description: str | None = None
    long_description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    featured_image: str | None = None
    required_resources: dict | None = None
    external_url: str | None = None

    @field_validator("required_resources", mode="before")
    @classmethod
    def parse_required_resources(cls, v):
        """Parse required_resources from FastAPI multipart form data."""
        # Handle direct JSON string from form data
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        # FastAPI can also send as list containing JSON string
        elif isinstance(v, list) and len(v) == 1 and isinstance(v[0], str):
            try:
                return json.loads(v[0])
            except json.JSONDecodeError:
                return None
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        """Parse tags from FastAPI multipart form data."""
        # Handle direct JSON string from form data
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Tags must be a valid JSON list or a list of strings.")
        return v


class ChartBase(ChartMetadata):
    """Base chart schema with core fields and metadata."""

    name: str = Field(min_length=3, max_length=64)
    type: WorkloadType


class ChartCreate(ChartBase):
    """API schema for creating charts."""

    signature: UploadFile | Path = File(...)
    files: list[UploadFile | Path] | None = File(None)

    async def to_data(self) -> dict:
        """Convert schema to dict with parsed file data for database storage."""
        data = self.model_dump(exclude={"signature", "files"})
        data["signature"] = await _parse_signature_file(self.signature)
        data["files"] = await _parse_chart_files(self.files) if self.files else []
        return data


class ChartUpdate(ChartMetadata):
    """API schema for updating charts."""

    name: str | None = Field(None, min_length=3, max_length=64)
    type: WorkloadType | None = None
    signature: UploadFile | Path | None = File(None)
    files: list[UploadFile | Path] | None = File(None)

    async def to_data(self) -> dict:
        """Convert schema to dict with parsed file data for database storage."""
        data = self.model_dump(exclude={"signature", "files"}, exclude_none=True)
        if self.signature:
            data["signature"] = await _parse_signature_file(self.signature)
        if self.files is not None:
            data["files"] = await _parse_chart_files(self.files)
        return data


class ChartResponse(BaseEntityPublic, ChartBase):
    """Response schema for charts."""

    signature: dict
    files: list[ChartFile] = []
    usage_scope: Literal["user", "project"]

    model_config = ConfigDict(from_attributes=True)


class ChartListResponse(BaseEntityPublic, ChartBase):
    """Lightweight response for listing charts."""

    usage_scope: Literal["user", "project"]

    model_config = ConfigDict(from_attributes=True)


class ChartsResponse(BaseModel):
    """Wrapper for collection of charts."""

    data: list[ChartListResponse] = Field(description="List of charts")
