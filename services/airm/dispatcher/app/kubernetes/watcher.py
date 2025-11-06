# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import time
from asyncio import AbstractEventLoop, to_thread
from collections.abc import Callable, Coroutine

from kubernetes import client, watch
from loguru import logger

from .watcher_health import register_watcher, update_last_watch_attempt


async def start_kubernetes_watcher(watcher_name: str, watch_function, callback: Callable, *args, **kwargs) -> Coroutine:
    register_watcher(watcher_name)
    loop = asyncio.get_running_loop()
    return await to_thread(__watch_k8s_resources, watcher_name, watch_function, callback, loop, *args, **kwargs)


def get_installed_version_for_custom_resource(kube_client, group: str, plural: str) -> str | None:
    try:
        api_ext = kube_client.ApiextensionsV1Api()
        crd = api_ext.read_custom_resource_definition(f"{plural}.{group}")
        version = None
        # Prefer the storage version if available
        for ver in crd.spec.versions:
            if ver.storage:
                version = ver.name
                break

        # If no storage version found, pick the first served version
        if version is None:
            for ver in crd.spec.versions:
                if ver.served:
                    version = ver.name
                    break
        logger.info(f"Found version {version} for custom resource {group}/{plural}")
        return version
    except client.ApiException as e:
        if e.status == 404:
            logger.warning(f"Custom resource {group}/{plural} not found.")
            return None
        else:
            logger.exception(f"Error checking custom resource {group}/{plural}.", e)
            raise


async def start_kubernetes_watcher_if_resource_exists(
    watcher_name: str, watch_function, callback: Callable, *args, **kwargs
) -> Coroutine | None:
    try:
        watch_function(*args, **kwargs)
    except client.ApiException as e:
        if e.status == 404 or e.status == 403:
            logger.warning(f"Resource targeted by {watcher_name} not found or inaccessible. Skipping watcher.")
            return None
        else:
            logger.exception(f"Error checking resource {watcher_name}.", e)
            raise

    return await start_kubernetes_watcher(watcher_name, watch_function, callback, *args, **kwargs)


def __watch_k8s_resources(watcher_name, watch_function, callback: Callable, loop: AbstractEventLoop, *args, **kwargs):
    logger.info(f"Starting Kubernetes event watchers {watcher_name}...")
    resource_version = None
    while True:
        w = watch.Watch()
        try:
            for event in w.stream(
                watch_function, *args, timeout_seconds=60, resource_version=resource_version, **kwargs
            ):
                resource = event["object"]
                event_type = event["type"]
                logger.info(f"Watcher {watcher_name} received event: {event_type}")

                try:
                    future = asyncio.run_coroutine_threadsafe(callback(resource, event_type), loop)
                    future.result(timeout=5)
                except Exception as e:
                    logger.exception(f"Error processing event {event_type} for {watch_function}: {resource}", e)
                resource_version = event["raw_object"]["metadata"]["resourceVersion"]

            update_last_watch_attempt(watcher_name)
        except client.ApiException as e:
            if e.status == 410:
                logger.info(
                    f"Resource version {resource_version} for {watcher_name} is too old. Restarting watcher without a resource version."
                )
                resource_version = None
                continue
            else:
                logger.exception(f"Error watching {watcher_name}. Restarting in 5 seconds.", e)
                time.sleep(5)
        except asyncio.CancelledError:
            logger.info(f"Watcher for {watcher_name} cancelled. Exiting.")
            break
        except Exception as e:
            logger.exception(f"Watcher {watcher_name} crashed. Restarting in 5 seconds.", e)
            time.sleep(5)
        finally:
            w.stop()
