// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package daemonset

import (
	"testing"

	"github.com/stretchr/testify/assert"
	appsv1 "k8s.io/api/apps/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name               string
		daemonSet          *appsv1.DaemonSet
		expectedStatus     string
		expectedReasonPart string
	}{
		{
			name: "no pods scheduled",
			daemonSet: &appsv1.DaemonSet{
				Status: appsv1.DaemonSetStatus{
					DesiredNumberScheduled: 3,
					CurrentNumberScheduled: 0,
					NumberReady:            0,
					NumberAvailable:        0,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "no current pods",
		},
		{
			name: "all pods ready",
			daemonSet: &appsv1.DaemonSet{
				Status: appsv1.DaemonSetStatus{
					DesiredNumberScheduled: 3,
					CurrentNumberScheduled: 3,
					NumberReady:            3,
					NumberAvailable:        3,
				},
			},
			expectedStatus:     common.StatusRunning,
			expectedReasonPart: "ready (3/3 pods ready)",
		},
		{
			name: "some pods ready",
			daemonSet: &appsv1.DaemonSet{
				Status: appsv1.DaemonSetStatus{
					DesiredNumberScheduled: 3,
					CurrentNumberScheduled: 3,
					NumberReady:            2,
					NumberAvailable:        2,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "partially ready (2/3 pods ready)",
		},
		{
			name: "pods starting",
			daemonSet: &appsv1.DaemonSet{
				Status: appsv1.DaemonSetStatus{
					DesiredNumberScheduled: 3,
					CurrentNumberScheduled: 2,
					NumberReady:            0,
					NumberAvailable:        0,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "starting (2/3 scheduled)",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.daemonSet)
			assert.Equal(t, tt.expectedStatus, status)
			assert.Contains(t, reason, tt.expectedReasonPart)
		})
	}
}
