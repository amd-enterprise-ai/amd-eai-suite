// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package ingress

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "networking.k8s.io", Kind: "Ingress"}

const (
	// Status reason messages
	statusReasonAdded = "Ingress resource has been added to the cluster."
)
