# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Loki client. Requires close - uses async httpx with persistent connection pool."""

import httpx
from fastapi import Request
from loguru import logger

from .config import LOKI_TIMEOUT_SECONDS, LOKI_URL

_loki_client: httpx.AsyncClient | None = None


def init_loki_client() -> httpx.AsyncClient:
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
    if not hasattr(request.app.state, "loki_client") or request.app.state.loki_client is None:
        logger.error("Loki client not initialized in app.state.")
        raise RuntimeError("Loki client not available.")
    return request.app.state.loki_client


async def close_loki_client():
    global _loki_client
    if _loki_client:
        await _loki_client.aclose()
        _loki_client = None
        logger.info("Loki client closed")
