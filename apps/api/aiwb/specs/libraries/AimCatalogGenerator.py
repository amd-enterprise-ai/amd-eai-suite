# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Dynamic test case generator for AIM catalog testing.
Uses Robot Framework Listener API v3 to create test cases at runtime.

This module generates end-to-end tests for each AIM model in the catalog.
For each model, it creates a sequence of tests:
1. Deploy the AIM
2. Verify deployment reaches Running state
3. Run inference tests
4. Verify metrics are available
5. Undeploy the AIM

Models are auto-discovered from the cluster's /v1/cluster/aims/models endpoint,
filtered to only Ready AIMs. An optional plain text name file can limit which
models are tested (one name per line, matched against model_name).
"""

import os
import re
import subprocess
import traceback
from pathlib import Path

from packaging.version import InvalidVersion, Version

# Import robot.api.logger only when running under Robot Framework
try:
    from robot.api import logger
except ImportError:
    # Fallback logger for testing outside Robot Framework
    class FallbackLogger:
        def info(self, msg):
            print(f"INFO: {msg}")

        def debug(self, msg):
            print(f"DEBUG: {msg}")

        def warn(self, msg):
            print(f"WARN: {msg}")

    logger = FallbackLogger()


class AimCatalogGenerator:
    """
    Listener and library that dynamically generates test cases for each AIM model.

    This class serves dual purposes:
    1. Robot Framework Listener - hooks into suite startup to generate tests
    2. Robot Framework Library - provides utility keywords if needed

    Usage in Robot Framework:
        # API mode (default — auto-discover from cluster):
        Library    AimCatalogGenerator    api    full
        # Name filter mode (test only listed models):
        Library    AimCatalogGenerator    config/aim_models.txt    full
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, model_config_file="api", test_mode="full"):
        """
        Initialize the generator.

        By default, all models are discovered dynamically from the cluster
        API. To test only a subset, provide a plain text file with one
        model name per line (lines starting with # are comments, blank
        lines are ignored). Names are matched against model_name from the API.

        Args:
            model_config_file: "api" (default) for all cluster models, or
                             path to a text file listing model names to test
            test_mode: Test mode to run - 'full', 'smoke', or 'quick'
                      'full' - All tests (deploy, inference, metrics, undeploy)
                      'smoke' - Deploy and basic inference only
                      'quick' - Deploy and undeploy only

        Usage examples:
            # Using Robot Framework variables (RECOMMENDED):
            robot --variable INCLUDE_TAGS:model:aim-qwen-qwen2-5-0-5b-instruct aim_catalog.robot
            robot --variable EXCLUDE_TAGS:requires-hf-token aim_catalog.robot

            # Combine include and exclude:
            robot --variable INCLUDE_TAGS:gpus:1 --variable EXCLUDE_TAGS:requires-hf-token aim_catalog.robot

            # All models:
            robot aim_catalog.robot

            # Test modes:
            robot --variable TEST_MODE:smoke aim_catalog.robot
            robot --variable TEST_MODE:quick aim_catalog.robot
        """
        self.test_mode = test_mode
        self.current_suite = None
        self.models = []
        self._api_base_url = None
        self._api_headers = {}
        self._templates_gpu_map = None

        if model_config_file and model_config_file.lower() not in ("api", "none"):
            self.name_filter = self._load_model_names(model_config_file)
            logger.info(f"Loaded {len(self.name_filter)} model names from filter file")
        else:
            self.name_filter = None
            logger.info("No name filter — will use all models from API")

    @staticmethod
    def _load_model_names(file_path):
        """
        Load model names from a plain text file.

        Expected format: one model name per line.
        Lines starting with # are comments. Blank lines are ignored.

        Args:
            file_path: Path to the text file

        Returns:
            Set of model name strings

        Raises:
            FileNotFoundError: If the file does not exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model name filter file not found: {file_path}")

        names = set()
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    names.add(stripped)

        return names

    def _resolve_api_url(self):
        """
        Resolve the base URL for the cluster API.

        Checks in order:
        1. Robot Framework variable ${AIM_CATALOG_API_URL}
        2. Robot Framework variable ${AIWB_BASE_URL}
        3. Environment variable AIWB_API_URL

        Returns:
            Base URL string (without trailing slash)

        Raises:
            RuntimeError: If no URL source is found
        """
        # Try Robot Framework variables first
        try:
            from robot.libraries.BuiltIn import BuiltIn  # noqa: PLC0415

            builtin = BuiltIn()

            url = builtin.get_variable_value("${AIM_CATALOG_API_URL}")
            if url:
                logger.info(f"Using AIM_CATALOG_API_URL: {url}")
                return url.rstrip("/")

            url = builtin.get_variable_value("${AIWB_BASE_URL}")
            if url:
                logger.info(f"Using AIWB_BASE_URL: {url}")
                return url.rstrip("/")
        except Exception as e:
            logger.debug(f"BuiltIn not available for URL resolution: {e}")

        # Fall back to environment variable
        url = os.environ.get("AIWB_API_URL")
        if url:
            logger.info(f"Using AIWB_API_URL env var: {url}")
            return url.rstrip("/")

        # Discover from cluster Gateway (same approach as deployment.resource)
        url = self._discover_url_from_cluster()
        if url:
            return url

        raise RuntimeError(
            "Cannot resolve API URL for AIM catalog discovery. "
            "Set ${AIM_CATALOG_API_URL}, ${AIWB_BASE_URL}, or AIWB_API_URL environment variable."
        )

    def _discover_url_from_cluster(self):
        """Discover AIWB API URL from the cluster Gateway hostname."""
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "gateway",
                    "https",
                    "-n",
                    "kgateway-system",
                    "-o",
                    "jsonpath={.spec.listeners[0].hostname}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                domain = result.stdout.strip().lstrip("*.")
                url = f"https://aiwbapi.{domain}"
                logger.info(f"Discovered API URL from cluster Gateway: {url}")
                return url
        except Exception as e:
            logger.debug(f"Could not discover URL from cluster: {e}")
        return None

    def _get_auth_token(self):
        """
        Get a bearer token for API authentication.

        Tries in order:
        1. AIWB_API_TOKEN environment variable
        2. kubectl exec-based OIDC token from kubeconfig

        Returns:
            Token string or None if no auth available
        """
        # Explicit token from environment
        token = os.environ.get("AIWB_API_TOKEN")
        if token:
            logger.debug("Using AIWB_API_TOKEN env var for auth")
            return token

        # Extract token from kubectl OIDC exec-based auth
        try:
            import json  # noqa: PLC0415

            # Get the exec-based credential from kubeconfig
            result = subprocess.run(
                ["kubectl", "config", "view", "--minify", "-o", "jsonpath={.users[0].user.exec}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            exec_config = json.loads(result.stdout)
            command = exec_config.get("command", "")
            args = exec_config.get("args", [])

            if not command or "oidc-login" not in str(args):
                return None

            # Run the OIDC login command to get a token
            token_result = subprocess.run(
                [command, *args],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if token_result.returncode != 0:
                logger.debug(f"OIDC token acquisition failed: {token_result.stderr}")
                return None

            token_data = json.loads(token_result.stdout)
            token = token_data.get("status", {}).get("token")
            if token:
                logger.debug("Acquired OIDC token from kubectl config")
            return token
        except Exception as e:
            logger.debug(f"Could not acquire auth token: {e}")
            return None

    def _load_models_from_api(self, name_filter=None):
        """
        Discover AIM models from the cluster API.

        Calls GET {base_url}/v1/cluster/aims/models and filters to only Ready AIMs.
        Authenticates using kubectl OIDC token if available.

        Args:
            name_filter: Optional set of model names. When provided, only
                        models whose model_name is in this set are returned.
                        Unmatched names are logged as warnings.

        Returns:
            List of model dicts
        """
        import requests  # noqa: PLC0415

        self._api_base_url = self._resolve_api_url()
        url = f"{self._api_base_url}/v1/cluster/aims/models"

        logger.info(f"Discovering AIMs from cluster API: {url}")

        token = self._get_auth_token()
        if token:
            self._api_headers = {"Authorization": f"Bearer {token}"}
            logger.debug("Using OIDC bearer token for API authentication")
        else:
            self._api_headers = {}

        try:
            response = requests.get(url, headers=self._api_headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch AIMs from cluster API ({url}): {e}") from e

        try:
            data = response.json()
        except ValueError as e:
            raise RuntimeError(f"API returned non-JSON response from {url}: {response.text[:200]}") from e
        aims = data.get("data", [])
        logger.info(f"API returned {len(aims)} AIMs total")

        models = []
        for aim in aims:
            status_value = aim.get("status_value") or aim.get("status", {}).get("status", "")
            if status_value != "Ready":
                resource_name = aim.get("resource_name", aim.get("metadata", {}).get("name", "unknown"))
                logger.debug(f"Skipping AIM '{resource_name}' with status '{status_value}'")
                continue

            model = self._map_aim_to_model(aim)
            models.append(model)
            logger.debug(
                f"Discovered AIM: {model['model_name']} "
                f"(image={model['image_name']}, gpus={model['gpu_count']}, hf_token={model['requires_hf_token']})"
            )

        # Version filtering vs dedup:
        # - Specific version/range: skip dedup, return all models matching the filter
        # - "latest" or unset: deduplicate by image_name, keeping highest version
        version_filter = self._get_version_filter()

        if version_filter and version_filter != "latest":
            logger.info(f"Applying version filter: {version_filter} (skipping dedup)")
            models = self._apply_version_filter(models, version_filter)
        else:
            models = self._deduplicate_models(models)

        # Apply name filter if provided
        if name_filter:
            matched_names = {m["model_name"] for m in models}
            unmatched = name_filter - matched_names
            for name in sorted(unmatched):
                logger.warn(f"Name filter entry not found in API results: {name}")

            models = [m for m in models if m["model_name"] in name_filter]
            logger.info(f"Name filter: kept {len(models)} models matching filter")

        logger.info(f"Discovered {len(models)} Ready AIMs from cluster API")
        return models

    def _map_aim_to_model(self, aim):
        """
        Map a single AIM API response dict to the internal model format.

        The API response uses Pydantic's serialization with computed fields,
        so it may contain both top-level convenience fields and nested structures.

        Args:
            aim: Dict from the /v1/cluster/aims/models API response

        Returns:
            Dict with keys: model_name, image_name, docker_image, gpu_count, requires_hf_token
        """
        # Extract nested status.imageMetadata.model fields
        status = aim.get("status", {})
        image_metadata = status.get("imageMetadata", status.get("image_metadata", {}))
        model_meta = image_metadata.get("model", {})

        # model_name: prefer canonicalName, fall back to resource_name
        canonical_name = model_meta.get("canonicalName", model_meta.get("canonical_name"))
        resource_name = aim.get("resource_name", aim.get("metadata", {}).get("name", ""))
        model_name = canonical_name or resource_name

        # docker_image: full image reference
        docker_image = aim.get("image_reference", aim.get("spec", {}).get("image", ""))

        # image_name: short name extracted from docker image or resource_name
        image_name = self._extract_image_name(docker_image, resource_name)

        # gpu_count: prefer AIMClusterServiceTemplate, fall back to recommendedDeployments
        gpu_count = self._get_templates_gpu_count(resource_name)
        if gpu_count > 0:
            logger.debug(f"GPU count for '{resource_name}': {gpu_count} (from templates)")
        else:
            recommended = model_meta.get("recommendedDeployments", model_meta.get("recommended_deployments", []))
            gpu_count = self._extract_gpu_count(recommended)
            logger.debug(f"GPU count for '{resource_name}': {gpu_count} (from recommendedDeployments)")

        # requires_hf_token
        hf_required = model_meta.get("hfTokenRequired", model_meta.get("hf_token_required"))
        requires_hf_token = bool(hf_required) if hf_required is not None else False

        version = self._extract_version(docker_image)

        return {
            "model_name": model_name,
            "image_name": image_name,
            "docker_image": docker_image,
            "gpu_count": gpu_count,
            "requires_hf_token": requires_hf_token,
            "version": version,
        }

    @staticmethod
    def _extract_image_name(docker_image, resource_name):
        """
        Extract a short image name from a full docker image reference.

        Strips registry prefix and version tag to produce names like "aim-foo".
        For example: "amdenterpriseai/aim-foo:0.8.4" -> "aim-foo"

        Falls back to resource_name if docker_image is empty or unparseable.

        Args:
            docker_image: Full docker image string (e.g., "registry/aim-name:tag")
            resource_name: Fallback resource name from k8s metadata

        Returns:
            Short image name string
        """
        if not docker_image:
            return resource_name or "unknown"

        # Strip registry/org prefix: "registry.io/org/aim-foo:tag" -> "aim-foo:tag"
        image_with_tag = docker_image.rsplit("/", 1)[-1]
        # Strip tag: "aim-foo:tag" -> "aim-foo"
        image_name = re.split(r"[:@]", image_with_tag)[0]

        return image_name or resource_name or "unknown"

    @staticmethod
    def _extract_gpu_count(recommended_deployments):
        """
        Extract GPU count from recommendedDeployments list.

        Tries common field names for GPU count across deployment entries
        and returns the minimum found value.

        Args:
            recommended_deployments: List of deployment config dicts from API

        Returns:
            Integer GPU count, defaults to 1 if not found
        """
        if not recommended_deployments:
            return 1

        gpu_counts = []
        gpu_field_names = ["gpuCount", "numGpus", "gpu_count", "num_gpus", "gpus"]

        for deployment in recommended_deployments:
            if not isinstance(deployment, dict):
                continue
            for field_name in gpu_field_names:
                if field_name in deployment:
                    try:
                        count = int(deployment[field_name])
                        if count > 0:
                            gpu_counts.append(count)
                            break
                    except (ValueError, TypeError):
                        continue

        return min(gpu_counts) if gpu_counts else 1

    def _get_templates_gpu_count(self, aim_resource_name):
        """
        Look up GPU count for an AIM from the cached templates map.

        On first call for a given AIM, fetches templates from the API and
        caches the result. Subsequent calls for the same AIM reuse the
        cached value to avoid redundant HTTP requests.

        Args:
            aim_resource_name: The AIM resource name to look up

        Returns:
            Integer GPU count from templates, or 0 if unavailable
        """
        if self._templates_gpu_map is None:
            self._templates_gpu_map = {}

        if aim_resource_name not in self._templates_gpu_map:
            self._templates_gpu_map[aim_resource_name] = self._fetch_templates_gpu_count(aim_resource_name)

        return self._templates_gpu_map[aim_resource_name]

    def _fetch_templates_gpu_count(self, aim_resource_name):
        """
        Fetch GPU count from AIMClusterServiceTemplate resources.

        Calls the templates API endpoint and extracts the minimum GPU count
        across all templates for the given model.

        Args:
            aim_resource_name: The AIM resource name to query templates for

        Returns:
            Integer GPU count from templates, or 0 if unavailable
        """
        if not self._api_base_url:
            return 0

        import requests  # noqa: PLC0415

        url = f"{self._api_base_url}/v1/cluster/aims/templates"
        try:
            response = requests.get(
                url,
                headers=self._api_headers,
                params={"aim_resource_name": aim_resource_name},
                timeout=30,
            )
            response.raise_for_status()
            templates = response.json().get("data", [])
        except (requests.RequestException, ValueError) as e:
            logger.debug(f"Could not fetch templates for '{aim_resource_name}': {e}\n{traceback.format_exc()}")
            return 0

        if not templates:
            return 0

        gpu_counts = []
        for template in templates:
            try:
                count = int(template["spec"]["hardware"]["gpu"]["requests"])
                if count > 0:
                    gpu_counts.append(count)
            except (KeyError, TypeError, ValueError):
                continue

        return min(gpu_counts) if gpu_counts else 0

    @staticmethod
    def _extract_version(docker_image):
        """
        Extract version tag from a docker image reference.

        For example: "amdenterpriseai/aim-foo:0.8.5" -> "0.8.5"
        Returns None if no tag is present or image is empty.
        """
        if not docker_image:
            return None

        # Digest references (image@sha256:...) don't have version tags
        if "@" in docker_image:
            return None

        if ":" in docker_image:
            tag = docker_image.rsplit(":", 1)[-1]
            # Ignore registry port numbers (e.g., registry:5000/org/image)
            if tag and not tag.startswith("sha256") and "/" not in tag:
                return tag
        return None

    @staticmethod
    def _parse_version_key(version_string):
        """
        Parse a version string into a comparable key.

        Uses packaging.version.Version for proper semver comparison,
        so "0.8.5-preview" < "0.8.5" and "0.9.0" > "0.8.5".
        Returns a tuple of (Version, original_string) for deterministic ordering
        when Version parsing fails.
        """
        if not version_string:
            return (Version("0"), "")
        try:
            return (Version(version_string), version_string)
        except InvalidVersion:
            return (Version("0"), version_string)

    def _get_version_filter(self):
        """
        Resolve the AIM_VERSION filter from Robot Framework variables or environment.

        Returns:
            Version filter string (e.g., "0.8.5", ">=0.9.0", "latest") or None
        """
        try:
            from robot.libraries.BuiltIn import BuiltIn  # noqa: PLC0415

            value = BuiltIn().get_variable_value("${AIM_VERSION}")
            if value and value not in ["None", "${None}", ""]:
                return str(value)
        except Exception:
            pass

        value = os.environ.get("AIM_VERSION")
        if value:
            return value

        return None

    def _deduplicate_models(self, models):
        """
        Deduplicate models by image_name, keeping the highest version.

        Multiple versions of the same model may exist (e.g., 0.8.4 and 0.8.5).
        When two models share the same image_name, the one with the higher
        semver version wins. If versions are equal or unparseable, the first
        occurrence is kept.

        Args:
            models: List of model dicts with at least 'image_name' and 'version' keys

        Returns:
            Deduplicated list of model dicts
        """
        seen = {}
        for model in models:
            key = model["image_name"]
            if key in seen:
                existing_ver = self._parse_version_key(seen[key].get("version"))
                new_ver = self._parse_version_key(model.get("version"))
                if new_ver > existing_ver:
                    logger.debug(f"Replacing {key} version {seen[key].get('version')} with {model.get('version')}")
                    seen[key] = model
            else:
                seen[key] = model
        if len(seen) < len(models):
            logger.info(f"Deduplicated {len(models)} AIMs to {len(seen)} unique image names (kept highest versions)")
        return list(seen.values())

    def _apply_version_filter(self, models, version_filter):
        """
        Filter models by a version constraint.

        Supported formats:
            - "0.8.5"    — exact match
            - ">=0.8.5"  — minimum version (inclusive)
            - ">0.8.5"   — greater than
            - "<=0.8.5"  — maximum version (inclusive)
            - "<0.8.5"   — less than
            - "latest"   — keep only the latest version per image_name (default dedup)

        Args:
            models: List of model dicts (must have "version" key)
            version_filter: Version constraint string

        Returns:
            Filtered list of model dicts
        """
        if not version_filter or version_filter == "latest":
            return models

        # Parse operator and version
        match = re.match(r"^(>=|>|<=|<)?\s*(.+)$", version_filter)
        if not match:
            logger.warn(f"Invalid version filter '{version_filter}', returning all models")
            return models

        operator = match.group(1) or "=="
        target_str = match.group(2).strip()

        try:
            target = Version(target_str)
        except InvalidVersion:
            logger.warn(f"Cannot parse version '{target_str}' for filtering, returning all models")
            return models

        filtered = []
        for model in models:
            model_version_str = model.get("version")
            if not model_version_str:
                logger.debug(f"Skipping {model['image_name']}: no version tag")
                continue

            try:
                model_version = Version(model_version_str)
            except InvalidVersion:
                logger.debug(f"Skipping {model['image_name']}: unparseable version '{model_version_str}'")
                continue

            if operator == "==" and model_version == target:
                filtered.append(model)
            elif operator == ">=" and model_version >= target:
                filtered.append(model)
            elif operator == ">" and model_version > target:
                filtered.append(model)
            elif operator == "<=" and model_version <= target:
                filtered.append(model)
            elif operator == "<" and model_version < target:
                filtered.append(model)

        logger.info(f"Version filter '{version_filter}': {len(models)} models -> {len(filtered)} models")
        return filtered

    def start_suite(self, data, result):
        """
        Listener method called when suite starts (Listener API v3).
        Dynamically creates test cases for all models.

        This method generates all test cases first, then applies tag filtering
        based on INCLUDE_TAGS and EXCLUDE_TAGS Robot Framework variables.

        IMPORTANT: This listener only activates for aim_catalog.robot suite.
        When used with other suites, it safely does nothing.

        Args:
            data: Suite data (robot.running.model.TestSuite)
            result: Suite result (robot.result.model.TestSuite)
        """
        self.current_suite = data

        # Only generate tests for the aim_catalog suite
        # This allows arguments.txt to be safely used for all test runs
        suite_name = data.name.lower() if data.name else ""
        is_aim_catalog = "aim_catalog" in suite_name or "aim catalog" in suite_name

        logger.debug(f"AimCatalogGenerator.start_suite called for: '{data.name}' (parent: {data.parent is not None})")

        if not is_aim_catalog:
            logger.debug(f"Skipping test generation for suite '{data.name}' (not aim_catalog)")
            return

        # Discover models from API (with optional name filter)
        logger.info("Discovering AIMs from cluster API...")
        self.models = self._load_models_from_api(name_filter=self.name_filter)
        if not self.models:
            raise RuntimeError(
                "No Ready AIMs discovered from cluster API. Ensure the cluster has AIM models with Ready status."
            )

        # Only generate tests for the main suite, not for sub-suites
        if data.parent is None:
            logger.info(f"Generating test cases for {len(self.models)} AIM models")

            # Compute max GPU count across all models so the project quota
            # can be set once to cover the largest model in the catalog.
            # Quota is a minimum guarantee — other workloads get preempted.
            max_gpu_count = max((m["gpu_count"] for m in self.models), default=1)
            logger.info(f"Max GPU count across catalog: {max_gpu_count}")

            # Set as suite variable for use in deploy template
            try:
                from robot.libraries.BuiltIn import BuiltIn  # noqa: PLC0415

                BuiltIn().set_suite_variable("${MAX_GPU_COUNT}", max_gpu_count)
            except Exception:
                logger.warn("Could not set MAX_GPU_COUNT suite variable")

            # Generate all test cases
            self._generate_test_cases(data)
            logger.info(f"Generated {len(data.tests)} test cases")

            # Remove the placeholder test (it's no longer needed)
            for test in list(data.tests):  # Create a copy to iterate safely
                if "DYNAMIC_TEST_PLACEHOLDER" in [str(tag) for tag in test.tags]:
                    data.tests.remove(test)
                    logger.debug("Removed placeholder test")
                    break

            # Apply tag filtering from Robot Framework variables
            include_tags = self._get_variable(data, "INCLUDE_TAGS")
            exclude_tags = self._get_variable(data, "EXCLUDE_TAGS")

            # Check if tags need filtering (ignore None, ${None}, empty strings)
            def is_valid_tag_filter(tag_value):
                """Check if tag value is valid for filtering (not None, ${None}, or empty)."""
                return tag_value and tag_value not in [None, "None", "${None}", ""]

            has_include = is_valid_tag_filter(include_tags)
            has_exclude = is_valid_tag_filter(exclude_tags)

            if has_include or has_exclude:
                tests_before = len(data.tests)

                if has_include:
                    logger.info(f"Applying INCLUDE_TAGS filter: {include_tags}")
                    data.filter(included_tags=include_tags)

                if has_exclude:
                    logger.info(f"Applying EXCLUDE_TAGS filter: {exclude_tags}")
                    data.filter(excluded_tags=exclude_tags)

                tests_after = len(data.tests)
                logger.info(f"Tag filtering: {tests_before} tests -> {tests_after} tests")
            else:
                logger.debug("No tag filtering applied (INCLUDE_TAGS and EXCLUDE_TAGS not set)")

    def _get_variable(self, suite_data, var_name):
        """
        Get a variable value from Robot Framework's variable scopes.

        Tries BuiltIn library first (resolves command-line --variable overrides),
        then falls back to reading from the suite model's Variables section.

        The BuiltIn approach is needed because command-line --variable values are
        applied at the variable scope level during execution, not in the parsed
        suite model. Without BuiltIn, the listener always sees the file-level
        default (e.g., ${None}) instead of the CLI override.

        Args:
            suite_data: Suite data object
            var_name: Variable name (without ${} wrapper)

        Returns:
            Variable value or None if not found
        """
        # Try BuiltIn first — this resolves command-line --variable overrides
        try:
            from robot.libraries.BuiltIn import BuiltIn  # noqa: PLC0415

            value = BuiltIn().get_variable_value(f"${{{var_name}}}")
            if value is not None:
                return str(value)
        except Exception as e:
            logger.debug(f"BuiltIn not available for variable {var_name}: {e}")

        # Fall back to suite model variables (from *** Variables *** section)
        try:
            if hasattr(suite_data, "resource") and hasattr(suite_data.resource, "variables"):
                for var in suite_data.resource.variables:
                    if var.name == f"${{{var_name}}}":
                        return var.value[0] if var.value else None
        except (AttributeError, IndexError, TypeError) as e:
            logger.debug(f"Could not access variable {var_name} from suite.resource.variables: {e}")

        return None

    def _generate_test_cases(self, suite):
        """
        Generate all test cases for all models.

        For each model, creates a sequence of test cases based on test_mode:
        - Deploy test
        - Running state verification test
        - Inference test (full/smoke mode)
        - Metrics test (full mode)
        - Undeploy test
        """
        for model in self.models:
            model_name = model["model_name"]
            image_name = model["image_name"]
            gpu_count = model["gpu_count"]
            requires_hf_token = model["requires_hf_token"]

            logger.info(f"Generating tests for {model_name}")

            version = model.get("version")

            # Common tags for all tests of this model
            common_tags = [
                f"model:{image_name}",
                f"gpus:{gpu_count}",
                "aim-catalog",
            ]

            if version:
                common_tags.append(f"version:{version}")

            if requires_hf_token:
                common_tags.append("requires-hf-token")

            # 1. Deploy test
            self._create_deploy_test(suite, model, common_tags)

            # 2. Running state verification test
            self._create_running_state_test(suite, model, common_tags)

            # 3. Inference test (skip in 'quick' mode)
            if self.test_mode in ["full", "smoke"]:
                self._create_inference_test(suite, model, common_tags)

            # 4. Metrics test (only in 'full' mode)
            if self.test_mode == "full":
                self._create_metrics_test(suite, model, common_tags)

            # 5. Undeploy test
            self._create_undeploy_test(suite, model, common_tags)

    def _create_deploy_test(self, suite, model, common_tags):
        """Create deployment test case for a model."""
        model_name = model["model_name"]
        image_name = model["image_name"]

        tc = suite.tests.create(
            name=f"Deploy {model_name}",
            tags=common_tags + ["deploy", "deployment"],
        )

        # Set documentation
        tc.doc = f"Deploy AIM model {model_name} and verify workload is created"

        # Call test template from resource file
        tc.body.create_keyword(
            name="Test Template: Deploy AIM Model",
            args=[image_name, model["requires_hf_token"]],
        )

    def _create_running_state_test(self, suite, model, common_tags):
        """Create running state verification test case for a model."""
        model_name = model["model_name"]
        image_name = model["image_name"]

        tc = suite.tests.create(
            name=f"Verify {model_name} reaches Running state",
            tags=common_tags + ["deploy", "status"],
        )

        tc.doc = f"Verify that deployed {model_name} reaches Running status"

        tc.body.create_keyword(
            name="Test Template: Verify AIM Running State",
            args=[image_name],
        )

    def _create_inference_test(self, suite, model, common_tags):
        """Create inference test case for a model."""
        model_name = model["model_name"]
        image_name = model["image_name"]

        tc = suite.tests.create(
            name=f"Run inference with {model_name}",
            tags=common_tags + ["inference", "external"],
        )

        tc.doc = f"Test inference capability of {model_name} via external endpoint"

        tc.body.create_keyword(
            name="Test Template: Run AIM Inference",
            args=[image_name],
        )

    def _create_metrics_test(self, suite, model, common_tags):
        """Create metrics verification test case for a model."""
        model_name = model["model_name"]
        image_name = model["image_name"]

        tc = suite.tests.create(
            name=f"Verify metrics for {model_name}",
            tags=common_tags + ["metrics", "analytics"],
        )

        tc.doc = f"Verify that inference metrics are available for {model_name}"

        tc.body.create_keyword(
            name="Test Template: Verify AIM Metrics",
            args=[image_name],
        )

    def _create_undeploy_test(self, suite, model, common_tags):
        """Create undeployment test case for a model."""
        model_name = model["model_name"]
        image_name = model["image_name"]

        tc = suite.tests.create(
            name=f"Undeploy {model_name}",
            tags=common_tags + ["undeploy", "cleanup"],
        )

        tc.doc = f"Undeploy {model_name} and verify cleanup"

        tc.body.create_keyword(
            name="Test Template: Undeploy AIM Model",
            args=[image_name],
        )

    # Library keywords (utility methods that can be called from Robot tests)

    def get_loaded_models(self):
        """
        Get list of loaded model names.

        Returns:
            List of model names that were loaded from configuration
        """
        return [model["model_name"] for model in self.models]

    def get_model_count(self):
        """
        Get total number of models loaded.

        Returns:
            Integer count of models
        """
        return len(self.models)

    def get_model_info(self, image_name):
        """
        Get information about a specific model by image name.

        Args:
            image_name: The image_name of the model to look up

        Returns:
            Dictionary with model information or None if not found
        """
        for model in self.models:
            if model["image_name"] == image_name:
                return model
        return None
