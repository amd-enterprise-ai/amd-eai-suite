# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Workload logging service for Loki integration."""

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse
from uuid import UUID

import httpx
import websockets
from fastapi import Request
from loguru import logger

from app.workloads.schemas import WorkloadWithComponents

from .config import LOKI_DEFAULT_TIME_RANGE_DAYS, LOKI_TIMEOUT_SECONDS, LOKI_URL
from .schemas import LogDirectionLiteral, LogEntry, LogLevel, PaginationMetadata, WorkloadLogsResponse

_loki_client: httpx.AsyncClient | None = None


def init_loki_client() -> httpx.AsyncClient:
    """Initialize Loki HTTP client. This will be called at application startup."""
    global _loki_client

    if _loki_client is not None:
        logger.warning("Loki client already initialized")
        return _loki_client

    _loki_client = httpx.AsyncClient(
        base_url=LOKI_URL, timeout=httpx.Timeout(LOKI_TIMEOUT_SECONDS), headers={"Content-Type": "application/json"}
    )

    logger.info(f"Loki client initialized with base URL: {LOKI_URL}")
    return _loki_client


def get_loki_client(request: Request) -> httpx.AsyncClient:
    """FastAPI dependency to get the initialized Loki client from app.state."""
    if not hasattr(request.app.state, "loki_client") or request.app.state.loki_client is None:
        logger.error("Loki client not initialized in app.state.")
        raise RuntimeError("Loki client not available.")
    return request.app.state.loki_client


async def close_loki_client():
    """Close the Loki client. This will be called at application shutdown."""
    global _loki_client
    if _loki_client:
        await _loki_client.aclose()
        _loki_client = None
        logger.info("Loki client closed")


class WebSocketConnectionFactory:
    """Factory for managing WebSocket connections for log streaming.

    Provides connection reuse and proper cleanup for WebSocket connections
    to the Loki tail API endpoint.
    """

    def __init__(self, base_url: str):
        """Initialize the factory with the base URL.

        Args:
            base_url: Base URL for Loki API (e.g., "http://loki:3100")
        """
        self.base_url = base_url
        self._connections: dict[str, websockets.ClientConnection] = {}
        self._connection_lock = asyncio.Lock()

    def _get_connection_key(self, workload_id: UUID, query: str, delay_seconds: int) -> str:
        """Generate a unique key for connection caching.

        Args:
            workload_id: The workload ID
            query: The Loki query string
            delay_seconds: Delay between polls

        Returns:
            String key for this connection configuration
        """
        return f"{workload_id}:{query}:{delay_seconds}"

    async def get_or_create_connection(
        self,
        workload_id: UUID,
        query: str,
        start_time: datetime | None = None,
        delay_seconds: int = 1,
    ) -> websockets.ClientConnection:
        """Get existing or create new WebSocket connection.

        Args:
            workload_id: The workload ID
            query: The Loki query string
            start_time: Optional start time for streaming
            delay_seconds: Delay between polls

        Returns:
            WebSocket connection

        Raises:
            websockets.WebSocketException: If connection fails
        """
        connection_key = self._get_connection_key(workload_id, query, delay_seconds)

        async with self._connection_lock:
            if connection_key in self._connections:
                conn = self._connections[connection_key]

                try:
                    await conn.ping()
                    return conn
                except websockets.ConnectionClosed:
                    del self._connections[connection_key]

            # Create new connection
            ws_url = _build_loki_websocket_url(self.base_url, query, start_time, delay_seconds)
            logger.info(f"Creating new WebSocket connection to: {ws_url}")

            try:
                connection = await websockets.connect(ws_url)
                self._connections[connection_key] = connection
                logger.info(f"Created new WebSocket connection for workload {workload_id}")
                return connection
            except Exception as e:
                logger.error(f"Failed to create WebSocket connection for workload {workload_id}: {e}")
                raise

    async def close_connection(self, workload_id: UUID, query: str, delay_seconds: int = 1):
        """Close a specific WebSocket connection.

        Args:
            workload_id: The workload ID
            query: The Loki query string
            delay_seconds: Delay between polls
        """
        connection_key = self._get_connection_key(workload_id, query, delay_seconds)

        try:
            async with self._connection_lock:
                if connection_key in self._connections:
                    conn = self._connections[connection_key]
                    del self._connections[connection_key]
                    await conn.close()
                    logger.debug(f"Closed WebSocket connection for workload {workload_id}")
        except Exception as e:
            logger.warning(f"Error closing WebSocket connection {connection_key}: {e}")

    async def close_all_connections(self):
        """Close all WebSocket connections. Called during app shutdown."""
        async with self._connection_lock:
            for connection_key, conn in list(self._connections.items()):
                try:
                    await conn.close()
                    logger.debug(f"Closed WebSocket connection: {connection_key}")
                except Exception as e:
                    logger.warning(f"Error closing WebSocket connection {connection_key}: {e}")

            self._connections.clear()
            logger.info("All WebSocket connections closed")


_websocket_factory: WebSocketConnectionFactory | None = None


def init_websocket_factory() -> WebSocketConnectionFactory:
    """Initialize WebSocket connection factory. This will be called at application startup."""
    global _websocket_factory

    if _websocket_factory is not None:
        logger.warning("WebSocket factory already initialized")
        return _websocket_factory

    if LOKI_URL is None:
        raise ValueError("LOKI_URL is not configured")

    _websocket_factory = WebSocketConnectionFactory(LOKI_URL)
    logger.info(f"WebSocket factory initialized with base URL: {LOKI_URL}")
    return _websocket_factory


def get_websocket_factory(request: Request) -> WebSocketConnectionFactory:
    """FastAPI dependency to get the initialized WebSocket factory from app.state."""
    if not hasattr(request.app.state, "websocket_factory") or request.app.state.websocket_factory is None:
        logger.error("WebSocket factory not initialized in app.state.")
        raise RuntimeError("WebSocket factory not available.")
    return request.app.state.websocket_factory


async def close_websocket_factory():
    """Close the WebSocket factory. This will be called at application shutdown."""
    global _websocket_factory
    if _websocket_factory:
        await _websocket_factory.close_all_connections()
        _websocket_factory = None
        logger.info("WebSocket factory closed")


def _parse_and_validate_dates(
    start_date: datetime | None,
    end_date: datetime | None,
    page_token: datetime | None,
    direction: LogDirectionLiteral,
) -> tuple[datetime, datetime]:
    """Parse and validate date parameters, handling pagination tokens and defaults.

    Returns:
        Tuple of (start_date, end_date) if valid, None if invalid range.
    """
    # Handle pagination with page_token
    if page_token is not None:
        if page_token.tzinfo is None:
            page_token = page_token.replace(tzinfo=UTC)

        if direction == "forward":
            # For forward pagination, page_token becomes the new start_date
            start_date = max(page_token, start_date) if start_date else page_token
            if end_date is None:
                end_date = datetime.now(UTC)
        else:
            # For backward pagination, page_token becomes the new end_date
            end_date = min(page_token, end_date) if end_date else page_token
            if start_date is None:
                start_date = datetime.now(UTC) - timedelta(days=LOKI_DEFAULT_TIME_RANGE_DAYS)
    else:
        # Set default time range when no page_token is provided
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=LOKI_DEFAULT_TIME_RANGE_DAYS)

    # Ensure timezone aware dates
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=UTC)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=UTC)

    # Ensure start_date is always before end_date (Loki requirement)
    if start_date >= end_date:
        raise ValueError(f"Invalid time range: start_date ({start_date}) >= end_date ({end_date})")

    return start_date, end_date


def _build_loki_query(component_names: set[str], level_filter: LogLevel | None = None) -> str:
    """Build LogQL query string for the given component and optional level filter."""
    component_regex = "|".join([f"{name}.*" for name in component_names])

    if level_filter is not None:
        # Get level filter value and all more severe levels
        level_values = [str(level) for level in LogLevel if level.value >= level_filter.value]
        level_regex = "|".join(level_values)
        return f'{{k8s_pod_name=~"{component_regex}", level=~"{level_regex}"}}'
    else:
        return f'{{k8s_pod_name=~"{component_regex}"}}'


async def _execute_loki_request(
    loki_client: httpx.AsyncClient,
    query: str,
    start_date: datetime,
    end_date: datetime,
    limit: int,
    direction: LogDirectionLiteral,
) -> dict:
    """Execute Loki query request and return the JSON response."""
    params = {
        "query": query,
        "start": int(start_date.timestamp() * 1_000_000_000),
        "end": int(end_date.timestamp() * 1_000_000_000),
        "limit": limit + 1,  # Request one extra to check if there are more results
        "direction": direction,
    }

    response: httpx.Response = await loki_client.get("/loki/api/v1/query_range", params=params)
    response.raise_for_status()
    return response.json()


def _parse_loki_response(response_data: dict) -> list[LogEntry]:
    """Parse Loki response data into LogEntry objects."""
    all_entries: list[LogEntry] = []
    for stream in response_data.get("data", {}).get("result", []):
        labels = stream.get("stream", {})

        for timestamp_ns, message in stream.get("values", []):
            timestamp_dt = datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000, tz=UTC)
            all_entries.append(
                LogEntry(
                    timestamp=timestamp_dt.isoformat(),
                    level=LogLevel.from_label(labels.get("detected_level")),
                    message=message,
                )
            )
    return all_entries


def _handle_pagination(
    entries: list[LogEntry], limit: int, direction: LogDirectionLiteral
) -> tuple[list[LogEntry], PaginationMetadata]:
    """Handle pagination logic and return entries with pagination metadata."""
    # Check if there are more results available
    has_more = len(entries) > limit

    # Return only the requested number of entries
    if has_more:
        returned_entries = entries[:limit]
        boundary_timestamp = datetime.fromisoformat(returned_entries[-1].timestamp.replace("Z", "+00:00"))

        # Set next page token based on direction
        if direction == "forward":
            # For forward direction, next page starts after the last entry
            next_page_timestamp = boundary_timestamp + timedelta(microseconds=1)
        else:
            # For backward direction, next page ends before the last entry
            next_page_timestamp = boundary_timestamp - timedelta(microseconds=1)

        next_page_token = next_page_timestamp.isoformat()
    else:
        returned_entries = entries
        next_page_token = None

    pagination = PaginationMetadata(has_more=has_more, page_token=next_page_token, total_returned=len(returned_entries))

    return returned_entries, pagination


async def get_workload_logs(
    workload: WorkloadWithComponents,
    loki_client: httpx.AsyncClient,
    start_date: datetime = None,
    end_date: datetime = None,
    page_token: datetime | None = None,
    limit: int = 1000,
    level_filter: LogLevel | None = None,
    direction: LogDirectionLiteral = "forward",
) -> WorkloadLogsResponse:
    """Get logs for a workload by ID using deployment names from workload components."""

    # Parse and validate dates
    start_date, end_date = _parse_and_validate_dates(start_date, end_date, page_token, direction)

    # Validate workload components
    if not workload.components:
        logger.warning(f"No components found for workload {workload.id}")
        return WorkloadLogsResponse(
            logs=[], pagination=PaginationMetadata(has_more=False, page_token=None, total_returned=0)
        )

    # workload_id is not indexed in Loki, so we need to use indexed labels
    # Use the first component name for pod/deployment queries
    component_names = set([c.name for c in workload.components])
    query = _build_loki_query(component_names, level_filter)
    logger.info(f"Querying logs for workload {workload.id} using components: {component_names}")

    try:
        response_data = await _execute_loki_request(loki_client, query, start_date, end_date, limit, direction)
        all_entries = _parse_loki_response(response_data)
        returned_entries, pagination = _handle_pagination(all_entries, limit, direction)

        if returned_entries:
            logger.info(f"Found {len(returned_entries)} log entries for workload {workload.id}")

        return WorkloadLogsResponse(logs=returned_entries, pagination=pagination)

    except Exception as e:
        logger.warning(f"Query '{query}' failed: {e}")
        return WorkloadLogsResponse(
            logs=[], pagination=PaginationMetadata(has_more=False, page_token=None, total_returned=0)
        )


async def stream_workload_logs(
    workload: WorkloadWithComponents,
    websocket_factory: WebSocketConnectionFactory,
    start_time: datetime | None = None,
    level_filter: LogLevel | None = None,
    delay_seconds: int = 1,
) -> AsyncGenerator[LogEntry]:
    """Stream logs for a workload using Loki's WebSocket tail API.

    Args:
        workload: The workload to stream logs for
        websocket_factory: Factory for managing WebSocket connections
        start_time: Start time for streaming (defaults to one hour ago)
        level_filter: Optional log level filter
        delay_seconds: Delay between polling requests in seconds

    Yields:
        LogEntry objects as they become available
    """
    if not workload.components:
        logger.warning(f"No components found for workload {workload.id}")
        return

    # Use the first component name for pod/deployment queries
    component_names = set([c.name for c in workload.components])
    query = _build_loki_query(component_names, level_filter)

    if start_time is not None and start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)

    logger.info(f"Starting log stream for workload {workload.id} using components: {component_names}")

    websocket = None
    try:
        websocket = await websocket_factory.get_or_create_connection(
            workload_id=workload.id,
            query=query,
            start_time=start_time,
            delay_seconds=delay_seconds,
        )

        logger.info(f"Connected to Loki WebSocket for workload {workload.id}")

        try:
            async for message in websocket:
                try:
                    tail_data = json.loads(message)

                    if "streams" in tail_data:
                        for stream in tail_data["streams"]:
                            labels = stream.get("stream", {})

                            for timestamp_ns, log_message in stream.get("values", []):
                                log_entry = _parse_websocket_log_entry(timestamp_ns, log_message, labels)
                                yield log_entry

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse WebSocket message: {message[:100]}... Error: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing WebSocket message: {e}")
                    continue

        except asyncio.CancelledError:
            # Client disconnection or request cancellation
            logger.info(f"Log stream cancelled for workload {workload.id}")
            raise  # Re-raise to properly handle cancellation

    except websockets.WebSocketException as e:
        logger.error(f"WebSocket connection failed for workload {workload.id}: {e}")
        # WebSocket streaming is not available, streaming stops
        raise
    except asyncio.CancelledError:
        # Client disconnection - cleanup and re-raise
        logger.info(f"Client disconnected from log stream for workload {workload.id}")
        raise
    except Exception as e:
        logger.error(f"Log streaming for workload {workload.id} failed: {e}")
        # Streaming failed, stopping
        raise
    finally:
        await websocket_factory.close_connection(workload.id, query, delay_seconds)
        logger.debug(f"WebSocket streaming finished for workload {workload.id}")


def _parse_websocket_log_entry(timestamp_ns: str, log_message: str, labels: dict = None) -> LogEntry:
    """Parse a single log entry from WebSocket message.

    Args:
        timestamp_ns: Timestamp in nanoseconds as string
        log_message: The log message content
        labels: Stream labels containing metadata like detected_level

    Returns:
        LogEntry object
    """
    timestamp_dt = datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000, tz=UTC)

    # Try to get level from stream labels first, then fall back to parsing message
    if labels and labels.get("detected_level"):
        level = LogLevel.from_label(labels.get("detected_level"))
    else:
        # Fall back to parsing level from message content
        level_str = log_message.split(": ")[0]
        level = LogLevel.from_label(level_str)

    return LogEntry(timestamp=timestamp_dt.isoformat(), level=level, message=log_message)


def _build_loki_websocket_url(base_url: str, query: str, start_time: datetime | None, delay_seconds: int) -> str:
    """Build WebSocket URL for Loki tail endpoint."""
    parsed = urlparse(str(base_url))
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"

    params = {
        "query": query,
        "delay_for": delay_seconds,
    }

    if start_time is not None:
        params["start"] = int(start_time.timestamp() * 1_000_000_000)

    ws_url = f"{ws_scheme}://{parsed.netloc}/loki/api/v1/tail?{urlencode(params)}"
    return ws_url
