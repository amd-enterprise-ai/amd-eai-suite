# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import json
import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import docker
import httpx
import pytest
import pytest_asyncio
from fastapi import Request
from filelock import FileLock
from prometheus_api_client import PrometheusConnect
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential
from testcontainers.postgres import PostgresContainer

from api_common.database import create_engine
from api_common.models import BaseEntity
from app.minio import MinioClient

# Test database configuration
TEST_DB_USER = "postgres"
TEST_DB_PASSWORD = "postgres"
TEST_DB_NAME_PREFIX = "aiwb_test"


def _get_session_tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
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


def cleanup_containers(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Clean up testcontainers to prevent resource leaks."""
    docker_client = docker.from_env()
    base_path = _get_session_tmp_path(tmp_path_factory)

    for container_file in base_path.rglob("*_container.json"):
        try:
            container_info = json.loads(container_file.read_text())
            containers = docker_client.containers.list(filters={"id": container_info["container_id"]})

            if containers:
                for container in containers:
                    container.stop()
                    container.wait()
                    container.remove(force=True, v=True)

            container_file.unlink(missing_ok=True)
        except Exception:
            # Cleanup failures shouldn't break tests
            pass


def pytest_sessionstart(session: pytest.Session) -> None:
    """Clean up containers before session starts."""
    if not hasattr(session.config, "workerinput"):
        cleanup_containers(session.config._tmp_path_factory)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clean up containers after session finishes."""
    if not hasattr(session.config, "workerinput"):
        cleanup_containers(session.config._tmp_path_factory)


@pytest.fixture(autouse=True)
def global_init_dependencies(monkeypatch):
    """Patch app startup dependencies to prevent external service connections during tests."""
    # Set dummy env vars to prevent startup errors
    monkeypatch.setenv("PROMETHEUS_URL", "http://dummy-prometheus-server.com")

    # Create an AsyncMock for kube_client that can be awaited during shutdown
    mock_kube_client = AsyncMock()

    with (
        patch("app.init_db", autospec=True),
        patch("app.load_k8s_config", autospec=True),
        patch("app.init_kube_client", return_value=mock_kube_client),
        patch("app.start_pollers", autospec=True),
        patch("app.init_prometheus_client") as mock_init_prometheus,
        patch("app.init_loki_client") as mock_init_loki,
    ):
        # Ensure the mock returns a MagicMock that can be used as if it's a PrometheusConnect client
        mock_init_prometheus.return_value = MagicMock(spec=PrometheusConnect)
        # Ensure the mock returns a properly configured Loki client
        mock_init_loki.return_value = MagicMock(spec=httpx.AsyncClient)
        yield


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5), stop=stop_after_attempt(5), reraise=True)
async def _connect_to_postgres(host: str, port: int) -> asyncpg.Connection:
    """Connect to postgres default database with retry logic."""
    return await asyncpg.connect(f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{host}:{port}/postgres", timeout=10)


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5), stop=stop_after_attempt(5), reraise=True)
async def _create_engine_with_schema(database_url: str) -> tuple:
    """Create database engine and schema with retry logic."""
    engine, session_local = create_engine(database_url)
    # Create schema
    async with engine.begin() as conn:
        await conn.run_sync(BaseEntity.metadata.create_all)
    return engine, session_local


def _coordinate_container_across_workers(
    tmp_path_factory: Any,
    worker_id: str,
    container_name: str,
    setup_fn: Any,
) -> tuple[Any, dict[str, Any]]:
    """Coordinate container startup across pytest-xdist workers."""
    fn = tmp_path_factory.getbasetemp().parent / f"{container_name}.json"

    if worker_id == "master":
        # Not running with xdist, start container normally
        container, container_info = setup_fn()
        fn.write_text(json.dumps(container_info))
        return container, container_info
    else:
        # Running with xdist - coordinate via lockfile
        lock_fn = tmp_path_factory.getbasetemp().parent / f"{container_name}.lock"
        with FileLock(str(lock_fn)):
            if not fn.exists():
                # First worker to acquire lock starts the container
                container, container_info = setup_fn()
                fn.write_text(json.dumps(container_info))
                return container, container_info
            else:
                # Subsequent workers read container info
                container_info = json.loads(fn.read_text())
                return None, container_info


@pytest.fixture(scope="session")
def postgres_container(tmp_path_factory: Any, worker_id: str) -> Generator[dict[str, Any]]:
    """Start PostgreSQL container (shared across all workers)."""

    def setup_postgres():
        container = PostgresContainer(
            image="postgres:17",
            username=TEST_DB_USER,
            password=TEST_DB_PASSWORD,
        )
        container.start()
        container_info = {
            "host": container.get_container_host_ip(),
            "port": container.get_exposed_port(5432),
            "container_id": container.get_wrapped_container().id,
        }
        return container, container_info

    container, info = _coordinate_container_across_workers(
        tmp_path_factory, worker_id, "postgres_container", setup_postgres
    )

    yield info

    # Only the process that created the container should stop it
    if container is not None:
        container.stop()


@pytest.fixture(scope="session")
def database_url(postgres_container: dict[str, Any], worker_id: str) -> Generator[str]:
    """Get database URL for worker-specific database."""

    host = postgres_container["host"]
    port = postgres_container["port"]

    # Each worker gets its own database
    db_name = f"{TEST_DB_NAME_PREFIX}_{worker_id}" if worker_id != "master" else TEST_DB_NAME_PREFIX

    # Create database
    async def create_db():
        conn = None
        try:
            conn = await _connect_to_postgres(host, port)
            await conn.execute(f"DROP DATABASE IF EXISTS {db_name}")
            await conn.execute(f"CREATE DATABASE {db_name}")
        except (asyncpg.exceptions.ConnectionDoesNotExistError, OSError, ConnectionRefusedError) as e:
            raise RuntimeError(f"Failed to connect to PostgreSQL container during database setup: {e}")
        finally:
            if conn is not None:
                try:
                    if not conn.is_closed():
                        await conn.close()
                except (asyncpg.exceptions.ConnectionDoesNotExistError, AttributeError):
                    pass

    asyncio.run(create_db())

    url = f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{host}:{port}/{db_name}"

    yield url

    # Cleanup database
    async def cleanup_db():
        conn = None
        try:
            conn = await _connect_to_postgres(host, port)
        except Exception:
            # Any connection failure during cleanup should be silent - container may be stopped
            # Database cleanup will be handled by container cleanup hooks
            return

        try:
            # Terminate other connections to this database
            await conn.execute(
                f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_name}'
                AND pid <> pg_backend_pid()
                """
            )
            # Drop the database
            await conn.execute(f"DROP DATABASE IF EXISTS {db_name}")
        except (asyncpg.exceptions.ConnectionDoesNotExistError, asyncpg.exceptions.InvalidCatalogNameError):
            # Connection was terminated during cleanup or database already dropped
            # This can happen in parallel test execution
            pass
        except Exception:
            # Suppress all other cleanup errors to avoid masking test failures
            pass
        finally:
            if conn is not None:
                try:
                    if not conn.is_closed():
                        await conn.close()
                except Exception:
                    # Suppress all connection close errors during cleanup
                    pass

    asyncio.run(cleanup_db())


@pytest_asyncio.fixture
async def engine_and_session_maker(database_url: str) -> AsyncGenerator[tuple[Any, Any]]:
    """
    Create database engine and session maker for tests.

    Note: This is function-scoped rather than session-scoped due to pytest-asyncio
    limitations with async session fixtures. While this recreates the engine per test,
    it ensures proper event loop integration and avoids "Task attached to different loop"
    errors. The performance impact is acceptable for the test suite size.

    Alternative approaches (session-scoped with asyncio.run) cause event loop conflicts
    between the fixture setup and pytest-asyncio's test execution.
    """
    engine, session_local = await _create_engine_with_schema(database_url)

    yield engine, session_local

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine_and_session_maker: tuple[Any, Any]) -> AsyncGenerator[AsyncSession]:
    """
    Provide a transactional database session for each test.

    Uses nested transactions (savepoints) to isolate tests. Each test gets a clean
    database state through automatic rollback after the test completes.

    Architecture:
    1. Creates a new session from the session factory
    2. Begins a transaction
    3. Creates a nested transaction (savepoint) for test isolation
    4. Yields the session to the test
    5. Rolls back the savepoint after the test (discards all changes)

    This pattern ensures:
    - Test isolation: Changes don't leak between tests
    - Performance: Uses transactions instead of recreating schema
    - Simplicity: Tests just use db_session without cleanup code
    """
    engine, session_local = engine_and_session_maker

    async with session_local() as session:
        async with session.begin():
            # Savepoint provides test isolation
            await session.begin_nested()

            yield session

            # Automatic rollback ensures test isolation
            await session.rollback()


@pytest.fixture
def test_namespace() -> str:
    """Provide a test namespace name."""
    return "test-namespace"


@pytest.fixture
def test_user() -> str:
    """Provide a test user email."""
    return "test@example.com"


@pytest.fixture
def mock_cluster_auth_client():  # type: ignore[misc]
    """
    Mock ClusterAuthClient for testing API key service functions.

    Provides AsyncMock instance with common response patterns for cluster-auth operations.
    Tests should configure return values for specific method calls as needed.
    """

    mock = AsyncMock()

    # Default responses for common operations
    mock.create_api_key.return_value = {
        "api_key": "amd_aim_api_key_hvs.abc123def456",
        "key_id": "test-key-id-123",
    }

    mock.lookup_api_key.return_value = {
        "ttl": "24h",
        "expire_time": "2025-01-16T12:00:00Z",
        "renewable": True,
        "num_uses": 0,
        "groups": [],
        "entity_id": "test-entity-id",
        "meta": {},
    }

    mock.revoke_api_key.return_value = {"status": "revoked"}
    mock.renew_api_key.return_value = {"lease_duration": 86400}
    mock.bind_api_key_to_group.return_value = {"groups": ["test-group"]}
    mock.unbind_api_key_from_group.return_value = {"groups": []}
    mock.create_group.return_value = {"id": "test-group-id", "name": "test-group"}
    mock.delete_group.return_value = {"status": "deleted"}

    return mock


@pytest.fixture
def mock_kube_client():  # type: ignore[misc]
    """
    Mock KubernetesClient for testing secrets service functions.

    Provides AsyncMock instance with common response patterns for K8s operations.
    Tests should configure return values for specific method calls as needed.
    """

    mock = AsyncMock()

    # Mock core_v1 API for native K8s secrets
    mock.core_v1 = MagicMock()
    mock.core_v1.create_namespaced_secret = MagicMock()
    mock.core_v1.replace_namespaced_secret = MagicMock()
    mock.core_v1.delete_namespaced_secret = MagicMock()

    # Mock custom_objects API for CRDs (ExternalSecrets)
    mock.create_crd.return_value = None
    mock.delete_crd.return_value = None

    return mock


@pytest.fixture
def mock_kube_api_client():  # type: ignore[misc]
    """
    Mock KubeAPIClient for testing gateway and syncer functions.

    Provides Mock instance with common response patterns for K8s API operations.
    Tests should configure return values for specific method calls as needed.
    """

    mock = MagicMock()

    # Mock core_v1 API
    mock.core_v1 = MagicMock()
    mock.core_v1.list_namespaced_secret.return_value = MagicMock(items=[])

    # Mock custom_objects API
    mock.custom_objects = MagicMock()
    mock.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

    # Mock namespace discovery
    mock.get_namespaces_with_label.return_value = []

    return mock


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session for unit tests.

    This is a lightweight mock for testing service functions without a real database.
    For integration tests that need a real database, use the 'db_session' fixture instead.
    """
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_prometheus_client() -> MagicMock:
    """Create a mock Prometheus client for unit tests.

    Provides a mock PrometheusConnect instance for testing metrics-related functions.
    Tests should configure return values for specific query methods as needed.
    """
    mock = MagicMock()
    mock.custom_query = MagicMock(return_value=[])
    mock.custom_query_range = MagicMock(return_value=[])
    return mock


@pytest.fixture
def minio_environment(monkeypatch):
    """Set up necessary environment variables for MinIO testing."""
    monkeypatch.setattr("app.minio.config.MINIO_ACCESS_KEY", "test-access-key")
    monkeypatch.setattr("app.minio.config.MINIO_URL", "http://localhost:9000")
    monkeypatch.setattr("app.minio.config.MINIO_SECRET_KEY", "test-secret-key")
    monkeypatch.setattr("app.minio.config.MINIO_BUCKET", "test-bucket")
    monkeypatch.setattr("app.datasets.config.DATASETS_PATH", "test-bucket/datasets")
    return monkeypatch


@pytest.fixture
def mock_minio_client():
    """Create a mock MinioClient for testing."""
    client = MagicMock(spec=MinioClient)
    client.upload_object = MagicMock()
    client.download_object = MagicMock(return_value=b'{"text": "test"}\n{"text": "test2"}')
    client.client.stat_object = MagicMock(return_value=MagicMock(size=len(b'{"text": "test"}\n{"text": "test2"}')))
    return client


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock FastAPI Request for testing service functions that accept requests."""
    return MagicMock(spec=Request)
