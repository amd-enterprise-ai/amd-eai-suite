# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Overlays service tests using real database + factories instead of extensive mocking.

This follows the established pattern:
- Use real database for all repository operations
- Use factories for test data creation
- Mock only external services (file operations, YAML parsing if needed)
- Focus tests on business logic rather than mock coordination
"""

import io
import uuid

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.overlays.service import (
    create_overlay,
    delete_overlay_by_id_service,
    get_overlay_by_id,
    parse_overlay_file,
)
from app.utilities.exceptions import ConflictException, NotFoundException, ValidationException
from tests import factory


@pytest.mark.asyncio
async def test_create_overlay_success(db_session: AsyncSession):
    """Test successful overlay creation with real database operations."""
    chart = await factory.create_chart(db_session, name="test-chart")

    overlay_data = {
        "values": {
            "image": {"tag": "v1.0.0"},
            "service": {"type": "ClusterIP", "port": 80},
        }
    }
    canonical_name = "production"
    creator = "test@example.com"

    result = await create_overlay(db_session, chart.id, overlay_data, canonical_name, creator)
    assert result is not None
    assert result.chart_id == chart.id
    assert result.overlay == overlay_data
    assert result.canonical_name == canonical_name
    assert result.created_by == creator


@pytest.mark.asyncio
async def test_create_overlay_chart_not_found(db_session: AsyncSession):
    """Test creating overlay with non-existent chart raises NotFoundException."""
    overlay_data = {"values": {"image": {"tag": "v1.0.0"}}}
    canonical_name = "test-overlay"
    creator = "test@example.com"
    non_existent_chart_id = uuid.uuid4()

    with pytest.raises(NotFoundException, match=f"Chart with ID {non_existent_chart_id} not found"):
        await create_overlay(db_session, non_existent_chart_id, overlay_data, canonical_name, creator)


@pytest.mark.asyncio
async def test_create_overlay_duplicate_canonical_name(db_session: AsyncSession):
    """Test creating overlay with duplicate canonical name raises ConflictException."""
    chart = await factory.create_chart(db_session, name="test-chart")

    overlay_data = {"values": {"image": {"tag": "v1.0.0"}}}
    canonical_name = "production"
    creator = "test@example.com"

    await create_overlay(db_session, chart.id, overlay_data, canonical_name, creator)
    with pytest.raises(ConflictException, match="already exists"):
        await create_overlay(db_session, chart.id, overlay_data, canonical_name, creator)


@pytest.mark.asyncio
async def test_get_overlay_by_id_success(db_session: AsyncSession):
    """Test retrieving overlay by ID with real database operations."""
    chart = await factory.create_chart(db_session, name="test-chart")
    overlay = await factory.create_overlay(
        db_session, chart, canonical_name="test-overlay", overlay_data={"test": "data"}
    )

    result = await get_overlay_by_id(db_session, overlay.id)
    assert result.id == overlay.id
    assert result.chart_id == chart.id
    assert result.canonical_name == "test-overlay"
    assert result.overlay == {"test": "data"}


@pytest.mark.asyncio
async def test_get_overlay_by_id_not_found(db_session: AsyncSession):
    """Test retrieving non-existent overlay raises NotFoundException."""
    non_existent_overlay_id = uuid.uuid4()

    with pytest.raises(NotFoundException, match=f"Overlay with ID {non_existent_overlay_id} not found"):
        await get_overlay_by_id(db_session, non_existent_overlay_id)


@pytest.mark.asyncio
async def test_delete_overlay_by_id_success(db_session: AsyncSession):
    """Test deleting overlay by ID with real database operations."""
    chart = await factory.create_chart(db_session, name="test-chart")
    overlay = await factory.create_overlay(
        db_session, chart, canonical_name="test-overlay", overlay_data={"test": "data"}
    )

    await delete_overlay_by_id_service(db_session, overlay.id)
    with pytest.raises(NotFoundException):
        await get_overlay_by_id(db_session, overlay.id)


@pytest.mark.asyncio
async def test_delete_overlay_by_id_not_found(db_session: AsyncSession):
    """Test deleting non-existent overlay raises NotFoundException."""
    non_existent_overlay_id = uuid.uuid4()

    with pytest.raises(NotFoundException, match=f"Overlay with ID {non_existent_overlay_id} not found"):
        await delete_overlay_by_id_service(db_session, non_existent_overlay_id)


@pytest.mark.asyncio
async def test_parse_overlay_file_valid_yaml():
    """Test parsing valid YAML overlay file."""
    yaml_content = """
values:
  image:
    tag: "v1.2.3"
  service:
    type: "LoadBalancer"
    port: 8080
  resources:
    limits:
      cpu: "500m"
      memory: "512Mi"
"""

    file_content = yaml_content.encode("utf-8")
    upload_file = UploadFile(filename="overlay.yaml", file=io.BytesIO(file_content))

    result = await parse_overlay_file(upload_file)
    expected = {
        "values": {
            "image": {"tag": "v1.2.3"},
            "service": {"type": "LoadBalancer", "port": 8080},
            "resources": {"limits": {"cpu": "500m", "memory": "512Mi"}},
        }
    }
    assert result == expected


@pytest.mark.asyncio
async def test_parse_overlay_file_invalid_format():
    """Test parsing file with invalid format raises ValidationException."""
    file_content = b"some content"
    upload_file = UploadFile(filename="overlay.txt", file=io.BytesIO(file_content))

    with pytest.raises(ValidationException, match="Invalid file format. Only YAML files are accepted."):
        await parse_overlay_file(upload_file)


@pytest.mark.asyncio
async def test_parse_overlay_file_invalid_yaml():
    """Test parsing invalid YAML content raises ValidationException."""
    invalid_yaml = """
values:
  image:
    tag: "v1.2.3"
  service:
    type: "LoadBalancer"
    port: 8080
    invalid_indent:
  bad_syntax: [unclosed
"""

    file_content = invalid_yaml.encode("utf-8")
    upload_file = UploadFile(filename="overlay.yaml", file=io.BytesIO(file_content))

    with pytest.raises(ValidationException, match="Invalid YAML format"):
        await parse_overlay_file(upload_file)


@pytest.mark.asyncio
async def test_create_overlay_without_canonical_name(db_session: AsyncSession):
    """Test creating overlay without canonical name (should work)."""
    chart = await factory.create_chart(db_session, name="test-chart")

    overlay_data = {"values": {"image": {"tag": "v1.0.0"}}}
    creator = "test@example.com"

    result = await create_overlay(db_session, chart.id, overlay_data, canonical_name=None, creator=creator)
    assert result is not None
    assert result.chart_id == chart.id
    assert result.overlay == overlay_data
    assert result.canonical_name is None
    assert result.created_by == creator


@pytest.mark.asyncio
async def test_create_overlay_without_creator(db_session: AsyncSession):
    """Test creating overlay without creator (should work)."""
    chart = await factory.create_chart(db_session, name="test-chart")

    overlay_data = {"values": {"image": {"tag": "v1.0.0"}}}
    canonical_name = "test-overlay"

    result = await create_overlay(db_session, chart.id, overlay_data, canonical_name, creator=None)
    assert result is not None
    assert result.chart_id == chart.id
    assert result.overlay == overlay_data
    assert result.canonical_name == canonical_name
    assert result.created_by is None
