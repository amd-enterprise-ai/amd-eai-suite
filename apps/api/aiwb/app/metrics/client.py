# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Prometheus client. No close needed - uses sync requests per-query, no connection pool."""

from fastapi import Request
from loguru import logger
from prometheus_api_client import PrometheusConnect

from .config import PROMETHEUS_URL


def init_prometheus_client() -> PrometheusConnect:
    if not PROMETHEUS_URL:
        raise ValueError("PROMETHEUS_URL environment variable must be set")
    client = PrometheusConnect(url=PROMETHEUS_URL)
    logger.info("Connected to Prometheus server at {}", PROMETHEUS_URL)
    return client


def get_prometheus_client(request: Request) -> PrometheusConnect:
    if not hasattr(request.app.state, "prometheus_client") or request.app.state.prometheus_client is None:
        logger.error("Prometheus client not initialized in app.state.")
        raise RuntimeError("Prometheus client not available.")
    return request.app.state.prometheus_client
