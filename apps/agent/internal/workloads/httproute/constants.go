// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package httproute

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "gateway.networking.k8s.io", Kind: "HTTPRoute"}

const (
	// Status reason messages
	statusReasonAdded             = "HTTPRoute resource has been added to the cluster."
	statusReasonAcceptedByGateway = "HTTPRoute has been accepted by parent gateway %s."
)
