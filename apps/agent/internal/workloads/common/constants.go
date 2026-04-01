// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

const (
	WorkloadFinalizer = "airm.silogen.ai/workloads-finalizer"

	WorkloadIDLabel   = "airm.silogen.ai/workload-id"
	ComponentIDLabel  = "airm.silogen.ai/component-id"
	WorkloadTypeLabel = "airm.silogen.ai/workload-type"
	KueueNameLabel    = "kueue.x-k8s.io/queue-name"

	KindJob          = "Job"
	KindDeployment   = "Deployment"
	KindStatefulSet  = "StatefulSet"
	KindPod          = "Pod"
	KindCronJob      = "CronJob"
	KindDaemonSet    = "DaemonSet"
	KindReplicaSet   = "ReplicaSet"
	KindKaiwoJob     = "KaiwoJob"
	KindKaiwoService = "KaiwoService"
	KindAIMService   = "AIMService"
	KindService      = "Service"
	KindConfigMap    = "ConfigMap"
	KindIngress      = "Ingress"
	KindHTTPRoute    = "HTTPRoute"

	StatusDeleted   = "Deleted"
	StatusPending   = "Pending"
	StatusRunning   = "Running"
	StatusReady     = "Ready"
	StatusSuspended = "Suspended"
	StatusComplete  = "Complete"
	StatusFailed    = "Failed"
	StatusAdded     = "Added"
	StatusInvalid   = "Invalid"
)
