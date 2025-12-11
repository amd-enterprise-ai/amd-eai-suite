# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factory import create_aim


async def test_aim_table_structure(db_session: AsyncSession):
    """Test the AIM model structure and required fields."""
    aim_id = uuid4()
    aim = await create_aim(
        db_session,
        id=aim_id,
        resource_name="aim-llama-0-1-0",
        image_reference="docker.io/amdenterpriseai/llama:0.1.0",
        labels={"com.amd.aim.model.canonicalName": "test/llama"},
        status="Ready",
        creator="test@example.com",
    )

    assert aim.id == aim_id
    assert aim.resource_name == "aim-llama-0-1-0"
    assert aim.image_reference == "docker.io/amdenterpriseai/llama:0.1.0"
    assert aim.labels == {"com.amd.aim.model.canonicalName": "test/llama"}
    assert aim.status == "Ready"
    assert aim.created_by == "test@example.com"
    assert aim.updated_by == "test@example.com"


async def test_aim_required_fields(db_session: AsyncSession):
    """Test AIM creation with minimal required fields."""
    aim = await create_aim(
        db_session,
        resource_name="aim-minimal-0-1-0",
        image_reference="docker.io/amdenterpriseai/minimal:0.1.0",
        creator="test@example.com",
    )
    assert aim.resource_name == "aim-minimal-0-1-0"
    assert aim.image_reference == "docker.io/amdenterpriseai/minimal:0.1.0"
    assert aim.status == "Ready"
    assert aim.created_by == "test@example.com"
    assert aim.updated_by == "test@example.com"

    # labels should default to empty dict
    assert aim.labels == {}


async def test_aim_unique_resource_name_constraint(db_session: AsyncSession):
    """Test that AIM enforces unique resource_name constraint."""
    await create_aim(
        db_session,
        resource_name="aim-unique-model",
        image_reference="docker.io/amd/model:v1",
        creator="user1@example.com",
    )

    # Attempt to create second AIM with the same resource_name should raise IntegrityError
    with pytest.raises(IntegrityError):
        await create_aim(
            db_session,
            resource_name="aim-unique-model",  # Same resource_name should fail
            image_reference="docker.io/amd/model:v2",
            creator="user2@example.com",
        )


async def test_aim_allows_different_resource_names(db_session: AsyncSession):
    """Test that AIMs can have different resource names."""
    aim1 = await create_aim(
        db_session,
        resource_name="aim-model-v1",
        image_reference="docker.io/amd/model:v1",
        creator="user1@example.com",
    )

    # Creating an AIM with a different resource_name should succeed
    aim2 = await create_aim(
        db_session,
        resource_name="aim-model-v2",
        image_reference="docker.io/amd/model:v2",
        creator="user2@example.com",
    )

    assert aim1.resource_name != aim2.resource_name
    assert aim1.id != aim2.id
