# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.database import session_scope
from app.messaging.sender import MessageSender, get_message_sender


async def get_session(
    _: MessageSender = Depends(get_message_sender),
) -> AsyncGenerator[AsyncSession]:
    """
    FastAPI dependency that provides a database session with transaction management.

    Depends on message_sender to enforce correct transactional ordering:
    FastAPI resolves dependencies first (message_sender, then session); cleanup reverses
    that order so the DB commits before outbound messages are flushed.
    """
    async with session_scope() as session:
        yield session
