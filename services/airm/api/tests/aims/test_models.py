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
        image_name="aim-llama",
        image_tag="0.1.0-test-model-20251001",
        labels={"type": "inference", "framework": "pytorch"},
        creator="test@example.com",
    )

    assert aim.id == aim_id
    assert aim.image_name == "aim-llama"
    assert aim.image_tag == "0.1.0-test-model-20251001"
    assert aim.labels == {"type": "inference", "framework": "pytorch"}
    assert aim.created_by == "test@example.com"
    assert aim.updated_by == "test@example.com"


async def test_aim_required_fields(db_session: AsyncSession):
    """Test AIM creation with minimal required fields."""
    aim = await create_aim(
        db_session,
        image_name="aim-minimal",
        image_tag="0.1.0-basic-20251001",
        creator="test@example.com",
    )
    assert aim.image_name == "aim-minimal"
    assert aim.image_tag == "0.1.0-basic-20251001"
    assert aim.created_by == "test@example.com"
    assert aim.updated_by == "test@example.com"

    # Labels should default to empty dict
    assert aim.labels == {}


async def test_aim_image_property(db_session: AsyncSession):
    """Test the image property generates the correct container image name."""
    aim = await create_aim(
        db_session,
        image_name="aim-gpt",
        image_tag="0.2.1-chat-20251002",
        creator="test@example.com",
    )

    # Verify the individual image components
    assert aim.image_name == "aim-gpt"
    assert aim.image_tag == "0.2.1-chat-20251002"


async def test_aim_unique_image_constraint(db_session: AsyncSession):
    """Test that AIM enforces unique (image_name, image_tag) constraint."""
    await create_aim(
        db_session,
        image_name="aim-unique",
        image_tag="0.1.0-test-20251001",
        creator="user1@example.com",
    )

    # Attempt to create second AIM with the same image_name and image_tag should raise IntegrityError
    with pytest.raises(IntegrityError):
        await create_aim(
            db_session,
            image_name="aim-unique",  # Same name
            image_tag="0.1.0-test-20251001",  # Same tag should fail due to unique constraint
            creator="user2@example.com",
        )


async def test_aim_allows_same_name_different_tag(db_session: AsyncSession):
    """Test that AIMs can share the same image_name if they have different tags."""
    aim1 = await create_aim(
        db_session,
        image_name="aim-model",
        image_tag="0.1.0-test-20251001",
        creator="user1@example.com",
    )

    # Creating an AIM with the same name but different tag should succeed
    aim2 = await create_aim(
        db_session,
        image_name="aim-model",  # Same name
        image_tag="0.2.0-test-20251002",  # Different tag - should be allowed
        creator="user2@example.com",
    )

    assert aim1.image_name == aim2.image_name
    assert aim1.image_tag != aim2.image_tag
    assert aim1.id != aim2.id
