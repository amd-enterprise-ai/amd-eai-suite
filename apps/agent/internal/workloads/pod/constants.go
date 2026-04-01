// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package pod

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "", Kind: "Pod"}

const (
	// Status reason messages
	statusReasonPending         = "Pod is pending scheduling or initialization"
	statusReasonRunning         = "Pod is running"
	statusReasonComplete        = "Pod completed successfully"
	statusReasonFailed          = "Pod has failed"
	statusReasonCannotDetermine = "Status information could not be determined"
)

const kaiwoSchedulerName = "kaiwo-scheduler"
const defaultSchedulerName = "default-scheduler"
