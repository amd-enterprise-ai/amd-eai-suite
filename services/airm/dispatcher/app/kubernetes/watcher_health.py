# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime, timedelta

from loguru import logger


def register_watcher(watcher_name: str) -> None:
    if watcher_name in watcher_status_map:
        raise ValueError(f"Watcher '{watcher_name}' is already registered.")

    watcher_status_map[watcher_name] = datetime.now()


watcher_status_map: dict[str, datetime] = {}


def update_last_watch_attempt(name: str) -> None:
    if name not in watcher_status_map:
        raise KeyError(f"Watcher '{name}' is not registered. Call register_watcher() first.")
    watcher_status_map[name] = datetime.now()


async def all_watchers_healthy() -> bool:
    #  verify that each watcher last_watch_attempt < 5 mins ago
    now = datetime.now()

    for name, last_attempt in watcher_status_map.items():
        age = now - last_attempt
        if age > timedelta(minutes=5):
            logger.error(f"Watcher '{name}' is stale: last attempted {age.total_seconds() / 60:.2f} minutes ago")
            return False

    return True
