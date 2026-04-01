// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package deployment

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "apps", Kind: "Deployment"}

const (
	// Status reason messages
	statusReasonNoReplicas      = "No replicas are ready."
	statusReasonScalingUp       = "Scaling up: %d ready of %d total."
	statusReasonAllReady        = "All replicas are running."
	statusReasonCannotDetermine = "Deployment status could not be determined."
)
