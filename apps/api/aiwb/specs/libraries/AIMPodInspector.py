# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Kubectl-based inference-pod inspection helpers for AIWB E2E tests.

The runtime-profile E2E scenarios must prove that profile values —
container image, accelerator product and count, precision, engine args, and
env vars — actually reach the *live inference pod*, not just the AIMService /
AIMProfile custom resources. The existing kubectl keywords stop at the CR
boundary (``AIMService CR should have runtime profile overrides``) and at pod
*count* (``Get AIM running pod count``); none of them read the running
container's spec.

This library resolves the predictor pod for an AIMService and exposes its
effective runtime configuration so behavioural keywords can assert on it.
Shell invocation and JSON parsing live here, per the project convention that
keyword bodies in ``.resource`` files delegate real logic to Python libraries
(see ``AIMModelHelper.py``).

aim-engine (an external operator) owns the exact pod shape, so the extractors
search across containers and across the locations a value can plausibly land
(resource limits for GPU count, container ``env`` for engine/container env,
container ``command``/``args`` for engine args). This keeps the assertions
resilient to aim-engine-side layout changes while still proving the value
reached the pod.
"""

import json
import subprocess

from robot.api.deco import keyword

_KUBECTL_TIMEOUT = 60

# Sidecars/init containers injected by the serving stack (KServe, service mesh,
# weight loaders) are not the inference container. Skip them when locating the
# container that carries the runtime profile so assertions target the real
# model server.
_NON_INFERENCE_CONTAINERS = frozenset(
    {
        "queue-proxy",
        "storage-initializer",
        "istio-proxy",
        "istio-init",
        "aim-sidecar",
    }
)


def _run_kubectl(args: list[str], action: str) -> str:
    try:
        result = subprocess.run(
            ["kubectl", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=_KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        raise RuntimeError(f"kubectl not found on PATH — cannot {action}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"kubectl timed out after {_KUBECTL_TIMEOUT}s while trying to {action}")
    if result.returncode != 0:
        raise RuntimeError(f"kubectl failed while trying to {action}: {result.stderr}")
    return result.stdout


def _predictor_pod(service_name: str, namespace: str) -> dict:
    """Return the JSON of the most recently created Running predictor pod for ``service_name``.

    Mirrors the deployment/pod matching in ``Get AIM running pod count``
    (``aiwb_aims.resource``): the predictor Deployment is named
    ``<service>-<hash>-predictor`` and its pods are prefixed with the
    Deployment name. Selecting on the name prefix keeps this independent of
    whatever labels aim-engine stamps on a given cluster.
    """
    deployments_raw = _run_kubectl(
        ["get", "deployments", "-n", namespace, "-o", "json"],
        f"list deployments in namespace {namespace}",
    )
    deployments = json.loads(deployments_raw).get("items", [])
    predictor_names = [
        d["metadata"]["name"]
        for d in deployments
        if d["metadata"]["name"].startswith(f"{service_name}-") and d["metadata"]["name"].endswith("-predictor")
    ]
    if not predictor_names:
        raise AssertionError(
            f"No predictor Deployment matching {service_name}-*-predictor found in namespace {namespace}"
        )

    # A rollout can leave more than one predictor Deployment (old + new) around,
    # each with Running pods at the same time. Scope the query to Running pods and,
    # among those belonging to any matching predictor Deployment, return the most
    # recently created one so assertions track the latest rollout rather than an
    # arbitrary stale revision. creationTimestamp is RFC3339 and therefore sorts
    # correctly lexicographically.
    pods_raw = _run_kubectl(
        ["get", "pods", "-n", namespace, "--field-selector=status.phase=Running", "-o", "json"],
        f"list Running pods in namespace {namespace}",
    )
    pods = json.loads(pods_raw).get("items", [])
    matching = [
        pod
        for pod in pods
        if any(pod["metadata"]["name"].startswith(f"{deployment_name}-") for deployment_name in predictor_names)
    ]
    if not matching:
        raise AssertionError(f"No Running pod for any predictor Deployment {predictor_names} in namespace {namespace}")
    return max(matching, key=lambda pod: pod["metadata"].get("creationTimestamp", ""))


def _inference_containers(pod: dict) -> list[dict]:
    containers = pod.get("spec", {}).get("containers", [])
    inference = [c for c in containers if c.get("name") not in _NON_INFERENCE_CONTAINERS]
    # Fall back to every container rather than raising: a cluster may name the
    # inference container something this list does not anticipate, and an
    # over-eager skip would hide a real value that did reach the pod.
    return inference or containers


def _gpu_limit(container: dict) -> int:
    limits = container.get("resources", {}).get("limits", {})
    for resource_name, value in limits.items():
        if "gpu" in resource_name.lower():
            return int(value)
    return 0


def _env_map(container: dict) -> dict[str, str]:
    env_map: dict[str, str] = {}
    for entry in container.get("env", []):
        name = entry.get("name")
        if name is not None and "value" in entry:
            env_map[name] = entry["value"]
    return env_map


def _arg_tokens(container: dict) -> list[str]:
    return [str(token) for token in (container.get("command", []) + container.get("args", []))]


@keyword("Get Inference Pod Runtime Config")
def get_inference_pod_runtime_config(service_name: str, namespace: str) -> dict:
    """Return the effective runtime config of the inference container.

    Shape::

        {
            "podName": str,
            "containerName": str,
            "image": str,
            "acceleratorCount": int,        # from resources.limits *gpu*
            "nodeSelector": dict,
            "env": {name: value, ...},      # engineEnv + containerEnv land here
            "args": [token, ...],           # command + args (engineArgs land here)
        }

    Picks the inference container with a GPU limit when one is present,
    otherwise the first non-sidecar container.
    """
    pod = _predictor_pod(service_name, namespace)
    containers = _inference_containers(pod)
    primary = next((c for c in containers if _gpu_limit(c) > 0), containers[0])
    return {
        "podName": pod["metadata"]["name"],
        "containerName": primary.get("name", ""),
        "image": primary.get("image", ""),
        "acceleratorCount": _gpu_limit(primary),
        "nodeSelector": pod.get("spec", {}).get("nodeSelector", {}),
        "env": _env_map(primary),
        "args": _arg_tokens(primary),
    }


@keyword("Inference Pod Should Use Image")
def inference_pod_should_use_image(service_name: str, namespace: str, expected_image: str) -> None:
    """Assert at least one inference container runs ``expected_image``.

    Substring match: aim-engine may resolve a family/tag to a fully qualified
    reference (registry host, digest), so the chosen image is expected to
    *contain* the value the user supplied rather than equal it byte-for-byte.
    """
    pod = _predictor_pod(service_name, namespace)
    images = [c.get("image", "") for c in _inference_containers(pod)]
    if not any(expected_image in image for image in images):
        raise AssertionError(
            f"No inference container uses image containing '{expected_image}'. "
            f"Container images on pod {pod['metadata']['name']}: {images}"
        )


@keyword("Inference Pod Should Request Accelerator Count")
def inference_pod_should_request_accelerator_count(service_name: str, namespace: str, expected_count: int) -> None:
    """Assert the inference container requests ``expected_count`` accelerators."""
    expected = int(expected_count)
    pod = _predictor_pod(service_name, namespace)
    counts = [_gpu_limit(c) for c in _inference_containers(pod)]
    if expected not in counts:
        raise AssertionError(
            f"No inference container requests {expected} accelerators "
            f"(found GPU limits {counts} on pod {pod['metadata']['name']})"
        )


@keyword("Inference Pod Should Be Scheduled On Accelerator")
def inference_pod_should_be_scheduled_on_accelerator(service_name: str, namespace: str, expected_product: str) -> None:
    """Assert the pod is pinned to ``expected_product`` accelerators.

    The product (e.g. MI300X) is not a container field; aim-engine expresses it
    as a node constraint. Check the pod ``nodeSelector`` values and node
    affinity match expressions, then fall back to the labels of the node the
    pod was scheduled onto — covering whichever mechanism the cluster uses.
    """
    pod = _predictor_pod(service_name, namespace)
    spec = pod.get("spec", {})

    haystack: list[str] = [str(v) for v in spec.get("nodeSelector", {}).values()]
    affinity = spec.get("affinity", {}).get("nodeAffinity", {})
    required = affinity.get("requiredDuringSchedulingIgnoredDuringExecution", {})
    for term in required.get("nodeSelectorTerms", []):
        for expr in term.get("matchExpressions", []):
            haystack.extend(str(v) for v in expr.get("values", []))

    if any(expected_product in value for value in haystack):
        return

    node_name = spec.get("nodeName")
    if node_name:
        node_raw = _run_kubectl(["get", "node", node_name, "-o", "json"], f"read node {node_name}")
        node_labels = json.loads(node_raw).get("metadata", {}).get("labels", {})
        if any(expected_product in str(v) for v in node_labels.values()):
            return

    raise AssertionError(
        f"Inference pod {pod['metadata']['name']} is not constrained to accelerator product "
        f"'{expected_product}' via nodeSelector, node affinity, or scheduled-node labels"
    )


@keyword("Inference Pod Should Carry Env")
def inference_pod_should_carry_env(service_name: str, namespace: str, name: str, expected_value: str) -> None:
    """Assert the inference container exposes env ``name`` set to ``expected_value``."""
    config = get_inference_pod_runtime_config(service_name, namespace)
    actual = config["env"].get(name)
    if actual is None:
        raise AssertionError(
            f"Env var '{name}' not present on inference container {config['containerName']} "
            f"(pod {config['podName']}); env keys: {sorted(config['env'])}"
        )
    if actual != expected_value:
        raise AssertionError(
            f"Env var '{name}' is '{actual}', expected '{expected_value}' "
            f"on inference container {config['containerName']} (pod {config['podName']})"
        )


@keyword("Inference Pod Should Carry Engine Arg")
def inference_pod_should_carry_engine_arg(service_name: str, namespace: str, expected_value: str) -> None:
    """Assert ``expected_value`` appears in the inference container's command/args.

    aim-engine renders ``engineArgs`` into the model-server CLI invocation.
    Both the flag form (``--max-model-len 8192``) and joined forms
    (``--max-model-len=8192``) are covered by matching the value as a token or
    substring of any token.
    """
    config = get_inference_pod_runtime_config(service_name, namespace)
    tokens = config["args"]
    if not any(expected_value in token for token in tokens):
        raise AssertionError(
            f"Engine arg containing '{expected_value}' not found in inference container "
            f"{config['containerName']} command/args (pod {config['podName']}); args: {tokens}"
        )
