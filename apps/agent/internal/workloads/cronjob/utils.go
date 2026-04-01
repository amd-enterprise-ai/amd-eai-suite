// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package cronjob

import (
	"fmt"

	batchv1 "k8s.io/api/batch/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from a CronJob resource.
func GetStatus(cronJob *batchv1.CronJob) (string, string) {
	spec := cronJob.Spec
	status := cronJob.Status

	if spec.Suspend != nil && *spec.Suspend {
		return common.StatusSuspended, statusReasonSuspended
	}

	activeJobs := len(status.Active)
	if activeJobs > 0 {
		return common.StatusRunning, fmt.Sprintf(statusReasonActiveJobs, activeJobs)
	}

	return common.StatusReady, statusReasonScheduledOnly
}
