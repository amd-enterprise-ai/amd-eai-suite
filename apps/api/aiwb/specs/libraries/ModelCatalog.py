# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Robot Framework library for selecting models from the finetunable catalog."""

import re

# Model families known to require a HuggingFace account or license acceptance.
# Used to deprioritize gated models in test selection so E2E tests run without
# an HF token secret assigned to the project.
_GATED_PREFIXES = (
    "meta-llama/",
    "google/gemma",
    "CohereLabs/",
)

# Model families that require HuggingFace approval / license acceptance before
# their weights can be downloaded. On clusters where the artifact download pod
# does not receive an HF token (e.g. app-dev), deploying any of these fails at
# weight download with "Access denied. This repository requires approval".
# Used by get_smallest_deployable_aim to prefer genuinely open models.
_APPROVAL_GATED_PREFIXES = (
    "meta-llama/",
    "google/",
    "CohereLabs/",
    "mistralai/",
)


def _aim_requires_approval(aim_id: str) -> bool:
    return any(aim_id.startswith(prefix) for prefix in _APPROVAL_GATED_PREFIXES)


def _auto_deployable_gpu_counts(profiles: list) -> dict:
    """Map aimId -> smallest GPU count that the *automatic* profile selector can use.

    A profile is auto-selectable only when it is Ready, has at least one matching
    node, and is NOT flagged manualSelectionOnly. Manual-only profiles exist
    (e.g. fp8 variants) but a default deploy that doesn't name a profile will
    never pick them, so they don't make a model auto-deployable.
    """
    result: dict[str, int] = {}
    for p in profiles:
        spec = p.get("spec", {})
        status = p.get("status", {})
        if status.get("status") != "Ready":
            continue
        if (status.get("matchingNodes") or 0) < 1:
            continue
        if spec.get("manualSelectionOnly"):
            continue
        aim_id = spec.get("aimId")
        gpus = spec.get("acceleratorCount")
        if not aim_id or not gpus:
            continue
        result[aim_id] = min(result.get(aim_id, 1_000_000), gpus)
    return result


def _param_count_billions(canonical_name: str) -> float:
    """Extract parameter count in billions from a model canonical name.

    Handles patterns like 1B, 3B, 8x7B (MoE — uses active params heuristic),
    27b, 32B. Returns 999 when no match is found so unknown models sort last.
    """
    # MoE pattern: NxMB → use N*M (total parameters) as the size proxy.
    # Total params matter for finetuning memory, not active params per token.
    moe = re.search(r"(\d+)x(\d+)[Bb]", canonical_name)
    if moe:
        return float(moe.group(1)) * float(moe.group(2))
    # Standard pattern: NB or Nb
    match = re.search(r"(\d+(?:\.\d+)?)[Bb](?:\b|-)", canonical_name)
    if match:
        return float(match.group(1))
    return 999.0


def _is_gated(canonical_name: str) -> bool:
    return any(canonical_name.startswith(prefix) for prefix in _GATED_PREFIXES)


def get_smallest_deployable_aim(aims: list, profiles: list) -> str:
    """Return the metadata.name of the smallest open, auto-deployable AIM.

    Used by inference E2E tests that need to deploy *some* AIM without caring which —
    the goal is the smallest blast radius (fewest GPUs, smallest params) on a model
    that a default deploy will actually bring up.

    Deployability is decided by the published profile catalog, not by the model's
    discoveredProfiles: a model is only auto-deployable at N GPUs if an
    AIMClusterProfile exists for its aimId that is Ready, has a matching node, and
    is NOT manualSelectionOnly (the automatic selector ignores manual-only profiles,
    so a default deploy of such a model fails with ProfileNotFound).

    Selection:
        - exclude models whose family requires HF approval (meta-llama/, google/,
          CohereLabs/, mistralai/) — their weights can't be downloaded on clusters
          where the artifact pod has no HF token
        - sort by smallest auto-selectable GPU count, then parameter count

    Args:
        aims: List of AIM dicts from GET /v1/inference/models response data.
        profiles: List of profile dicts from GET /v1/inference/profiles response data.

    Returns:
        metadata.name (Kubernetes resource name) of the smallest deployable AIM.

    Raises:
        ValueError: If no open AIM with an auto-selectable deployable profile is found.
    """
    if not aims:
        raise ValueError("No AIMs provided")
    auto_gpu = _auto_deployable_gpu_counts(profiles)
    if not auto_gpu:
        raise ValueError("No auto-selectable deployable profiles found in catalog")
    candidates = []
    for aim in aims:
        status = aim.get("status", {})
        if status.get("status") != "Ready":
            continue
        aim_id = status.get("aimId", "")
        if aim_id not in auto_gpu:
            continue
        if _aim_requires_approval(aim_id):
            continue
        resource_name = aim.get("metadata", {}).get("name")
        if not resource_name:
            continue
        candidates.append(
            (
                auto_gpu[aim_id],
                _param_count_billions(aim_id),
                resource_name,
            )
        )
    if not candidates:
        raise ValueError(
            "No open AIM with an auto-selectable deployable profile found "
            "(checked Ready models against Ready, matchingNodes>=1, "
            "manualSelectionOnly=False profiles for non-approval-gated families)"
        )
    candidates.sort()
    return candidates[0][2]


def get_second_smallest_deployable_aim(aims: list, profiles: list) -> str:
    """Return the second-smallest open, auto-deployable AIM (same criteria as
    get_smallest_deployable_aim, second sorted candidate).

    Used by multi-AIM regression tests that need two distinct models deployed at
    once. Raises ValueError if fewer than two such AIMs exist in the catalog.
    """
    if not aims:
        raise ValueError("No AIMs provided")
    auto_gpu = _auto_deployable_gpu_counts(profiles)
    if not auto_gpu:
        raise ValueError("No auto-selectable deployable profiles found in catalog")
    candidates = []
    for aim in aims:
        status = aim.get("status", {})
        if status.get("status") != "Ready":
            continue
        aim_id = status.get("aimId", "")
        if aim_id not in auto_gpu:
            continue
        if _aim_requires_approval(aim_id):
            continue
        resource_name = aim.get("metadata", {}).get("name")
        if not resource_name:
            continue
        candidates.append(
            (
                auto_gpu[aim_id],
                _param_count_billions(aim_id),
                resource_name,
            )
        )
    if len(candidates) < 2:
        raise ValueError(
            f"Need at least two open auto-deployable AIMs for dual-AIM regression tests; "
            f"found {len(candidates)}. Deploy a second distinct model on this cluster "
            "or reduce the profile quota requirements."
        )
    candidates.sort()
    return candidates[1][2]


def get_smallest_finetunable_model(models: list) -> str:
    """Return the canonicalName of the smallest open finetunable model.

    Primary sort: open models before gated (meta-llama/, google/gemma require HF token).
    Secondary sort: gpuCount ascending (explicit GPU requirement).
    Tertiary sort: parameter count parsed from canonicalName (B suffix).

    This means the test always picks the smallest open model first, avoiding
    the need for a HuggingFace token secret assigned to the test project.

    Args:
        models: List of model dicts from GET /v1/finetunable response data.

    Returns:
        canonicalName of the smallest open model (or smallest gated if all are gated).

    Raises:
        ValueError: If models list is empty.
    """
    if not models:
        raise ValueError("No finetunable models provided")
    sorted_models = sorted(
        models,
        key=lambda m: (
            _is_gated(m.get("canonicalName", "")),
            m.get("gpuCount", 999),
            _param_count_billions(m.get("canonicalName", "")),
        ),
    )
    best = sorted_models[0]
    name = best.get("canonicalName")
    if not name:
        raise ValueError(f"Finetunable model entry is missing canonicalName: {best!r}")
    return name
