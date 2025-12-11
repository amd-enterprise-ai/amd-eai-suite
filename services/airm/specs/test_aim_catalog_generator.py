#!/usr/bin/env python3
# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Simple test to verify AimCatalogGenerator works correctly.
"""

import sys
from pathlib import Path

# Add libraries to path
sys.path.insert(0, str(Path(__file__).parent / "libraries"))

from AimCatalogGenerator import AimCatalogGenerator


def test_model_loading():
    """Test that models are loaded correctly from CSV."""
    print("Test 1: Model Loading")
    print("=" * 60)

    generator = AimCatalogGenerator("config/aim_models.csv", "full")

    assert len(generator.models) == 24, f"Expected 24 models, got {len(generator.models)}"
    print(f"✓ Loaded {len(generator.models)} models correctly")

    # Check first model
    first_model = generator.models[0]
    assert "model_name" in first_model
    assert "image_name" in first_model
    assert "gpu_count" in first_model
    assert "requires_hf_token" in first_model
    print("✓ Model structure is correct")
    print(
        f"  Example: {first_model['model_name']} (GPUs: {first_model['gpu_count']}, HF Token: {first_model['requires_hf_token']})"
    )
    print()


def test_variable_extraction():
    """Test that _get_variable method works."""
    print("Test 2: Variable Extraction")
    print("=" * 60)

    generator = AimCatalogGenerator("config/aim_models.csv", "full")

    # Create a mock suite object to test variable extraction
    class MockVariable:
        def __init__(self, name, value):
            self.name = name
            self.value = [value]

    class MockResource:
        def __init__(self):
            self.variables = [
                MockVariable("${INCLUDE_TAGS}", "gpus:1"),
                MockVariable("${EXCLUDE_TAGS}", "requires-hf-token"),
                MockVariable("${TEST_MODE}", "smoke"),
            ]

    class MockSuite:
        def __init__(self):
            self.resource = MockResource()

    suite = MockSuite()

    # Test extracting variables
    include = generator._get_variable(suite, "INCLUDE_TAGS")
    assert include == "gpus:1", f"Expected 'gpus:1', got '{include}'"
    print(f"✓ INCLUDE_TAGS extracted correctly: {include}")

    exclude = generator._get_variable(suite, "EXCLUDE_TAGS")
    assert exclude == "requires-hf-token", f"Expected 'requires-hf-token', got '{exclude}'"
    print(f"✓ EXCLUDE_TAGS extracted correctly: {exclude}")

    mode = generator._get_variable(suite, "TEST_MODE")
    assert mode == "smoke", f"Expected 'smoke', got '{mode}'"
    print(f"✓ TEST_MODE extracted correctly: {mode}")

    # Test non-existent variable
    nonexistent = generator._get_variable(suite, "NONEXISTENT")
    assert nonexistent is None, f"Expected None, got '{nonexistent}'"
    print("✓ Non-existent variable returns None")
    print()


def test_test_modes():
    """Test different test modes."""
    print("Test 3: Test Modes")
    print("=" * 60)

    for mode in ["full", "smoke", "quick"]:
        generator = AimCatalogGenerator("config/aim_models.csv", mode)
        assert generator.test_mode == mode
        print(f"✓ Test mode '{mode}' initialized correctly")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("=" * 60)
    print("AimCatalogGenerator Tests")
    print("=" * 60)
    print()

    try:
        test_model_loading()
        test_variable_extraction()
        test_test_modes()

        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print()
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
