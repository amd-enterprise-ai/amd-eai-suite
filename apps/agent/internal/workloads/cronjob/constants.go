// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package cronjob

import "k8s.io/apimachinery/pkg/runtime/schema"

var GroupKind = schema.GroupKind{Group: "batch", Kind: "CronJob"}

const (
	// Status reason messages
	statusReasonSuspended     = "CronJob is currently suspended"
	statusReasonActiveJobs    = "CronJob has %d active job(s) running"
	statusReasonScheduledOnly = "CronJob is scheduled but hasn't run yet"
)
