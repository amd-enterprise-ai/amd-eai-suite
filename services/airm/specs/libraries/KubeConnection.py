# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Kubernetes connection utilities for Robot Framework tests."""

import json
import logging
import random
import socket
import subprocess
import time

logger = logging.getLogger(__name__)

# Global cache for port forwarding connections
_PORT_FORWARD_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 3600  # 1 hour

# Global process tracking for port forwards (for cleanup)
_PORT_FORWARD_PROCESSES: dict[str, subprocess.Popen] = {}


def _run_kubectl(cmd: list) -> str:
    """Run kubectl command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"kubectl command failed: {' '.join(cmd)}, error: {e.stderr}")
        raise RuntimeError(f"kubectl command failed: {e.stderr}")


def _check_port_ready(port: int, timeout: int = 10) -> bool:
    """Check if a port is ready to accept connections.

    Args:
        port: The local port to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if port is ready, False otherwise
    """
    logger.info(f"Checking if port {port} is ready to accept connections...")

    for attempt in range(timeout):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                logger.info(f"Port {port} is ready after {attempt + 1} second(s)")
                return True
        except (TimeoutError, OSError) as e:
            logger.debug(f"Port {port} not ready yet (attempt {attempt + 1}/{timeout}): {e}")

        if attempt < timeout - 1:
            time.sleep(1)

    logger.warning(f"Port {port} not ready after {timeout} seconds")
    return False


def _find_existing_port_forward(service_name: str, namespace: str, service_port: int) -> int | None:
    """Find existing port forward for a service.

    Args:
        service_name: The k8s service name
        namespace: The k8s namespace
        service_port: The service port being forwarded

    Returns:
        Local port number if found, None otherwise
    """
    try:
        # Use ps to find kubectl port-forward processes
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True)

        # Look for matching port-forward command
        # Example: kubectl port-forward service/airm-api 31234:80 -n airm
        for line in result.stdout.splitlines():
            if "kubectl" in line and "port-forward" in line:
                if f"service/{service_name}" in line and f"-n {namespace}" in line:
                    # Extract local port from pattern "local_port:service_port"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if f":{service_port}" in part:
                            # Format is "local_port:service_port"
                            local_port_str = part.split(":")[0]
                            try:
                                local_port = int(local_port_str)
                                # Verify this port is actually listening
                                if _check_port_ready(local_port, timeout=1):
                                    logger.info(
                                        f"Found existing port forward: localhost:{local_port} -> {service_name}:{service_port}"
                                    )
                                    return local_port
                            except ValueError:
                                continue
    except (subprocess.CalledProcessError, Exception) as e:
        logger.debug(f"Could not search for existing port forwards: {e}")

    return None


def _start_port_forward(service_name: str, namespace: str, local_port: int, service_port: int) -> subprocess.Popen:
    """Start port forwarding in background and wait for it to be ready.

    Args:
        service_name: The k8s service name
        namespace: The k8s namespace
        local_port: The local port to forward to
        service_port: The service port to forward from

    Returns:
        The Popen process object for the port forward

    Raises:
        RuntimeError: If port forward fails to become ready
    """
    cmd = ["kubectl", "port-forward", f"service/{service_name}", f"{local_port}:{service_port}", "-n", namespace]
    cache_key = f"{namespace}:{service_name}"

    try:
        # Start port-forward as a background process (don't wait for it to complete)
        # Suppress output by redirecting to devnull
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Track the process for cleanup
        _PORT_FORWARD_PROCESSES[cache_key] = process

        logger.debug(f"Started port-forward process (PID {process.pid}): {' '.join(cmd)}")
    except Exception as e:
        logger.error(f"Failed to start port forward: {e}")
        raise RuntimeError(f"Failed to start port forward: {e}")

    # Wait for port forward to be ready (up to 10 seconds)
    if not _check_port_ready(local_port, timeout=10):
        raise RuntimeError(
            f"Port forward to {service_name}:{service_port} failed to become ready on localhost:{local_port}"
        )

    logger.info(f"Port forwarding ready: {service_name}:{service_port} -> localhost:{local_port}")
    return process


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

    This function will:
    1. Check the cache for an existing port forward
    2. Search for existing kubectl port-forward processes
    3. Create a new port forward if none exists
    4. Verify the port is ready before returning

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

    # Check cache first
    current_time = time.time()
    if cache_key in _PORT_FORWARD_CACHE:
        cached_host, timestamp = _PORT_FORWARD_CACHE[cache_key]
        if current_time - timestamp < _CACHE_TTL:
            # Verify cached port is still accessible
            port = int(cached_host.split(":")[1])
            if _check_port_ready(port, timeout=1):
                logger.info(f"Using cached host for {cache_key}: {cached_host}")
                return cached_host
            else:
                # CRITICAL: Remove stale cache entry
                del _PORT_FORWARD_CACHE[cache_key]
                logger.warning(f"Removed stale cache entry for {cache_key} (port {port} no longer accessible)")

    # Get service port
    try:
        service_port = _get_service_port(micro_service, namespace)
    except Exception as e:
        raise RuntimeError(f"Failed to get service port for {micro_service} in namespace {namespace}: {e}")

    # Check for existing port forward process
    existing_port = _find_existing_port_forward(micro_service, namespace, service_port)
    if existing_port:
        host = f"localhost:{existing_port}"
        _PORT_FORWARD_CACHE[cache_key] = (host, current_time)
        logger.info(f"Reusing existing port forward for {cache_key}: {host}")
        return host

    # No existing forward found, create a new one
    # Generate random local port
    local_port = random.randint(30000, 32767)

    # Start port forwarding (this will wait for port to be ready)
    _start_port_forward(micro_service, namespace, local_port, service_port)

    # Create host address
    host = f"localhost:{local_port}"

    # Cache the result
    _PORT_FORWARD_CACHE[cache_key] = (host, current_time)
    logger.info(f"Created new port forward for {cache_key}: {host}")

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


def cleanup_all_port_forwards():
    """Terminate all tracked port forward processes and clear caches.

    This function should be called at test suite teardown to ensure all
    kubectl port-forward processes are properly terminated.

    Example usage in Robot Framework:
        Suite Teardown    Cleanup All Port Forwards
    """
    logger.info(f"Cleaning up {len(_PORT_FORWARD_PROCESSES)} port forward processes")

    for cache_key, process in list(_PORT_FORWARD_PROCESSES.items()):
        if process.poll() is None:  # Process still running
            try:
                process.terminate()
                logger.debug(f"Terminated port forward: {cache_key} (PID {process.pid})")

                # Wait briefly for graceful termination
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if termination times out
                    process.kill()
                    logger.warning(f"Forcefully killed port forward: {cache_key} (PID {process.pid})")
            except Exception as e:
                logger.error(f"Error terminating port forward {cache_key}: {e}")
        else:
            logger.debug(f"Port forward {cache_key} already terminated (exit code: {process.returncode})")

    # Clear tracking dictionaries
    _PORT_FORWARD_PROCESSES.clear()
    _PORT_FORWARD_CACHE.clear()

    logger.info("Port forward cleanup complete")
