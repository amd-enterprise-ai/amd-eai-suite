# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest

from app.aims.service import process_aim_cluster_model_resource, publish_aim_cluster_models_message_to_queue
from app.workloads.constants import AIM_CLUSTER_MODEL_RESOURCE_PLURAL, AIM_SERVICE_API_GROUP


def test_process_valid_resource():
    resource = {
        "metadata": {"name": "aim-test-model-0-8-4"},
        "spec": {"image": "docker.io/test/aim-test-model:0.8.4"},
        "status": {
            "status": "Ready",
            "imageMetadata": {
                "originalLabels": {
                    "com.amd.aim.model.canonicalName": "test/model",
                    "com.amd.aim.hfToken.required": "False",
                    "com.amd.aim.title": "Test Model",
                    "org.opencontainers.image.description": "A test model",
                },
            },
        },
    }

    result = process_aim_cluster_model_resource(resource)

    assert result is not None
    assert result.resource_name == "aim-test-model-0-8-4"
    assert result.image_reference == "docker.io/test/aim-test-model:0.8.4"
    assert result.labels == resource["status"]["imageMetadata"]["originalLabels"]
    assert result.status == "Ready"


def test_process_resource_missing_image():
    resource = {"metadata": {"name": "test"}, "spec": {}, "status": {}}
    result = process_aim_cluster_model_resource(resource)
    assert result is None


def test_process_resource_missing_image_metadata():
    resource = {"metadata": {"name": "test"}, "spec": {"image": "test:1.0"}, "status": {}}
    result = process_aim_cluster_model_resource(resource)
    assert result is None


def test_process_resource_exception_handling():
    result = process_aim_cluster_model_resource(None)
    assert result is None


def test_process_resource_missing_original_labels():
    """Test that AIMs without originalLabels are skipped."""
    resource = {
        "metadata": {"name": "test-model-no-labels"},
        "spec": {"image": "test/model:1.0"},
        "status": {
            "status": "Ready",
            "imageMetadata": {
                # originalLabels is missing
                "model": {"canonicalName": "test/model"},
            },
        },
    }
    result = process_aim_cluster_model_resource(resource)
    assert result is None


def test_process_resource_empty_original_labels():
    """Test that AIMs with empty originalLabels are skipped."""
    resource = {
        "metadata": {"name": "test-model-empty-labels"},
        "spec": {"image": "test/model:1.0"},
        "status": {
            "status": "Ready",
            "imageMetadata": {
                "originalLabels": {},  # Empty labels
            },
        },
    }
    result = process_aim_cluster_model_resource(resource)
    assert result is None


@pytest.mark.asyncio
@patch("app.aims.service.get_installed_version_for_custom_resource", return_value="v1alpha1")
@patch("app.aims.service.publish_to_common_feedback_queue")
@patch("app.aims.service.client.CustomObjectsApi")
async def test_publish_aim_cluster_models_message_to_queue_success(mock_api_class, mock_publish, mock_get_version):
    """Test successful sync of AIMClusterModel resources."""
    # Mock API response
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.list_cluster_custom_object.return_value = {
        "items": [
            {
                "metadata": {"name": "model1"},
                "spec": {"image": "test/model1:1.0"},
                "status": {
                    "status": "Ready",
                    "imageMetadata": {
                        "originalLabels": {
                            "com.amd.aim.model.canonicalName": "test/model1",
                        },
                    },
                },
            },
            {
                "metadata": {"name": "model2"},
                "spec": {"image": "test/model2:2.0"},
                "status": {
                    "status": "Pending",
                    "imageMetadata": {
                        "originalLabels": {
                            "com.amd.aim.model.canonicalName": "test/model2",
                        },
                    },
                },
            },
        ]
    }

    fake_connection = MagicMock()
    fake_channel = MagicMock()

    await publish_aim_cluster_models_message_to_queue(fake_connection, fake_channel)

    # Verify version lookup was called
    mock_get_version.assert_called_once()

    # Verify API was called with dynamically resolved version
    mock_api.list_cluster_custom_object.assert_called_once_with(
        group=AIM_SERVICE_API_GROUP, version="v1alpha1", plural=AIM_CLUSTER_MODEL_RESOURCE_PLURAL
    )

    # Verify publish was called
    mock_publish.assert_called_once()
    call_args = mock_publish.call_args
    message = call_args.kwargs["message"]

    assert message.message_type == "aim_cluster_models"
    assert len(message.models) == 2
    assert message.models[0].resource_name == "model1"
    assert message.models[0].image_reference == "test/model1:1.0"
    assert message.models[0].status == "Ready"
    assert message.models[1].resource_name == "model2"
    assert message.models[1].status == "Pending"


@pytest.mark.asyncio
@patch("app.aims.service.get_installed_version_for_custom_resource", return_value="v1alpha1")
@patch("app.aims.service.publish_to_common_feedback_queue")
@patch("app.aims.service.client.CustomObjectsApi")
async def test_publish_aim_cluster_models_message_to_queue_no_items(mock_api_class, mock_publish, mock_get_version):
    """Test sync when no AIMClusterModel resources exist."""
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.list_cluster_custom_object.return_value = {"items": []}

    fake_connection = MagicMock()
    fake_channel = MagicMock()

    # Should not raise exception
    await publish_aim_cluster_models_message_to_queue(fake_connection, fake_channel)

    mock_api.list_cluster_custom_object.assert_called_once()
    # Should still publish with empty models list
    mock_publish.assert_called_once()


@pytest.mark.asyncio
@patch("app.aims.service.get_installed_version_for_custom_resource", return_value=None)
async def test_publish_aim_cluster_models_message_to_queue_crd_not_found(mock_get_version):
    """Test sync when AIMClusterModel CRD doesn't exist."""
    fake_connection = MagicMock()
    fake_channel = MagicMock()

    # Should log warning but not raise exception
    await publish_aim_cluster_models_message_to_queue(fake_connection, fake_channel)

    # Version lookup was called and returned None
    mock_get_version.assert_called_once()


@pytest.mark.asyncio
@patch("app.aims.service.get_installed_version_for_custom_resource", return_value="v1alpha1")
@patch("app.aims.service.publish_to_common_feedback_queue")
@patch("app.aims.service.client.CustomObjectsApi")
async def test_publish_aim_cluster_models_skips_aims_without_labels(mock_api_class, mock_publish, mock_get_version):
    """Test that AIMs without originalLabels are skipped during sync."""
    # Mock API response with mix of valid and invalid AIMs
    mock_api = MagicMock()
    mock_api_class.return_value = mock_api
    mock_api.list_cluster_custom_object.return_value = {
        "items": [
            {
                "metadata": {"name": "valid-model"},
                "spec": {"image": "test/valid:1.0"},
                "status": {
                    "status": "Ready",
                    "imageMetadata": {
                        "originalLabels": {
                            "com.amd.aim.model.canonicalName": "test/valid",
                        },
                    },
                },
            },
            {
                "metadata": {"name": "model-no-labels"},
                "spec": {"image": "test/no-labels:1.0"},
                "status": {
                    "status": "Ready",
                    "imageMetadata": {
                        # Missing originalLabels
                        "model": {"canonicalName": "test/no-labels"},
                    },
                },
            },
            {
                "metadata": {"name": "model-empty-labels"},
                "spec": {"image": "test/empty-labels:1.0"},
                "status": {
                    "status": "Ready",
                    "imageMetadata": {
                        "originalLabels": {},  # Empty labels
                    },
                },
            },
        ]
    }

    fake_connection = MagicMock()
    fake_channel = MagicMock()

    await publish_aim_cluster_models_message_to_queue(fake_connection, fake_channel)

    # Verify publish was called
    mock_publish.assert_called_once()
    call_args = mock_publish.call_args
    message = call_args.kwargs["message"]

    # Only the valid model should be in the message
    assert message.message_type == "aim_cluster_models"
    assert len(message.models) == 1
    assert message.models[0].resource_name == "valid-model"
    assert message.models[0].image_reference == "test/valid:1.0"
