// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package job

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "batch", Kind: "Job"}

const (
	// Status reason messages
	statusReasonSuspended = "Job is currently suspended"
	statusReasonRunning   = "Job is actively running."
	statusReasonComplete  = "Job has completed all desired pods successfully."
	statusReasonFailed    = "Job has failed."
	statusReasonPending   = "Job has not started yet"
)
