// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package job

import (
	"testing"

	"github.com/stretchr/testify/assert"
	batchv1 "k8s.io/api/batch/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name           string
		job            *batchv1.Job
		expectedStatus string
		expectedReason string
	}{
		{
			name: "suspended",
			job: &batchv1.Job{
				Spec: batchv1.JobSpec{
					Suspend: ptr(true),
				},
			},
			expectedStatus: common.StatusSuspended,
			expectedReason: statusReasonSuspended,
		},
		{
			name: "running (active > 0)",
			job: &batchv1.Job{
				Status: batchv1.JobStatus{
					Active: 1,
				},
			},
			expectedStatus: common.StatusRunning,
			expectedReason: statusReasonRunning,
		},
		{
			name: "complete (succeeded >= completions)",
			job: &batchv1.Job{
				Spec: batchv1.JobSpec{
					Completions: ptr(int32(2)),
				},
				Status: batchv1.JobStatus{
					Succeeded: 2,
				},
			},
			expectedStatus: common.StatusComplete,
			expectedReason: statusReasonComplete,
		},
		{
			name: "failed (failed > 0)",
			job: &batchv1.Job{
				Status: batchv1.JobStatus{
					Failed: 1,
				},
			},
			expectedStatus: common.StatusFailed,
			expectedReason: statusReasonFailed,
		},
		{
			name:           "pending (default)",
			job:            &batchv1.Job{},
			expectedStatus: common.StatusPending,
			expectedReason: statusReasonPending,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.job)
			assert.Equal(t, tt.expectedStatus, status)
			assert.Equal(t, tt.expectedReason, reason)
		})
	}
}

func ptr[T any](v T) *T { return &v }
