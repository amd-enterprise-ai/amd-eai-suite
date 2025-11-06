# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import pytest

from app.models.utils import (
    InvalidPathError,
    format_model_path,
    get_finetuned_model_weights_path,
    get_model_weights_path,
    validate_project_scoped_path,
)


def test_format_model_path():
    assert format_model_path("s3://bucket/path") == "s3://bucket/path"

    assert format_model_path("bucket/path") == "s3://bucket/path"
    assert format_model_path("/absolute/path") == "s3:///absolute/path"

    assert format_model_path("") == "s3://"

    with pytest.raises(TypeError):
        format_model_path(None)


def test_get_model_weights_path_basic():
    """Test basic functionality of get_model_weights_path"""
    result = get_model_weights_path("meta-llama/Llama-3.1-8B", "My Test Project")
    assert result == "my-test-project/models/meta-llama/Llama-3.1-8B"


def test_get_model_weights_path_with_special_characters():
    """Test get_model_weights_path with special characters in project name"""
    result = get_model_weights_path("test/model", "Test! @#$%^&*() Project")
    assert result == "test-project/models/test/model"


def test_get_model_weights_path_with_already_slugified_name():
    """Test get_model_weights_path with already slugified project name"""
    result = get_model_weights_path("test/model", "test-project")
    assert result == "test-project/models/test/model"


def test_get_model_weights_path_with_unicode_characters():
    """Test get_model_weights_path with unicode characters in project name"""
    result = get_model_weights_path("test/model", "Téśt Prójéct")
    assert result == "téśt-prójéct/models/test/model"


def test_get_finetuned_model_weights_path_basic():
    """Test basic functionality of get_finetuned_model_weights_path"""
    result = get_finetuned_model_weights_path("meta-llama/Llama-3.1-8B", "my-finetune", "My Test Project")
    assert result == "my-test-project/finetuned-models/meta-llama/Llama-3.1-8B/my-finetune"


def test_get_finetuned_model_weights_path_with_special_characters():
    """Test get_finetuned_model_weights_path with special characters in project name"""
    result = get_finetuned_model_weights_path("test/model", "custom-finetune", "Test! @#$%^&*() Project")
    assert result == "test-project/finetuned-models/test/model/custom-finetune"


def test_get_finetuned_model_weights_path_with_already_slugified_name():
    """Test get_finetuned_model_weights_path with already slugified project name"""
    result = get_finetuned_model_weights_path("test/model", "custom-finetune", "test-project")
    assert result == "test-project/finetuned-models/test/model/custom-finetune"


def test_validate_project_scoped_path_valid_with_base_path():
    """Test validate_project_scoped_path with valid path that starts with project name"""
    validate_project_scoped_path("test-project/models/meta-llama/Llama-3.1-8B", "Test Project")


def test_validate_project_scoped_path_valid_without_base_path():
    """Test validate_project_scoped_path with valid path that contains project name"""
    validate_project_scoped_path(
        "my-project/datasets/dataset1.jsonl",
        "My Project",
    )


def test_validate_project_scoped_path_valid_with_bucket_prefix():
    """Test validate_project_scoped_path with valid bucket-prefixed path"""
    validate_project_scoped_path("default-bucket/test-project/models/meta-llama/Llama-3.1-8B", "Test Project")
    validate_project_scoped_path("my-bucket/my-project/finetuned-models/base-model/fine-name", "My Project")


def test_validate_project_scoped_path_missing_project_name():
    """Test validate_project_scoped_path raises error when path doesn't include project name"""
    with pytest.raises(InvalidPathError) as exc_info:
        validate_project_scoped_path("models/meta-llama/Llama-3.1-8B", "Test Project")
    assert "must include the project name" in str(exc_info.value)


def test_validate_project_scoped_path_wrong_base_path():
    """Test validate_project_scoped_path raises error when path doesn't start with project name"""
    with pytest.raises(InvalidPathError) as exc_info:
        validate_project_scoped_path("wrong-project/models/meta-llama/Llama-3.1-8B", "Test Project")
    assert "must include the project name" in str(exc_info.value)


def test_validate_project_scoped_path_incorrect_project_name():
    """Test validate_project_scoped_path raises error when path has wrong project name"""
    with pytest.raises(InvalidPathError) as exc_info:
        validate_project_scoped_path(
            "wrong-project/models/meta-llama/Llama-3.1-8B",
            "Test Project",
        )
    assert "must include the project name" in str(exc_info.value)


def test_validate_project_scoped_path_bucket_prefix_wrong_project():
    """Test validate_project_scoped_path raises error when bucket-prefixed path has wrong project"""
    with pytest.raises(InvalidPathError) as exc_info:
        validate_project_scoped_path(
            "default-bucket/wrong-project/models/meta-llama/Llama-3.1-8B",
            "Test Project",
        )
    assert "must include the project name" in str(exc_info.value)


def test_validate_project_scoped_path_bucket_prefix_missing_project():
    """Test validate_project_scoped_path raises error when bucket-prefixed path missing project"""
    with pytest.raises(InvalidPathError) as exc_info:
        validate_project_scoped_path(
            "default-bucket/models/meta-llama/Llama-3.1-8B",
            "Test Project",
        )
    assert "must include the project name" in str(exc_info.value)
