# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for Kubernetes client."""

import threading
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kubernetes_asyncio.client import ApiClient, ApiException, CoreV1Event, CoreV1EventList

import app.dispatch.kube_client as kc_module
from app.dispatch.kube_client import (
    KubernetesClient,
    close_dynamic_client,
    get_dynamic_client,
    get_kube_client,
    init_kube_client,
)


@pytest.fixture
def mock_api_client():
    """Mock kubernetes_asyncio ApiClient."""
    with patch("app.dispatch.kube_client.client.ApiClient") as mock:
        mock_instance = MagicMock(spec=ApiClient)
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def kube_client(mock_api_client):
    """Create KubernetesClient instance."""
    return KubernetesClient()


# =============================================================================
# KubernetesClient tests
# =============================================================================


def test_kube_client_initialization(kube_client, mock_api_client):
    """Test KubernetesClient initialization creates all API clients."""
    assert kube_client._api_client == mock_api_client
    assert kube_client.core_v1 is not None
    assert kube_client.custom_objects is not None
    assert kube_client.api_extensions is not None


@pytest.mark.asyncio
async def test_kube_client_close(kube_client, mock_api_client):
    """Test closing the client."""
    mock_api_client.close = AsyncMock()
    await kube_client.close()
    mock_api_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_kube_client_check_required_crds_all_present(kube_client):
    """Test check_required_crds succeeds when all CRDs are present."""
    kube_client.api_extensions.read_custom_resource_definition = AsyncMock()

    await kube_client.check_required_crds()

    # Should have checked all required CRDs
    assert kube_client.api_extensions.read_custom_resource_definition.call_count > 0


@pytest.mark.asyncio
async def test_kube_client_check_required_crds_missing(kube_client):
    """Test check_required_crds exits when CRDs are missing."""
    kube_client.api_extensions.read_custom_resource_definition = AsyncMock(
        side_effect=ApiException(status=404, reason="Not Found")
    )

    with pytest.raises(SystemExit):
        await kube_client.check_required_crds()


@pytest.mark.asyncio
async def test_kube_client_check_required_crds_api_error(kube_client):
    """Test check_required_crds raises on API errors."""
    kube_client.api_extensions.read_custom_resource_definition = AsyncMock(
        side_effect=ApiException(status=500, reason="Internal Server Error")
    )

    with pytest.raises(ApiException):
        await kube_client.check_required_crds()


@pytest.mark.asyncio
async def test_kube_client_get_namespaced_custom_object_success(kube_client):
    """Test getting a custom object successfully."""
    expected_obj = {"metadata": {"name": "test-obj"}, "spec": {}}
    kube_client.custom_objects.get_namespaced_custom_object = AsyncMock(return_value=expected_obj)

    result = await kube_client.get_namespaced_custom_object(
        group="example.com", version="v1", plural="testobjects", namespace="default", name="test-obj"
    )

    assert result == expected_obj
    kube_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
        group="example.com", version="v1", namespace="default", plural="testobjects", name="test-obj"
    )


@pytest.mark.asyncio
async def test_kube_client_get_namespaced_custom_object_not_found(kube_client):
    """Test getting a custom object that doesn't exist returns None."""
    kube_client.custom_objects.get_namespaced_custom_object = AsyncMock(
        side_effect=ApiException(status=404, reason="Not Found")
    )

    result = await kube_client.get_namespaced_custom_object(
        group="example.com", version="v1", plural="testobjects", namespace="default", name="missing-obj"
    )

    assert result is None


@pytest.mark.asyncio
async def test_kube_client_get_namespaced_custom_object_error(kube_client):
    """Test getting a custom object with API error raises."""
    kube_client.custom_objects.get_namespaced_custom_object = AsyncMock(
        side_effect=ApiException(status=500, reason="Internal Server Error")
    )

    with pytest.raises(ApiException):
        await kube_client.get_namespaced_custom_object(
            group="example.com", version="v1", plural="testobjects", namespace="default", name="test-obj"
        )


@pytest.mark.asyncio
async def test_kube_client_get_events_for_resource(kube_client):
    """Test getting events for a resource."""
    mock_event = MagicMock(spec=CoreV1Event)
    mock_event.involved_object.name = "test-pod"
    mock_event.involved_object.kind = "Pod"
    mock_event.type = "Normal"
    mock_event.reason = "Started"
    mock_event.message = "Container started"
    mock_event.last_timestamp = datetime.now(UTC)
    mock_event.event_time = None
    mock_event.count = 1
    mock_event.source.component = "kubelet"

    mock_list = MagicMock(spec=CoreV1EventList)
    mock_list.items = [mock_event]

    kube_client.core_v1.list_namespaced_event = AsyncMock(return_value=mock_list)

    events = await kube_client.get_events_for_resource(namespace="default", resource_name="test-pod")

    assert len(events) == 1
    assert events[0]["type"] == "Normal"
    assert events[0]["reason"] == "Started"
    assert events[0]["message"] == "Container started"
    assert events[0]["count"] == 1


@pytest.mark.asyncio
async def test_kube_client_get_events_for_resource_with_kind_filter(kube_client):
    """Test getting events with kind filter."""
    mock_pod_event = MagicMock(spec=CoreV1Event)
    mock_pod_event.involved_object.name = "test-resource"
    mock_pod_event.involved_object.kind = "Pod"
    mock_pod_event.type = "Normal"
    mock_pod_event.reason = "Started"
    mock_pod_event.message = "Pod started"
    mock_pod_event.last_timestamp = None
    mock_pod_event.event_time = None
    mock_pod_event.count = 1
    mock_pod_event.source = None

    mock_job_event = MagicMock(spec=CoreV1Event)
    mock_job_event.involved_object.name = "test-resource"
    mock_job_event.involved_object.kind = "Job"
    mock_job_event.type = "Normal"
    mock_job_event.reason = "Created"
    mock_job_event.message = "Job created"
    mock_job_event.last_timestamp = None
    mock_job_event.event_time = None
    mock_job_event.count = 1
    mock_job_event.source = None

    mock_list = MagicMock(spec=CoreV1EventList)
    mock_list.items = [mock_pod_event, mock_job_event]

    kube_client.core_v1.list_namespaced_event = AsyncMock(return_value=mock_list)

    # Filter for Pod events only
    events = await kube_client.get_events_for_resource(
        namespace="default", resource_name="test-resource", resource_kind="Pod"
    )

    assert len(events) == 1
    assert events[0]["reason"] == "Started"


@pytest.mark.asyncio
async def test_kube_client_get_events_for_resource_api_error(kube_client):
    """Test getting events returns empty list on API error."""
    kube_client.core_v1.list_namespaced_event = AsyncMock(
        side_effect=ApiException(status=500, reason="Internal Server Error")
    )

    events = await kube_client.get_events_for_resource(namespace="default", resource_name="test-pod")

    assert events == []


# =============================================================================
# Global client management tests
# =============================================================================


def test_get_kube_client_not_initialized():
    """Test get_kube_client raises when not initialized."""
    # Reset global client
    kc_module._kube_client = None

    with pytest.raises(RuntimeError, match="not initialized"):
        get_kube_client()


@pytest.mark.asyncio
@patch("app.dispatch.kube_client.KubernetesClient")
async def test_init_kube_client_success(mock_kube_client_class):
    """Test init_kube_client creates and caches client."""
    mock_client = MagicMock(spec=KubernetesClient)
    mock_client.check_required_crds = AsyncMock()
    mock_kube_client_class.return_value = mock_client

    result = await init_kube_client()

    assert result == mock_client
    mock_client.check_required_crds.assert_called_once()


@pytest.mark.asyncio
@patch("app.dispatch.kube_client.KubernetesClient")
async def test_init_kube_client_system_exit(mock_kube_client_class):
    """Test init_kube_client propagates SystemExit from CRD check."""
    mock_client = MagicMock(spec=KubernetesClient)
    mock_client.check_required_crds = AsyncMock(side_effect=SystemExit(1))
    mock_kube_client_class.return_value = mock_client

    with pytest.raises(SystemExit):
        await init_kube_client()


@pytest.mark.asyncio
@patch("app.dispatch.kube_client.KubernetesClient")
async def test_init_kube_client_error(mock_kube_client_class):
    """Test init_kube_client propagates exceptions on failure."""
    mock_kube_client_class.side_effect = Exception("Connection failed")

    with pytest.raises(Exception, match="Connection failed"):
        await init_kube_client()


@patch("app.dispatch.kube_client.sync_config.load_kube_config")
@patch("app.dispatch.kube_client.sync_client.ApiClient")
@patch("app.dispatch.kube_client.dynamic.DynamicClient")
def test_get_dynamic_client_local_context(mock_dynamic, mock_api_client, mock_load_config):
    """Test get_dynamic_client with local context."""
    # Reset global state
    kc_module._dynamic_client = None
    kc_module._sync_api_client = None

    with patch.object(kc_module, "USE_LOCAL_KUBE_CONTEXT", True):
        client = get_dynamic_client()

    mock_load_config.assert_called_once()
    mock_dynamic.assert_called_once()
    assert client is not None


@patch("app.dispatch.kube_client.sync_config.load_incluster_config")
@patch("app.dispatch.kube_client.sync_client.ApiClient")
@patch("app.dispatch.kube_client.dynamic.DynamicClient")
def test_get_dynamic_client_in_cluster(mock_dynamic, mock_api_client, mock_load_config):
    """Test get_dynamic_client with in-cluster config."""
    # Reset global state
    kc_module._dynamic_client = None
    kc_module._sync_api_client = None

    with patch.object(kc_module, "USE_LOCAL_KUBE_CONTEXT", False):
        client = get_dynamic_client()

    mock_load_config.assert_called_once()
    mock_dynamic.assert_called_once()
    assert client is not None


@patch("app.dispatch.kube_client.sync_config.load_incluster_config")
@patch("app.dispatch.kube_client.sync_client.ApiClient")
@patch("app.dispatch.kube_client.dynamic.DynamicClient")
def test_get_dynamic_client_cached(mock_dynamic, mock_api_client, mock_load_config):
    """Test get_dynamic_client returns cached instance."""
    # Reset and create first instance
    kc_module._dynamic_client = None
    kc_module._sync_api_client = None

    with patch.object(kc_module, "USE_LOCAL_KUBE_CONTEXT", False):
        client1 = get_dynamic_client()
        client2 = get_dynamic_client()

    # Should only load config once
    assert mock_load_config.call_count == 1
    assert client1 is client2


def test_close_dynamic_client_when_not_initialized():
    """Test close_dynamic_client does nothing when client is not initialized."""
    kc_module._sync_api_client = None

    # Should not raise
    close_dynamic_client()


def test_close_dynamic_client_closes_api_client():
    """Test close_dynamic_client closes the sync API client."""
    mock_api_client = MagicMock(spec=ApiClient)
    kc_module._sync_api_client = mock_api_client

    close_dynamic_client()

    mock_api_client.close.assert_called_once()


def test_close_dynamic_client_handles_error():
    """Test close_dynamic_client handles errors gracefully."""
    mock_api_client = MagicMock(spec=ApiClient)
    mock_api_client.close.side_effect = Exception("Connection error")
    kc_module._sync_api_client = mock_api_client

    # Should not raise
    close_dynamic_client()


# =============================================================================
# Concurrent access tests for dynamic client
# =============================================================================


@patch("app.dispatch.kube_client.sync_config.load_incluster_config")
@patch("app.dispatch.kube_client.sync_client.ApiClient")
@patch("app.dispatch.kube_client.dynamic.DynamicClient")
def test_get_dynamic_client_concurrent_access_thread_safe(mock_dynamic, mock_api_client, mock_load_config):
    """Test get_dynamic_client is thread-safe under concurrent access."""

    # Reset global state
    kc_module._dynamic_client = None
    kc_module._sync_api_client = None

    mock_client = MagicMock()
    mock_dynamic.return_value = mock_client

    results = []
    errors = []

    def get_client():
        try:
            client = get_dynamic_client()
            results.append(client)
        except Exception as e:
            errors.append(e)

    # Create multiple threads that try to get the client simultaneously
    threads = [threading.Thread(target=get_client) for _ in range(10)]

    with patch.object(kc_module, "USE_LOCAL_KUBE_CONTEXT", False):
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    # All threads should succeed
    assert len(errors) == 0
    assert len(results) == 10

    # All threads should get the same client instance (cached)
    assert all(client is results[0] for client in results)

    # Config should only be loaded once (thread-safe initialization)
    assert mock_load_config.call_count == 1


@patch("app.dispatch.kube_client.sync_config.load_incluster_config")
@patch("app.dispatch.kube_client.sync_client.ApiClient")
@patch("app.dispatch.kube_client.dynamic.DynamicClient")
def test_get_dynamic_client_concurrent_with_errors(mock_dynamic, mock_api_client, mock_load_config):
    """Test get_dynamic_client handles concurrent access when initialization fails."""

    # Reset global state
    kc_module._dynamic_client = None
    kc_module._sync_api_client = None

    # Make initialization fail
    mock_load_config.side_effect = Exception("Failed to load config")

    errors = []

    def get_client():
        try:
            get_dynamic_client()
        except Exception as e:
            errors.append(type(e).__name__)

    # Create multiple threads
    threads = [threading.Thread(target=get_client) for _ in range(5)]

    with patch.object(kc_module, "USE_LOCAL_KUBE_CONTEXT", False):
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    # All threads should get RuntimeError
    assert len(errors) == 5
    assert all(error == "RuntimeError" for error in errors)


@patch("app.dispatch.kube_client.sync_config.load_kube_config")
@patch("app.dispatch.kube_client.sync_client.ApiClient")
@patch("app.dispatch.kube_client.dynamic.DynamicClient")
def test_get_dynamic_client_race_condition_double_check_locking(mock_dynamic, mock_api_client, mock_load_config):
    """Test get_dynamic_client double-check locking prevents race conditions."""

    # Reset global state
    kc_module._dynamic_client = None
    kc_module._sync_api_client = None

    mock_client = MagicMock()
    mock_dynamic.return_value = mock_client

    initialization_count = 0

    def slow_init(*args, **kwargs):
        nonlocal initialization_count
        initialization_count += 1
        time.sleep(0.01)  # Simulate slow initialization
        return mock_client

    mock_dynamic.side_effect = slow_init

    results = []

    def get_client():
        client = get_dynamic_client()
        results.append(client)

    # Create threads that will hit the initialization path
    threads = [threading.Thread(target=get_client) for _ in range(5)]

    with patch.object(kc_module, "USE_LOCAL_KUBE_CONTEXT", True):
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    # Should only initialize once despite concurrent access
    assert initialization_count == 1
    assert len(results) == 5
    assert all(client is results[0] for client in results)
