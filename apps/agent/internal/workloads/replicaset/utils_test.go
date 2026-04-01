// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package replicaset

import (
	"testing"

	"github.com/stretchr/testify/assert"
	appsv1 "k8s.io/api/apps/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name               string
		replicaSet         *appsv1.ReplicaSet
		expectedStatus     string
		expectedReason     string
		expectedReasonPart string
	}{
		{
			name: "no replicas",
			replicaSet: &appsv1.ReplicaSet{
				Status: appsv1.ReplicaSetStatus{
					Replicas:      0,
					ReadyReplicas: 0,
				},
			},
			expectedStatus: common.StatusPending,
			expectedReason: statusReasonNoReplicas,
		},
		{
			name: "zero ready replicas",
			replicaSet: &appsv1.ReplicaSet{
				Status: appsv1.ReplicaSetStatus{
					Replicas:      3,
					ReadyReplicas: 0,
				},
			},
			expectedStatus: common.StatusPending,
			expectedReason: statusReasonNoReplicas,
		},
		{
			name: "scaling up - some ready",
			replicaSet: &appsv1.ReplicaSet{
				Status: appsv1.ReplicaSetStatus{
					Replicas:      3,
					ReadyReplicas: 2,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "Scaling up",
		},
		{
			name: "all replicas ready",
			replicaSet: &appsv1.ReplicaSet{
				Status: appsv1.ReplicaSetStatus{
					Replicas:      3,
					ReadyReplicas: 3,
				},
			},
			expectedStatus: common.StatusRunning,
			expectedReason: statusReasonAllReady,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.replicaSet)
			assert.Equal(t, tt.expectedStatus, status)
			if tt.expectedReason != "" {
				assert.Equal(t, tt.expectedReason, reason)
			}
			if tt.expectedReasonPart != "" {
				assert.Contains(t, reason, tt.expectedReasonPart)
			}
		})
	}
}
