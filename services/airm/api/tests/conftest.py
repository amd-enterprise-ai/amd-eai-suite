# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import json
import os
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import asyncpg
import docker
import httpx
import pytest  # Added for monkeypatch
import pytest_asyncio
from fastapi.testclient import TestClient
from filelock import FileLock
from keycloak import KeycloakAdmin
from loguru import logger
from prometheus_api_client import PrometheusConnect
from tenacity import retry, stop_after_attempt, wait_exponential
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

from app import app  # type: ignore
from app.utilities.database import create_engine
from app.utilities.models import BaseEntity
from app.utilities.security import Roles, create_logged_in_user_in_system, track_user_activity_from_token

# Set Loki configuration before any module imports
os.environ.setdefault("LOKI_KEEPALIVE_TIMEOUT_SECONDS", "1")

# Mock cluster auth service configuration
MOCK_CLUSTER_AUTH_PORT = 48012
MOCK_CLUSTER_AUTH_READY_LOG_PATTERN = rf"Uvicorn running on http://0\.0\.0\.0:{MOCK_CLUSTER_AUTH_PORT}"
MOCK_CLUSTER_AUTH_STARTUP_TIMEOUT = 30


@retry(
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def _connect_to_postgres(host: str, port: int) -> asyncpg.Connection:
    """Connect to postgres default database with retry logic for parallel test startup."""
    return await asyncpg.connect(f"postgresql://postgres:postgres@{host}:{port}/postgres", timeout=10)


@retry(
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2.5),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def _create_engine_with_schema(database_url: str):
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


def pytest_configure(config):
    """Configure pytest hooks."""
    # Testcontainers handles automatic container cleanup
    pass


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
    from sqlalchemy.exc import PendingRollbackError

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
def worker_id(request):
    """
    Provide unique worker ID for pytest-xdist parallel testing.

    When running with pytest-xdist, this returns the worker ID (e.g., 'gw0', 'gw1').
    When running normally (single process), this returns 'main' for consistency.
    """
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workerid"]
    else:
        return "main"


@pytest.fixture(scope="session")
def postgres_container(tmp_path_factory, worker_id):
    """Start Postgres container using testcontainers (shared across xdist workers)."""
    if worker_id == "master":
        # Not running with xdist, start container normally
        with PostgresContainer("postgres:17", username="postgres", password="postgres", dbname="postgres") as postgres:
            yield postgres
    else:
        # Running with xdist - coordinate across workers
        root_tmp_dir = tmp_path_factory.getbasetemp().parent
        fn = root_tmp_dir / "postgres_container.json"

        with FileLock(str(fn) + ".lock"):
            if fn.is_file():
                # Another worker already started the container
                container_info = json.loads(fn.read_text())
            else:
                # First worker - start container and save info
                container = PostgresContainer(
                    "postgres:17", username="postgres", password="postgres", dbname="postgres"
                )
                container.start()
                container_info = {
                    "host": container.get_container_host_ip(),
                    "port": int(container.get_exposed_port(5432)),
                    "container_id": container._container.id,
                }
                fn.write_text(json.dumps(container_info))

        yield container_info


@pytest.fixture
def postgres_service(postgres_container):
    """Ensure that Postgres service is up and responsive."""
    if isinstance(postgres_container, dict):
        # Worker received container info
        return postgres_container["host"], postgres_container["port"]
    else:
        # Master has actual container object
        host = postgres_container.get_container_host_ip()
        port = int(postgres_container.get_exposed_port(5432))
        return host, port


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
        patch("app.init_loki_client") as mock_init_loki,
    ):
        # Ensure the mock returns a MagicMock that can be used as if it's a KeycloakAdmin client
        mock_init_kc.return_value = MagicMock(spec=KeycloakAdmin)
        # Ensure the mock returns a MagicMock that can be used as if it's a PrometheusConnect client
        mock_init_prometheus.return_value = MagicMock(spec=PrometheusConnect)
        # Ensure the mock returns a properly configured Loki client
        mock_init_loki.return_value = MagicMock(spec=httpx.AsyncClient)
        yield


@pytest_asyncio.fixture
async def db_session(postgres_service, worker_id):
    """
    Create a session with automatic transaction handling like production.

    Supports parallel testing via pytest-xdist by creating separate databases
    per worker process. Each worker gets its own isolated database instance.

    This fixture provides the same transaction behavior as the production session_scope():
    - Automatic commit on successful operations
    - Automatic rollback on exceptions (including IntegrityError)
    - Proper session cleanup

    This eliminates the need for manual transaction management in tests.
    """
    host, port = postgres_service

    # Create unique database name per worker for parallel testing
    db_name = f"airm_test_{worker_id}"
    base_database_url = f"postgresql+asyncpg://postgres:postgres@{host}:{port}"
    database_url = f"{base_database_url}/{db_name}"

    # Add small delay to stagger worker startup and reduce connection contention
    if worker_id != "main":
        worker_num = int(worker_id.replace("gw", "")) if worker_id.startswith("gw") else 0
        await asyncio.sleep(worker_num * 0.1)  # 0.1s delay per worker

    # Create the database for this worker
    # Connect to postgres default database to create worker-specific database
    conn = await _connect_to_postgres(host, port)

    try:
        # Drop database if it exists (cleanup from previous runs)
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        # Create fresh database for this worker
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()

    # Now connect to the worker-specific database with retry logic
    #
    # Connection pool design for tests:
    # - Uses QueuePool (default) rather than StaticPool for database-per-worker setup
    # - QueuePool provides connection health monitoring and transaction isolation
    # - StaticPool would use single persistent connection but lacks resilience features
    # - Each worker gets isolated database, so pool overhead is minimal vs benefits
    # - Mirrors production connection behavior for more realistic testing
    #
    # Reference: https://docs.sqlalchemy.org/en/20/core/pooling.html#sqlalchemy.pool.StaticPool
    engine, session_local = await _create_engine_with_schema(database_url)

    # Use test_session_scope for automatic transaction handling
    async with test_session_scope(session_local) as session:
        yield session

    # Cleanup database schema after session is fully closed
    async with engine.begin() as conn:
        await conn.run_sync(BaseEntity.metadata.drop_all)
    await engine.dispose()

    # Drop the worker-specific database after tests complete
    conn = await _connect_to_postgres_for_cleanup(host, port)
    if conn is None:
        return  # Cleanup connection failed, already logged

    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    finally:
        await conn.close()


@contextmanager
def get_test_client():
    """Create a clean TestClient for each test and ensure proper cleanup.
    This context manager guarantees that the TestClient is properly closed
    and all dependency overrides are cleared, regardless of whether an exception occurs.
    """
    client = None
    try:
        client = TestClient(app)
        yield client
    finally:
        if client:
            client.close()
        # Ensure all overrides are cleared
        app.dependency_overrides.clear()


@pytest.fixture
def mock_claimset():
    """Provides a mock claimset for simulating an authenticated user."""
    return {
        "sub": str(uuid4()),
        "email": "test-overlay-user@example.com",
        "preferred_username": "test-overlay-user",
        "realm_access": {"roles": [Roles.TEAM_MEMBER.value]},
        "organization": [{"test-overlay-org": {"id": str(uuid4())}}, "test-overlay-org"],
    }


@pytest.fixture
def mock_super_admin_claimset():
    """Provides a mock claimset for simulating an authenticated super admin."""
    return {
        "sub": str(uuid4()),
        "email": "test-overlay-user@example.com",
        "preferred_username": "test-overlay-user",
        "realm_access": {"roles": [Roles.SUPER_ADMINISTRATOR.value]},
        "organization": [{"test-overlay-org": {"id": str(uuid4())}}, "test-overlay-org"],
    }


@pytest.fixture(scope="session")
def mock_cluster_auth_container(tmp_path_factory, worker_id):
    """Start mock-cluster-auth service using DockerContainer (shared across xdist workers)."""
    if worker_id == "master":
        # Not running with xdist, start container normally
        docker_client = docker.from_env()
        build_context = Path(__file__).resolve().parent.parent.parent.parent.parent / "tooling" / "mock-cluster-auth"

        if not build_context.exists():
            raise FileNotFoundError(f"Build context not found: {build_context}")

        # Build image with a unique tag
        image_tag = f"mock-cluster-auth-test:{os.getpid()}"
        docker_client.images.build(
            path=str(build_context),
            dockerfile="Dockerfile",
            tag=image_tag,
            rm=True,
        )

        # Use DockerContainer with the built image
        container = (
            DockerContainer(image_tag)
            .with_exposed_ports(MOCK_CLUSTER_AUTH_PORT)
            .with_env("ADMIN_TOKEN", "mock-admin-token")
            .with_env("LOG_LEVEL", "INFO")
        )

        with container as mock:
            # Wait for Uvicorn to be ready via log message
            wait_for_logs(mock, MOCK_CLUSTER_AUTH_READY_LOG_PATTERN, timeout=MOCK_CLUSTER_AUTH_STARTUP_TIMEOUT)
            yield mock

        # Clean up the built image
        try:
            docker_client.images.remove(image_tag, force=True)
        except Exception:
            pass
    else:
        # Running with xdist - coordinate across workers
        root_tmp_dir = tmp_path_factory.getbasetemp().parent
        fn = root_tmp_dir / "mock_cluster_auth_container.json"

        with FileLock(str(fn) + ".lock"):
            if fn.is_file():
                # Another worker already started the container
                container_info = json.loads(fn.read_text())
            else:
                # First worker - build image and start container
                docker_client = docker.from_env()
                build_context = (
                    Path(__file__).resolve().parent.parent.parent.parent.parent / "tooling" / "mock-cluster-auth"
                )

                if not build_context.exists():
                    raise FileNotFoundError(f"Build context not found: {build_context}")

                # Build image with a unique tag for this test session
                image_tag = f"mock-cluster-auth-test:{os.getpid()}"
                docker_client.images.build(
                    path=str(build_context),
                    dockerfile="Dockerfile",
                    tag=image_tag,
                    rm=True,
                )

                # Use DockerContainer with the built image
                container = (
                    DockerContainer(image_tag)
                    .with_exposed_ports(MOCK_CLUSTER_AUTH_PORT)
                    .with_env("ADMIN_TOKEN", "mock-admin-token")
                    .with_env("LOG_LEVEL", "INFO")
                )
                container.start()

                # Wait for Uvicorn to be ready via log message
                wait_for_logs(container, MOCK_CLUSTER_AUTH_READY_LOG_PATTERN, timeout=MOCK_CLUSTER_AUTH_STARTUP_TIMEOUT)

                host = container.get_container_host_ip()
                port = int(container.get_exposed_port(MOCK_CLUSTER_AUTH_PORT))

                container_info = {
                    "host": host,
                    "port": port,
                    "container_id": container._container.id,
                    "image_tag": image_tag,
                }
                fn.write_text(json.dumps(container_info))

        yield container_info


@pytest.fixture
def mock_cluster_auth_service(mock_cluster_auth_container):
    """Get the mock-cluster-auth service URL from DockerContainer."""
    if isinstance(mock_cluster_auth_container, dict):
        # Worker received container info
        return f"http://{mock_cluster_auth_container['host']}:{mock_cluster_auth_container['port']}"
    else:
        # Master has actual container object
        host = mock_cluster_auth_container.get_container_host_ip()
        port = int(mock_cluster_auth_container.get_exposed_port(MOCK_CLUSTER_AUTH_PORT))
        return f"http://{host}:{port}"


@pytest_asyncio.fixture
async def mock_cluster_auth_client(mock_cluster_auth_service):
    """Create a ClusterAuthClient pointing to the testcontainers mock-cluster-auth service."""
    from app.apikeys.cluster_auth_client import ClusterAuthClient

    client = ClusterAuthClient(base_url=mock_cluster_auth_service, admin_token="mock-admin-token")
    yield client
    await client.close()
