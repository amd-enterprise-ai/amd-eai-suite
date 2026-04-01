// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package daemonset

import (
	"fmt"

	appsv1 "k8s.io/api/apps/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from a DaemonSet resource.
func GetStatus(daemonSet *appsv1.DaemonSet) (string, string) {
	status := daemonSet.Status

	desiredNumberScheduled := status.DesiredNumberScheduled
	currentNumberScheduled := status.CurrentNumberScheduled
	numberReady := status.NumberReady
	numberAvailable := status.NumberAvailable

	if currentNumberScheduled == 0 {
		return common.StatusPending, statusReasonNoPodsScheduled
	}

	if numberReady == desiredNumberScheduled &&
		numberAvailable == desiredNumberScheduled &&
		currentNumberScheduled == desiredNumberScheduled {
		return common.StatusRunning, fmt.Sprintf(statusReasonReady, numberReady, desiredNumberScheduled)
	}

	if numberReady > 0 {
		return common.StatusPending, fmt.Sprintf(statusReasonPartiallyReady, numberReady, desiredNumberScheduled)
	}

	if currentNumberScheduled > 0 {
		return common.StatusPending, fmt.Sprintf(statusReasonPodsStarting, currentNumberScheduled, desiredNumberScheduled)
	}

	return common.StatusPending, statusReasonCannotDetermine
}
