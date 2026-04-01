// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aimservice

import (
	"testing"

	aimv1alpha1 "github.com/amd-enterprise-ai/aim-engine/api/v1alpha1"
	"github.com/stretchr/testify/assert"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestGetStatus(t *testing.T) {
	tests := []struct {
		name                string
		aimService          *aimv1alpha1.AIMService
		expectedStatus      string
		expectedReason      string
		statusShouldBeEmpty bool
	}{
		{
			name: "Running status",
			aimService: &aimv1alpha1.AIMService{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-aimservice",
					Namespace: "test-ns",
				},
				Status: aimv1alpha1.AIMServiceStatus{
					Status: "Running",
				},
			},
			expectedStatus: "Running",
			expectedReason: "AIMService status: Running",
		},
		{
			name: "Pending status",
			aimService: &aimv1alpha1.AIMService{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-aimservice",
					Namespace: "test-ns",
				},
				Status: aimv1alpha1.AIMServiceStatus{
					Status: "Pending",
				},
			},
			expectedStatus: "Pending",
			expectedReason: "AIMService status: Pending",
		},
		{
			name: "Empty status",
			aimService: &aimv1alpha1.AIMService{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-aimservice",
					Namespace: "test-ns",
				},
				Status: aimv1alpha1.AIMServiceStatus{},
			},
			statusShouldBeEmpty: true,
			expectedReason:      "Status information could not be determined",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, reason := GetStatus(tt.aimService)

			if tt.statusShouldBeEmpty {
				assert.Empty(t, status)
			} else {
				assert.Equal(t, tt.expectedStatus, status)
			}
			assert.Equal(t, tt.expectedReason, reason)
		})
	}
}
