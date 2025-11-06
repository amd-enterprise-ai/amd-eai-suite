# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from uuid import uuid4

from app.namespaces.constants import KUEUE_MANAGED_LABEL, PROJECT_ID_LABEL
from app.namespaces.utils import build_namespace_manifest


def test_build_namespace_manifest_basic():
    project_id = uuid4()
    namespace_name = "test-namespace"

    manifest = build_namespace_manifest(name=namespace_name, project_id=project_id)

    assert manifest["apiVersion"] == "v1"
    assert manifest["kind"] == "Namespace"
    assert manifest["metadata"]["name"] == namespace_name

    labels = manifest["metadata"]["labels"]
    assert labels[PROJECT_ID_LABEL] == str(project_id)
    assert labels[KUEUE_MANAGED_LABEL] == "true"

    assert len(labels) == 2

    assert "annotations" not in manifest["metadata"]


def test_build_namespace_manifest_with_additional_labels():
    project_id = uuid4()
    namespace_name = "test-namespace"
    additional_labels = {"environment": "production", "team": "ml-platform", "cost-center": "engineering"}

    manifest = build_namespace_manifest(name=namespace_name, project_id=project_id, additional_labels=additional_labels)

    labels = manifest["metadata"]["labels"]

    assert labels[PROJECT_ID_LABEL] == str(project_id)
    assert labels[KUEUE_MANAGED_LABEL] == "true"

    assert labels["environment"] == "production"
    assert labels["team"] == "ml-platform"
    assert labels["cost-center"] == "engineering"

    assert len(labels) == 5


def test_build_namespace_manifest_with_annotations():
    project_id = uuid4()
    namespace_name = "test-namespace"
    annotations = {"description": "ML training namespace", "contact": "ml-team@company.com", "created-by": "automation"}

    manifest = build_namespace_manifest(name=namespace_name, project_id=project_id, additional_annotations=annotations)

    manifest_annotations = manifest["metadata"]["annotations"]
    assert manifest_annotations["description"] == "ML training namespace"
    assert manifest_annotations["contact"] == "ml-team@company.com"
    assert manifest_annotations["created-by"] == "automation"
    assert len(manifest_annotations) == 3


def test_build_namespace_manifest_with_labels_and_annotations():
    project_id = uuid4()
    namespace_name = "test-namespace"
    additional_labels = {"environment": "staging", "version": "v1.2.3"}
    annotations = {"description": "Test environment namespace", "managed-by": "airm"}

    manifest = build_namespace_manifest(
        name=namespace_name,
        project_id=project_id,
        additional_labels=additional_labels,
        additional_annotations=annotations,
    )

    labels = manifest["metadata"]["labels"]
    assert len(labels) == 4  # 2 base + 2 additional
    assert labels["environment"] == "staging"
    assert labels["version"] == "v1.2.3"

    manifest_annotations = manifest["metadata"]["annotations"]
    assert len(manifest_annotations) == 2
    assert manifest_annotations["description"] == "Test environment namespace"
    assert manifest_annotations["managed-by"] == "airm"


def test_build_namespace_manifest_label_override():
    project_id = uuid4()
    namespace_name = "test-namespace"
    additional_labels = {KUEUE_MANAGED_LABEL: "false"}

    manifest = build_namespace_manifest(name=namespace_name, project_id=project_id, additional_labels=additional_labels)

    labels = manifest["metadata"]["labels"]

    assert labels[KUEUE_MANAGED_LABEL] == "false"

    # Verify non-overridden label remains
    assert labels[PROJECT_ID_LABEL] == str(project_id)


def test_build_namespace_manifest_empty_additional_labels():
    project_id = uuid4()
    namespace_name = "test-namespace"

    manifest = build_namespace_manifest(name=namespace_name, project_id=project_id, additional_labels={})

    labels = manifest["metadata"]["labels"]
    # Should only have base labels
    assert len(labels) == 2


def test_build_namespace_manifest_none_parameters():
    project_id = uuid4()
    namespace_name = "test-namespace"

    manifest = build_namespace_manifest(
        name=namespace_name, project_id=project_id, additional_labels=None, additional_annotations=None
    )

    # Should behave same as basic test
    labels = manifest["metadata"]["labels"]
    assert len(labels) == 2
    assert "annotations" not in manifest["metadata"]
