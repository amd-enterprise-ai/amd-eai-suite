# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum


class WorkloadType(StrEnum):
    MODEL_DOWNLOAD = "MODEL_DOWNLOAD"
    INFERENCE = "INFERENCE"
    FINE_TUNING = "FINE_TUNING"
    WORKSPACE = "WORKSPACE"
    CUSTOM = "CUSTOM"


class WorkloadStatus(StrEnum):
    COMPLETE = "Complete"
    FAILED = "Failed"
    DELETING = "Deleting"
    DELETE_FAILED = "DeleteFailed"
    DELETED = "Deleted"
    PENDING = "Pending"
    RUNNING = "Running"
    TERMINATED = "Terminated"
    UNKNOWN = "Unknown"


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


class ReplicaSetStatus(StrEnum):
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
    REPLICA_SET = "ReplicaSet"
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
    | ReplicaSetStatus
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
