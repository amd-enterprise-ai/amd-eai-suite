# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, TypeAdapter

from ..workloads.constants import WORKLOAD_SUBMITTER_MAX_LENGTH


class ProjectSecretStatus(StrEnum):
    PENDING = "Pending"
    SYNCED = "Synced"
    FAILED = "Failed"
    SYNCED_ERROR = "SyncedError"
    DELETE_FAILED = "DeleteFailed"
    DELETED = "Deleted"
    DELETING = "Deleting"
    UNKNOWN = "Unknown"


class ProjectStorageStatus(StrEnum):
    PENDING = "Pending"
    SYNCED = "Synced"
    FAILED = "Failed"
    SYNCED_ERROR = "SyncedError"
    DELETE_FAILED = "DeleteFailed"
    DELETED = "Deleted"
    DELETING = "Deleting"
    UNKNOWN = "Unknown"


class WorkloadStatus(StrEnum):
    COMPLETE = "Complete"
    DOWNLOADING = "Downloading"
    FAILED = "Failed"
    DELETING = "Deleting"
    DELETE_FAILED = "DeleteFailed"
    DELETED = "Deleted"
    PENDING = "Pending"
    RUNNING = "Running"
    TERMINATED = "Terminated"
    UNKNOWN = "Unknown"


class QuotaStatus(StrEnum):
    PENDING = "Pending"
    READY = "Ready"
    DELETING = "Deleting"
    FAILED = "Failed"
    DELETED = "Deleted"


class NamespaceStatus(StrEnum):
    ACTIVE = "Active"
    TERMINATING = "Terminating"
    PENDING = "Pending"
    FAILED = "Failed"
    DELETED = "Deleted"
    DELETE_FAILED = "DeleteFailed"


class GPUVendor(StrEnum):
    NVIDIA = "NVIDIA"
    AMD = "AMD"


class CommonComponentStatus(StrEnum):
    """
    Common status values shared by all component types.
    These represent fundamental states that apply regardless of component kind.
    """

    REGISTERED = "Registered"
    DELETING = "Deleting"
    DELETED = "Deleted"
    DELETE_FAILED = "DeleteFailed"
    CREATE_FAILED = "CreateFailed"


class DeploymentStatus(StrEnum):
    PENDING = "Pending"
    RUNNING = "Running"


class KaiwoJobStatus(StrEnum):
    FAILED = "FAILED"
    PENDING = "PENDING"
    ERROR = "ERROR"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    TERMINATING = "TERMINATING"
    DOWNLOADING = "DOWNLOADING"
    TERMINATED = "TERMINATED"


class KaiwoServiceStatus(StrEnum):
    FAILED = "FAILED"
    PENDING = "PENDING"
    ERROR = "ERROR"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    TERMINATING = "TERMINATING"
    DOWNLOADING = "DOWNLOADING"
    TERMINATED = "TERMINATED"


class AIMServiceStatus(StrEnum):
    PENDING = "Pending"
    STARTING = "Starting"
    RUNNING = "Running"
    FAILED = "Failed"
    DEGRADED = "Degraded"


class JobStatus(StrEnum):
    RUNNING = "Running"
    FAILED = "Failed"
    PENDING = "Pending"
    COMPLETE = "Complete"
    SUSPENDED = "Suspended"


class StatefulSetStatus(StrEnum):
    RUNNING = "Running"
    PENDING = "Pending"


class DaemonSetStatus(StrEnum):
    PENDING = "Pending"
    RUNNING = "Running"


class CronJobStatus(StrEnum):
    READY = "Ready"
    RUNNING = "Running"
    SUSPENDED = "Suspended"


class PodStatus(StrEnum):
    RUNNING = "Running"
    FAILED = "Failed"
    PENDING = "Pending"
    COMPLETE = "Complete"


class ConfigMapStatus(StrEnum):
    ADDED = "Added"
    DELETED = "Deleted"
    FAILED = "Failed"


class HTTPRouteStatus(StrEnum):
    ADDED = "Added"


class IngressStatus(StrEnum):
    ADDED = "Added"


class ServiceStatus(StrEnum):
    INVALID = "Invalid"
    PENDING = "Pending"
    READY = "Ready"


class WorkloadComponentKind(StrEnum):
    DEPLOYMENT = "Deployment"
    JOB = "Job"
    STATEFUL_SET = "StatefulSet"
    DAEMON_SET = "DaemonSet"
    CRON_JOB = "CronJob"
    POD = "Pod"
    KAIWO_JOB = "KaiwoJob"
    KAIWO_SERVICE = "KaiwoService"
    AIM_SERVICE = "AIMService"
    SERVICE = "Service"
    CONFIG_MAP = "ConfigMap"
    HTTPROUTE = "HTTPRoute"
    INGRESS = "Ingress"


WorkloadComponentStatus = (
    JobStatus
    | DeploymentStatus
    | ConfigMapStatus
    | ServiceStatus
    | KaiwoJobStatus
    | KaiwoServiceStatus
    | HTTPRouteStatus
    | IngressStatus
    | StatefulSetStatus
    | DaemonSetStatus
    | CronJobStatus
    | PodStatus
    | AIMServiceStatus
    | CommonComponentStatus
)


class PriorityClass(BaseModel):
    name: str = Field(description="The name of the priority class")
    priority: int = Field(description="The priority value (0-100)")


class HeartbeatMessage(BaseModel):
    message_type: Literal["heartbeat"]
    last_heartbeat_at: AwareDatetime = Field(description="The heartbeat timestamp of the cluster.")
    cluster_name: str = Field(pattern=r"^[0-9A-Za-z-_]+$", description="The name of the cluster.")
    organization_name: str = Field(description="The name of the organization.")


class WorkloadMessage(BaseModel):
    message_type: Literal["workload"]
    manifest: str = Field(description="The workload manifest.")
    user_token: str = Field(description="The user's token")
    workload_id: UUID = Field(description="The workload ID.")


class DeleteWorkloadMessage(BaseModel):
    message_type: Literal["delete_workload"]
    workload_id: UUID = Field(description="The workload ID.")


class WorkloadStatusMessage(BaseModel):
    message_type: Literal["workload_status_update"]
    status: str = Field(description="The status of the workload.")
    workload_id: UUID = Field(description="The workload ID.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
    status_reason: str | None = Field(description="Details if any about the status")


class WorkloadComponentStatusMessage(BaseModel):
    message_type: Literal["workload_component_status_update"]
    id: UUID = Field(description="The component id")
    name: str = Field(description="The name of the component.")
    kind: WorkloadComponentKind = Field(description="The kind of the component.")
    api_version: str = Field(description="The component API version.")
    workload_id: UUID = Field(description="The workload ID.")
    status: WorkloadComponentStatus | None = Field(description="The status of the component.")
    status_reason: str | None = Field(description="Details if any about the status")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class AutoDiscoveredWorkloadComponentMessage(BaseModel):
    message_type: Literal["auto_discovered_workload_component"]
    project_id: UUID = Field(description="The project ID.")
    workload_id: UUID = Field(description="The workload ID.")
    component_id: UUID = Field(description="The component ID.")
    name: str = Field(description="The name of the component.")
    kind: WorkloadComponentKind = Field(description="The kind of the component.")
    api_version: str = Field(description="The component API version.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
    submitter: str | None = Field(
        None, description="The submitter of the workload component, if known", max_length=WORKLOAD_SUBMITTER_MAX_LENGTH
    )


class GPUInformation(BaseModel):
    count: int = Field(description="The number of GPUs available in the node")
    type: str = Field(description="The type of GPU available in the node")
    vendor: GPUVendor = Field(description="The vendor of the GPU available in the node")
    vram_bytes_per_device: int = Field(description="The total VRAM in bytes of each GPU available in the node")
    product_name: str = Field(description="The product name of the GPU available in the node")


class ClusterNode(BaseModel):
    name: str = Field(description="The name of the node.")
    cpu_milli_cores: int = Field(description="The number of CPU milli-cores available in the node.")
    memory_bytes: int = Field(description="The total memory in bytes.")
    ephemeral_storage_bytes: int = Field(description="The total ephemeral storage in bytes.")
    gpu_information: GPUInformation | None = Field(None, description="GPU information if available")
    status: str = Field(description="The status of the node.")
    is_ready: bool = Field(description="Node readiness flag.")


class ClusterNodesMessage(BaseModel):
    message_type: Literal["cluster_nodes"]
    cluster_nodes: list[ClusterNode] = Field(description="The list of nodes in the cluster.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class ClusterQuotaAllocation(BaseModel):
    cpu_milli_cores: int = Field(description="The guaranteed number of CPU milli cores.")
    gpu_count: int = Field(description="The guaranteed number of GPUs.")
    memory_bytes: int = Field(description="The guaranteed memory in bytes.")
    ephemeral_storage_bytes: int = Field(description="The guaranteed ephemeral storage in bytes.")
    quota_name: str = Field(description="The quota name to uniquely identify the quota in the cluster.")
    namespaces: list[str] = Field(description="The list of namespaces to which the quota applies.")


class ClusterQuotasAllocationMessage(BaseModel):
    message_type: Literal["cluster_quotas_allocation"]
    gpu_vendor: GPUVendor | None = Field(None, description="The vendor of the GPU in the cluster")
    quota_allocations: list[ClusterQuotaAllocation] = Field(description="The list of quota allocations to apply.")
    priority_classes: list[PriorityClass] = Field(description="The list of priority classes to configure.")


class ClusterQuotasStatusMessage(BaseModel):
    message_type: Literal["cluster_quotas_status"]
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")
    quota_allocations: list[ClusterQuotaAllocation] = Field(description="The list of quota allocations.")


class ClusterQuotasFailureMessage(BaseModel):
    message_type: Literal["cluster_quotas_failure"]
    reason: str | None = Field(None, description="The reason for the failure.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class ProjectSecretsCreateMessage(BaseModel):
    message_type: Literal["project_secrets_create"]
    project_name: str = Field(description="The name of the project.")
    secret_name: str = Field(description="The name of the secret.")
    project_secret_id: UUID = Field(description="The ID of the secret.")
    manifest: str = Field(description="YAML content of the secret.")
    secret_type: "SecretsComponentKind" = Field(description="The Kubernetes resource kind to manage for this secret.")


class ProjectSecretsDeleteMessage(BaseModel):
    message_type: Literal["project_secrets_delete"]
    project_secret_id: UUID = Field(description="The ID of the secret.")
    project_name: str = Field(description="The name of the project.")
    secret_type: "SecretsComponentKind" = Field(description="The Kubernetes resource kind to manage for this secret.")


class ProjectSecretsUpdateMessage(BaseModel):
    message_type: Literal["project_secrets_update"]
    project_secret_id: UUID = Field(description="The ID of the secret.")
    status: ProjectSecretStatus = Field(description="The status of the secret.")
    status_reason: str | None = Field(None, description="The reason for the update.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class ProjectS3StorageCreateMessage(BaseModel):
    message_type: Literal["project_s3_storage_create"]
    project_storage_id: UUID = Field(description="The ID of the storage.")
    project_name: str = Field(description="The name of the project.")
    storage_name: str = Field(description="The name of the storage.")
    secret_name: str = Field(description="The name of the secret.")
    bucket_url: str = Field(description="URL to the S3 or S3-compatible bucket.")
    secret_key_name: str = Field(description="The Name of the secret key used for access key name.")
    access_key_name: str = Field(description="The Name of the secret key that stores the secret access name.")


class ProjectStorageDeleteMessage(BaseModel):
    message_type: Literal["project_storage_delete"]
    project_storage_id: UUID = Field(description="The ID of the storage.")
    project_name: str = Field(description="The name of the project.")


class ProjectStorageUpdateMessage(BaseModel):
    message_type: Literal["project_storage_update"]
    project_storage_id: UUID = Field(description="The ID of the storage.")
    status: ConfigMapStatus = Field(description="The status of the storage.")
    status_reason: str | None = Field(None, description="The reason for the update.")
    updated_at: AwareDatetime = Field(description="The timestamp of the update.")


class ProjectNamespaceCreateMessage(BaseModel):
    message_type: Literal["project_namespace_create"]
    name: str = Field(description="The name of the namespace.")
    project_id: UUID = Field(description="The ID of the project.")


class ProjectNamespaceDeleteMessage(BaseModel):
    message_type: Literal["project_namespace_delete"]
    name: str = Field(description="The name of the namespace to delete.")
    project_id: UUID = Field(description="The ID of the project associated with the namespace.")


class ProjectNamespaceStatusMessage(BaseModel):
    message_type: Literal["project_namespace_status"]
    project_id: UUID = Field(description="The ID of the project.")
    status: NamespaceStatus = Field(description="The status of the namespace.")
    status_reason: str | None = Field(None, description="The reason for the status.")


class SecretsComponentKind(StrEnum):
    EXTERNAL_SECRET = "ExternalSecret"
    KUBERNETES_SECRET = "Secret"


Message = (
    HeartbeatMessage
    | WorkloadMessage
    | WorkloadStatusMessage
    | DeleteWorkloadMessage
    | ClusterNodesMessage
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
    | ProjectNamespaceStatusMessage
    | ProjectNamespaceDeleteMessage
    | AutoDiscoveredWorkloadComponentMessage
)

AnnotatedMessage = Annotated[Message, Field(discriminator="message_type")]
MessageAdapter: TypeAdapter[Message] = TypeAdapter(AnnotatedMessage)
