// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package deployment

import (
	"fmt"

	appsv1 "k8s.io/api/apps/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from a Deployment resource.
func GetStatus(deployment *appsv1.Deployment) (string, string) {
	status := deployment.Status
	if status.Replicas == 0 && status.ReadyReplicas == 0 {
		return common.StatusPending, statusReasonNoReplicas
	}

	readyReplicas := status.ReadyReplicas
	replicas := status.Replicas

	if readyReplicas == 0 {
		return common.StatusPending, statusReasonNoReplicas
	} else if readyReplicas < replicas {
		return common.StatusPending, fmt.Sprintf(statusReasonScalingUp, readyReplicas, replicas)
	} else if readyReplicas == replicas {
		return common.StatusRunning, statusReasonAllReady
	}

	return common.StatusPending, statusReasonCannotDetermine
}
