// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwojob

import (
	"testing"

	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	"github.com/stretchr/testify/assert"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name               string
		kj                 *kaiwov1alpha1.KaiwoJob
		expectedStatus     string
		expectedReasonPart string
	}{
		{
			name:           "missing status.status",
			kj:             &kaiwov1alpha1.KaiwoJob{},
			expectedStatus: "",
		},
		{
			name:               "has status.status",
			kj:                 withStatus(&kaiwov1alpha1.KaiwoJob{}, kaiwov1alpha1.WorkloadStatusRunning),
			expectedStatus:     "RUNNING",
			expectedReasonPart: "KaiwoJob status: RUNNING",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.kj)
			if tt.expectedStatus != "" {
				assert.Equal(t, tt.expectedStatus, status)
				assert.Contains(t, reason, tt.expectedReasonPart)
			} else {
				assert.Empty(t, status)
				assert.Contains(t, reason, "Status information could not be determined")
			}
		})
	}
}

func withStatus(obj *kaiwov1alpha1.KaiwoJob, status kaiwov1alpha1.WorkloadStatus) *kaiwov1alpha1.KaiwoJob {
	obj.Status.Status = status
	return obj
}
