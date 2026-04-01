// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "", Kind: "ConfigMap"}

const (
	// Status reason messages
	statusReasonAdded = "ConfigMap has been added to the cluster."
)
