# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import ANY, patch
from uuid import uuid4

import pytest
import yaml
from fastapi import status

from app import app  # type: ignore
from app.charts.models import Chart
from app.charts.schemas import ChartFile as ChartFileSchema
from app.charts.schemas import ChartListResponse, ChartResponse
from app.utilities.database import get_session
from app.utilities.exceptions import ConflictException, NotFoundException
from app.utilities.security import auth_token_claimset, get_user_email
from app.workloads.enums import WorkloadType

from ..conftest import get_test_client


@pytest.fixture(autouse=True)
def setup_app_depends(mock_super_admin_claimset, db_session):
    """Set up common dependency overrides for chart tests.

    This fixture configures the common dependency overrides needed for chart tests
    and cleans them up after the test is complete.
    """
    # Set up common dependency overrides
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[auth_token_claimset] = lambda: mock_super_admin_claimset
    app.dependency_overrides[get_user_email] = lambda: mock_super_admin_claimset["preferred_username"]

    yield

    # Clean up after the test
    app.dependency_overrides.clear()


@pytest.fixture
def chart_id():
    return uuid4()


@pytest.fixture
def chart_response():
    return ChartResponse(
        id=uuid4(),
        name="Test Chart",
        slug="test-chart-slug",
        display_name="Test Chart Display Name",
        type=WorkloadType.INFERENCE,
        signature={"key": "value"},
        usage_scope="user",  # Add usage_scope to the mock response
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        created_by="test@example.com",
        updated_by="test@example.com",
        files=[],
    )


@pytest.mark.asyncio
@patch("app.charts.router.list_charts", autospec=True)
async def test_list_charts(mock_repo_list_charts, sample_chart: Chart):
    expected_response = ChartListResponse.model_validate(sample_chart)
    mock_repo_list_charts.return_value = [expected_response]

    with get_test_client() as client:
        response = client.get("/v1/charts")
        response_data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response_data, list)
        assert len(response_data) == 1
        assert response_data[0]["id"] == str(expected_response.id)
        assert response_data[0]["name"] == expected_response.name
        assert response_data[0]["usage_scope"] == expected_response.usage_scope  # Verify actual usage_scope value
        mock_repo_list_charts.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.list_charts", autospec=True)
async def test_list_charts_with_type_filter(mock_repo_list_charts, sample_chart: Chart):
    expected_response = ChartListResponse.model_validate(sample_chart)
    mock_repo_list_charts.return_value = [expected_response]

    with get_test_client() as client:
        response = client.get("/v1/charts", params={"type": WorkloadType.INFERENCE.value})
        response_data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response_data, list)
        assert len(response_data) == 1
        assert response_data[0]["id"] == str(expected_response.id)
        assert response_data[0]["name"] == expected_response.name
        assert response_data[0]["usage_scope"] == expected_response.usage_scope  # Verify actual usage_scope value

        mock_repo_list_charts.assert_awaited_once_with(ANY, WorkloadType.INFERENCE)


@pytest.mark.asyncio
@patch("app.charts.router.list_charts", autospec=True)
async def test_list_charts_without_type_filter_forwards_none(mock_repo_list_charts, sample_chart: Chart):
    expected_response = ChartListResponse.model_validate(sample_chart)
    mock_repo_list_charts.return_value = [expected_response]

    with get_test_client() as client:
        response = client.get("/v1/charts")
        assert response.status_code == status.HTTP_200_OK

        mock_repo_list_charts.assert_awaited_once_with(ANY, None)


@pytest.mark.asyncio
async def test_list_charts_with_invalid_type_returns_422():
    with get_test_client() as client:
        response = client.get("/v1/charts", params={"type": "INVALID_TYPE"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_list_charts_with_lowercase_type_returns_422():
    with get_test_client() as client:
        response = client.get("/v1/charts", params={"type": "inference"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch("app.charts.router.create_chart", autospec=True)
async def test_create_chart_success(mock_repo_create_chart, chart_response):
    mock_repo_create_chart.return_value = chart_response

    test_files = [ChartFileSchema(path="file1.yaml", content="content1")]
    with get_test_client() as client:
        response = client.post(
            "/v1/charts",
            data={"name": chart_response.name, "type": chart_response.type.value},
            files=[
                ("signature", ("values.yaml", yaml.dump(chart_response.signature), "text/yaml")),
                *[("files", (f.path, f.content, "text/plain")) for f in test_files],
            ],
        )
        assert response.status_code == status.HTTP_201_CREATED
        response_json = response.json()
        assert response_json["id"] == str(chart_response.id)
        assert response_json["name"] == chart_response.name
        assert response_json["type"] == chart_response.type.value
        assert "usage_scope" in response_json  # Verify usage_scope is included

        mock_repo_create_chart.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.update_chart", autospec=True)
async def test_update_chart_success(
    mock_update_chart,
    chart_response,
):
    mock_update_chart.return_value = chart_response

    with get_test_client() as client:
        response = client.put(
            f"/v1/charts/{chart_response.id}",
            data={"name": chart_response.name, "type": chart_response.type.value},
            files=[
                ("signature", ("values.yaml", yaml.dump(chart_response.signature), "text/yaml")),
                ("files", ("file1.yaml", "file content", "text/plain")),
            ],
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(chart_response.id)
    assert data["name"] == chart_response.name
    assert data["type"] == chart_response.type.value
    assert "usage_scope" in data  # Verify usage_scope is included

    mock_update_chart.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.update_chart", autospec=True)
async def test_update_chart_success_without_files(
    mock_update_chart,
    chart_response,
):
    mock_update_chart.return_value = chart_response

    with get_test_client() as client:
        response = client.put(
            f"/v1/charts/{chart_response.id}",
            data={"name": chart_response.name, "type": chart_response.type.value},
            files=[
                ("signature", ("values.yaml", yaml.dump(chart_response.signature), "text/yaml")),
            ],
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(chart_response.id)
    assert data["name"] == chart_response.name

    mock_update_chart.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.update_chart", autospec=True)
async def test_update_chart_conflict(
    mock_update_chart,
    chart_response,
):
    mock_update_chart.side_effect = ConflictException("Chart with the same name already exists")

    with get_test_client() as client:
        response = client.put(
            f"/v1/charts/{chart_response.id}",
            data={"name": chart_response.name, "type": chart_response.type.value},
            files=[
                ("signature", ("values.yaml", yaml.dump(chart_response.signature), "text/yaml")),
            ],
        )

    assert response.status_code == status.HTTP_409_CONFLICT

    mock_update_chart.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.repository.select_chart")
async def test_update_chart_invalid_yaml(
    mock_select_chart,
    chart_response,
):
    # Mock chart selection to return existing chart (avoid DB issues)
    from app.charts.models import Chart

    mock_chart = Chart(
        id=chart_response.id, name=chart_response.name, type=chart_response.type, signature={"existing": "data"}
    )
    mock_select_chart.return_value = mock_chart

    # Test with actual invalid YAML that will cause parsing to fail
    with get_test_client() as client:
        response = client.put(
            f"/v1/charts/{chart_response.id}",
            data={"name": chart_response.name, "type": chart_response.type.value},
            files=[
                ("signature", ("bad.yaml", b"bad: [", "text/yaml")),
            ],
        )

    # Should return 400 due to invalid YAML parsing
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_data = response.json()
    assert "Invalid YAML" in response_data["detail"]


@pytest.mark.asyncio
@patch(
    "app.charts.router.create_chart",
    side_effect=ConflictException("Chart with the same name already exists"),
    autospec=True,
)
async def test_create_chart_duplicate_name(mock_repo_create_chart_integrity):
    test_files = [ChartFileSchema(path="env.txt", content="ENV=production")]
    with get_test_client() as client:
        response = client.post(
            "/v1/charts",
            data={"name": "duplicate-chart", "type": WorkloadType.FINE_TUNING},
            files=[
                ("signature", ("values.yaml", yaml.dump({"key": "value"}), "text/yaml")),
                *[("files", (f.path, f.content, "text/plain")) for f in test_files],
            ],
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]
        mock_repo_create_chart_integrity.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.create_chart", side_effect=ValueError("Invalid input"), autospec=True)
async def test_create_chart_invalid_values(mock_repo_create_chart_value_error):
    test_files = [ChartFileSchema(path="env.txt", content="ENV=production")]
    with get_test_client() as client:
        response = client.post(
            "/v1/charts",
            data={"name": "invalid-chart", "type": WorkloadType.FINE_TUNING},
            files=[
                ("signature", ("values.yaml", yaml.dump({"key": "value"}), "text/yaml")),
                *[("files", (f.path, f.content, "text/plain")) for f in test_files],
            ],
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid input" in response.json()["detail"]
        mock_repo_create_chart_value_error.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.delete_chart", return_value=False, autospec=True)
async def test_delete_chart_not_found(mock_repo_delete_chart_notfound):
    non_existent_chart_id = uuid4()
    with get_test_client() as client:
        response = client.delete(f"/v1/charts/{non_existent_chart_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Chart not found" in response.json()["detail"]
        mock_repo_delete_chart_notfound.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.delete_chart", autospec=True)
async def test_delete_chart_success(mock_repo_delete_chart, sample_chart: Chart):
    mock_repo_delete_chart.return_value = True

    with get_test_client() as client:
        response = client.delete(f"/v1/charts/{sample_chart.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_repo_delete_chart.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.charts.router.get_chart", autospec=True)
async def test_get_chart_success(mock_get_chart, chart_response):
    mock_get_chart.return_value = chart_response

    with get_test_client() as client:
        response = client.get(f"/v1/charts/{chart_response.id}")

        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        assert response_json["id"] == str(chart_response.id)
        assert response_json["name"] == chart_response.name
        assert response_json["type"] == chart_response.type.value
        assert "usage_scope" in response_json  # Verify usage_scope is included

        mock_get_chart.assert_awaited()


@pytest.mark.asyncio
@patch("app.charts.router.get_chart", autospec=True)
async def test_get_chart_not_found(mock_get_chart):
    non_existent_chart_id = uuid4()
    mock_get_chart.side_effect = NotFoundException(f"Chart with ID {non_existent_chart_id} not found")

    with get_test_client() as client:
        response = client.get(f"/v1/charts/{non_existent_chart_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert f"Chart with ID {non_existent_chart_id} not found" in response.json()["detail"]
        mock_get_chart.assert_awaited()


@pytest.mark.asyncio
@patch("app.charts.router.create_chart", autospec=True)
async def test_create_chart_forbidden(mock_repo_create_chart, chart_response, mock_claimset):
    # Override the default fixture to use a regular claimset
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset

    test_files = [ChartFileSchema(path="env.txt", content="ENV=production")]
    with get_test_client() as client:
        response = client.post(
            "/v1/charts",
            data={"name": chart_response.name, "type": chart_response.type.value},
            files=[
                ("signature", ("values.yaml", yaml.dump(chart_response.signature), "text/yaml")),
                *[("files", (f.path, f.content, "text/plain")) for f in test_files],
            ],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Missing required role: Super Administrator" in response.json()["detail"]

        mock_repo_create_chart.assert_not_called()


@pytest.mark.asyncio
@patch("app.charts.router.delete_chart", autospec=True)
async def test_delete_chart_forbidden(mock_repo_delete_chart, mock_claimset):
    # Override the default fixture to use a regular claimset
    app.dependency_overrides[auth_token_claimset] = lambda: mock_claimset

    chart_id = uuid4()

    with get_test_client() as client:
        response = client.delete(f"/v1/charts/{chart_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Missing required role: Super Administrator" in response.json()["detail"]

        mock_repo_delete_chart.assert_not_called()


@pytest.mark.asyncio
@patch("app.charts.router.list_charts", autospec=True)
async def test_list_charts_workspace_usage_scope(mock_repo_list_charts, workspace_charts):
    """Test that workspace charts return correct usage_scope values."""
    vscode_chart, mlflow_chart = workspace_charts

    # Create expected responses from real Chart models
    vscode_response = ChartListResponse.model_validate(vscode_chart)
    mlflow_response = ChartListResponse.model_validate(mlflow_chart)

    mock_repo_list_charts.return_value = [vscode_response, mlflow_response]

    with get_test_client() as client:
        response = client.get("/v1/charts")
        response_data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(response_data) == 2

        # Find charts by name and verify their usage_scope
        vscode_data = next(chart for chart in response_data if chart["name"] == "development-workspace")
        mlflow_data = next(chart for chart in response_data if chart["name"] == "dev-tracking-mlflow")

        # Verify the actual computed values from the Chart models
        assert vscode_data["usage_scope"] == "user"  # VSCode workspace -> user scope
        assert mlflow_data["usage_scope"] == "project"  # MLFlow workspace -> project scope

        mock_repo_list_charts.assert_awaited_once()
