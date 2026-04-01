// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package httproute

import (
	"fmt"

	gatewayv1 "sigs.k8s.io/gateway-api/apis/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from an HTTPRoute resource.
func GetStatus(httpRoute *gatewayv1.HTTPRoute) (string, string) {
	// Check if there are any accepted routes based on RouteParentStatus
	if len(httpRoute.Status.Parents) > 0 {
		for _, parent := range httpRoute.Status.Parents {
			for _, condition := range parent.Conditions {
				if condition.Type == "Accepted" && condition.Status == "True" {
					return common.StatusAdded, fmt.Sprintf(statusReasonAcceptedByGateway, parent.ParentRef.Name)
				}
			}
		}
	}

	return common.StatusAdded, statusReasonAdded
}
