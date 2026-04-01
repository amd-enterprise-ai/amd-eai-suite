// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package pod

import (
	corev1 "k8s.io/api/core/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from a Pod resource.
func GetStatus(pod *corev1.Pod) (string, string) {
	phase := pod.Status.Phase

	switch phase {
	case corev1.PodPending:
		return common.StatusPending, statusReasonPending
	case corev1.PodRunning:
		return common.StatusRunning, statusReasonRunning
	case corev1.PodSucceeded:
		return common.StatusComplete, statusReasonComplete
	case corev1.PodFailed:
		return common.StatusFailed, statusReasonFailed
	default:
		return string(phase), statusReasonCannotDetermine
	}
}
