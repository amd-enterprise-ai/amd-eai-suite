// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package pod

import (
	"testing"

	"github.com/stretchr/testify/assert"
	corev1 "k8s.io/api/core/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name               string
		pod                *corev1.Pod
		expectedStatus     string
		expectedReasonPart string
	}{
		{
			name: "pending pod",
			pod: &corev1.Pod{
				Status: corev1.PodStatus{
					Phase: corev1.PodPending,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "pending",
		},
		{
			name: "running pod",
			pod: &corev1.Pod{
				Status: corev1.PodStatus{
					Phase: corev1.PodRunning,
				},
			},
			expectedStatus:     common.StatusRunning,
			expectedReasonPart: "running",
		},
		{
			name: "succeeded pod",
			pod: &corev1.Pod{
				Status: corev1.PodStatus{
					Phase: corev1.PodSucceeded,
				},
			},
			expectedStatus:     common.StatusComplete,
			expectedReasonPart: "completed successfully",
		},
		{
			name: "failed pod",
			pod: &corev1.Pod{
				Status: corev1.PodStatus{
					Phase: corev1.PodFailed,
				},
			},
			expectedStatus:     common.StatusFailed,
			expectedReasonPart: "failed",
		},
		{
			name: "unknown phase",
			pod: &corev1.Pod{
				Status: corev1.PodStatus{
					Phase: corev1.PodPhase("Unknown"),
				},
			},
			expectedStatus:     "Unknown",
			expectedReasonPart: "could not be determined",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.pod)
			assert.Equal(t, tt.expectedStatus, status)
			assert.Contains(t, reason, tt.expectedReasonPart)
		})
	}
}
