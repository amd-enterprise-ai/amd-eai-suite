// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package ingress

import (
	networkingv1 "k8s.io/api/networking/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from an Ingress resource.
func GetStatus(_ *networkingv1.Ingress) (string, string) {
	return common.StatusAdded, statusReasonAdded
}
