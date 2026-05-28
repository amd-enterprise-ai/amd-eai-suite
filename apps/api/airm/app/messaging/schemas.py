# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""RabbitMQ wire contract (discriminated union) and TypeAdapter."""

from typing import Annotated

from pydantic import Field, TypeAdapter

from ..clusters.messaging import (
    ClusterNodeDeleteMessage,
    ClusterNodesMessage,
    ClusterNodeUpdateMessage,
    HeartbeatMessage,
)
from ..namespaces.messaging import (
    NamespaceDeletedMessage,
    ProjectNamespaceCreateMessage,
    ProjectNamespaceDeleteMessage,
    ProjectNamespaceStatusMessage,
    ProjectNamespaceUpdateMessage,
    UnmanagedNamespaceMessage,
)
from ..quotas.messaging import (
    ClusterQuotasAllocationMessage,
    ClusterQuotasFailureMessage,
    ClusterQuotasStatusMessage,
)
from ..secrets.messaging import (
    AutoDiscoveredSecretMessage,
    ProjectSecretsCreateMessage,
    ProjectSecretsDeleteMessage,
    ProjectSecretsUpdateMessage,
)
from ..storages.messaging import (
    ProjectS3StorageCreateMessage,
    ProjectStorageDeleteMessage,
    ProjectStorageUpdateMessage,
)
from ..workloads.messaging import (
    AutoDiscoveredWorkloadComponentMessage,
    DeleteWorkloadMessage,
    WorkloadComponentStatusMessage,
    WorkloadMessage,
    WorkloadStatusMessage,
)

Message = (
    HeartbeatMessage
    | WorkloadMessage
    | WorkloadStatusMessage
    | DeleteWorkloadMessage
    | ClusterNodesMessage
    | ClusterNodeUpdateMessage
    | ClusterNodeDeleteMessage
    | ClusterQuotasAllocationMessage
    | ClusterQuotasStatusMessage
    | ClusterQuotasFailureMessage
    | WorkloadComponentStatusMessage
    | ProjectSecretsCreateMessage
    | ProjectSecretsDeleteMessage
    | ProjectSecretsUpdateMessage
    | ProjectS3StorageCreateMessage
    | ProjectStorageDeleteMessage
    | ProjectStorageUpdateMessage
    | ProjectNamespaceCreateMessage
    | ProjectNamespaceUpdateMessage
    | ProjectNamespaceStatusMessage
    | ProjectNamespaceDeleteMessage
    | UnmanagedNamespaceMessage
    | NamespaceDeletedMessage
    | AutoDiscoveredWorkloadComponentMessage
    | AutoDiscoveredSecretMessage
)

AnnotatedMessage = Annotated[Message, Field(discriminator="message_type")]
MessageAdapter: TypeAdapter[Message] = TypeAdapter(AnnotatedMessage)
