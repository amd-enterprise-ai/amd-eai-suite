// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package statefulset

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "apps", Kind: "StatefulSet"}

const (
	// Status reason messages
	statusReasonNoReplicasDefined = "StatefulSet has no replicas defined."
	statusReasonScalingUp         = "StatefulSet is scaling up (%d/%d replicas)"
	statusReasonReady             = "StatefulSet is ready (%d/%d replicas)"
	statusReasonPartiallyReady    = "StatefulSet partially ready (%d/%d ready)"
	statusReasonCannotDetermine   = "StatefulSet status could not be determined"
)
