# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app import app  # type: ignore
from app.overlays.schemas import OverlayResponse
from app.utilities.database import get_session
from app.utilities.security import auth_token_claimset, get_user_email

from ..conftest import get_test_client


@pytest.fixture(autouse=True)
def setup_app_depends(mock_super_admin_claimset, db_session):
    """Set up common dependency overrides for overlay tests.

    This fixture configures the common dependency overrides needed for overlay tests
    and cleans them up after the test is complete.
    """
    # Set up common dependency overrides
    app.dependency_overrides[auth_token_claimset] = lambda: mock_super_admin_claimset
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_user_email] = lambda: mock_super_admin_claimset["preferred_username"]

    yield

    # Clean up after the test
    app.dependency_overrides.clear()


@pytest.fixture
def overlay_id():
    return uuid4()


@pytest.fixture
def chart_id():
    return uuid4()


@pytest.fixture
def overlay_response(chart_id):
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


@pytest.mark.asyncio
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.create_overlay", autospec=True)
async def test_create_overlay_success(
    mock_service_create_overlay, mock_helper_parse_overlay, overlay_response, chart_id
):
    canonical_name = "test-mock-overlay"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data
    mock_service_create_overlay.return_value = overlay_response

    with get_test_client() as client:
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


@pytest.mark.asyncio
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.create_overlay", side_effect=ValueError("Chart not found"), autospec=True)
async def test_create_overlay_non_existent_chart(mock_service_create_overlay, mock_helper_parse_overlay, chart_id):
    canonical_name = "test-mock-nonexistent-chart"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data
    with get_test_client() as client:
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


@pytest.mark.asyncio
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.create_overlay", side_effect=ValueError("Duplicate canonical name"), autospec=True)
async def test_create_overlay_duplicate(mock_service_create_overlay, mock_helper_parse_overlay, chart_id):
    canonical_name = "test-mock-duplicate"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data

    with get_test_client() as client:
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


@pytest.mark.asyncio
@patch("app.overlays.router.parse_overlay_file", side_effect=ValueError("Invalid YAML"), autospec=True)
async def test_create_overlay_invalid_yaml(mock_helper_parse_overlay, chart_id):
    canonical_name = "test-mock-invalid-yaml"

    with get_test_client() as client:
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


@pytest.mark.asyncio
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.update_overlay", autospec=True)
async def test_update_overlay_success(
    mock_service_update_overlay, mock_helper_parse_overlay, overlay_response, chart_id
):
    canonical_name = "test-mock-overlay"
    overlay_data = {"key": "value", "name": canonical_name}

    mock_helper_parse_overlay.return_value = overlay_data
    mock_service_update_overlay.return_value = overlay_response

    with get_test_client() as client:
        response = client.put(
            "/v1/overlays/" + str(overlay_response.id),
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


@pytest.mark.asyncio
@patch("app.overlays.router.update_overlay", autospec=True)
async def test_update_overlay_without_file(
    mock_update_overlay,
    overlay_response,
    chart_id,
):
    canonical_name = "test-no-file"
    mock_update_overlay.return_value = overlay_response

    with get_test_client() as client:
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


@pytest.mark.asyncio
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.update_overlay", autospec=True)
async def test_update_overlay_invalid_yaml(
    mock_update_overlay,
    mock_parse_overlay_file,
    overlay_response,
    chart_id,
):
    mock_parse_overlay_file.side_effect = Exception("Invalid YAML")

    with pytest.raises(Exception, match="Invalid YAML"):
        with get_test_client() as client:
            client.put(
                f"/v1/overlays/{overlay_response.id}",
                data={
                    "chart_id": str(chart_id),
                },
                files={
                    "overlay_file": ("bad.yaml", BytesIO(b"bad: ["), "application/x-yaml"),
                },
            )

    mock_parse_overlay_file.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.overlays.router.update_overlay", autospec=True)
async def test_update_overlay_not_found(
    mock_update_overlay,
    overlay_response,
    chart_id,
):
    mock_update_overlay.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found")
    with get_test_client() as client:
        resp = client.put(
            f"/v1/overlays/{overlay_response.id}",
            data={
                "chart_id": str(chart_id),
            },
        )
    resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("app.overlays.router.update_overlay", autospec=True)
async def test_update_overlay_empty(
    mock_update_overlay,
    overlay_response,
):
    mock_update_overlay.side_effect = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found")
    with get_test_client() as client:
        resp = client.put(
            f"/v1/overlays/{overlay_response.id}",
        )
    resp.status_code == status.HTTP_400_BAD_REQUEST
    response_data = resp.json()
    assert "detail" in response_data
    assert response_data["detail"] == "Either 'overlay_file' or 'chart_id' or 'canonical_name' must be provided"


@patch("app.overlays.router.get_overlay_by_id", autospec=True)
async def test_get_overlay_success(mock_service_get_overlay_by_id, overlay_response, chart_id):
    mock_service_get_overlay_by_id.return_value = overlay_response
    with get_test_client() as client:
        response = client.get(f"/v1/overlays/{overlay_response.id}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == str(overlay_response.id)
    assert response_data["canonical_name"] == overlay_response.canonical_name
    assert response_data["chart_id"] == str(overlay_response.chart_id)
    assert response_data["overlay"] == overlay_response.overlay
    assert response_data["created_by"] == overlay_response.created_by

    mock_service_get_overlay_by_id.assert_awaited_once()


@pytest.mark.asyncio
@patch(
    "app.overlays.router.get_overlay_by_id",
    side_effect=HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found"),
)
async def test_get_overlay_not_found(mock_service_get_overlay_by_id, overlay_id):
    """Test retrieval of a non-existent overlay (mocking router's HTTPException response)."""
    with get_test_client() as client:
        response = client.get(f"/v1/overlays/{overlay_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Overlay not found" in response.json()["detail"]

    mock_service_get_overlay_by_id.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.overlays.router.delete_overlay_by_id_service", autospec=True)
async def test_delete_overlay_success(mock_service_delete_overlay_by_id_service, overlay_id):
    mock_service_delete_overlay_by_id_service.return_value = None

    with get_test_client() as client:
        response = client.delete(f"/v1/overlays/{overlay_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_service_delete_overlay_by_id_service.assert_awaited_once()


@pytest.mark.asyncio
@patch(
    "app.overlays.router.delete_overlay_by_id_service",
    side_effect=HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found"),
)
async def test_delete_overlay_not_found(mock_service_delete_overlay_by_id_service, overlay_id):
    with get_test_client() as client:
        response = client.delete(f"/v1/overlays/{overlay_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Overlay not found" in response.json()["detail"]

    mock_service_delete_overlay_by_id_service.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.overlays.router.parse_overlay_file", autospec=True)
@patch("app.overlays.router.create_overlay", autospec=True)
async def test_create_overlay_forbidden(mock_service_create_overlay, mock_helper_parse_overlay, chart_id):
    # Override the default super admin claimset with a regular user claimset
    regular_user_claimset = {"preferred_username": "regular-user", "realm_access": {"roles": ["user"]}}
    app.dependency_overrides[auth_token_claimset] = lambda: regular_user_claimset
    app.dependency_overrides[get_user_email] = lambda: regular_user_claimset["preferred_username"]

    canonical_name = "test-forbidden-overlay"

    with get_test_client() as client:
        response = client.post(
            "/v1/overlays",
            data={
                "chart_id": str(chart_id),
                "canonical_name": canonical_name,
            },
            files={"overlay_file": ("test.yaml", BytesIO(b"key: value"), "application/x-yaml")},
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Missing required role: Super Administrator" in response.json()["detail"]

    mock_service_create_overlay.assert_not_called()
    mock_helper_parse_overlay.assert_not_called()


@pytest.mark.asyncio
@patch("app.overlays.router.delete_overlay_by_id_service", autospec=True)
async def test_delete_overlay_forbidden(mock_service_delete_overlay_by_id_service, overlay_id):
    # Override the default super admin claimset with a regular user claimset
    regular_user_claimset = {"preferred_username": "regular-user", "realm_access": {"roles": ["user"]}}
    app.dependency_overrides[auth_token_claimset] = lambda: regular_user_claimset
    app.dependency_overrides[get_user_email] = lambda: regular_user_claimset["preferred_username"]

    with get_test_client() as client:
        response = client.delete(f"/v1/overlays/{overlay_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Missing required role: Super Administrator" in response.json()["detail"]

    mock_service_delete_overlay_by_id_service.assert_not_called()
