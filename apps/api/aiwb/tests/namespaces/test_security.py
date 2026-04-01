# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.namespaces.security import (
    _validate_namespace,
    ensure_access_to_workbench_namespace,
    get_workbench_namespace,
    is_valid_workbench_namespace,
)
from tests.factory import make_namespace_crd


@pytest.mark.asyncio
async def test_validate_namespace_success_standalone_mode(mock_kube_client: MagicMock) -> None:
    """Test successful namespace validation in standalone mode with default namespace."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", True),
        patch("app.namespaces.security.DEFAULT_NAMESPACE", "workbench"),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
    ):
        ns = make_namespace_crd(name="workbench", project_id="test-id")
        mock_get_ns.return_value = ns

        result = await _validate_namespace("workbench", ["group1", "group2"], mock_kube_client)

        assert result.name == "workbench"
        assert result.id == "test-id"
        mock_get_ns.assert_called_once_with(mock_kube_client, "workbench")


@pytest.mark.asyncio
async def test_validate_namespace_forbidden_standalone_mode_wrong_namespace(mock_kube_client: MagicMock) -> None:
    """Test that non-default namespace is rejected in standalone mode."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", True),
        patch("app.namespaces.security.DEFAULT_NAMESPACE", "workbench"),
        pytest.raises(HTTPException) as exc_info,
    ):
        await _validate_namespace("other-namespace", ["group1"], mock_kube_client)

    assert exc_info.value.status_code == 403
    assert "standalone mode" in exc_info.value.detail.lower()
    assert "workbench" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_namespace_success_combined_mode(mock_kube_client: MagicMock) -> None:
    """Test successful namespace validation in combined mode with user having access."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
    ):
        ns = make_namespace_crd(name="project-a", project_id="proj-a-id")
        mock_get_ns.return_value = ns

        result = await _validate_namespace("project-a", ["project-a", "project-b"], mock_kube_client)

        assert result.name == "project-a"
        assert result.id == "proj-a-id"
        mock_get_ns.assert_called_once_with(mock_kube_client, "project-a")


@pytest.mark.asyncio
async def test_validate_namespace_forbidden_combined_mode_no_access(mock_kube_client: MagicMock) -> None:
    """Test that namespace is rejected when user lacks group membership in combined mode."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        pytest.raises(HTTPException) as exc_info,
    ):
        await _validate_namespace("project-a", ["project-b", "project-c"], mock_kube_client)

    assert exc_info.value.status_code == 403
    assert "does not have access" in exc_info.value.detail.lower()
    assert "project-a" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_namespace_not_found(mock_kube_client: MagicMock) -> None:
    """Test that non-existent namespace returns 404."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
        pytest.raises(HTTPException) as exc_info,
    ):
        mock_get_ns.return_value = None

        await _validate_namespace("missing-ns", ["missing-ns"], mock_kube_client)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()
    assert "missing-ns" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_namespace_missing_project_id_label(mock_kube_client: MagicMock) -> None:
    """Test that namespace without project-id label is rejected."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
        pytest.raises(HTTPException) as exc_info,
    ):
        ns = make_namespace_crd(name="system-ns", labels={}, project_id=None)
        mock_get_ns.return_value = ns

        await _validate_namespace("system-ns", ["system-ns"], mock_kube_client)

    assert exc_info.value.status_code == 403
    assert "not a workbench namespace" in exc_info.value.detail.lower()
    assert "project-id" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_validate_namespace_empty_user_groups(mock_kube_client: MagicMock) -> None:
    """Test that user with no groups cannot access any namespace in combined mode."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        pytest.raises(HTTPException) as exc_info,
    ):
        await _validate_namespace("project-a", [], mock_kube_client)

    assert exc_info.value.status_code == 403
    assert "does not have access" in exc_info.value.detail.lower()


def test_is_valid_workbench_namespace_standalone_mode_default_namespace() -> None:
    """Test namespace validation in standalone mode with default namespace."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", True),
        patch("app.namespaces.security.DEFAULT_NAMESPACE", "workbench"),
    ):
        ns = make_namespace_crd(name="workbench", project_id="test-id")

        result = is_valid_workbench_namespace(ns, ["any", "groups"])

        assert result is True


def test_is_valid_workbench_namespace_standalone_mode_wrong_namespace() -> None:
    """Test namespace validation in standalone mode with non-default namespace."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", True),
        patch("app.namespaces.security.DEFAULT_NAMESPACE", "workbench"),
    ):
        ns = make_namespace_crd(name="other-ns", project_id="test-id")

        result = is_valid_workbench_namespace(ns, ["other-ns"])

        assert result is False


def test_is_valid_workbench_namespace_standalone_mode_no_project_id() -> None:
    """Test namespace without project-id label is rejected in standalone mode."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", True),
        patch("app.namespaces.security.DEFAULT_NAMESPACE", "workbench"),
    ):
        ns = make_namespace_crd(name="workbench", labels={}, project_id=None)

        result = is_valid_workbench_namespace(ns, ["workbench"])

        assert result is False


def test_is_valid_workbench_namespace_combined_mode_user_has_access() -> None:
    """Test namespace validation in combined mode when user has group membership."""
    with patch("app.namespaces.security.STANDALONE_MODE", False):
        ns = make_namespace_crd(name="project-a", project_id="proj-a-id")

        result = is_valid_workbench_namespace(ns, ["project-a", "project-b"])

        assert result is True


def test_is_valid_workbench_namespace_combined_mode_user_no_access() -> None:
    """Test namespace validation in combined mode when user lacks group membership."""
    with patch("app.namespaces.security.STANDALONE_MODE", False):
        ns = make_namespace_crd(name="project-a", project_id="proj-a-id")

        result = is_valid_workbench_namespace(ns, ["project-b", "project-c"])

        assert result is False


def test_is_valid_workbench_namespace_combined_mode_no_project_id() -> None:
    """Test namespace without project-id label is rejected in combined mode."""
    with patch("app.namespaces.security.STANDALONE_MODE", False):
        ns = make_namespace_crd(name="project-a", labels={}, project_id=None)

        result = is_valid_workbench_namespace(ns, ["project-a"])

        assert result is False


def test_is_valid_workbench_namespace_empty_user_groups_combined_mode() -> None:
    """Test that user with empty groups cannot access namespace in combined mode."""
    with patch("app.namespaces.security.STANDALONE_MODE", False):
        ns = make_namespace_crd(name="project-a", project_id="proj-a-id")

        result = is_valid_workbench_namespace(ns, [])

        assert result is False


@pytest.mark.asyncio
async def test_ensure_access_to_workbench_namespace_returns_name(mock_kube_client: MagicMock) -> None:
    """Test ensure_access_to_workbench_namespace returns namespace name on success."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
    ):
        ns = make_namespace_crd(name="project-a", project_id="proj-a-id")
        mock_get_ns.return_value = ns

        result = await ensure_access_to_workbench_namespace("project-a", ["project-a"], mock_kube_client)

        assert result == "project-a"
        assert isinstance(result, str)


@pytest.mark.asyncio
async def test_ensure_access_to_workbench_namespace_raises_on_invalid(mock_kube_client: MagicMock) -> None:
    """Test ensure_access_to_workbench_namespace raises HTTPException on validation failure."""
    with patch("app.namespaces.security.STANDALONE_MODE", False):
        with pytest.raises(HTTPException) as exc_info:
            await ensure_access_to_workbench_namespace("project-a", ["project-b"], mock_kube_client)

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_workbench_namespace_returns_namespace_object(mock_kube_client: MagicMock) -> None:
    """Test get_workbench_namespace returns full Namespace object on success."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
    ):
        ns = make_namespace_crd(
            name="project-a",
            project_id="proj-a-id",
            annotations={"key": "value"},
        )
        mock_get_ns.return_value = ns

        result = await get_workbench_namespace("project-a", ["project-a"], mock_kube_client)

        assert result.name == "project-a"
        assert result.id == "proj-a-id"
        assert result.labels == {"airm.silogen.ai/project-id": "proj-a-id"}


@pytest.mark.asyncio
async def test_get_workbench_namespace_raises_on_invalid(mock_kube_client: MagicMock) -> None:
    """Test get_workbench_namespace raises HTTPException on validation failure."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
        pytest.raises(HTTPException) as exc_info,
    ):
        mock_get_ns.return_value = None

        await get_workbench_namespace("missing-ns", ["missing-ns"], mock_kube_client)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_namespace_combined_mode_case_sensitive_matching(mock_kube_client: MagicMock) -> None:
    """Test that namespace matching in user groups is case-sensitive in combined mode."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        pytest.raises(HTTPException) as exc_info,
    ):
        await _validate_namespace("Project-A", ["project-a"], mock_kube_client)

    assert exc_info.value.status_code == 403
    assert "does not have access" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_validate_namespace_multiple_user_groups(mock_kube_client: MagicMock) -> None:
    """Test validation succeeds when namespace matches any of multiple user groups."""
    with (
        patch("app.namespaces.security.STANDALONE_MODE", False),
        patch("app.namespaces.security.get_namespace", autospec=True) as mock_get_ns,
    ):
        ns = make_namespace_crd(name="project-c", project_id="proj-c-id")
        mock_get_ns.return_value = ns

        result = await _validate_namespace(
            "project-c", ["project-a", "project-b", "project-c", "project-d"], mock_kube_client
        )

        assert result.name == "project-c"
