# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Kubernetes connection utilities for Robot Framework tests."""

import json
import logging
import random
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

# Global cache for port forwarding connections
_PORT_FORWARD_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 3600  # 1 hour


def _run_kubectl(cmd: list) -> str:
    """Run kubectl command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"kubectl command failed: {' '.join(cmd)}, error: {e.stderr}")
        raise RuntimeError(f"kubectl command failed: {e.stderr}")


def _start_port_forward(service_name: str, namespace: str, local_port: int, service_port: int):
    """Start port forwarding in background thread."""

    def port_forward():
        cmd = ["kubectl", "port-forward", f"service/{service_name}", f"{local_port}:{service_port}", "-n", namespace]
        try:
            # Suppress output by redirecting to devnull
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logger.error(f"Port forward failed: {e}")

    thread = threading.Thread(target=port_forward, daemon=True)
    thread.start()

    # Wait a moment for port forward to establish
    time.sleep(2)
    logger.info(f"Port forwarding started: {service_name}:{service_port} -> localhost:{local_port}")


def _get_service_port(service_name: str, namespace: str) -> int:
    """Get the first port from a k8s service."""
    cmd = ["kubectl", "get", "service", service_name, "-n", namespace, "-o", "json"]
    output = _run_kubectl(cmd)
    service_data = json.loads(output)

    ports = service_data.get("spec", {}).get("ports", [])
    if not ports:
        raise RuntimeError(f"No ports found for service {service_name}")

    return ports[0]["port"]


def external_host_for(service: str, micro_service: str, prefix: str = None) -> str:
    """Returns an external host for a service by setting up port forwarding.

    Args:
        service: The service name (used as namespace if prefix is None)
        micro_service: The microservice name (actual k8s service name)
        prefix: Optional namespace prefix

    Returns:
        Accessible address (localhost:port)
    """
    # Determine namespace
    namespace = f"{prefix}-{service}" if prefix else service
    cache_key = f"{namespace}:{micro_service}"

    # Check cache
    current_time = time.time()
    if cache_key in _PORT_FORWARD_CACHE:
        cached_host, timestamp = _PORT_FORWARD_CACHE[cache_key]
        if current_time - timestamp < _CACHE_TTL:
            logger.info(f"Using cached host for {cache_key}: {cached_host}")
            return cached_host
        else:
            logger.info(f"Cached host for {cache_key} expired, refreshing")

    # Get service port
    try:
        service_port = _get_service_port(micro_service, namespace)
    except Exception as e:
        raise RuntimeError(f"Failed to get service port for {micro_service} in namespace {namespace}: {e}")

    # Generate random local port
    local_port = random.randint(30000, 32767)

    # Start port forwarding
    _start_port_forward(micro_service, namespace, local_port, service_port)

    # Create host address
    host = f"localhost:{local_port}"

    # Cache the result
    _PORT_FORWARD_CACHE[cache_key] = (host, current_time)
    logger.info(f"Cached new host for {cache_key}: {host}")

    return host


def internal_host_for(service: str, micro_service: str, prefix: str = None) -> str:
    """Returns an internal host for a service with automatic port resolution.

    Args:
        service: The service name (e.g., "keycloak")
        micro_service: The microservice name (e.g., "keycloak")
        prefix: Optional namespace prefix

    Returns:
        Internal cluster DNS name with port (e.g., "keycloak.keycloak.svc.cluster.local:8080")
    """
    # Determine namespace
    namespace = f"{prefix}-{service}" if prefix else service

    # Get service port
    try:
        service_port = _get_service_port(micro_service, namespace)
    except Exception as e:
        raise RuntimeError(f"Failed to get service port for {micro_service} in namespace {namespace}: {e}")

    # Return internal cluster DNS name
    return f"{micro_service}.{namespace}.svc.cluster.local:{service_port}"
