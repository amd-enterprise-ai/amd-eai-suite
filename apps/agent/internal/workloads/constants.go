// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"k8s.io/apimachinery/pkg/runtime/schema"

	"github.com/silogen/agent/internal/workloads/aimservice"
	"github.com/silogen/agent/internal/workloads/configmap"
	"github.com/silogen/agent/internal/workloads/cronjob"
	"github.com/silogen/agent/internal/workloads/daemonset"
	"github.com/silogen/agent/internal/workloads/deployment"
	"github.com/silogen/agent/internal/workloads/httproute"
	"github.com/silogen/agent/internal/workloads/ingress"
	"github.com/silogen/agent/internal/workloads/job"
	"github.com/silogen/agent/internal/workloads/kaiwojob"
	"github.com/silogen/agent/internal/workloads/kaiwoservice"
	"github.com/silogen/agent/internal/workloads/pod"
	"github.com/silogen/agent/internal/workloads/replicaset"
	"github.com/silogen/agent/internal/workloads/service"
	"github.com/silogen/agent/internal/workloads/statefulset"
)

// KnownComponentGroupKinds lists the Kubernetes resource kinds that the agent
// treats as workload components, assembled from per-sub-package GroupKind constants.
var KnownComponentGroupKinds = []schema.GroupKind{
	job.GroupKind,
	cronjob.GroupKind,
	deployment.GroupKind,
	statefulset.GroupKind,
	daemonset.GroupKind,
	replicaset.GroupKind,
	pod.GroupKind,
	service.GroupKind,
	configmap.GroupKind,
	ingress.GroupKind,
	httproute.GroupKind,
	kaiwojob.GroupKind,
	kaiwoservice.GroupKind,
	aimservice.GroupKind,
}
