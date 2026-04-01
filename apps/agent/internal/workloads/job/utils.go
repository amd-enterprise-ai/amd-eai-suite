// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package job

import (
	batchv1 "k8s.io/api/batch/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from a Job resource.
func GetStatus(job *batchv1.Job) (string, string) {
	if job.Spec.Suspend != nil && *job.Spec.Suspend {
		return common.StatusSuspended, statusReasonSuspended
	}

	// Check if the job is active
	active := int32(0)
	if job.Status.Active > 0 {
		active = job.Status.Active
	}
	if active > 0 {
		return common.StatusRunning, statusReasonRunning
	}

	// Check if the job has completed all desired pods successfully
	completions := int32(1)
	if job.Spec.Completions != nil {
		completions = *job.Spec.Completions
		if completions <= 0 {
			completions = 1
		}
	}
	succeeded := int32(0)
	if job.Status.Succeeded > 0 {
		succeeded = job.Status.Succeeded
	}
	if succeeded >= completions {
		return common.StatusComplete, statusReasonComplete
	}

	// Check if the job has failed
	failed := int32(0)
	if job.Status.Failed > 0 {
		failed = job.Status.Failed
	}
	if failed > 0 {
		return common.StatusFailed, statusReasonFailed
	}

	return common.StatusPending, statusReasonPending
}
