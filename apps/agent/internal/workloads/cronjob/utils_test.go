// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package cronjob

import (
	"testing"

	"github.com/stretchr/testify/assert"
	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

func TestGetStatus(t *testing.T) {
	suspend := true
	tests := []struct {
		name               string
		cronJob            *batchv1.CronJob
		expectedStatus     string
		expectedReasonPart string
	}{
		{
			name: "suspended",
			cronJob: &batchv1.CronJob{
				Spec: batchv1.CronJobSpec{
					Suspend: &suspend,
				},
			},
			expectedStatus:     common.StatusSuspended,
			expectedReasonPart: "suspended",
		},
		{
			name: "active jobs running",
			cronJob: &batchv1.CronJob{
				Status: batchv1.CronJobStatus{
					Active: []corev1.ObjectReference{
						{Name: "job-1"},
						{Name: "job-2"},
					},
				},
			},
			expectedStatus:     common.StatusRunning,
			expectedReasonPart: "2 active job(s)",
		},
		{
			name: "scheduled but not run",
			cronJob: &batchv1.CronJob{
				Status: batchv1.CronJobStatus{
					Active: []corev1.ObjectReference{},
				},
			},
			expectedStatus:     common.StatusReady,
			expectedReasonPart: "scheduled but hasn't run",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.cronJob)
			assert.Equal(t, tt.expectedStatus, status)
			assert.Contains(t, reason, tt.expectedReasonPart)
		})
	}
}
