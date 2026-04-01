# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from ..messaging.schemas import (
    AIMServiceStatus,
    ConfigMapStatus,
    CronJobStatus,
    DaemonSetStatus,
    DeploymentStatus,
    HTTPRouteStatus,
    IngressStatus,
    JobStatus,
    KaiwoJobStatus,
    KaiwoServiceStatus,
    PodStatus,
    ReplicaSetStatus,
    ServiceStatus,
    StatefulSetStatus,
    WorkloadComponentKind,
    WorkloadStatus,
)

WORKLOAD_ID_LABEL = "airm.silogen.ai/workload-id"
COMPONENT_ID_LABEL = "airm.silogen.ai/component-id"
PROJECT_ID_LABEL = "airm.silogen.ai/project-id"
KUEUE_MANAGED_LABEL = "kueue-managed"
KUEUE_QUEUE_NAME_LABEL = "kueue.x-k8s.io/queue-name"

WORKLOAD_STATS_STATUSES = [
    WorkloadStatus.COMPLETE,
    WorkloadStatus.FAILED,
    WorkloadStatus.DELETING,
    WorkloadStatus.DELETE_FAILED,
    WorkloadStatus.RUNNING,
    WorkloadStatus.PENDING,
    WorkloadStatus.TERMINATED,
]

COMPONENT_SPECIFIC_COMPLETED_STATUSES: dict[WorkloadComponentKind, list] = {
    WorkloadComponentKind.JOB: [JobStatus.COMPLETE],
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.COMPLETE],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.COMPLETE],
    WorkloadComponentKind.SERVICE: [ServiceStatus.READY],
    WorkloadComponentKind.CONFIG_MAP: [ConfigMapStatus.ADDED],
    WorkloadComponentKind.HTTPROUTE: [HTTPRouteStatus.ADDED],
    WorkloadComponentKind.INGRESS: [IngressStatus.ADDED],
    WorkloadComponentKind.POD: [PodStatus.COMPLETE],
}

COMPONENT_SPECIFIC_FAILED_STATUSES: dict[WorkloadComponentKind, list] = {
    WorkloadComponentKind.JOB: [JobStatus.FAILED],
    WorkloadComponentKind.POD: [PodStatus.FAILED],
    WorkloadComponentKind.SERVICE: [ServiceStatus.INVALID],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.FAILED],
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.FAILED],
    WorkloadComponentKind.AIM_SERVICE: [AIMServiceStatus.FAILED],
    WorkloadComponentKind.CONFIG_MAP: [ConfigMapStatus.FAILED],
}

COMPONENT_SPECIFIC_PENDING_STATUSES: dict[WorkloadComponentKind, list] = {
    WorkloadComponentKind.JOB: [JobStatus.SUSPENDED, JobStatus.PENDING],
    WorkloadComponentKind.DEPLOYMENT: [DeploymentStatus.PENDING],
    WorkloadComponentKind.REPLICA_SET: [ReplicaSetStatus.PENDING],
    WorkloadComponentKind.STATEFUL_SET: [StatefulSetStatus.PENDING],
    WorkloadComponentKind.POD: [PodStatus.PENDING],
    WorkloadComponentKind.DAEMON_SET: [DaemonSetStatus.PENDING],
    WorkloadComponentKind.CRON_JOB: [CronJobStatus.SUSPENDED],
    WorkloadComponentKind.KAIWO_SERVICE: [
        KaiwoServiceStatus.PENDING,
        KaiwoServiceStatus.DOWNLOADING,
        KaiwoServiceStatus.ERROR,
        KaiwoServiceStatus.STARTING,
        KaiwoServiceStatus.TERMINATING,
    ],
    WorkloadComponentKind.KAIWO_JOB: [
        KaiwoJobStatus.PENDING,
        KaiwoJobStatus.DOWNLOADING,
        KaiwoJobStatus.ERROR,
        KaiwoJobStatus.STARTING,
        KaiwoJobStatus.TERMINATING,
    ],
    WorkloadComponentKind.AIM_SERVICE: [AIMServiceStatus.PENDING, AIMServiceStatus.STARTING, AIMServiceStatus.DEGRADED],
    WorkloadComponentKind.SERVICE: [ServiceStatus.PENDING],
}

COMPONENT_SPECIFIC_RUNNING_STATUSES: dict[WorkloadComponentKind, list] = {
    WorkloadComponentKind.JOB: [JobStatus.RUNNING],
    WorkloadComponentKind.DEPLOYMENT: [DeploymentStatus.RUNNING],
    WorkloadComponentKind.REPLICA_SET: [ReplicaSetStatus.RUNNING],
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.RUNNING],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.RUNNING],
    WorkloadComponentKind.AIM_SERVICE: [AIMServiceStatus.RUNNING],
    WorkloadComponentKind.DAEMON_SET: [DaemonSetStatus.RUNNING],
    WorkloadComponentKind.STATEFUL_SET: [StatefulSetStatus.RUNNING],
    WorkloadComponentKind.CRON_JOB: [CronJobStatus.RUNNING, CronJobStatus.READY],
    WorkloadComponentKind.POD: [PodStatus.RUNNING],
}

COMPONENT_SPECIFIC_TERMINATED_STATUSES: dict[WorkloadComponentKind, list] = {
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.TERMINATED],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.TERMINATED],
}
