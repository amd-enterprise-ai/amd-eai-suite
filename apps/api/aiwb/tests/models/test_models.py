# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from app.models.models import InferenceModel, OnboardingStatus


def test_onboarding_status_enum() -> None:
    """Test that OnboardingStatus enum has expected values."""
    assert OnboardingStatus.pending == "pending"
    assert OnboardingStatus.ready == "ready"
    assert OnboardingStatus.failed == "failed"

    # Test that the enum has the expected values
    assert set(OnboardingStatus) == {"pending", "ready", "failed"}


def test_inference_model_table_structure() -> None:
    """Test that InferenceModel can be instantiated with all fields."""
    model_id = uuid4()
    namespace = "test-namespace"

    model = InferenceModel(
        id=model_id,
        namespace=namespace,
        name="Test Model",
        onboarding_status=OnboardingStatus.ready,
        model_weights_path="/path/to/weights",
        canonical_name="test-model",
        created_by="test@example.com",
        updated_by="test@example.com",
    )

    # Verify all fields were set correctly
    assert model.id == model_id
    assert model.namespace == namespace
    assert model.name == "Test Model"
    assert model.onboarding_status == OnboardingStatus.ready
    assert model.model_weights_path == "/path/to/weights"
    assert model.canonical_name == "test-model"
