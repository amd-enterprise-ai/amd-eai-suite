# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import yaml

from app.charts.registration import normalize_api_files, register_workloads


def make_session_scope_cm(session: AsyncMock | None = None):
    """Build an async context manager that yields an AsyncSession-like object."""
    if session is None:
        session = AsyncMock(name="AsyncSession")
    cm = AsyncMock(name="session_scope_cm")
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    return cm, session


def make_workload(
    *,
    chart_name: str,
    chart_type: str = "INFERENCE",
    metadata: dict | None = None,
    chart_upload_data: dict | None = None,
    overlay_files: list[tuple[Path, str]] | None = None,
):
    """
    Build a MagicMock workload with the minimal API used by register_workloads.
    - get_overlay_files returns a list of (Path, rel_path_str)
    """
    wl = MagicMock(name="WorkloadMock")
    wl.chart_name = chart_name
    wl.type = chart_type
    wl.get_metadata_for_api.return_value = metadata or {}
    wl.get_chart_upload_data.return_value = chart_upload_data or {
        "signature": ["sig/path.yaml"],  # list to exercise normalize_api_files
        "files": ["a", "b"],
    }
    wl.get_overlay_files.return_value = overlay_files or []
    return wl


def write_overlay(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


@pytest.mark.asyncio
@patch("app.charts.registration.update_overlay", autospec=True)
@patch("app.charts.registration.create_overlay", autospec=True)
@patch("app.charts.registration.list_overlays", autospec=True)
@patch("app.charts.registration.update_chart", autospec=True)
@patch("app.charts.registration.create_chart", autospec=True)
@patch("app.charts.registration.select_chart", autospec=True)
@patch("app.charts.registration.get_registerable_workloads", autospec=True)
@patch("app.charts.registration.get_session", autospec=True)
async def test_updates_existing_chart_and_overlay(
    session_scope_mock,
    mock_get_registerable_workloads,
    mock_select_chart,
    mock_create_chart,
    mock_update_chart,
    mock_list_overlays,
    mock_create_overlay,
    mock_update_overlay,
    tmp_path: Path,
    db_session,
):
    cm, _session = make_session_scope_cm(db_session)
    session_scope_mock.return_value = cm

    chart_id = uuid4()
    overlay_id = uuid4()

    # Overlay YAML includes model field; code will use it for canonical_name
    overlay_path = write_overlay(tmp_path, "valid_overlay.yaml", "model: foo/bar\nx: 1\n")
    wl = make_workload(
        chart_name="Existing Chart",
        overlay_files=[(overlay_path, "overlays/valid_overlay.yaml")],
    )

    mock_get_registerable_workloads.return_value = [wl]
    mock_select_chart.return_value = SimpleNamespace(id=chart_id)
    mock_update_chart.return_value = SimpleNamespace(id=chart_id)
    mock_list_overlays.return_value = [SimpleNamespace(id=overlay_id, canonical_name="old/name")]

    await register_workloads()

    mock_create_chart.assert_not_awaited()
    mock_update_chart.assert_awaited_once()
    mock_create_overlay.assert_not_awaited()
    mock_update_overlay.assert_awaited_once()

    args, kwargs = mock_update_overlay.await_args
    assert args == ()
    assert kwargs["overlay_id"] == overlay_id
    ov = kwargs["overlay_update"]
    assert str(ov.chart_id) == str(chart_id)
    assert ov.updated_by == "system"


@pytest.mark.asyncio
@patch("app.charts.registration.update_overlay", autospec=True)
@patch("app.charts.registration.create_overlay", autospec=True)
@patch("app.charts.registration.list_overlays", autospec=True)
@patch("app.charts.registration.update_chart", autospec=True)
@patch("app.charts.registration.create_chart", autospec=True)
@patch("app.charts.registration.select_chart", autospec=True)
@patch("app.charts.registration.get_registerable_workloads", autospec=True)
@patch("app.charts.registration.get_session", autospec=True)
async def test_updates_existing_chart_creates_overlay_when_missing(
    session_scope_mock,
    mock_get_registerable_workloads,
    mock_select_chart,
    mock_create_chart,
    mock_update_chart,
    mock_list_overlays,
    mock_create_overlay,
    mock_update_overlay,
    tmp_path: Path,
    db_session,
):
    cm, _session = make_session_scope_cm(db_session)
    session_scope_mock.return_value = cm

    chart_id = uuid4()

    overlay_dict = {"model": "new/overlay", "a": 1}
    overlay_path = write_overlay(tmp_path, "new_overlay.yaml", yaml.safe_dump(overlay_dict))
    wl = make_workload(
        chart_name="Existing Chart",
        overlay_files=[(overlay_path, "overlays/new_overlay.yaml")],
    )

    mock_get_registerable_workloads.return_value = [wl]
    mock_select_chart.return_value = SimpleNamespace(id=chart_id)
    mock_update_chart.return_value = SimpleNamespace(id=chart_id)
    mock_list_overlays.return_value = []

    await register_workloads()

    mock_create_chart.assert_not_awaited()
    mock_update_chart.assert_awaited_once()
    mock_update_overlay.assert_not_awaited()
    mock_create_overlay.assert_awaited_once()

    mock_create_overlay.assert_awaited_once_with(
        session=ANY,
        chart_id=chart_id,
        overlay_data=overlay_dict,
        canonical_name="new/overlay",
        creator="system",
    )


@pytest.mark.asyncio
@patch("app.charts.registration.update_overlay", autospec=True)
@patch("app.charts.registration.create_overlay", autospec=True)
@patch("app.charts.registration.list_overlays", autospec=True)
@patch("app.charts.registration.update_chart", autospec=True)
@patch("app.charts.registration.create_chart", autospec=True)
@patch("app.charts.registration.select_chart", autospec=True)
@patch("app.charts.registration.get_registerable_workloads", autospec=True)
@patch("app.charts.registration.get_session", autospec=True)
async def test_updates_chart_only_when_no_overlay_files(
    session_scope_mock,
    mock_get_registerable_workloads,
    mock_select_chart,
    mock_create_chart,
    mock_update_chart,
    mock_list_overlays,
    mock_create_overlay,
    mock_update_overlay,
    db_session,
):
    cm, _session = make_session_scope_cm(db_session)
    session_scope_mock.return_value = cm

    chart_id = uuid4()
    wl = make_workload(chart_name="Existing Chart", overlay_files=[])

    mock_get_registerable_workloads.return_value = [wl]
    mock_select_chart.return_value = SimpleNamespace(id=chart_id)
    mock_update_chart.return_value = SimpleNamespace(id=chart_id)

    await register_workloads()

    mock_create_chart.assert_not_awaited()
    mock_update_chart.assert_awaited_once()
    mock_create_overlay.assert_not_awaited()
    mock_update_overlay.assert_not_awaited()
    mock_list_overlays.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.charts.registration.update_overlay", autospec=True)
@patch("app.charts.registration.create_overlay", autospec=True)
@patch("app.charts.registration.list_overlays", autospec=True)
@patch("app.charts.registration.update_chart", autospec=True)
@patch("app.charts.registration.create_chart", autospec=True)
@patch("app.charts.registration.select_chart", autospec=True)
@patch("app.charts.registration.get_registerable_workloads", autospec=True)
@patch("app.charts.registration.get_session", autospec=True)
async def test_creates_new_chart_and_overlay(
    session_scope_mock,
    mock_get_registerable_workloads,
    mock_select_chart,
    mock_create_chart,
    mock_update_chart,
    mock_list_overlays,
    mock_create_overlay,
    mock_update_overlay,
    tmp_path: Path,
):
    cm, _session = make_session_scope_cm()
    session_scope_mock.return_value = cm

    new_chart_id = uuid4()
    overlay_dict = {"model": "brand/new", "z": 9}
    overlay_path = write_overlay(tmp_path, "brand_new.yaml", yaml.safe_dump(overlay_dict))
    wl = make_workload(
        chart_name="Brand New",
        overlay_files=[(overlay_path, "overlays/brand_new.yaml")],
    )

    mock_get_registerable_workloads.return_value = [wl]
    mock_select_chart.return_value = None
    mock_create_chart.return_value = SimpleNamespace(id=new_chart_id)
    mock_list_overlays.return_value = []

    await register_workloads()

    mock_create_chart.assert_awaited_once()
    mock_update_chart.assert_not_awaited()
    mock_update_overlay.assert_not_awaited()
    mock_create_overlay.assert_awaited_once()

    mock_create_overlay.assert_awaited_once_with(
        session=ANY,
        chart_id=new_chart_id,
        overlay_data=overlay_dict,
        canonical_name="brand/new",
        creator="system",
    )


@pytest.mark.asyncio
@patch("app.charts.registration.update_overlay", autospec=True)
@patch("app.charts.registration.create_overlay", autospec=True)
@patch("app.charts.registration.list_overlays", autospec=True)
@patch("app.charts.registration.update_chart", autospec=True)
@patch("app.charts.registration.create_chart", autospec=True)
@patch("app.charts.registration.select_chart", autospec=True)
@patch("app.charts.registration.get_registerable_workloads", autospec=True)
@patch("app.charts.registration.get_session", autospec=True)
async def test_invalid_overlay_yaml_raises_value_error_when_overlay_missing(
    session_scope_mock,
    mock_get_registerable_workloads,
    mock_select_chart,
    mock_create_chart,
    mock_update_chart,
    mock_list_overlays,
    mock_create_overlay,
    mock_update_overlay,
    tmp_path: Path,
):
    cm, _session = make_session_scope_cm()
    session_scope_mock.return_value = cm

    chart_id = uuid4()
    overlay_path = write_overlay(tmp_path, "bad.yaml", "not: valid: [")

    wl = make_workload(
        chart_name="Existing Chart",
        overlay_files=[(overlay_path, "overlays/bad.yaml")],
    )

    mock_get_registerable_workloads.return_value = [wl]
    mock_select_chart.return_value = SimpleNamespace(id=chart_id)
    mock_update_chart.return_value = SimpleNamespace(id=chart_id)
    mock_list_overlays.return_value = []  # go down the "create" path

    with patch("app.charts.registration.yaml.safe_load", return_value=None):
        with pytest.raises(ValueError, match="Overlay data is required for creating an overlay."):
            await register_workloads()

    mock_update_chart.assert_awaited_once()
    mock_create_overlay.assert_not_awaited()
    mock_update_overlay.assert_not_awaited()


# Tests for normalize_api_files function


def test_normalize_api_files_with_list_signature():
    """Test normalize_api_files extracts first item from signature list."""
    files = {"signature": ["sig1.yaml", "sig2.yaml"], "files": ["file1.yaml", "file2.yaml"]}

    result = normalize_api_files(files)

    assert result == {"files": ["file1.yaml", "file2.yaml"], "signature": "sig1.yaml"}  # First item from list


def test_normalize_api_files_with_string_signature():
    """Test normalize_api_files preserves string signature unchanged."""
    files = {"signature": "single_sig.yaml", "files": ["file1.yaml", "file2.yaml"]}

    result = normalize_api_files(files)

    assert result == {"files": ["file1.yaml", "file2.yaml"], "signature": "single_sig.yaml"}  # Unchanged


def test_normalize_api_files_with_empty_list_signature():
    """Test normalize_api_files handles empty signature list safely."""
    files = {"signature": [], "files": ["file1.yaml"]}

    result = normalize_api_files(files)

    assert result == {"files": ["file1.yaml"], "signature": []}  # Empty list unchanged
