# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Common database utilities - same pattern as apps/api/airm with optional messaging support.

This maintains compatibility with AIRM's MessageSender pattern but allows it to be disabled
for services like AIWB that don't use RabbitMQ.
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

# Module-level globals - same pattern as AIRM
engine: AsyncEngine | None = None
session_maker: async_sessionmaker[AsyncSession] | None = None

# Database connection configuration - same as AIRM
DATABASE_PROTOCOL = os.environ.get("DATABASE_PROTOCOL", "postgresql+asyncpg")
DATABASE_HOST = os.environ.get("DATABASE_HOST", "localhost")
DATABASE_PORT = int(os.environ.get("DATABASE_PORT", 5432))
DATABASE_NAME = os.environ.get("DATABASE_NAME", "postgres")
DATABASE_USER = os.environ.get("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "postgres")
DATABASE_CONNECTION_STRING = os.environ.get(
    "DATABASE_CONNECTION_STRING",
    f"{DATABASE_PROTOCOL}://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}",
)

# Database connection pool settings
DATABASE_POOL_SIZE = os.environ.get("DATABASE_POOL_SIZE")
DATABASE_MAX_OVERFLOW = os.environ.get("DATABASE_MAX_OVERFLOW")
DATABASE_POOL_TIMEOUT = os.environ.get("DATABASE_POOL_TIMEOUT")
DATABASE_POOL_RECYCLE = os.environ.get("DATABASE_POOL_RECYCLE")

# Messaging support - disabled by default for services that don't need it
USE_MESSAGING = False
_message_sender_dependency: Any = None


def enable_messaging(get_message_sender_func: Any) -> None:
    """
    Enable MessageSender dependency for transactional messaging (like AIRM).

    Call this during app initialization if you want get_session() to depend on MessageSender.

    Example (AIRM):
        from app.messaging.sender import get_message_sender
        from api_common.database import enable_messaging
        enable_messaging(get_message_sender)
    """
    global USE_MESSAGING, _message_sender_dependency
    USE_MESSAGING = True
    _message_sender_dependency = get_message_sender_func


def create_engine(
    database_connection_string: str = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Create and configure the database engine with connection pooling.

    Identical to AIRM's create_engine.
    """
    global engine, session_maker

    # Use provided connection string or build from env vars
    conn_string = database_connection_string or DATABASE_CONNECTION_STRING

    # Build engine kwargs, only including pool settings if they're configured
    engine_kwargs: dict[str, int | bool] = {
        "echo": False,
        "pool_pre_ping": True,
    }

    if DATABASE_POOL_SIZE is not None:
        engine_kwargs["pool_size"] = int(DATABASE_POOL_SIZE)
    if DATABASE_MAX_OVERFLOW is not None:
        engine_kwargs["max_overflow"] = int(DATABASE_MAX_OVERFLOW)
    if DATABASE_POOL_TIMEOUT is not None:
        engine_kwargs["pool_timeout"] = int(DATABASE_POOL_TIMEOUT)
    if DATABASE_POOL_RECYCLE is not None:
        engine_kwargs["pool_recycle"] = int(DATABASE_POOL_RECYCLE)

    engine = create_async_engine(
        conn_string,
        **engine_kwargs,
    )
    session_maker = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return engine, session_maker


def init_db(database_connection_string: str = None) -> None:
    """Initialize database engine."""
    create_engine(database_connection_string)

    if not engine:
        raise RuntimeError("Database engine is not initialized")
    logger.info("Connected to database with url {0}", engine.sync_engine.url)


async def dispose_db() -> None:
    """
    Dispose of the database engine and close all connections.

    Called during application shutdown to properly clean up database resources.
    """
    if engine:
        await engine.dispose()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession]:
    """
    Async context manager providing database session with automatic transaction handling.

    Identical to AIRM's session_scope.
    """
    if not session_maker:
        raise RuntimeError("Database not initialized")

    session = session_maker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncGenerator[AsyncSession]:
    """
    FastAPI dependency that provides a database session with transaction management.

    This is the base version without messaging support (used by AIWB).
    AIRM uses get_session_with_messaging() instead.

    Usage:
        @router.post("/workloads")
        async def create(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with session_scope() as session:
        yield session


async def get_session_with_messaging(
    _message_sender: Any = None,
) -> AsyncGenerator[AsyncSession]:
    """
    FastAPI dependency for database session WITH messaging support (AIRM only).

    The _message_sender parameter enforces transactional ordering.
    AIRM should use this instead of get_session().
    """
    async with session_scope() as session:
        yield session
