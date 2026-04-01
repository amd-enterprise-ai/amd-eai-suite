# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for AimCatalogGenerator covering API mode, name filtering, and utility methods."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError

# Add libraries to path so AimCatalogGenerator is importable
sys.path.insert(0, str(Path(__file__).parent / "libraries"))

from AimCatalogGenerator import AimCatalogGenerator

# -- Fixtures --


@pytest.fixture()
def api_generator():
    """Generator in API mode (no name filter, no models loaded)."""
    return AimCatalogGenerator("api", "full")


# -- Name filter loading --


def test_load_model_names(tmp_path):
    """Model names are loaded correctly from a text file."""
    name_file = tmp_path / "models.txt"
    name_file.write_text("# comment\n\nalpha/Model-A\nbeta/Model-B\n   \n")

    names = AimCatalogGenerator._load_model_names(str(name_file))

    assert names == {"alpha/Model-A", "beta/Model-B"}


def test_load_model_names_file_not_found():
    """FileNotFoundError is raised for missing file."""
    with pytest.raises(FileNotFoundError, match="not found"):
        AimCatalogGenerator._load_model_names("/nonexistent/path.txt")


def test_init_with_name_filter(tmp_path):
    """Init with a file path sets name_filter."""
    name_file = tmp_path / "models.txt"
    name_file.write_text("model-x\nmodel-y\n")

    generator = AimCatalogGenerator(str(name_file), "full")

    assert generator.name_filter == {"model-x", "model-y"}
    assert generator.models == []


# -- API mode initialization --


@pytest.mark.parametrize("arg", ["api", "API", "Api"])
def test_api_mode_no_filter(arg):
    """'api' (case-insensitive) sets no name filter."""
    generator = AimCatalogGenerator(arg, "full")

    assert generator.name_filter is None
    assert generator.models == []


@pytest.mark.parametrize("mode", ["full", "smoke", "quick"])
def test_test_modes(mode):
    """All test modes are accepted and stored."""
    generator = AimCatalogGenerator("api", mode)
    assert generator.test_mode == mode


# -- Variable extraction --


class _MockVariable:
    def __init__(self, name, value):
        self.name = name
        self.value = [value]


class _MockSuite:
    class resource:
        variables = [
            _MockVariable("${INCLUDE_TAGS}", "gpus:1"),
            _MockVariable("${EXCLUDE_TAGS}", "requires-hf-token"),
            _MockVariable("${TEST_MODE}", "smoke"),
        ]


def test_get_variable_extracts_existing(api_generator):
    """_get_variable returns values from suite resource variables."""
    assert api_generator._get_variable(_MockSuite, "INCLUDE_TAGS") == "gpus:1"
    assert api_generator._get_variable(_MockSuite, "EXCLUDE_TAGS") == "requires-hf-token"
    assert api_generator._get_variable(_MockSuite, "TEST_MODE") == "smoke"


def test_get_variable_returns_none_for_missing(api_generator):
    """_get_variable returns None for non-existent variables."""
    assert api_generator._get_variable(_MockSuite, "NONEXISTENT") is None


# -- AIM-to-model mapping --


FULL_AIM_RESPONSE = {
    "metadata": {"name": "aim-meta-llama-llama-3-1-8b-instruct", "namespace": "default"},
    "spec": {"image": "amdenterpriseai/aim-meta-llama-llama-3-1-8b-instruct:0.8.4"},
    "status": {
        "status": "Ready",
        "imageMetadata": {
            "model": {
                "canonicalName": "meta-llama/Llama-3.1-8B-Instruct",
                "hfTokenRequired": True,
                "recommendedDeployments": [{"gpuCount": 1, "gpuModel": "MI300X", "metric": "latency"}],
                "tags": ["chat", "text-generation"],
            },
        },
    },
    "resource_name": "aim-meta-llama-llama-3-1-8b-instruct",
    "image_reference": "amdenterpriseai/aim-meta-llama-llama-3-1-8b-instruct:0.8.4",
    "status_value": "Ready",
}


def test_map_aim_to_model_full_response(api_generator):
    """Full API response maps all fields correctly."""
    model = api_generator._map_aim_to_model(FULL_AIM_RESPONSE)

    assert model["model_name"] == "meta-llama/Llama-3.1-8B-Instruct"
    assert model["image_name"] == "aim-meta-llama-llama-3-1-8b-instruct"
    assert model["docker_image"] == "amdenterpriseai/aim-meta-llama-llama-3-1-8b-instruct:0.8.4"
    assert model["gpu_count"] == 1
    assert model["requires_hf_token"] is True
    assert model["version"] == "0.8.4"


def test_map_aim_to_model_fallback_fields(api_generator):
    """Missing top-level computed fields fall back to nested equivalents."""
    aim_response = {
        "metadata": {"name": "aim-custom-model"},
        "spec": {"image": "registry.example.com/org/aim-custom-model:1.0.0"},
        "status": {
            "status": "Ready",
            "imageMetadata": {
                "model": {
                    "recommendedDeployments": [{"gpuCount": 4}],
                },
            },
        },
    }

    model = api_generator._map_aim_to_model(aim_response)

    assert model["model_name"] == "aim-custom-model"
    assert model["image_name"] == "aim-custom-model"
    assert model["docker_image"] == "registry.example.com/org/aim-custom-model:1.0.0"
    assert model["gpu_count"] == 4
    assert model["requires_hf_token"] is False
    assert model["version"] == "1.0.0"


# -- GPU count extraction --


@pytest.mark.parametrize(
    ("deployments", "expected"),
    [
        ([{"gpuCount": 8, "gpuModel": "MI300X"}], 8),
        ([{"numGpus": 8}], 8),
        ([{"gpu_count": 2}], 2),
        ([{"gpus": 16}], 16),
        # Multiple deployments returns minimum
        ([{"gpuCount": 2}, {"gpuCount": 4}], 2),
    ],
    ids=["gpuCount", "numGpus", "gpu_count", "gpus", "min-of-multiple"],
)
def test_extract_gpu_count(deployments, expected):
    """GPU count is extracted from various field names, min across deployments."""
    assert AimCatalogGenerator._extract_gpu_count(deployments) == expected


@pytest.mark.parametrize(
    "deployments",
    [
        [],
        None,
        [{"name": "default", "memory": "16Gi"}],
        ["not-a-dict", 42],
        [{"numGpus": "invalid"}],
        [{"numGpus": 0}],
    ],
    ids=["empty-list", "none", "no-gpu-fields", "non-dict", "invalid-value", "zero"],
)
def test_extract_gpu_count_defaults_to_1(deployments):
    """GPU count defaults to 1 when data is missing, invalid, or zero."""
    assert AimCatalogGenerator._extract_gpu_count(deployments) == 1


# -- Template-based GPU count --

TEMPLATES_RESPONSE = {
    "data": [
        {
            "metadata": {"name": "template-latency-mi300x"},
            "spec": {
                "hardware": {"gpu": {"requests": 1, "model": "MI300X"}},
                "metric": "latency",
            },
            "status": {},
        },
        {
            "metadata": {"name": "template-throughput-mi300x"},
            "spec": {
                "hardware": {"gpu": {"requests": 4, "model": "MI300X"}},
                "metric": "throughput",
            },
            "status": {},
        },
    ]
}


@pytest.fixture()
def api_ready_generator():
    """Generator with API state initialized (base URL and headers set)."""
    gen = AimCatalogGenerator("api", "full")
    gen._api_base_url = "https://aiwbapi.example.com"
    gen._api_headers = {"Authorization": "Bearer test-token"}
    return gen


def _mock_templates_response(data, status_code=200):
    """Create a mock requests.Response for the templates endpoint."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = data
    mock_response.raise_for_status.return_value = None
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
    return mock_response


@patch("requests.get")
def test_fetch_templates_gpu_count_returns_minimum(mock_get, api_ready_generator):
    """Templates GPU count returns minimum across all templates."""
    mock_get.return_value = _mock_templates_response(TEMPLATES_RESPONSE)

    result = api_ready_generator._fetch_templates_gpu_count("aim-test-model")

    assert result == 1
    mock_get.assert_called_once_with(
        "https://aiwbapi.example.com/v1/cluster/aims/templates",
        headers={"Authorization": "Bearer test-token"},
        params={"aim_resource_name": "aim-test-model"},
        timeout=30,
    )


@patch("requests.get")
def test_fetch_templates_gpu_count_single_template(mock_get, api_ready_generator):
    """Single template returns its GPU count directly."""
    single_template = {"data": [TEMPLATES_RESPONSE["data"][1]]}
    mock_get.return_value = _mock_templates_response(single_template)

    result = api_ready_generator._fetch_templates_gpu_count("aim-test-model")

    assert result == 4


@patch("requests.get")
def test_fetch_templates_gpu_count_empty_response(mock_get, api_ready_generator):
    """Empty templates response returns 0."""
    mock_get.return_value = _mock_templates_response({"data": []})

    result = api_ready_generator._fetch_templates_gpu_count("aim-test-model")

    assert result == 0


@patch("requests.get")
def test_fetch_templates_gpu_count_api_error(mock_get, api_ready_generator):
    """API errors return 0 without raising."""
    mock_get.return_value = _mock_templates_response({}, status_code=500)

    result = api_ready_generator._fetch_templates_gpu_count("aim-test-model")

    assert result == 0


def test_fetch_templates_gpu_count_no_base_url(api_generator):
    """Returns 0 when API base URL is not set (no API calls made)."""
    result = api_generator._fetch_templates_gpu_count("aim-test-model")

    assert result == 0


@patch("requests.get")
def test_fetch_templates_gpu_count_malformed_template(mock_get, api_ready_generator):
    """Templates missing gpu.requests fields are skipped."""
    malformed = {"data": [{"metadata": {}, "spec": {"hardware": {}}, "status": {}}]}
    mock_get.return_value = _mock_templates_response(malformed)

    result = api_ready_generator._fetch_templates_gpu_count("aim-test-model")

    assert result == 0


# -- Cached template GPU lookup --


@patch("requests.get")
def test_get_templates_gpu_count_caches_results(mock_get, api_ready_generator):
    """Repeated calls for the same AIM reuse the cached result (no extra HTTP calls)."""
    mock_get.return_value = _mock_templates_response(TEMPLATES_RESPONSE)

    result1 = api_ready_generator._get_templates_gpu_count("aim-test-model")
    result2 = api_ready_generator._get_templates_gpu_count("aim-test-model")

    assert result1 == 1
    assert result2 == 1
    assert mock_get.call_count == 1


# -- GPU count source selection in _map_aim_to_model --


@patch("requests.get")
def test_map_aim_to_model_prefers_templates(mock_get, api_ready_generator):
    """_map_aim_to_model uses template GPU count when available."""
    mock_get.return_value = _mock_templates_response(TEMPLATES_RESPONSE)

    aim_response = {
        "metadata": {"name": "aim-test-model"},
        "spec": {"image": "amdenterpriseai/aim-test-model:0.9.0"},
        "status": {
            "status": "Ready",
            "imageMetadata": {
                "model": {
                    "recommendedDeployments": [{"gpuCount": 8}],
                },
            },
        },
        "resource_name": "aim-test-model",
        "image_reference": "amdenterpriseai/aim-test-model:0.9.0",
    }

    model = api_ready_generator._map_aim_to_model(aim_response)

    # Templates return min(1, 4) = 1, not recommendedDeployments' 8
    assert model["gpu_count"] == 1


@patch("requests.get")
def test_map_aim_to_model_falls_back_to_recommended(mock_get, api_ready_generator):
    """_map_aim_to_model falls back to recommendedDeployments when templates return 0."""
    mock_get.return_value = _mock_templates_response({"data": []})

    aim_response = {
        "metadata": {"name": "aim-fallback-model"},
        "spec": {"image": "amdenterpriseai/aim-fallback-model:0.9.0"},
        "status": {
            "status": "Ready",
            "imageMetadata": {
                "model": {
                    "recommendedDeployments": [{"gpuCount": 8}],
                },
            },
        },
        "resource_name": "aim-fallback-model",
        "image_reference": "amdenterpriseai/aim-fallback-model:0.9.0",
    }

    model = api_ready_generator._map_aim_to_model(aim_response)

    assert model["gpu_count"] == 8


# -- Image name extraction --


@pytest.mark.parametrize(
    ("docker_image", "resource_name", "expected"),
    [
        ("amdenterpriseai/aim-foo:0.8.4", "fallback", "aim-foo"),
        ("registry.io/org/aim-bar:latest", "fallback", "aim-bar"),
        ("amdenterpriseai/aim-baz", "fallback", "aim-baz"),
        ("org/aim-digest@sha256:abc123", "fallback", "aim-digest"),
        ("", "my-fallback", "my-fallback"),
        ("", "", "unknown"),
    ],
    ids=["standard", "full-registry", "no-tag", "digest", "empty-uses-fallback", "both-empty"],
)
def test_extract_image_name(docker_image, resource_name, expected):
    """Image name is extracted from docker refs with proper fallbacks."""
    assert AimCatalogGenerator._extract_image_name(docker_image, resource_name) == expected


# -- Version extraction --


@pytest.mark.parametrize(
    ("docker_image", "expected"),
    [
        ("amdenterpriseai/aim-foo:0.8.5", "0.8.5"),
        ("registry.io/org/aim-bar:latest", "latest"),
        ("org/aim-foo:1.0.0-preview", "1.0.0-preview"),
        ("amdenterpriseai/aim-baz", None),
        ("", None),
        ("org/aim-foo@sha256:abcdef1234567890", None),
        ("registry.example.com:5000/org/aim-foo", None),
        ("registry:5000/aim-foo:0.8.5", "0.8.5"),
    ],
    ids=[
        "semver",
        "latest-tag",
        "prerelease",
        "no-tag",
        "empty",
        "sha256-digest",
        "registry-port-no-tag",
        "registry-port-with-tag",
    ],
)
def test_extract_version(docker_image, expected):
    """Version tag is extracted from docker image references."""
    assert AimCatalogGenerator._extract_version(docker_image) == expected


# -- Version key parsing --


@pytest.mark.parametrize(
    ("version_a", "version_b", "a_is_greater"),
    [
        ("0.9.0", "0.8.5", True),
        ("0.8.5", "0.8.5-preview", True),
        ("1.0.0", "0.99.99", True),
        ("0.8.5", "0.8.5", False),
    ],
    ids=["minor-higher", "release-beats-preview", "major-higher", "equal"],
)
def test_parse_version_key_ordering(version_a, version_b, a_is_greater):
    """Version keys compare correctly using packaging.version semantics."""
    key_a = AimCatalogGenerator._parse_version_key(version_a)
    key_b = AimCatalogGenerator._parse_version_key(version_b)

    if a_is_greater:
        assert key_a > key_b
    else:
        assert key_a == key_b


def test_parse_version_key_none_and_invalid():
    """None and invalid versions parse to Version('0') for safe comparison."""
    none_key = AimCatalogGenerator._parse_version_key(None)
    invalid_key = AimCatalogGenerator._parse_version_key("not-a-version")
    valid_key = AimCatalogGenerator._parse_version_key("0.8.5")

    assert none_key < valid_key
    assert invalid_key < valid_key


# -- Version filtering --


def _make_models(*versions):
    """Create model dicts with the given versions for filtering tests."""
    return [{"image_name": f"aim-model-{i}", "version": v, "model_name": f"model-{i}"} for i, v in enumerate(versions)]


@pytest.mark.parametrize(
    ("version_filter", "versions", "expected_versions"),
    [
        ("0.8.5", ["0.8.4", "0.8.5", "0.9.0"], ["0.8.5"]),
        (">=0.9.0", ["0.8.4", "0.8.5", "0.9.0", "1.0.0"], ["0.9.0", "1.0.0"]),
        (">0.8.5", ["0.8.4", "0.8.5", "0.9.0"], ["0.9.0"]),
        ("<=0.8.5", ["0.8.4", "0.8.5", "0.9.0"], ["0.8.4", "0.8.5"]),
        ("<0.9.0", ["0.8.4", "0.8.5", "0.9.0"], ["0.8.4", "0.8.5"]),
    ],
    ids=["exact", "gte", "gt", "lte", "lt"],
)
def test_apply_version_filter(api_generator, version_filter, versions, expected_versions):
    """Version filter operators select the correct subset of models."""
    models = _make_models(*versions)
    filtered = api_generator._apply_version_filter(models, version_filter)
    assert [m["version"] for m in filtered] == expected_versions


def test_apply_version_filter_skips_unversioned(api_generator):
    """Models without a version tag are excluded by version filters."""
    models = _make_models("0.8.5", None, "0.9.0")
    filtered = api_generator._apply_version_filter(models, ">=0.8.5")
    assert len(filtered) == 2
    assert all(m["version"] is not None for m in filtered)


def test_apply_version_filter_skips_unparseable(api_generator):
    """Models with unparseable version strings are excluded by version filters."""
    models = _make_models("0.8.5", "not-a-version", "0.9.0")
    filtered = api_generator._apply_version_filter(models, ">=0.8.5")
    assert len(filtered) == 2


def test_apply_version_filter_latest_returns_all(api_generator):
    """'latest' filter is a no-op (dedup is handled separately)."""
    models = _make_models("0.8.4", "0.8.5", "0.9.0")
    filtered = api_generator._apply_version_filter(models, "latest")
    assert len(filtered) == 3


def test_apply_version_filter_invalid_target(api_generator):
    """Invalid filter target returns all models with a warning."""
    models = _make_models("0.8.5", "0.9.0")
    filtered = api_generator._apply_version_filter(models, "not-a-version")
    assert len(filtered) == 2


def test_apply_version_filter_none_returns_all(api_generator):
    """None filter is a no-op."""
    models = _make_models("0.8.4", "0.8.5")
    filtered = api_generator._apply_version_filter(models, None)
    assert filtered == models


def test_apply_version_filter_empty_returns_all(api_generator):
    """Empty string filter is a no-op."""
    models = _make_models("0.8.4", "0.8.5")
    filtered = api_generator._apply_version_filter(models, "")
    assert filtered == models


# -- Deduplication --


def test_dedup_keeps_highest_version(api_generator):
    """Dedup by image_name keeps the model with the highest version."""
    models = [
        {"image_name": "aim-foo", "version": "0.8.4", "model_name": "foo-old"},
        {"image_name": "aim-foo", "version": "0.9.0", "model_name": "foo-new"},
        {"image_name": "aim-bar", "version": "1.0.0", "model_name": "bar"},
    ]
    result = api_generator._deduplicate_models(models)

    assert len(result) == 2
    assert result[0]["version"] == "0.9.0"
    assert result[0]["model_name"] == "foo-new"
    assert result[1]["image_name"] == "aim-bar"


def test_dedup_keeps_first_when_no_version(api_generator):
    """Dedup keeps the first model when neither has a version."""
    models = [
        {"image_name": "aim-foo", "version": None, "model_name": "first"},
        {"image_name": "aim-foo", "version": None, "model_name": "second"},
    ]
    result = api_generator._deduplicate_models(models)

    assert len(result) == 1
    assert result[0]["model_name"] == "first"


def test_dedup_no_duplicates_is_noop(api_generator):
    """Dedup with all unique image_names returns all models."""
    models = [
        {"image_name": "aim-a", "version": "1.0.0", "model_name": "a"},
        {"image_name": "aim-b", "version": "2.0.0", "model_name": "b"},
        {"image_name": "aim-c", "version": "3.0.0", "model_name": "c"},
    ]
    result = api_generator._deduplicate_models(models)

    assert len(result) == 3


# -- Snake_case API field fallbacks --


def test_map_aim_to_model_snake_case_fields(api_generator):
    """API response with snake_case fields maps correctly."""
    aim_response = {
        "metadata": {"name": "aim-snake-model"},
        "spec": {"image": "registry.io/aim-snake-model:0.9.0"},
        "status": {
            "status": "Ready",
            "image_metadata": {
                "model": {
                    "canonical_name": "org/SnakeModel",
                    "hf_token_required": True,
                    "recommended_deployments": [{"gpu_count": 2}],
                },
            },
        },
    }

    model = api_generator._map_aim_to_model(aim_response)

    assert model["model_name"] == "org/SnakeModel"
    assert model["gpu_count"] == 2
    assert model["requires_hf_token"] is True


def test_map_aim_to_model_minimal_input(api_generator):
    """Minimal/empty input produces safe defaults without raising."""
    model = api_generator._map_aim_to_model({"metadata": {}, "spec": {}, "status": {}})

    assert model["model_name"] == ""
    assert model["image_name"] == "unknown"
    assert model["docker_image"] == ""
    assert model["gpu_count"] == 1
    assert model["requires_hf_token"] is False
    assert model["version"] is None


# -- Name filter error paths --


def test_name_filter_file_not_found():
    """FileNotFoundError is raised for non-existent name filter path."""
    with pytest.raises(FileNotFoundError, match="not found"):
        AimCatalogGenerator("/nonexistent/path/models.txt", "full")
