# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import json
import os
import time
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import aio_pika
import asyncpg
import docker
import pytest  # Added for monkeypatch
import pytest_asyncio
from fastapi.testclient import TestClient
from filelock import FileLock
from keycloak import KeycloakAdmin
from loguru import logger
from prometheus_api_client import PrometheusConnect
from sqlalchemy import text
from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tenacity import retry, stop_after_attempt, wait_exponential
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

import app.utilities.database as db_module
from app import app  # type: ignore
from app.utilities.database import create_engine
from app.utilities.models import BaseEntity
from app.utilities.security import (
    Roles,
    create_logged_in_user_in_system,
    track_user_activity_from_token,
)

# Set Loki configuration before any module imports
os.environ.setdefault("LOKI_KEEPALIVE_TIMEOUT_SECONDS", "1")

# Mock cluster auth service configuration
MOCK_CLUSTER_AUTH_PORT = 48012
MOCK_CLUSTER_AUTH_READY_LOG_PATTERN = rf"Uvicorn running on http://0\.0\.0\.0:{MOCK_CLUSTER_AUTH_PORT}"
MOCK_CLUSTER_AUTH_STARTUP_TIMEOUT = 30


def get_session_tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Get the session-scoped temporary path.

    xdist workers get per-worker basetemp (e.g. /tmp/pytest-of-user/pytest-123/gw0),
    so .parent gives the shared session dir. Without xdist, basetemp is already the
    session dir. Using the session dir (not its parent) prevents cleanup from
    accidentally killing containers belonging to other concurrent pytest sessions.
    """
    return (
        tmp_path_factory.getbasetemp().parent
        if os.environ.get("PYTEST_XDIST_WORKER")
        else tmp_path_factory.getbasetemp()
    )


def cleanup_containers(session: pytest.Session) -> None:
    """Clean up containers from the current session only."""
    if not hasattr(session.config, "workerinput"):
        docker_client = docker.from_env()
        base_path = get_session_tmp_path(session.config._tmp_path_factory)
        for container_file in base_path.rglob("*_container.json"):
            container_info = json.loads(container_file.read_text())
            containers = docker_client.containers.list(filters={"id": container_info["container_id"]})
            if containers:
                for container in containers:
                    try:
                        container.stop()
                        container.wait()
                        container.remove(force=True, v=True)
                    except docker.errors.NotFound:
                        pass
                if (image_id := container_info.get("image_id")) is not None:
                    image = docker_client.images.get(image_id)
                    success = False
                    max_attempts = 50  # ~5 seconds total with 0.1s sleep
                    for _ in range(1, max_attempts + 1):
                        time.sleep(0.1)
                        try:
                            image.remove(force=True)
                            success = True
                            container_file.unlink()
                            break
                        except docker.errors.APIError as e:
                            pass
                    if not success:
                        logger.warning(
                            "Giving up on removing Docker image %s after %d attempts.",
                            image_id,
                            max_attempts,
                        )
                else:
                    container_file.unlink()
            else:
                container_file.unlink()


def pytest_sessionstart(session: pytest.Session) -> None:
    """Clean up containers before session starts."""
    cleanup_containers(session)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clean up containers after session finishes."""
    cleanup_containers(session)


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5), stop=stop_after_attempt(5), reraise=True)
async def _connect_to_postgres(host: str, port: int) -> asyncpg.Connection:
    """Connect to postgres default database with retry logic for parallel test startup."""
    return await asyncpg.connect(f"postgresql://postgres:postgres@{host}:{port}/postgres", timeout=10)


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5), stop=stop_after_attempt(10), reraise=True)
async def _connect_to_rabbitmq(host: str, port: int) -> aio_pika.abc.AbstractRobustConnection:
    """Connect to RabbitMQ with retry logic for parallel test startup."""
    return await aio_pika.connect_robust(
        f"amqp://guest:guest@{host}:{port}/vh_airm_common",
        timeout=10,
    )


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5), stop=stop_after_attempt(5), reraise=True)
async def _create_engine_with_schema(database_url: str) -> tuple:
    """Create database engine and schema with retry logic for startup issues."""
    engine, session_local = create_engine(database_url)
    # Test the connection and create schema
    async with engine.begin() as conn:
        await conn.run_sync(BaseEntity.metadata.create_all)
    return engine, session_local


@retry(
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5),
    stop=stop_after_attempt(5),
    reraise=False,  # Don't fail cleanup
)
async def _connect_to_postgres_for_cleanup(host: str, port: int) -> asyncpg.Connection | None:
    """Connect to postgres for cleanup with retry logic. Returns None if all attempts fail."""
    try:
        return await asyncpg.connect(f"postgresql://postgres:postgres@{host}:{port}/postgres", timeout=10)
    except (
        ConnectionRefusedError,
        asyncpg.exceptions.ConnectionFailureError,
        ConnectionResetError,
        asyncpg.exceptions.CannotConnectNowError,
    ) as e:
        # Don't fail cleanup - just log and continue
        logger.warning(f"Failed to connect for database cleanup: {e}")
        return None


def _coordinate_container_across_workers(
    tmp_path_factory: Any,
    worker_id: str,
    container_name: str,
    setup_fn: Callable[[], tuple[Any, dict[str, Any]]],
) -> tuple[Any | None, dict[str, Any] | None]:
    """
    Coordinate container startup across pytest-xdist workers.

    This helper eliminates duplication between postgres_container and mock_cluster_auth_container
    by centralizing the xdist worker coordination logic.

    Args:
        tmp_path_factory: pytest fixture for creating temporary paths
        worker_id: pytest-xdist worker identifier ("master" for single process)
        container_name: unique name for the container (used for lock/json files)
        setup_fn: callable that starts container and returns (container, container_info) tuple

    Returns:
        Tuple of (container object or None, container_info dict or None)
    """
    fn = get_session_tmp_path(tmp_path_factory) / f"{container_name}.json"

    if worker_id == "master":
        # Not running with xdist, start container normally
        container, container_info = setup_fn()
        fn.write_text(json.dumps(container_info))
        return container, container_info
    else:
        # Running with xdist - coordinate across workers
        with FileLock(str(fn) + ".lock"):
            if fn.is_file():
                # Another worker already started the container
                container_info = json.loads(fn.read_text())
                return None, container_info
            else:
                # First worker - start container and save info
                container, container_info = setup_fn()
                fn.write_text(json.dumps(container_info))
                return container, container_info


@asynccontextmanager
async def test_session_scope(session_maker):
    """
    Test-specific session scope that provides automatic transaction handling
    like production session_scope() but optimized for testing scenarios.

    This context manager automatically:
    - Commits successful operations
    - Rolls back on exceptions (including IntegrityError)
    - Closes session in finally block

    This eliminates the need for manual rollback handling in constraint violation tests.
    """
    session = session_maker()
    try:
        yield session
        try:
            await session.commit()
        except PendingRollbackError:
            # Session was already rolled back due to an IntegrityError that was caught
            # by pytest.raises - this is expected behavior in constraint violation tests
            pass
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@pytest.fixture(scope="session")
def postgres_container(
    tmp_path_factory: pytest.TempPathFactory, worker_id: str
) -> Generator[tuple[PostgresContainer | None, dict[str, Any] | None]]:
    """Start Postgres container using testcontainers (shared across xdist workers)."""

    def container_setup() -> tuple[PostgresContainer, dict[str, Any]]:
        container = PostgresContainer("postgres:17", username="postgres", password="postgres", dbname="postgres")
        container.start()
        container_info = {
            "host": container.get_container_host_ip(),
            "port": int(container.get_exposed_port(5432)),
            "container_id": container._container.id,
        }
        return container, container_info

    container, container_info = _coordinate_container_across_workers(
        tmp_path_factory,
        worker_id,
        "postgres_container",
        container_setup,
    )

    yield container, container_info


@pytest.fixture(scope="session")
def postgres_service(
    postgres_container: tuple[PostgresContainer | None, dict[str, Any] | None],
) -> Generator[tuple[str, int]]:
    """Ensure that Postgres service is up and responsive."""
    match postgres_container:
        case (None, container_info) if container_info is not None:
            yield container_info["host"], container_info["port"]
        case (container, _) if container is not None:
            yield container.get_container_host_ip(), int(container.get_exposed_port(5432))
        case _:
            raise RuntimeError("Invalid postgres_container state")


@pytest.fixture(scope="session")
def rabbitmq_container(
    tmp_path_factory: pytest.TempPathFactory, worker_id: str
) -> Generator[tuple[RabbitMqContainer | None, dict[str, Any] | None]]:
    """Start RabbitMQ container using testcontainers (shared across xdist workers)."""

    def container_setup() -> tuple[RabbitMqContainer, dict[str, Any]]:
        container = RabbitMqContainer("rabbitmq:4.0-management")
        # Use default credentials and vhost - custom vhost will be created after startup
        container.start()

        # Create the vh_airm_common vhost after container is ready
        result = container.get_wrapped_container().exec_run(["rabbitmqctl", "add_vhost", "vh_airm_common"])
        if result.exit_code != 0:
            logger.warning(f"Failed to create vhost: {result.output.decode()}")

        # Set permissions for guest user on the new vhost
        result = container.get_wrapped_container().exec_run(
            ["rabbitmqctl", "set_permissions", "-p", "vh_airm_common", "guest", ".*", ".*", ".*"]
        )
        if result.exit_code != 0:
            logger.warning(f"Failed to set permissions: {result.output.decode()}")

        container_info = {
            "host": container.get_container_host_ip(),
            "port": int(container.get_exposed_port(5672)),
            "container_id": container._container.id,
        }
        return container, container_info

    container, container_info = _coordinate_container_across_workers(
        tmp_path_factory,
        worker_id,
        "rabbitmq_container",
        container_setup,
    )

    yield container, container_info


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def rabbitmq_service(
    rabbitmq_container: tuple[RabbitMqContainer | None, dict[str, Any] | None],
) -> AsyncGenerator[tuple[str, int]]:
    """Ensure that RabbitMQ service is up and responsive."""
    match rabbitmq_container:
        case (None, container_info) if container_info is not None:
            host, port = container_info["host"], container_info["port"]
        case (container, _) if container is not None:
            host, port = container.get_container_host_ip(), int(container.get_exposed_port(5672))
        case _:
            raise RuntimeError("Invalid rabbitmq_container state")

    # Wait for RabbitMQ to be ready
    connection = await _connect_to_rabbitmq(host, port)
    await connection.close()

    yield host, port


@pytest.fixture(autouse=True)
async def global_init_dependencies(monkeypatch):
    # Set dummy env vars for Keycloak client to prevent startup error
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://dummy-keycloak-server.com")
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_ID", "dummy_client_id")
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "dummy_client_secret")
    monkeypatch.setenv("KEYCLOAK_REALM", "dummy_realm")

    # Set dummy env var for Prometheus client to prevent startup error
    monkeypatch.setenv("PROMETHEUS_URL", "http://dummy-prometheus-server.com")

    # Set dummy env var for POST_REGISTRATION_REDIRECT_URL to prevent startup error
    monkeypatch.setenv("POST_REGISTRATION_REDIRECT_URL", "http://test-redirect-url.com")

    app.dependency_overrides[create_logged_in_user_in_system] = lambda: MagicMock(spec=create_logged_in_user_in_system)
    app.dependency_overrides[track_user_activity_from_token] = lambda: MagicMock(spec=track_user_activity_from_token)
    with (
        patch("app.init_db", autospec=True),
        patch("app.configure_inbound_vhost", autospec=True),
        patch("app.configure_queues_for_common_vhost", autospec=True),
        patch("app.start_consuming_from_common_feedback_queue", autospec=True),
        patch("app.start_metrics_server", autospec=True),
        patch("app.init_keycloak_admin_client") as mock_init_kc,
        patch("app.init_prometheus_client") as mock_init_prometheus,
    ):
        # Ensure the mock returns a MagicMock that can be used as if it's a KeycloakAdmin client
        mock_init_kc.return_value = MagicMock(spec=KeycloakAdmin)
        # Ensure the mock returns a MagicMock that can be used as if it's a PrometheusConnect client
        mock_init_prometheus.return_value = MagicMock(spec=PrometheusConnect)
        yield


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_config(postgres_service: tuple[str, int], worker_id: str) -> AsyncGenerator[dict[str, Any]]:
    """Session-scoped fixture that creates the database once per worker."""
    host, port = postgres_service
    db_name = f"airm_test_{worker_id}"
    database_url = f"postgresql+asyncpg://postgres:postgres@{host}:{port}/{db_name}"

    conn = await _connect_to_postgres(host, port)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()

    schema_created = {"done": False}
    yield {
        "database_url": database_url,
        "db_name": db_name,
        "schema_created": schema_created,
        "host": host,
        "port": port,
    }

    # Cleanup
    conn = await _connect_to_postgres_for_cleanup(host, port)
    if conn:
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        finally:
            await conn.close()


@pytest_asyncio.fixture(loop_scope="function")
async def db_session(db_config):
    """
    Create a session with automatic transaction handling. Schema/DB created once per worker.

    Uses TRUNCATE for test isolation instead of transaction rollback because:
    - Tests call session.commit() and session.refresh() which require real commits
    - Transaction rollback would make committed data invisible to refresh()
    - TRUNCATE is faster than DROP/CREATE schema (~40s vs ~140s for full suite)
    """
    database_url = db_config["database_url"]
    schema_created = db_config["schema_created"]

    if not schema_created["done"]:
        schema_engine = create_async_engine(database_url, echo=False, poolclass=NullPool)
        async with schema_engine.begin() as conn:
            await conn.run_sync(BaseEntity.metadata.create_all)
        await schema_engine.dispose()
        schema_created["done"] = True

    engine = create_async_engine(database_url, echo=False, poolclass=NullPool)
    session_local = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_module.engine = engine
    db_module.session_maker = session_local

    async with test_session_scope(session_local) as session:
        yield session

    async with engine.begin() as conn:
        table_names = list(BaseEntity.metadata.tables.keys())
        if table_names:
            # Safely quote table names using the engine's dialect
            quoted_tables = [conn.dialect.identifier_preparer.quote(t) for t in table_names]
            truncate_stmt = f"TRUNCATE {', '.join(quoted_tables)} RESTART IDENTITY CASCADE"
            await conn.execute(text(truncate_stmt))
    await engine.dispose()


@contextmanager
def get_test_client():
    """Create a clean TestClient for each test and ensure proper cleanup.
    This context manager guarantees that the TestClient is properly closed.
    Note: Dependency override cleanup is handled by test-specific fixtures to avoid
    race conditions in parallel test execution.
    """
    client = None
    try:
        client = TestClient(app)
        yield client
    finally:
        if client:
            client.close()


@pytest.fixture
def mock_claimset():
    """Provides a mock claimset for simulating an authenticated user."""
    return {
        "sub": str(uuid4()),
        "email": "test-overlay-user@example.com",
        "preferred_username": "test-overlay-user",
        "realm_access": {"roles": [Roles.TEAM_MEMBER.value]},
    }


@pytest.fixture
def mock_platform_admin_claimset():
    """Provides a mock claimset for simulating an authenticated super admin."""
    return {
        "sub": str(uuid4()),
        "email": "test-overlay-user@example.com",
        "preferred_username": "test-overlay-user",
        "realm_access": {"roles": [Roles.PLATFORM_ADMINISTRATOR.value]},
    }


@pytest.fixture
def mock_regular_user_claimset():
    """Provides a mock claimset for simulating a regular user (non-admin)."""
    return {
        "sub": str(uuid4()),
        "email": "regular-user@example.com",
        "preferred_username": "regular-user",
        "realm_access": {"roles": [Roles.TEAM_MEMBER.value]},
    }
