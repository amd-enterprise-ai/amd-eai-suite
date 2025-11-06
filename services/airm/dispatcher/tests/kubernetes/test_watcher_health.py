# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import datetime, timedelta

import pytest

from app.kubernetes import watcher_health


@pytest.fixture(autouse=True)
def reset_watcher_status_map():
    # Clear the map before each test
    watcher_health.watcher_status_map.clear()


def test_register_watcher_adds_new_entry():
    watcher_health.register_watcher("job_watcher")
    assert "job_watcher" in watcher_health.watcher_status_map
    assert isinstance(watcher_health.watcher_status_map["job_watcher"], datetime)


def test_register_watcher_raises_on_duplicate():
    watcher_health.register_watcher("job_watcher")
    with pytest.raises(ValueError, match="already registered"):
        watcher_health.register_watcher("job_watcher")


def test_update_last_watch_attempt_updates_time():
    watcher_health.register_watcher("job_watcher")
    old_time = watcher_health.watcher_status_map["job_watcher"]

    watcher_health.update_last_watch_attempt("job_watcher")
    new_time = watcher_health.watcher_status_map["job_watcher"]

    assert new_time >= old_time


def test_update_last_watch_attempt_raises_for_unknown():
    with pytest.raises(KeyError, match="is not registered"):
        watcher_health.update_last_watch_attempt("unknown_watcher")


@pytest.mark.asyncio
async def test_all_watchers_healthy_true_when_recent():
    watcher_health.register_watcher("job_watcher")
    watcher_health.register_watcher("service_watcher")
    watcher_health.update_last_watch_attempt("job_watcher")
    watcher_health.update_last_watch_attempt("service_watcher")

    assert await watcher_health.all_watchers_healthy() is True


@pytest.mark.asyncio
async def test_all_watchers_healthy_false_when_stale(monkeypatch):
    watcher_health.register_watcher("job_watcher")
    # Simulate stale time (6 minutes ago)
    stale_time = datetime.now() - timedelta(minutes=6)
    watcher_health.watcher_status_map["job_watcher"] = stale_time

    assert await watcher_health.all_watchers_healthy() is False
