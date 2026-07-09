# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Inference capability module.

Exposes capability-shaped routes for deploying and managing inference
deployments. The implementation reuses the existing AIM service and gateway
layers (v1alpha2 selector-based profiles) so behavior stays consistent while
clients migrate from the legacy ``/aims/services/*`` paths.
"""
