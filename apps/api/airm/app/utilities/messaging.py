# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Shared Pydantic pieces for RabbitMQ payloads that embed Kubernetes manifests."""

from pydantic import BaseModel, ConfigDict


class KubernetesMetadata(BaseModel):
    """Kubernetes metadata section."""

    model_config = ConfigDict(extra="allow")  # Allow additional fields like resourceVersion, uid, etc.

    name: str | None = None
    namespace: str | None = None
    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
