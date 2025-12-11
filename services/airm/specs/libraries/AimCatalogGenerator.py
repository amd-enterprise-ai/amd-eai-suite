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

The test generation is controlled by a CSV configuration file that lists
all AIM models to be tested with their properties (GPU requirements,
HuggingFace token requirements, etc.).
"""

import csv
from pathlib import Path

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
        Library    AimCatalogGenerator    ${CURDIR}/config/aim_models.csv
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, model_config_file="config/aim_models.csv", test_mode="full"):
        """
        Initialize the generator with a model configuration file.

        Args:
            model_config_file: Path to CSV file containing model configurations
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
        self.models = self._load_models(model_config_file)
        self.test_mode = test_mode
        self.current_suite = None

        logger.info(f"Loaded {len(self.models)} AIM models for testing in '{test_mode}' mode")

    def _load_models(self, file_path):
        """
        Load model configurations from CSV file.

        Expected CSV format:
        model_name,image_name,docker_image,gpu_count,requires_hf_token

        Returns:
            List of dictionaries containing model configuration
        """
        models = []
        csv_path = Path(file_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"Model config file not found: {file_path}")

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert string boolean to actual boolean
                row["requires_hf_token"] = row.get("requires_hf_token", "false").lower() == "true"
                row["gpu_count"] = int(row.get("gpu_count", "1"))
                models.append(row)

        if not models:
            raise ValueError(f"No models found in configuration file: {file_path}")

        return models

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

        # Only generate tests for the main suite, not for sub-suites
        if data.parent is None:
            logger.info(f"Generating test cases for {len(self.models)} AIM models")

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
                logger.info(f"Tag filtering: {tests_before} tests → {tests_after} tests")
            else:
                logger.debug("No tag filtering applied (INCLUDE_TAGS and EXCLUDE_TAGS not set)")

    def _get_variable(self, suite_data, var_name):
        """
        Get a variable value from Robot Framework's variable scopes.

        This method accesses variables set via --variable command line or in the suite.
        Variables set via --variable are in the suite's resource.variables, while
        variables defined in *** Variables *** section are also accessible there.

        Args:
            suite_data: Suite data object
            var_name: Variable name (without ${} wrapper)

        Returns:
            Variable value or None if not found
        """
        try:
            # Try to get from suite's resource variables (includes --variable values)
            if hasattr(suite_data, "resource") and hasattr(suite_data.resource, "variables"):
                for var in suite_data.resource.variables:
                    if var.name == f"${{{var_name}}}":
                        # Return the first value (variables are stored as [value])
                        return var.value[0] if var.value else None
        except (AttributeError, IndexError, TypeError) as e:
            logger.debug(f"Could not access variable {var_name} from suite.resource.variables: {e}")

        try:
            # Also try accessing via the suite's variables property directly
            # This handles variables set via --variable command line
            if hasattr(suite_data, "variables"):
                var_value = suite_data.variables.get(f"${{{var_name}}}")
                if var_value is not None:
                    return var_value
        except (AttributeError, TypeError) as e:
            logger.debug(f"Could not access variable {var_name} from suite.variables: {e}")

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

            # Common tags for all tests of this model
            common_tags = [
                f"model:{image_name}",
                f"gpus:{gpu_count}",
                "aim-catalog",
            ]

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
