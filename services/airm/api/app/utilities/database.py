# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import os
from contextlib import asynccontextmanager

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

engine: AsyncEngine | None = None
session_maker: AsyncSession | None = None


DATABASE_PROTOCOL = os.environ.get("DATABASE_PROTOCOL", "postgresql+asyncpg")
DATABASE_HOST = os.environ.get("DATABASE_HOST", "localhost")
DATABASE_PORT = int(os.environ.get("DATABASE_PORT", 5432))
DATABASE_NAME = os.environ.get("DATABASE_NAME", "airm")
DATABASE_USER = os.environ.get("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "postgres")
DATABASE_CONNECTION_STRING = os.environ.get(
    "DATABASE_CONNECTION_STRING",
    f"{DATABASE_PROTOCOL}://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}",
)

# Database connection pool settings - only set if environment variables are provided
# This allows SQLAlchemy to use its own defaults when not explicitly configured
#
# Design rationale:
# - Uses QueuePool (SQLAlchemy default for PostgreSQL) rather than StaticPool
# - QueuePool provides connection health monitoring, recycling, and overflow handling
# - StaticPool would use a single persistent connection, which could be faster for
#   single-threaded scenarios but lacks resilience and connection lifecycle management
# - For production workloads, QueuePool's connection reuse and health checks are essential
# - For tests with database-per-worker, QueuePool still provides better isolation and
#   transaction boundary testing that mirrors production behavior
#
# Environment variables allow tuning without code changes:
# - DATABASE_POOL_SIZE: Base number of connections (SQLAlchemy default: 5)
# - DATABASE_MAX_OVERFLOW: Additional connections beyond pool_size (SQLAlchemy default: 10)
# - DATABASE_POOL_TIMEOUT: Seconds to wait for connection (SQLAlchemy default: 30)
# - DATABASE_POOL_RECYCLE: Seconds before recycling connections (SQLAlchemy default: -1, no recycling)
#
# References:
# - SQLAlchemy pooling: https://docs.sqlalchemy.org/en/20/core/pooling.html
# - AsyncIO engine: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.create_async_engine
DATABASE_POOL_SIZE = os.environ.get("DATABASE_POOL_SIZE")
DATABASE_MAX_OVERFLOW = os.environ.get("DATABASE_MAX_OVERFLOW")
DATABASE_POOL_TIMEOUT = os.environ.get("DATABASE_POOL_TIMEOUT")
DATABASE_POOL_RECYCLE = os.environ.get("DATABASE_POOL_RECYCLE")


def create_engine(database_connection_string: str | None = None):
    """
    Create and configure the database engine with connection pooling.

    Sets up the async SQLAlchemy engine with QueuePool for connection management.
    Pool settings are configured via environment variables with sensible defaults.

    Args:
        database_connection_string: Optional override for the database connection string.
                                   Uses DATABASE_CONNECTION_STRING environment variable if not provided.

    Returns:
        Tuple of (engine, session_maker) for database operations

    Note:
        Uses QueuePool for production resilience and connection health monitoring.
        Pool settings can be configured via DATABASE_POOL_* environment variables.
    """
    global engine, session_maker

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
        database_connection_string or DATABASE_CONNECTION_STRING,
        **engine_kwargs,
    )
    session_maker = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return engine, session_maker


def init_db() -> None:
    """Initialize database engine"""
    create_engine()

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
async def session_scope() -> AsyncSession:
    """
    Async context manager providing database session with automatic transaction handling.

    Manages the complete transaction lifecycle:
    - Begins transaction automatically
    - Commits on successful completion
    - Rolls back on any exception
    - Always closes the session

    Yields:
        AsyncSession: Database session for use in service/repository layers

    Note:
        Used by FastAPI dependency injection via get_session().
        Service and repository layers should NOT call commit/rollback themselves.
    """

    session = session_maker()  # type: ignore[misc]
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session():
    """
    FastAPI dependency that provides a database session with transaction management.

    Yields:
        AsyncSession: Database session with automatic commit/rollback handling

    Note:
        This is the standard dependency used in FastAPI route handlers.
        The session automatically handles transactions via session_scope().
    """
    async with session_scope() as session:
        yield session
