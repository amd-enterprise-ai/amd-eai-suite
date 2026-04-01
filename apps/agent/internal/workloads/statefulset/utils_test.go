// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package statefulset

import (
	"testing"

	"github.com/stretchr/testify/assert"
	appsv1 "k8s.io/api/apps/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name               string
		sts                *appsv1.StatefulSet
		expectedStatus     string
		expectedReason     string
		expectedReasonPart string
	}{
		{
			name: "no replicas defined",
			sts: &appsv1.StatefulSet{
				Spec: appsv1.StatefulSetSpec{
					Replicas: ptr(int32(0)),
				},
			},
			expectedStatus: common.StatusPending,
			expectedReason: statusReasonNoReplicasDefined,
		},
		{
			name: "scaling up (current < desired)",
			sts: &appsv1.StatefulSet{
				Spec: appsv1.StatefulSetSpec{
					Replicas: ptr(int32(3)),
				},
				Status: appsv1.StatefulSetStatus{
					CurrentReplicas: 1,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "scaling up",
		},
		{
			name: "ready (ready == desired and available == desired)",
			sts: &appsv1.StatefulSet{
				Spec: appsv1.StatefulSetSpec{
					Replicas: ptr(int32(3)),
				},
				Status: appsv1.StatefulSetStatus{
					CurrentReplicas:   3,
					ReadyReplicas:     3,
					AvailableReplicas: 3,
				},
			},
			expectedStatus:     common.StatusRunning,
			expectedReasonPart: "StatefulSet is ready",
		},
		{
			name: "partially ready",
			sts: &appsv1.StatefulSet{
				Spec: appsv1.StatefulSetSpec{
					Replicas: ptr(int32(3)),
				},
				Status: appsv1.StatefulSetStatus{
					CurrentReplicas:   3,
					ReadyReplicas:     1,
					AvailableReplicas: 1,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "partially ready",
		},
		{
			name: "scaling up with 0 current replicas (still scaling up)",
			sts: &appsv1.StatefulSet{
				Spec: appsv1.StatefulSetSpec{
					Replicas: ptr(int32(3)),
				},
				Status: appsv1.StatefulSetStatus{
					CurrentReplicas: 0,
				},
			},
			expectedStatus:     common.StatusPending,
			expectedReasonPart: "scaling up",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.sts)
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

func ptr[T any](v T) *T { return &v }
