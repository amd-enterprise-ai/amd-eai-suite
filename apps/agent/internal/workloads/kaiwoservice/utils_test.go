// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwoservice

import (
	"testing"

	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	"github.com/stretchr/testify/assert"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name               string
		ks                 *kaiwov1alpha1.KaiwoService
		expectedStatus     string
		expectedReasonPart string
	}{
		{
			name:           "missing status.status",
			ks:             &kaiwov1alpha1.KaiwoService{},
			expectedStatus: "",
		},
		{
			name:               "has status.status",
			ks:                 withStatus(&kaiwov1alpha1.KaiwoService{}, kaiwov1alpha1.WorkloadStatusRunning),
			expectedStatus:     "RUNNING",
			expectedReasonPart: "KaiwoService status: RUNNING",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.ks)
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

func withStatus(obj *kaiwov1alpha1.KaiwoService, status kaiwov1alpha1.WorkloadStatus) *kaiwov1alpha1.KaiwoService {
	obj.Status.Status = status
	return obj
}
