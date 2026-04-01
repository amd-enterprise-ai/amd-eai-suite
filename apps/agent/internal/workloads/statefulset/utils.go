// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package statefulset

import (
	"fmt"

	appsv1 "k8s.io/api/apps/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus mirrors Agent get_status_for_stateful_set.
func GetStatus(sts *appsv1.StatefulSet) (string, string) {
	replicas := int32(0)
	if sts.Spec.Replicas != nil {
		replicas = *sts.Spec.Replicas
	}
	readyReplicas := sts.Status.ReadyReplicas
	currentReplicas := sts.Status.CurrentReplicas
	availableReplicas := sts.Status.AvailableReplicas

	if replicas == 0 {
		return common.StatusPending, statusReasonNoReplicasDefined
	}
	if currentReplicas < replicas {
		return common.StatusPending, fmt.Sprintf(statusReasonScalingUp, currentReplicas, replicas)
	}
	if readyReplicas == replicas && availableReplicas == replicas {
		return common.StatusRunning, fmt.Sprintf(statusReasonReady, readyReplicas, replicas)
	}
	if currentReplicas > 0 {
		return common.StatusPending, fmt.Sprintf(statusReasonPartiallyReady, readyReplicas, replicas)
	}

	return "", statusReasonCannotDetermine
}
