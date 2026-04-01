// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package service

import (
	corev1 "k8s.io/api/core/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from a Service resource.
func GetStatus(svc *corev1.Service) (string, string) {
	// Basic integrity check
	if len(svc.Spec.Ports) == 0 {
		return common.StatusInvalid, statusReasonNoPorts
	}

	if len(svc.Spec.Selector) == 0 {
		return common.StatusInvalid, statusReasonNoSelector
	}

	// Check if it's a LoadBalancer service and has been provisioned
	if svc.Spec.Type == corev1.ServiceTypeLoadBalancer {
		if len(svc.Status.LoadBalancer.Ingress) > 0 {
			return common.StatusReady, statusReasonLoadBalancerReady
		}
		return common.StatusPending, statusReasonLoadBalancerPending
	}

	// Fallback success
	return common.StatusReady, statusReasonConfiguredProperly
}
