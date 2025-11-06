# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, mock_open, patch

from app.aims.fetching import discover_images, fetch_tag_labels, generate_kaiwo_manifests, main


@patch("app.aims.fetching.OrasClient")
def test_fetch_tag_labels_no_config_digest(mock_client_class):
    mock_client = Mock()
    mock_client.get_manifest.return_value = {}

    result = fetch_tag_labels(mock_client, "aim-test", "1.0.0")
    assert result is None


@patch("app.aims.fetching.OrasClient")
def test_fetch_tag_labels_no_labels(mock_client_class):
    mock_client = Mock()
    mock_client.get_manifest.return_value = {"config": {"digest": "sha256:abc123"}}
    mock_response = Mock()
    mock_response.json.return_value = {"config": {}}
    mock_client.get_blob.return_value = mock_response

    result = fetch_tag_labels(mock_client, "aim-test", "1.0.0")
    assert result is None


@patch("app.aims.fetching.OrasClient")
def test_fetch_tag_labels_successful(mock_client_class):
    mock_client = Mock()
    mock_client.get_manifest.return_value = {"config": {"digest": "sha256:abc123"}}
    mock_response = Mock()
    mock_response.json.return_value = {"config": {"Labels": {"vendor": "AMD", "version": "1.0"}}}
    mock_client.get_blob.return_value = mock_response

    result = fetch_tag_labels(mock_client, "aim-test", "1.0.0")
    assert result == {"tag": "1.0.0", "labels": {"vendor": "AMD", "version": "1.0"}}


@patch("app.aims.fetching.requests")
def test_discover_images_filters_by_prefix(mock_requests):
    mock_response = Mock()
    mock_response.json.return_value = [
        {"name": "aim-llama"},
        {"name": "aim-mistral"},
        {"name": "other-image"},
        {"name": "aim-base"},
        {"name": "aim-base-rc"},
    ]
    mock_response.raise_for_status = Mock()
    mock_requests.get.return_value = mock_response

    result = discover_images(Mock())
    assert "aim-llama" in result
    assert "aim-mistral" in result
    assert "other-image" not in result
    assert "aim-base" not in result
    assert "aim-base-rc" not in result


@patch("app.aims.fetching.requests")
def test_discover_images_empty_response(mock_requests):
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()
    mock_requests.get.return_value = mock_response

    result = discover_images(Mock())
    assert result == []


@patch("app.aims.fetching.AIM_METADATA_FILE_PATH")
def test_generate_kaiwo_manifests_filters_by_label(mock_metadata_path):
    mock_metadata_path.parent = Mock()
    mock_metadata_path.parent.parent = Mock()
    mock_metadata_path.parent.parent.parent = Mock()
    mock_metadata_path.parent.parent.parent.parent = Mock()

    mock_file = mock_open()
    mock_path = Mock()
    mock_path.open = mock_file
    mock_metadata_path.parent.parent.parent.parent.__truediv__ = Mock(return_value=mock_path)

    results = [
        {
            "name": "aim-llama",
            "tags": [
                {
                    "tag": "1.0.0",
                    "labels": {"com.amd.aim.model.recommendedDeployments": "vllm"},
                },
                {
                    "tag": "2.0.0",
                    "labels": {"vendor": "AMD"},
                },
            ],
        },
        {
            "name": "aim-mistral",
            "tags": [
                {
                    "tag": "3.0.0",
                    "labels": {"com.amd.aim.model.recommendedDeployments": "tgi,vllm"},
                },
            ],
        },
    ]

    with patch("app.aims.fetching.yaml.safe_dump") as mock_yaml_dump:
        generate_kaiwo_manifests(results)

        # Should only generate 2 manifests (tags with recommendedDeployments label)
        assert mock_yaml_dump.call_count == 2

        # Verify the manifests have correct structure
        first_call = mock_yaml_dump.call_args_list[0][0][0]
        assert first_call["apiVersion"] == "aim.silogen.ai/v1alpha1"
        assert first_call["kind"] == "AIMClusterModel"
        assert first_call["metadata"]["name"] == "aim-llama-1-0-0"
        assert first_call["spec"]["image"] == "docker.io/amdenterpriseai/aim-llama:1.0.0"


@patch("app.aims.fetching.AIM_METADATA_FILE_PATH")
def test_generate_kaiwo_manifests_no_matching_tags(mock_metadata_path):
    mock_metadata_path.parent = Mock()
    mock_metadata_path.parent.parent = Mock()
    mock_metadata_path.parent.parent.parent = Mock()
    mock_metadata_path.parent.parent.parent.parent = Mock()

    mock_file = mock_open()
    mock_path = Mock()
    mock_path.open = mock_file
    mock_metadata_path.parent.parent.parent.parent.__truediv__ = Mock(return_value=mock_path)

    results = [
        {
            "name": "aim-test",
            "tags": [
                {"tag": "1.0.0", "labels": {"vendor": "AMD"}},
                {"tag": "2.0.0", "labels": {}},
            ],
        }
    ]

    with patch("app.aims.fetching.yaml.safe_dump") as mock_yaml_dump:
        generate_kaiwo_manifests(results)

        # Should not generate any manifests (no tags with recommendedDeployments label)
        assert mock_yaml_dump.call_count == 0


@patch("app.aims.fetching.AIM_METADATA_FILE_PATH")
def test_generate_kaiwo_manifests_empty_results(mock_metadata_path):
    mock_metadata_path.parent = Mock()
    mock_metadata_path.parent.parent = Mock()
    mock_metadata_path.parent.parent.parent = Mock()
    mock_metadata_path.parent.parent.parent.parent = Mock()

    mock_file = mock_open()
    mock_path = Mock()
    mock_path.open = mock_file
    mock_metadata_path.parent.parent.parent.parent.__truediv__ = Mock(return_value=mock_path)

    results = []

    with patch("app.aims.fetching.yaml.safe_dump") as mock_yaml_dump:
        generate_kaiwo_manifests(results)

        # Should not generate any manifests
        assert mock_yaml_dump.call_count == 0


@patch("app.aims.fetching.OrasClient")
@patch("app.aims.fetching.discover_images")
@patch("app.aims.fetching.AIM_METADATA_FILE_PATH")
@patch("app.aims.fetching.generate_kaiwo_manifests")
def test_main_filters_tags_by_recommended_deployments(
    mock_generate_manifests, mock_metadata_path, mock_discover_images, mock_client_class
):
    # Setup mocks
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_discover_images.return_value = ["aim-test"]
    mock_client.get_tags.return_value = ["1.0.0", "2.0.0", "3.0.0"]

    # Mock fetch_tag_labels responses - only some tags have labels ending with recommendedDeployments
    def mock_get_manifest(ref):
        if "1.0.0" in ref:
            return {"config": {"digest": "sha256:abc1"}}
        elif "2.0.0" in ref:
            return {"config": {"digest": "sha256:abc2"}}
        elif "3.0.0" in ref:
            return {"config": {"digest": "sha256:abc3"}}
        return {}

    def mock_get_blob(ref, digest):
        mock_response = Mock()
        if "1.0.0" in ref:
            mock_response.json.return_value = {
                "config": {"Labels": {"com.amd.aim.model.recommendedDeployments": "vllm"}}
            }
        elif "2.0.0" in ref:
            mock_response.json.return_value = {"config": {"Labels": {"vendor": "AMD"}}}
        elif "3.0.0" in ref:
            mock_response.json.return_value = {"config": {"Labels": {"custom.label.recommendedDeployments": "tgi"}}}
        return mock_response

    mock_client.get_manifest = mock_get_manifest
    mock_client.get_blob = mock_get_blob

    # Setup file mocks
    mock_metadata_path.parent = Mock()
    mock_metadata_path.parent.mkdir = Mock()
    mock_file = mock_open()
    mock_metadata_path.open = mock_file

    with patch("app.aims.fetching.yaml.safe_dump") as mock_yaml_dump:
        main()

        # Verify yaml.safe_dump was called for the metadata file
        assert mock_yaml_dump.call_count >= 1
        metadata_call = mock_yaml_dump.call_args_list[0][0][0]

        # Should only have 2 tags in results (1.0.0 and 3.0.0 have labels ending with recommendedDeployments)
        assert len(metadata_call["images"]) == 1
        assert len(metadata_call["images"][0]["tags"]) == 2
        tag_names = [tag["tag"] for tag in metadata_call["images"][0]["tags"]]
        assert "1.0.0" in tag_names
        assert "3.0.0" in tag_names
        assert "2.0.0" not in tag_names
