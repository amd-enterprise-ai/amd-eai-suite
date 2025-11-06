# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Fetch AIM metadata from container registries."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import requests
import yaml
from loguru import logger
from oras.client import OrasClient
from tqdm import tqdm

from .config import (
    AIM_EXCLUDED_IMAGES,
    AIM_IMAGE_NAMES_PREFIX,
    AIM_METADATA_FILE_PATH,
    AIM_REGISTRY_HOST,
    AIM_REGISTRY_ORG,
    GITHUB_TOKEN,
    TLS_VERIFY,
    WORKERS,
)
from .utils import kubernetes_name


def fetch_tag_labels(client: OrasClient, image: str, tag: str) -> dict[str, Any] | None:
    ref = f"{AIM_REGISTRY_HOST}/{AIM_REGISTRY_ORG}/{image}:{tag}"
    manifest = client.get_manifest(ref)
    config_digest = manifest.get("config", {}).get("digest")
    if not config_digest:
        return None

    config_blob = client.get_blob(ref, config_digest).json()
    labels = config_blob.get("config", {}).get("Labels", {})
    return {"tag": tag, "labels": labels} if labels else None


def discover_images(client: OrasClient) -> list[str]:
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    all_packages: list = []

    for package_type in ["container"]:
        page = 1
        while True:
            try:
                response = requests.get(
                    f"https://api.github.com/orgs/{AIM_REGISTRY_ORG}/packages?package_type={package_type}&per_page=100&page={page}",
                    headers=headers,
                )

                if response.status_code == 422:
                    break

                response.raise_for_status()
                packages = response.json()

                if not packages:
                    break

                existing_names = {p.get("name") for p in all_packages}
                for pkg in packages:
                    if pkg.get("name") not in existing_names:
                        all_packages.append(pkg)

                if len(packages) < 100:
                    break

                page += 1

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logger.error("Authentication failed")
                    raise
                break

    found_images = [
        package.get("name", "")
        for package in all_packages
        if package.get("name", "").startswith(AIM_IMAGE_NAMES_PREFIX)
        and package.get("name", "") not in AIM_EXCLUDED_IMAGES
    ]

    return found_images


def generate_kaiwo_manifests(results: list[dict[str, Any]]) -> None:
    """Generate AIMClusterModel manifests for Kaiwō team as a single YAML file."""
    manifest_file = (
        AIM_METADATA_FILE_PATH.parent.parent.parent.parent
        / "helm/airm/charts/airm-api/templates/aim-cluster-images.yaml"
    )

    manifests = []
    for image_data in results:
        image_name = image_data["name"]
        tags = image_data["tags"]

        if not tags:
            continue

        for tag_data in tags:
            tag = tag_data["tag"]
            labels = tag_data.get("labels", {})

            if not any(label.endswith("recommendedDeployments") for label in labels):
                continue

            name = kubernetes_name(image_name, tag)
            manifest = {
                "apiVersion": "aim.silogen.ai/v1alpha1",
                "kind": "AIMClusterModel",
                "metadata": {"name": name},
                "spec": {"image": f"{AIM_REGISTRY_HOST}/{AIM_REGISTRY_ORG}/{image_name}:{tag}"},
            }
            manifests.append(manifest)

    with manifest_file.open("w") as f:
        for i, manifest in enumerate(manifests):
            if i > 0:
                f.write("---\n")
            yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)


def main() -> None:
    client = OrasClient(tls_verify=TLS_VERIFY)

    try:
        client.login(username="token", password=GITHUB_TOKEN, hostname=AIM_REGISTRY_HOST)
    except Exception as e:
        logger.warning(f"ORAS login failed: {e}")

    images = discover_images(client)
    if not images:
        return

    results = []
    for image in images:
        tags_list = client.get_tags(f"{AIM_REGISTRY_HOST}/{AIM_REGISTRY_ORG}/{image}")

        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            tags = [
                r
                for r in tqdm(
                    executor.map(lambda tag: fetch_tag_labels(client, image, tag), tags_list),
                    total=len(tags_list),
                    desc=image,
                )
                if r and any(label.endswith("recommendedDeployments") for label in r.get("labels", {}))
            ]

        results.append({"name": image, "tags": tags})

    AIM_METADATA_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AIM_METADATA_FILE_PATH.open("w") as f:
        yaml.safe_dump(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "registry": AIM_REGISTRY_HOST,
                "org": AIM_REGISTRY_ORG,
                "images": results,
            },
            f,
            sort_keys=True,
        )

    generate_kaiwo_manifests(results)


if __name__ == "__main__":
    main()
