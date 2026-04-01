# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for Overlays router endpoints using FastAPI TestClient."""

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api_common.exceptions import NotFoundException
from app import app  # type: ignore[attr-defined]
from app.overlays.schemas import OverlayResponse
from tests.dependency_overrides import BASE_OVERRIDES, override_dependencies


@pytest.fixture
def overlay_id() -> UUID:
    return uuid4()


@pytest.fixture
def chart_id() -> UUID:
    return uuid4()


@pytest.fixture
def overlay_response(chart_id: UUID) -> OverlayResponse:
    return OverlayResponse(
        id=uuid4(),
        canonical_name="test-overlay",
        chart_id=chart_id,
        overlay={"key": "value"},
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        created_by="test-user",
        updated_by="test-user",
    )


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.create_overlay", autospec=True)
def test_create_overlay(
    mock_service_create_overlay: MagicMock,
    mock_helper_parse_overlay: MagicMock,
    overlay_response: OverlayResponse,
    chart_id: UUID,
) -> None:
    """Test creating an overlay."""
    canonical_name = "test-mock-overlay"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data
    mock_service_create_overlay.return_value = overlay_response

    with TestClient(app) as client:
        response = client.post(
            "/v1/overlays",
            data={
                "chart_id": str(chart_id),
                "canonical_name": canonical_name,
            },
            files={
                "overlay_file": ("test.yaml", BytesIO(b"key: value"), "application/x-yaml"),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["canonical_name"] == overlay_response.canonical_name
    assert response_data["chart_id"] == str(overlay_response.chart_id)
    assert response_data["overlay"] == overlay_response.overlay

    mock_helper_parse_overlay.assert_awaited_once()
    mock_service_create_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.create_overlay", side_effect=ValueError("Chart not found"), autospec=True)
def test_create_overlay_non_existent_chart(
    mock_service_create_overlay: MagicMock, mock_helper_parse_overlay: MagicMock, chart_id: UUID
) -> None:
    """Test creating overlay with non-existent chart."""
    canonical_name = "test-mock-nonexistent-chart"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data

    with TestClient(app) as client:
        response = client.post(
            "/v1/overlays",
            data={
                "chart_id": str(chart_id),
                "canonical_name": canonical_name,
            },
            files={
                "overlay_file": ("test.yaml", BytesIO(b"key: value"), "application/x-yaml"),
            },
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Chart not found" in response.json()["detail"]

    mock_helper_parse_overlay.assert_awaited_once()
    mock_service_create_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.create_overlay", side_effect=ValueError("Duplicate canonical name"), autospec=True)
def test_create_overlay_duplicate(
    mock_service_create_overlay: MagicMock, mock_helper_parse_overlay: MagicMock, chart_id: UUID
) -> None:
    """Test creating duplicate overlay."""
    canonical_name = "test-mock-duplicate"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data

    with TestClient(app) as client:
        response = client.post(
            "/v1/overlays",
            data={
                "chart_id": str(chart_id),
                "canonical_name": canonical_name,
            },
            files={
                "overlay_file": ("test.yaml", BytesIO(b"key: value"), "application/x-yaml"),
            },
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Duplicate canonical name" in response.json()["detail"]

    mock_helper_parse_overlay.assert_awaited_once()
    mock_service_create_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.parse_overlay_file", side_effect=ValueError("Invalid YAML"), autospec=True)
def test_create_overlay_invalid_yaml(mock_helper_parse_overlay: MagicMock, chart_id: UUID) -> None:
    """Test creating overlay with invalid YAML."""
    canonical_name = "test-mock-invalid-yaml"

    with TestClient(app) as client:
        response = client.post(
            "/v1/overlays",
            data={
                "chart_id": str(chart_id),
                "canonical_name": canonical_name,
            },
            files={
                "overlay_file": ("test.yaml", BytesIO(b"invalid: yaml: content"), "application/x-yaml"),
            },
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid YAML" in response.json()["detail"]

    mock_helper_parse_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.update_overlay", autospec=True)
def test_update_overlay_with_file(
    mock_service_update_overlay: MagicMock,
    mock_helper_parse_overlay: MagicMock,
    overlay_response: OverlayResponse,
    chart_id: UUID,
) -> None:
    """Test updating an overlay with a new file."""
    canonical_name = "test-mock-overlay"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data
    mock_service_update_overlay.return_value = overlay_response

    with TestClient(app) as client:
        response = client.put(
            f"/v1/overlays/{overlay_response.id}",
            data={
                "chart_id": str(chart_id),
                "canonical_name": canonical_name,
            },
            files={
                "overlay_file": ("test.yaml", BytesIO(b"key: value"), "application/x-yaml"),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["canonical_name"] == overlay_response.canonical_name
    assert response_data["chart_id"] == str(overlay_response.chart_id)
    assert response_data["overlay"] == overlay_response.overlay

    mock_helper_parse_overlay.assert_awaited_once()
    mock_service_update_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.update_overlay", autospec=True)
def test_update_overlay_without_file(
    mock_update_overlay: MagicMock, overlay_response: OverlayResponse, chart_id: UUID
) -> None:
    """Test updating overlay without providing a new file."""
    canonical_name = "test-no-file"
    mock_update_overlay.return_value = overlay_response

    with TestClient(app) as client:
        response = client.put(
            f"/v1/overlays/{overlay_response.id}",
            data={
                "chart_id": str(chart_id),
                "canonical_name": canonical_name,
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["canonical_name"] == overlay_response.canonical_name
    assert data["chart_id"] == str(overlay_response.chart_id)

    mock_update_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.update_overlay", autospec=True)
def test_update_overlay_empty_request(mock_update_overlay: MagicMock, overlay_response: OverlayResponse) -> None:
    """Test updating overlay with no data returns validation error."""
    with TestClient(app) as client:
        resp = client.put(f"/v1/overlays/{overlay_response.id}")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    response_data = resp.json()
    assert "detail" in response_data
    assert "Either 'overlay_file' or 'chart_id' or 'canonical_name' must be provided" in response_data["detail"]


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.get_overlay_by_id", autospec=True)
def test_get_overlay(mock_service_get_overlay_by_id: MagicMock, overlay_response: OverlayResponse) -> None:
    """Test getting an overlay by ID."""
    mock_service_get_overlay_by_id.return_value = overlay_response

    with TestClient(app) as client:
        response = client.get(f"/v1/overlays/{overlay_response.id}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == str(overlay_response.id)
    assert response_data["canonical_name"] == overlay_response.canonical_name
    assert response_data["chart_id"] == str(overlay_response.chart_id)
    assert response_data["overlay"] == overlay_response.overlay
    assert response_data["created_by"] == overlay_response.created_by

    mock_service_get_overlay_by_id.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.get_overlay_by_id", autospec=True)
def test_get_overlay_not_found(mock_service_get_overlay_by_id: MagicMock, overlay_id: UUID) -> None:
    """Test getting a non-existent overlay returns 404."""
    mock_service_get_overlay_by_id.side_effect = NotFoundException("Overlay not found")

    with TestClient(app) as client:
        response = client.get(f"/v1/overlays/{overlay_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Overlay not found" in response.json()["detail"]

    mock_service_get_overlay_by_id.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.delete_overlay_by_id_service", autospec=True)
def test_delete_overlay(mock_service_delete_overlay: MagicMock, overlay_id: UUID) -> None:
    """Test deleting an overlay."""
    mock_service_delete_overlay.return_value = None

    with TestClient(app) as client:
        response = client.delete(f"/v1/overlays/{overlay_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_service_delete_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.delete_overlay_by_id_service", autospec=True)
def test_delete_overlay_not_found(mock_service_delete_overlay: MagicMock, overlay_id: UUID) -> None:
    """Test deleting a non-existent overlay returns 404."""
    mock_service_delete_overlay.side_effect = NotFoundException("Overlay not found")

    with TestClient(app) as client:
        response = client.delete(f"/v1/overlays/{overlay_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Overlay not found" in response.json()["detail"]

    mock_service_delete_overlay.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.list_overlays", autospec=True)
def test_list_overlays(mock_list_overlays: MagicMock, overlay_response: OverlayResponse) -> None:
    """Test listing overlays."""
    mock_list_overlays.return_value = [overlay_response]

    with TestClient(app) as client:
        response = client.get("/v1/overlays")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert len(response_data["data"]) == 1
    assert response_data["data"][0]["id"] == str(overlay_response.id)

    mock_list_overlays.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.list_overlays", autospec=True)
def test_list_overlays_with_chart_filter(mock_list_overlays: MagicMock, chart_id: UUID) -> None:
    """Test listing overlays with chart_id filter."""
    mock_list_overlays.return_value = []

    with TestClient(app) as client:
        response = client.get(f"/v1/overlays?chart_id={chart_id}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "data" in response_data
    assert len(response_data["data"]) == 0

    mock_list_overlays.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.delete_overlays", autospec=True)
def test_batch_delete_overlays(mock_delete_overlays: MagicMock) -> None:
    """Test batch deleting overlays."""
    ids_to_delete = [uuid4(), uuid4()]
    mock_delete_overlays.return_value = ids_to_delete

    with TestClient(app) as client:
        response = client.post(
            "/v1/overlays/delete",
            json={"ids": [str(id) for id in ids_to_delete]},
        )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_delete_overlays.assert_awaited_once()


@override_dependencies(BASE_OVERRIDES)
@patch("app.overlays.router.delete_overlays", autospec=True)
def test_batch_delete_overlays_partial_not_found(mock_delete_overlays: MagicMock) -> None:
    """Test batch delete when some overlays are not found."""
    ids_to_delete = [uuid4(), uuid4()]
    # Only return first ID as deleted
    mock_delete_overlays.return_value = [ids_to_delete[0]]

    with TestClient(app) as client:
        response = client.post(
            "/v1/overlays/delete",
            json={"ids": [str(id) for id in ids_to_delete]},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]
    mock_delete_overlays.assert_awaited_once()
