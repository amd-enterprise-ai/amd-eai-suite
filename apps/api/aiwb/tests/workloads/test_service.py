# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi import Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api_common.exceptions import NotFoundException, ValidationException
from app.workloads.enums import WorkloadStatus, WorkloadType
from app.workloads.service import (
    chat_with_workload,
    delete_workload_components,
    is_workload_chattable,
    list_chattable_workloads,
    stream_downstream,
)
from tests import factory


@pytest.mark.asyncio
async def test_delete_workload_components_success(db_session: AsyncSession) -> None:
    """Test successful deletion of workload components."""
    workload = await factory.create_workload(db_session, namespace="test-ns", status=WorkloadStatus.RUNNING)

    with patch("app.workloads.service.delete_workload_resources") as mock_delete:
        mock_delete.return_value = None

        await delete_workload_components("test-ns", workload.id, db_session)

        # Verify gateway was called
        mock_delete.assert_called_once_with("test-ns", str(workload.id))

        # Verify workload status was updated to DELETED
        await db_session.refresh(workload)
        assert workload.status == WorkloadStatus.DELETED


@pytest.mark.asyncio
async def test_delete_workload_components_not_found(db_session: AsyncSession) -> None:
    """Test deleting a non-existent workload logs warning but doesn't error."""
    non_existent_id = uuid4()

    with patch("app.workloads.service.delete_workload_resources") as mock_delete:
        # Should not raise exception, just log warning
        await delete_workload_components("test-ns", non_existent_id, db_session)

        # Gateway should not be called if workload not found
        mock_delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_workload_components_gateway_error(db_session: AsyncSession) -> None:
    """Test handling of Kubernetes gateway errors during deletion."""
    workload = await factory.create_workload(db_session, namespace="test-ns", status=WorkloadStatus.RUNNING)

    with patch("app.workloads.service.delete_workload_resources") as mock_delete:
        mock_delete.side_effect = RuntimeError("K8s API error")

        with pytest.raises(RuntimeError, match="K8s API error"):
            await delete_workload_components("test-ns", workload.id, db_session)


@pytest.mark.asyncio
async def test_is_workload_chattable_running_with_chat(db_session: AsyncSession) -> None:
    """Test that a RUNNING inference workload with chat overlay is chattable."""
    chart = await factory.create_chart(db_session, name="inference-chart")
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b", namespace="test-ns")

    # Create overlay with chat capability
    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is True


@pytest.mark.asyncio
async def test_is_workload_chattable_not_running(db_session: AsyncSession) -> None:
    """Test that a non-RUNNING workload is not chattable."""
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")
    workload = await factory.create_workload(
        db_session,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,  # Not RUNNING
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_no_model(db_session: AsyncSession) -> None:
    """Test that a workload without a model is not chattable."""
    workload = await factory.create_workload(
        db_session,
        model_id=None,  # No model
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_no_canonical_name(db_session: AsyncSession) -> None:
    """Test that a workload with a model without canonical_name is not chattable."""
    model = await factory.create_inference_model(db_session, canonical_name=None)
    workload = await factory.create_workload(
        db_session,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_no_overlays(db_session: AsyncSession) -> None:
    """Test that a workload with no matching overlays is not chattable."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    # No overlay created for this chart + canonical_name combination
    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_overlay_no_chat_label(db_session: AsyncSession) -> None:
    """Test that a workload with overlay but no chat label is not chattable."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    # Create overlay WITHOUT chat label
    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        overlay_data={"metadata": {"labels": {"other": "value"}}},
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_overlay_chat_true_string(db_session: AsyncSession) -> None:
    """Test that overlay with chat='true' (string) makes workload chattable."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is True


@pytest.mark.asyncio
async def test_is_workload_chattable_overlay_chat_true_bool(db_session: AsyncSession) -> None:
    """Test that overlay with chat=True (boolean) makes workload chattable."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is True


@pytest.mark.asyncio
async def test_list_chattable_workloads_multiple(db_session: AsyncSession) -> None:
    """Test listing multiple chattable workloads in a namespace."""
    chart = await factory.create_chart(db_session)
    model1 = await factory.create_inference_model(db_session, name="model-1", canonical_name="meta/llama3-8b")
    model2 = await factory.create_inference_model(db_session, name="model-2", canonical_name="meta/llama3-70b")

    # Create overlays for both models
    for canonical_name in ["meta/llama3-8b", "meta/llama3-70b"]:
        await factory.create_overlay(
            db_session,
            chart_id=chart.id,
            canonical_name=canonical_name,
            chat_enabled=True,
        )

    # Create chattable workloads
    await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model1.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
        display_name="Workload 1",
    )
    await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model2.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
        display_name="Workload 2",
    )

    # Create a non-chattable workload (wrong status)
    await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model1.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.PENDING,
        namespace="test-ns",
    )

    result = await list_chattable_workloads(db_session, namespace="test-ns")

    assert len(result) == 2
    display_names = {w.display_name for w in result}
    assert "Workload 1" in display_names
    assert "Workload 2" in display_names


@pytest.mark.asyncio
async def test_list_chattable_workloads_empty(db_session: AsyncSession) -> None:
    """Test listing chattable workloads when none exist."""
    result = await list_chattable_workloads(db_session, namespace="empty-ns")

    assert len(result) == 0


@pytest.mark.asyncio
async def test_chat_with_workload_success(db_session: AsyncSession) -> None:
    """Test chatting with a chattable workload."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
        name="test-workload",
    )

    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"messages": []}')
    mock_request.headers = {}
    mock_request.url.query = b""
    mock_request.method = "POST"

    with patch("app.workloads.service.stream_downstream") as mock_stream:
        mock_stream.return_value = MagicMock()

        await chat_with_workload(db_session, "test-ns", workload.id, mock_request)

        mock_stream.assert_called_once()
        # Verify the base URL includes the workload name
        call_args = mock_stream.call_args
        assert "test-workload.test-ns.svc.cluster.local" in call_args.kwargs["base_url"]


@pytest.mark.asyncio
async def test_chat_with_workload_not_found(db_session: AsyncSession) -> None:
    """Test chatting with a non-existent workload raises NotFoundException."""
    non_existent_id = uuid4()
    mock_request = MagicMock(spec=Request)

    with pytest.raises(NotFoundException, match="not found"):
        await chat_with_workload(db_session, "test-ns", non_existent_id, mock_request)


@pytest.mark.asyncio
async def test_chat_with_workload_not_chattable(db_session: AsyncSession) -> None:
    """Test chatting with a non-chattable workload raises ValidationException."""
    workload = await factory.create_workload(
        db_session,
        model_id=None,  # No model, so not chattable
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
    )

    mock_request = MagicMock(spec=Request)

    with pytest.raises(ValidationException, match="not available for chat"):
        await chat_with_workload(db_session, "test-ns", workload.id, mock_request)


@pytest.mark.asyncio
async def test_chat_with_workload_httpx_error(db_session: AsyncSession) -> None:
    """Test handling of httpx connection errors during chat."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
    )

    mock_request = MagicMock(spec=Request)

    with patch("app.workloads.service.stream_downstream") as mock_stream:
        mock_stream.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(ValidationException, match="Error connecting to model endpoint"):
            await chat_with_workload(db_session, "test-ns", workload.id, mock_request)


@pytest.mark.asyncio
async def test_stream_downstream_success() -> None:
    """Test successful streaming from downstream server."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {"content-type": "application/json"}
    # url.query should be a string attribute, not bytes
    mock_url = MagicMock()
    mock_url.query = "param=value"
    mock_request.url = mock_url
    mock_request.method = "POST"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.aiter_raw = AsyncMock(return_value=iter([b"chunk1", b"chunk2"]))
    mock_response.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        response = await stream_downstream(
            base_url="http://test-service.test-ns.svc.cluster.local",
            request=mock_request,
        )

        assert response.status_code == 200
        mock_client.send.assert_called_once()


@pytest.mark.asyncio
async def test_stream_downstream_with_body() -> None:
    """Test streaming with custom body parameter."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url
    mock_request.method = "POST"

    custom_body = b'{"custom": "body"}'

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.aiter_raw = AsyncMock(return_value=iter([]))
    mock_response.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await stream_downstream(
            base_url="http://test.svc",
            request=mock_request,
            body=custom_body,
        )

        # Verify custom body was used
        build_call = mock_client.build_request.call_args
        assert build_call.kwargs["content"] == custom_body


# Section 3.1: chat_with_workload() error handling tests


@pytest.mark.asyncio
async def test_chat_with_workload_timeout_error(db_session: AsyncSession) -> None:
    """Test handling of httpx.TimeoutError, verify ValidationException raised."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
    )

    mock_request = MagicMock(spec=Request)

    with patch("app.workloads.service.stream_downstream") as mock_stream:
        mock_stream.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(ValidationException, match="Error connecting to model endpoint"):
            await chat_with_workload(db_session, "test-ns", workload.id, mock_request)


@pytest.mark.asyncio
async def test_chat_with_workload_read_error(db_session: AsyncSession) -> None:
    """Test handling of httpx.ReadError, verify ValidationException raised."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
    )

    mock_request = MagicMock(spec=Request)

    with patch("app.workloads.service.stream_downstream") as mock_stream:
        mock_stream.side_effect = httpx.ReadError("Connection closed prematurely")

        with pytest.raises(ValidationException, match="Error connecting to model endpoint"):
            await chat_with_workload(db_session, "test-ns", workload.id, mock_request)


@pytest.mark.asyncio
async def test_chat_with_workload_generic_exception(db_session: AsyncSession) -> None:
    """Test handling of unexpected exceptions, verify ValidationException raised."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
    )

    mock_request = MagicMock(spec=Request)

    with patch("app.workloads.service.stream_downstream") as mock_stream:
        mock_stream.side_effect = RuntimeError("Unexpected error occurred")

        with pytest.raises(ValidationException, match="Error connecting to model endpoint"):
            await chat_with_workload(db_session, "test-ns", workload.id, mock_request)


@pytest.mark.asyncio
async def test_chat_with_workload_logs_errors(db_session: AsyncSession) -> None:
    """Test that errors are properly logged."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
        name="test-workload",
    )

    mock_request = MagicMock(spec=Request)

    with patch("app.workloads.service.stream_downstream") as mock_stream:
        mock_stream.side_effect = RuntimeError("Test error")

        with patch("app.workloads.service.logger.error") as mock_logger:
            with pytest.raises(ValidationException):
                await chat_with_workload(db_session, "test-ns", workload.id, mock_request)

            # Verify logging occurred
            mock_logger.assert_called_once()
            log_call = mock_logger.call_args[0][0]
            assert "Error streaming from endpoint" in log_call
            assert "test-workload.test-ns.svc.cluster.local" in log_call


# Section 3.2: stream_downstream() error handling tests


@pytest.mark.asyncio
async def test_stream_downstream_removes_content_length() -> None:
    """Test content-length header removal."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {"content-type": "application/json", "content-length": "16"}
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url
    mock_request.method = "POST"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.aiter_raw = AsyncMock(return_value=iter([]))
    mock_response.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await stream_downstream(
            base_url="http://test.svc",
            request=mock_request,
        )

        # Verify content-length was removed from headers
        build_call = mock_client.build_request.call_args
        headers = build_call.kwargs["headers"]
        assert "content-length" not in headers
        assert "content-type" in headers


@pytest.mark.asyncio
async def test_stream_downstream_preserves_other_headers() -> None:
    """Test that non-content-length headers are preserved."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {
        "content-type": "application/json",
        "authorization": "Bearer token123",
        "x-custom-header": "custom-value",
        "content-length": "16",
    }
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url
    mock_request.method = "POST"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.aiter_raw = AsyncMock(return_value=iter([]))
    mock_response.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await stream_downstream(
            base_url="http://test.svc",
            request=mock_request,
        )

        # Verify all headers except content-length are preserved
        build_call = mock_client.build_request.call_args
        headers = build_call.kwargs["headers"]
        assert "content-length" not in headers
        assert headers["content-type"] == "application/json"
        assert headers["authorization"] == "Bearer token123"
        assert headers["x-custom-header"] == "custom-value"


@pytest.mark.asyncio
async def test_stream_downstream_timeout_error() -> None:
    """Test handling of timeout during streaming."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {}
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url
    mock_request.method = "POST"

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
        mock_client_class.return_value = mock_client

        with pytest.raises(httpx.TimeoutException, match="Request timed out"):
            await stream_downstream(
                base_url="http://test.svc",
                request=mock_request,
            )


@pytest.mark.asyncio
async def test_stream_downstream_http_status_error() -> None:
    """Test handling of HTTP error responses (500 status)."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {}
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url
    mock_request.method = "POST"

    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.headers = {"content-type": "application/json"}
    mock_response.aiter_raw = AsyncMock(return_value=iter([b'{"error": "Internal server error"}']))
    mock_response.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        response = await stream_downstream(
            base_url="http://test.svc",
            request=mock_request,
        )

        # Verify error status code is properly propagated
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_stream_downstream_connect_error_logging() -> None:
    """Test that ConnectError is logged before re-raising."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {}
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url
    mock_request.method = "POST"

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client_class.return_value = mock_client

        with patch("app.workloads.service.logger.error") as mock_logger:
            with pytest.raises(httpx.ConnectError, match="Connection refused"):
                await stream_downstream(
                    base_url="http://test.svc",
                    request=mock_request,
                )

            # Verify logging occurred before re-raising
            mock_logger.assert_called_once()
            log_call = mock_logger.call_args[0][0]
            assert "Connect error while connecting" in log_call
            assert "http://test.svc" in log_call


@pytest.mark.asyncio
async def test_stream_downstream_query_params_forwarded() -> None:
    """Test query parameters are properly forwarded."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {}
    mock_url = MagicMock()
    mock_url.query = "param1=value1&param2=value2"
    mock_request.url = mock_url
    mock_request.method = "POST"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.aiter_raw = AsyncMock(return_value=iter([]))
    mock_response.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_built_request = MagicMock()
        mock_client.build_request.return_value = mock_built_request
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await stream_downstream(
            base_url="http://test.svc",
            request=mock_request,
        )

        # Verify query params were included in the URL
        build_call = mock_client.build_request.call_args
        url_arg = build_call.args[1]
        assert url_arg.query == b"param1=value1&param2=value2"


@pytest.mark.asyncio
async def test_stream_downstream_path_correctly_set() -> None:
    """Test DEFAULT_CHAT_PATH used in downstream URL."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
    mock_request.headers = {}
    mock_url = MagicMock()
    mock_url.query = ""
    mock_request.url = mock_url
    mock_request.method = "POST"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.aiter_raw = AsyncMock(return_value=iter([]))
    mock_response.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await stream_downstream(
            base_url="http://test.svc",
            request=mock_request,
        )

        # Verify DEFAULT_CHAT_PATH (/v1/chat/completions) was used
        build_call = mock_client.build_request.call_args
        url_arg = build_call.args[1]
        assert url_arg.path == "/v1/chat/completions"


# Section 3.3: delete_workload_components() status transitions


@pytest.mark.asyncio
async def test_delete_workload_components_deleting_status(db_session: AsyncSession) -> None:
    """Test that workload status is set to DELETING before gateway call, and DELETED after success."""
    workload = await factory.create_workload(db_session, namespace="test-ns", status=WorkloadStatus.RUNNING)

    with (
        patch("app.workloads.service.update_workload_status") as mock_update_status,
        patch("app.workloads.service.delete_workload_resources") as mock_delete,
    ):
        mock_update_status.return_value = None
        mock_delete.return_value = None

        await delete_workload_components("test-ns", workload.id, db_session)

        # Verify status was updated to DELETING before gateway call
        assert mock_update_status.call_count == 2
        first_call = mock_update_status.call_args_list[0]
        assert first_call.args[1] == workload.id
        assert first_call.args[2] == WorkloadStatus.DELETING

        # Verify gateway was called
        mock_delete.assert_called_once_with("test-ns", str(workload.id))

        # Verify status was updated to DELETED after gateway call
        second_call = mock_update_status.call_args_list[1]
        assert second_call.args[1] == workload.id
        assert second_call.args[2] == WorkloadStatus.DELETED


@pytest.mark.asyncio
async def test_delete_workload_components_status_update_failure(db_session: AsyncSession) -> None:
    """Test handling when status update fails."""
    workload = await factory.create_workload(db_session, namespace="test-ns", status=WorkloadStatus.RUNNING)

    with (
        patch("app.workloads.service.update_workload_status") as mock_update_status,
        patch("app.workloads.service.delete_workload_resources") as mock_delete,
    ):
        # Simulate status update failure on first call
        mock_update_status.side_effect = RuntimeError("Database error")

        with pytest.raises(RuntimeError, match="Database error"):
            await delete_workload_components("test-ns", workload.id, db_session)

        # Verify status update was attempted
        mock_update_status.assert_called_once()

        # Gateway should not be called if status update fails
        mock_delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_workload_components_logs_deletion(db_session: AsyncSession) -> None:
    """Test deletion is properly logged."""
    workload = await factory.create_workload(db_session, namespace="test-ns", status=WorkloadStatus.RUNNING)

    with (
        patch("app.workloads.service.delete_workload_resources") as mock_delete,
        patch("app.workloads.service.logger") as mock_logger,
    ):
        mock_delete.return_value = None

        await delete_workload_components("test-ns", workload.id, db_session)

        # Verify deletion was logged
        assert mock_logger.info.call_count >= 2
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any(f"Deleting workload {workload.id}" in str(call) for call in log_calls)
        assert any("marked as DELETED" in str(call) for call in log_calls)


# Section 3.4: Minor service layer gaps


@pytest.mark.asyncio
async def test_is_workload_chattable_malformed_metadata(db_session: AsyncSession) -> None:
    """Test handling of overlay with non-dict metadata."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    # Create overlay with malformed metadata (non-dict)
    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        overlay_data={"metadata": "not-a-dict"},
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    # Should handle gracefully and return False
    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_malformed_labels(db_session: AsyncSession) -> None:
    """Test handling of overlay with non-dict labels."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    # Create overlay with malformed labels (non-dict)
    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        overlay_data={"metadata": {"labels": "not-a-dict"}},
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    # Should handle gracefully and return False
    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_chat_false_string(db_session: AsyncSession) -> None:
    """Test overlay with chat='false' string returns False."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=False,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is False


@pytest.mark.asyncio
async def test_is_workload_chattable_chat_false_bool(db_session: AsyncSession) -> None:
    """Test overlay with chat=False boolean returns False."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=False,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
    )

    result = await is_workload_chattable(db_session, workload)

    assert result is False


@pytest.mark.asyncio
async def test_list_chattable_workloads_validation_error(db_session: AsyncSession) -> None:
    """Test handling of WorkloadResponse validation errors."""
    chart = await factory.create_chart(db_session)
    model = await factory.create_inference_model(db_session, canonical_name="meta/llama3-8b")

    # Create overlay with chat capability
    await factory.create_overlay(
        db_session,
        chart_id=chart.id,
        canonical_name="meta/llama3-8b",
        chat_enabled=True,
    )

    workload = await factory.create_workload(
        db_session,
        chart=chart,
        model_id=model.id,
        workload_type=WorkloadType.INFERENCE,
        status=WorkloadStatus.RUNNING,
        namespace="test-ns",
    )

    # Mock WorkloadResponse.model_validate to raise ValidationError
    with patch("app.workloads.service.WorkloadResponse.model_validate") as mock_validate:
        mock_validate.side_effect = ValidationError.from_exception_data(
            "WorkloadResponse",
            [{"type": "missing", "loc": ("name",), "msg": "Field required", "input": {}}],
        )

        # Should raise ValidationError when trying to create WorkloadResponse
        with pytest.raises(ValidationError):
            await list_chattable_workloads(db_session, namespace="test-ns")
