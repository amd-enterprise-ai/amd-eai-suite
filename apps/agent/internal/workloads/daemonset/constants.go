// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package daemonset

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "apps", Kind: "DaemonSet"}

const (
	// Status reason messages
	statusReasonNoPodsScheduled = "DaemonSet has no current pods scheduled."
	statusReasonReady           = "DaemonSet is ready (%d/%d pods ready)"
	statusReasonPartiallyReady  = "DaemonSet partially ready (%d/%d pods ready)"
	statusReasonPodsStarting    = "DaemonSet pods starting (%d/%d scheduled)"
	statusReasonCannotDetermine = "DaemonSet status could not be determined"
)
