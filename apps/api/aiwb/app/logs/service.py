# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse
from uuid import UUID

import httpx
import websockets
from loguru import logger

from api_common.schemas import PaginationDirection, PaginationMetadataResponse

from .config import LOKI_DEFAULT_TIME_RANGE_DAYS, LOKI_KEEPALIVE_TIMEOUT_SECONDS, LOKI_URL
from .schemas import LogEntry, LogLevel, LogType, WorkloadLogsResponse


async def create_websocket_connection(
    workload_id: UUID,
    query: str,
    start_time: datetime | None = None,
    delay_seconds: int = 1,
) -> websockets.ClientConnection:
    """Create a new WebSocket connection for log streaming.

    Raises:
        websockets.WebSocketException: If connection fails
        ValueError: If LOKI_URL is not configured
    """
    if LOKI_URL is None:
        raise ValueError("LOKI_URL is not configured")

    # Create new connection
    ws_url = _build_loki_websocket_url(LOKI_URL, query, start_time, delay_seconds)
    logger.info(f"Creating new WebSocket connection to: {ws_url}")

    try:
        # Add connection timeout and ping interval for better connection health
        connection = await websockets.connect(
            ws_url,
            ping_interval=30,  # Send ping every 30 seconds
            ping_timeout=10,  # Wait 10 seconds for pong response
            close_timeout=10,  # Wait 10 seconds for close handshake
        )
        logger.info(f"Created new WebSocket connection for workload {workload_id}")
        return connection
    except Exception as e:
        logger.error(f"Failed to create WebSocket connection for workload {workload_id}: {e}")
        raise


def _parse_and_validate_dates(
    start_date: datetime,
    end_date: datetime,
    page_token: datetime | None,
    direction: PaginationDirection,
) -> tuple[datetime, datetime]:
    """Parse and validate date parameters, handling pagination tokens.

    All datetime params are AwareDatetime (timezone-aware) from Pydantic validation.

    Returns:
        Tuple of (start_date, end_date)
    """
    # Handle pagination with page_token
    if page_token is not None:
        if direction == PaginationDirection.FORWARD:
            start_date = max(page_token, start_date)
        else:
            end_date = min(page_token, end_date)

    # Ensure start_date is always before end_date (Loki requirement)
    if start_date >= end_date:
        raise ValueError(f"Invalid time range: start_date ({start_date}) >= end_date ({end_date})")

    return start_date, end_date


def _build_loki_query(workload_id: str, log_level: LogLevel | None = None, log_type: LogType = LogType.WORKLOAD) -> str:
    """Build LogQL query string for the given workload_id.

    Queries directly by workload_id label which is set by the OTEL collector
    from the pod's workload-id label. This approach is reliable even after
    pods are deleted since logs retain the workload_id label.

    Note: In production, only k8s events have log_type="k8s_event" set by the OTEL collector.
    Regular pod logs don't have log_type at all. In LogQL:
    - log_type="k8s_event" matches only logs with that label value
    - log_type="" matches logs where the label doesn't exist (regular pod logs)
    """
    log_type_filter = ""

    if log_type == LogType.EVENT:
        # Only k8s events have this label set
        log_type_filter = ', log_type="k8s_event"'
    else:
        # Regular pod logs don't have log_type label; log_type="" matches missing labels
        log_type_filter = ', log_type=""'

    if log_level is not None:
        # Get all levels at or above the specified severity; map to Loki label values
        levels = LogLevel.levels_at_or_above(log_level)
        level_values = [f'detected_level="{level.to_loki_label()}"' for level in levels]
        level_query = " or ".join(level_values)
        return f'{{workload_id="{workload_id}"{log_type_filter}}}|{level_query}'
    else:
        return f'{{workload_id="{workload_id}"{log_type_filter}}}'


async def _execute_loki_request(
    loki_client: httpx.AsyncClient,
    query: str,
    start_date: datetime,
    end_date: datetime,
    limit: int,
    direction: PaginationDirection,
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


def _parse_loki_response(response_data: dict, log_type: LogType) -> list[LogEntry]:
    """Parse Loki response data into LogEntry objects."""
    all_entries: list[LogEntry] = []
    for stream in response_data.get("data", {}).get("result", []) or response_data.get("streams", {}).get("result", []):
        labels = stream.get("stream", {})

        for timestamp_ns, message in stream.get("values", []):
            log_entry = LogEntry.from_loki(timestamp_ns, message, labels)
            all_entries.append(log_entry)
    return all_entries


def _handle_pagination(
    entries: list[LogEntry], limit: int, direction: PaginationDirection
) -> tuple[list[LogEntry], PaginationMetadataResponse]:
    """Handle pagination logic and return entries with pagination metadata."""
    # Check if there are more results available
    has_more = len(entries) > limit

    # Return only the requested number of entries
    if has_more:
        returned_entries = entries[:limit]
        boundary_timestamp = returned_entries[-1].timestamp

        # Set next page token based on direction
        if direction == PaginationDirection.FORWARD:
            # For forward direction, next page starts after the last entry
            next_page_timestamp = boundary_timestamp + timedelta(microseconds=1)
        else:
            # For backward direction, next page ends before the last entry
            next_page_timestamp = boundary_timestamp - timedelta(microseconds=1)

        next_page_token = next_page_timestamp.isoformat()
    else:
        returned_entries = entries
        next_page_token = None

    pagination = PaginationMetadataResponse(
        has_more=has_more, page_token=next_page_token, total_returned=len(returned_entries)
    )

    return returned_entries, pagination


async def get_logs_by_workload_id(
    workload_id: str,
    loki_client: httpx.AsyncClient,
    start_date: datetime,
    end_date: datetime,
    page_token: datetime | None = None,
    limit: int = 1000,
    level_filter: LogLevel | None = None,
    log_type: LogType = LogType.WORKLOAD,
    direction: PaginationDirection = PaginationDirection.FORWARD,
) -> WorkloadLogsResponse:
    """Get logs by querying Loki directly by workload_id.

    This approach queries by workload_id label which is always present in logs
    (set by OTEL collector from pod label). This is reliable even after pods
    are deleted since logs retain the workload_id label in Loki.
    """
    # Parse and validate dates
    start_date, end_date = _parse_and_validate_dates(start_date, end_date, page_token, direction)

    # Build query directly by workload_id
    query = _build_loki_query(workload_id, level_filter, log_type)
    logger.info(f"Querying logs for workload {workload_id}")

    try:
        response_data = await _execute_loki_request(loki_client, query, start_date, end_date, limit, direction)
        all_entries = _parse_loki_response(response_data, log_type)
        returned_entries, pagination = _handle_pagination(all_entries, limit, direction)

        if returned_entries:
            logger.info(f"Found {len(returned_entries)} log entries for workload {workload_id}")

        return WorkloadLogsResponse(data=returned_entries, pagination=pagination)

    except Exception as e:
        logger.warning(f"Query '{query}' failed: {e}")
        return WorkloadLogsResponse(
            data=[], pagination=PaginationMetadataResponse(has_more=False, page_token=None, total_returned=0)
        )


async def stream_workload_logs_sse(
    workload_id: str,
    start_time: datetime | None = None,
    level_filter: LogLevel | None = None,
    log_type: LogType = LogType.WORKLOAD,
    delay_seconds: int = 1,
) -> AsyncGenerator[str]:
    """Stream logs for a workload as Server-Sent Events.

    Wraps stream_workload_logs and formats output for SSE consumption.

    Yields:
        SSE-formatted strings (data: {message}\n\n)
    """
    try:
        async for message in stream_workload_logs(
            workload_id=workload_id,
            start_time=start_time,
            level_filter=level_filter,
            log_type=log_type,
            delay_seconds=delay_seconds,
        ):
            yield f"data: {message}\n\n"

        # Send completion marker when stream ends gracefully
        yield "data: [DONE]\n\n"

    except asyncio.CancelledError:
        # Client disconnection - log and exit gracefully
        logger.info(f"Log stream for workload {workload_id} cancelled by client")
        return
    except Exception as e:
        logger.error(f"Log stream error for workload {workload_id}: {e}")
        error_data = {"error": str(e)}
        yield f"data: {json.dumps(error_data)}\n\n"


async def stream_workload_logs(
    workload_id: str,
    start_time: datetime | None = None,
    level_filter: LogLevel | None = None,
    log_type: LogType = LogType.WORKLOAD,
    delay_seconds: int = 1,
) -> AsyncGenerator[str]:
    """Stream logs for a workload using Loki's WebSocket tail API.

    Yields:
        LogEntry serialized as JSON string
    """
    # Build query directly by workload_id
    query = _build_loki_query(workload_id, level_filter, log_type)
    logger.info(f"Starting log stream for workload {workload_id}")

    if start_time is not None and start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    else:
        start_time = datetime.now(UTC) - timedelta(days=LOKI_DEFAULT_TIME_RANGE_DAYS)

    websocket = None

    websocket = await create_websocket_connection(
        workload_id=UUID(workload_id) if isinstance(workload_id, str) else workload_id,
        query=query,
        start_time=start_time,
        delay_seconds=delay_seconds,
    )

    logger.info(f"Connected to Loki WebSocket for workload {workload_id}")

    try:
        while True:
            try:
                async with asyncio.timeout(LOKI_KEEPALIVE_TIMEOUT_SECONDS):
                    message = await websocket.recv()
                    tail_data = json.loads(message)

                    if "streams" not in tail_data:
                        continue

                    for stream in tail_data["streams"]:
                        labels = stream.get("stream", {})
                        for timestamp_ns, log_message in stream.get("values", []):
                            log_entry = LogEntry.from_loki(timestamp_ns, log_message, labels)

                            yield log_entry.model_dump_json()

            except TimeoutError:
                yield "[HEARTBEAT]"
                continue
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse WebSocket message: {message[:100]}... Error: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing WebSocket message: {e}")
                continue

    except asyncio.CancelledError:
        # Client disconnection or request cancellation - handle gracefully
        logger.info(f"Log stream cancelled for workload {workload_id}")
        return  # Exit gracefully without re-raising
    except websockets.WebSocketException as e:
        logger.error(f"WebSocket connection failed for workload {workload_id}: {e}")
        # WebSocket streaming is not available, streaming stops
        raise
    except Exception as e:
        logger.error(f"Log streaming for workload {workload_id} failed: {e}")
        # Streaming failed, stopping
        raise
    finally:
        if websocket:
            try:
                await websocket.close()
                logger.info(f"WebSocket connection closed for workload {workload_id}")
            except Exception as e:
                logger.warning(f"Error closing WebSocket connection for workload {workload_id}: {e}")
            logger.info(f"WebSocket streaming finished for workload {workload_id}")


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
