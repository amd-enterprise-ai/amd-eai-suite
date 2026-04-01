// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package service

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "", Kind: "Service"}

const (
	// Status reason messages
	statusReasonNoPorts             = "Service has no defined ports."
	statusReasonNoSelector          = "Service has no selector defined."
	statusReasonLoadBalancerReady   = "LoadBalancer is provisioned with ingress."
	statusReasonLoadBalancerPending = "Waiting for LoadBalancer ingress."
	statusReasonConfiguredProperly  = "Service is configured properly."
)
