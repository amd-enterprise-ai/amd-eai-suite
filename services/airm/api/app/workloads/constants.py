# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from airm.messaging.schemas import (
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
    ServiceStatus,
    StatefulSetStatus,
    WorkloadComponentKind,
)

KUEUE_QUEUE_NAME_LABEL = "kueue.x-k8s.io/queue-name"

COMPONENT_SPECIFIC_COMPLETED_STATUSES = {
    WorkloadComponentKind.JOB: [JobStatus.COMPLETE],
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.COMPLETE],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.COMPLETE],
    WorkloadComponentKind.SERVICE: [ServiceStatus.READY],
    WorkloadComponentKind.CONFIG_MAP: [ConfigMapStatus.ADDED],
    WorkloadComponentKind.HTTPROUTE: [HTTPRouteStatus.ADDED],
    WorkloadComponentKind.INGRESS: [IngressStatus.ADDED],
    WorkloadComponentKind.POD: [PodStatus.COMPLETE],
}

COMPONENT_SPECIFIC_FAILED_STATUSES = {
    WorkloadComponentKind.JOB: [JobStatus.FAILED],
    WorkloadComponentKind.POD: [PodStatus.FAILED],
    WorkloadComponentKind.SERVICE: [ServiceStatus.INVALID],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.FAILED],
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.FAILED],
    WorkloadComponentKind.AIM_SERVICE: [AIMServiceStatus.FAILED],
    WorkloadComponentKind.CONFIG_MAP: [ConfigMapStatus.FAILED],
}

COMPONENT_SPECIFIC_PENDING_STATUSES = {
    WorkloadComponentKind.JOB: [JobStatus.SUSPENDED, JobStatus.PENDING],
    WorkloadComponentKind.DEPLOYMENT: [DeploymentStatus.PENDING],
    WorkloadComponentKind.STATEFUL_SET: [StatefulSetStatus.PENDING],
    WorkloadComponentKind.POD: [PodStatus.PENDING],
    WorkloadComponentKind.DAEMON_SET: [DaemonSetStatus.PENDING],
    WorkloadComponentKind.CRON_JOB: [CronJobStatus.SUSPENDED],
    WorkloadComponentKind.KAIWO_SERVICE: [
        KaiwoServiceStatus.PENDING,
        KaiwoServiceStatus.ERROR,
        KaiwoServiceStatus.STARTING,
        KaiwoServiceStatus.TERMINATING,
    ],
    WorkloadComponentKind.KAIWO_JOB: [
        KaiwoJobStatus.PENDING,
        KaiwoJobStatus.ERROR,
        KaiwoJobStatus.STARTING,
        KaiwoJobStatus.TERMINATING,
    ],
    WorkloadComponentKind.AIM_SERVICE: [AIMServiceStatus.PENDING, AIMServiceStatus.STARTING, AIMServiceStatus.DEGRADED],
    WorkloadComponentKind.SERVICE: [ServiceStatus.PENDING],
}

COMPONENT_SPECIFIC_RUNNING_STATUSES = {
    WorkloadComponentKind.JOB: [JobStatus.RUNNING],
    WorkloadComponentKind.DEPLOYMENT: [DeploymentStatus.RUNNING],
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.RUNNING],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.RUNNING],
    WorkloadComponentKind.AIM_SERVICE: [AIMServiceStatus.RUNNING],
    WorkloadComponentKind.DAEMON_SET: [DaemonSetStatus.RUNNING],
    WorkloadComponentKind.STATEFUL_SET: [StatefulSetStatus.RUNNING],
    WorkloadComponentKind.CRON_JOB: [CronJobStatus.RUNNING, CronJobStatus.READY],
    WorkloadComponentKind.POD: [PodStatus.RUNNING],
}

COMPONENT_SPECIFIC_DOWNLOADING_STATUSES = {
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.DOWNLOADING],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.DOWNLOADING],
}

COMPONENT_SPECIFIC_TERMINATED_STATUSES = {
    WorkloadComponentKind.KAIWO_JOB: [KaiwoJobStatus.TERMINATED],
    WorkloadComponentKind.KAIWO_SERVICE: [KaiwoServiceStatus.TERMINATED],
}
