# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from app.storages.utils import build_configmap_manifest


def test_build_configmap_manifest_basic():
    manifest = build_configmap_manifest(
        name="test-configmap",
        namespace="test-ns",
        bucket_url="http://bucket",
        project_storage_id=uuid4(),
        secret_key_name="key",
        access_key_name="access",
        secret_name="secret",
    )
    assert manifest["apiVersion"] == "v1"
    assert manifest["kind"] == "ConfigMap"
    assert manifest["metadata"]["name"] == "test-configmap"
    assert manifest["metadata"]["namespace"] == "test-ns"
    assert "BUCKET_URL" in manifest["data"]
    assert "ACCESS_KEY_NAME" in manifest["data"]
    assert "SECRET_KEY_NAME" in manifest["data"]
    assert "SECRET_NAME" in manifest["data"]


def test_build_configmap_manifest_with_labels_and_annotations():
    manifest = build_configmap_manifest(
        name="test-configmap",
        namespace="test-ns",
        bucket_url="http://bucket",
        project_storage_id=uuid4(),
        secret_key_name="key",
        access_key_name="access",
        secret_name="secret",
        additional_labels={"custom": "label"},
        additional_annotations={"anno": "value"},
    )
    assert manifest["metadata"]["labels"]["custom"] == "label"
    assert manifest["metadata"]["annotations"]["anno"] == "value"
