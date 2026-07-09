# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Kubectl-based AIMModel CR helpers for AIWB E2E tests.

Keeps YAML construction and shell invocation out of .resource files, where
the project conventions require keyword bodies to delegate real logic to
Python libraries.
"""

import json
import subprocess
import tempfile
from pathlib import Path

from robot.api.deco import keyword

_KUBECTL_TIMEOUT = 60


def _apply_yaml(yaml_body: str, namespace: str, error_label: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, prefix="aimmodel-") as tmp:
        tmp.write(yaml_body)
        tmp_path = Path(tmp.name)
    try:
        result = subprocess.run(
            ["kubectl", "apply", "-f", str(tmp_path), "-n", namespace],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError(f"kubectl not found on PATH — cannot apply YAML for {error_label}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl apply timed out after {_KUBECTL_TIMEOUT}s for {error_label}")
    finally:
        tmp_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create {error_label}: {result.stderr}")


@keyword("Apply Dummy AIMModel CR")
def apply_dummy_aim_model_cr(name: str, namespace: str) -> str:
    """Apply a minimal AIMModel CR that simulates a completed fine-tuned model.

    No GPU or actual fine-tuning needed — the CR exposes the same K8s shape
    the API surfaces for real models, so list/get tests can run on any cluster.
    """
    # airm.silogen.ai/workload-type=FINE_TUNING is the contract with
    # fine_tuning.service._is_fine_tuning_model; without it the dummy AIMModel
    # is invisible to GET /v1/projects/{p}/fine-tuning/models and the discovery
    # tests fail with 404 / empty list.
    yaml_body = (
        "apiVersion: aim.eai.amd.com/v1alpha1\n"
        "kind: AIMModel\n"
        "metadata:\n"
        f"  name: {name}\n"
        "  labels:\n"
        f'    aiwb.apps.eai.amd.com/model-name: "{name}"\n'
        '    airm.silogen.ai/workload-type: "FINE_TUNING"\n'
        "spec:\n"
        '  image: "fake-registry/dummy:latest"\n'
    )
    _apply_yaml(yaml_body, namespace, f"dummy AIMModel CR {name}")
    return name


@keyword("Apply AIMModel CR With Source")
def apply_aim_model_cr_with_source(name: str, namespace: str) -> str:
    """Apply an AIMModel CR pointing at an S3 model source.

    Used by deletion tests that need a CR registered against a source URI
    (the API treats source-backed and source-less models the same for delete).
    """
    # airm.silogen.ai/workload-type=FINE_TUNING is required for the fine-tuning
    # capability endpoints (delete/get/list) to find the CR; the filter rejects
    # models that lack it.
    yaml_body = (
        "apiVersion: aim.eai.amd.com/v1alpha1\n"
        "kind: AIMModel\n"
        "metadata:\n"
        f"  name: {name}\n"
        f"  namespace: {namespace}\n"
        "  labels:\n"
        '    airm.silogen.ai/workload-type: "FINE_TUNING"\n'
        "spec:\n"
        # aimId + versionPolicy=latest satisfies the CRD's "image required unless aimId+versionPolicy" rule
        # without needing a real image reference.
        f"  aimId: test-aim-{name}\n"
        "  custom:\n"
        "    versionPolicy: latest\n"
        "  modelSources:\n"
        # modelId must match org/name pattern; we synthesize one from the test name.
        f"    - modelId: test-org/{name}\n"
        f"      sourceUri: s3://test-bucket/{namespace}/models/{name}/\n"
    )
    _apply_yaml(yaml_body, namespace, f"AIMModel CR {name}")
    return name


@keyword("Apply Multiple Dummy AIMModel CRs")
def apply_multiple_dummy_aim_model_crs(
    namespace: str,
    count: int,
    name_prefix: str = "page-test-model",
) -> list[str]:
    """Apply ``count`` minimal AIMModel CRs in ``namespace``.

    Used by pagination tests that need more rows than fit on a single page
    without invoking real fine-tuning. Returns the list of names so callers
    can clean up explicitly if they're not relying on namespace cascade.
    """
    names: list[str] = []
    for i in range(int(count)):
        name = f"{name_prefix}-{i:03d}"
        apply_dummy_aim_model_cr(name, namespace)
        names.append(name)
    return names


@keyword("AIMModel CR Should Be Absent")
def aim_model_cr_should_be_absent(name: str, namespace: str) -> None:
    """Assert the AIMModel CR is no longer present in the namespace."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "aimmodels", name, "-n", namespace],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError("kubectl not found on PATH — cannot verify AIMModel CR absence")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl get timed out after {_KUBECTL_TIMEOUT}s for AIMModel {name}")
    if result.returncode == 0:
        raise AssertionError(f"AIMModel CR {name} still exists in namespace {namespace}")
    stderr_lower = result.stderr.lower()
    if "not found" not in stderr_lower and "notfound" not in stderr_lower:
        raise RuntimeError(f"kubectl get failed unexpectedly (not a 'not found' error): {result.stderr}")


@keyword("Apply AIMService Referencing Model")
def apply_aim_service_referencing_model(name: str, model_name: str, namespace: str) -> str:
    """Apply a minimal v1alpha2 AIMService CR that references ``model_name``.

    Used by the delete active-deployment guard test. The service only needs to
    exist and carry ``spec.model.name`` — the workbench guard lists AIMServices
    and matches that field, so the service does not need to reach Ready (no GPU
    or real profile is required).
    """
    yaml_body = (
        "apiVersion: aim.eai.amd.com/v1alpha2\n"
        "kind: AIMService\n"
        "metadata:\n"
        f"  name: {name}\n"
        f"  namespace: {namespace}\n"
        "spec:\n"
        "  model:\n"
        f"    name: {model_name}\n"
    )
    _apply_yaml(yaml_body, namespace, f"AIMService CR {name}")
    return name


@keyword("Delete AIMService CR")
def delete_aim_service_cr(name: str, namespace: str) -> None:
    """Delete the named AIMService CR, tolerating one that is already gone.

    Used by the delete active-deployment guard test's teardown so the blocking
    service is removed and the referenced AIMModel can be cleaned up afterwards —
    without it the model stays pinned by the 409 guard and pollutes later tests.
    """
    try:
        result = subprocess.run(
            ["kubectl", "delete", "aimservice", name, "-n", namespace, "--ignore-not-found"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError("kubectl not found on PATH — cannot delete AIMService CR")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl delete timed out after {_KUBECTL_TIMEOUT}s for AIMService {name}")
    if result.returncode != 0:
        raise RuntimeError(f"Failed to delete AIMService CR {name}: {result.stderr}")


@keyword("AIMProfile For Model Should Be Absent")
def aim_profile_for_model_should_be_absent(model_name: str, namespace: str) -> None:
    """Assert no AIMProfile derived from ``model_name`` remains in the namespace.

    aim-engine stamps the ``aim.eai.amd.com/model.name`` label on every
    AIMProfile it derives from an AIMModel; once the AIMModel is deleted the
    AIMProfile (and its AIMProfileSet) are garbage-collected via owner references.
    A label-filtered ``get`` returns exit 0 with empty output when nothing matches.
    """
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "aimprofiles",
                "-n",
                namespace,
                "-l",
                f"aim.eai.amd.com/model.name={model_name}",
                "-o",
                "name",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError("kubectl not found on PATH — cannot verify AIMProfile absence")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl get timed out after {_KUBECTL_TIMEOUT}s for AIMProfiles of {model_name}")
    if result.returncode != 0:
        raise RuntimeError(f"kubectl get aimprofiles failed unexpectedly: {result.stderr}")
    remaining = result.stdout.strip()
    if remaining:
        raise AssertionError(
            f"AIMProfile(s) derived from AIMModel {model_name} still present in namespace {namespace}: {remaining}"
        )


@keyword("AIMProfile For Model Should Exist")
def aim_profile_for_model_should_exist(model_name: str, namespace: str) -> None:
    """Assert at least one AIMProfile derived from ``model_name`` exists.

    Used to confirm aim-engine has derived the profile before the delete step,
    so the cascade-cleanup assertion is meaningful.
    """
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "aimprofiles",
                "-n",
                namespace,
                "-l",
                f"aim.eai.amd.com/model.name={model_name}",
                "-o",
                "name",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError("kubectl not found on PATH — cannot verify AIMProfile presence")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl get timed out after {_KUBECTL_TIMEOUT}s for AIMProfiles of {model_name}")
    if result.returncode != 0:
        raise RuntimeError(f"kubectl get aimprofiles failed unexpectedly: {result.stderr}")
    if not result.stdout.strip():
        raise AssertionError(f"No AIMProfile derived from AIMModel {model_name} found in namespace {namespace}")


@keyword("Get AIMProfile Name For Model")
def get_aim_profile_name_for_model(model_name: str, namespace: str) -> str:
    """Return ``metadata.name`` of the AIMProfile derived from ``model_name``.

    Matches the backend lookup keyed by ``aim.eai.amd.com/model.name``.
    """
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "aimprofiles",
                "-n",
                namespace,
                "-l",
                f"aim.eai.amd.com/model.name={model_name}",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError("kubectl not found on PATH — cannot resolve AIMProfile name")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl get timed out after {_KUBECTL_TIMEOUT}s for AIMProfiles of {model_name}")
    if result.returncode != 0:
        raise RuntimeError(f"kubectl get aimprofiles failed unexpectedly: {result.stderr}")

    items = json.loads(result.stdout).get("items", [])
    if not items:
        raise AssertionError(f"No AIMProfile derived from AIMModel {model_name} found in namespace {namespace}")
    return items[0]["metadata"]["name"]


@keyword("Get AIMProfile Spec For Model")
def get_aim_profile_spec_for_model(model_name: str, namespace: str) -> dict:
    """Return the ``spec`` of the AIMProfile derived from ``model_name``.

    Lets pod-level assertions cross-check the running container against the
    profile aim-engine actually emitted (acceleratorModel, acceleratorCount,
    precision, engineArgs, engineEnv) rather than against hardcoded values that
    a given cluster may not schedule.
    """
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "aimprofiles",
                "-n",
                namespace,
                "-l",
                f"aim.eai.amd.com/model.name={model_name}",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError("kubectl not found on PATH — cannot read AIMProfile spec")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl get timed out after {_KUBECTL_TIMEOUT}s for AIMProfiles of {model_name}")
    if result.returncode != 0:
        raise RuntimeError(f"kubectl get aimprofiles failed unexpectedly: {result.stderr}")

    items = json.loads(result.stdout).get("items", [])
    if not items:
        raise AssertionError(f"No AIMProfile derived from AIMModel {model_name} found in namespace {namespace}")
    return items[0].get("spec", {})
