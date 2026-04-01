// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestIsComponentAutoDiscovered(t *testing.T) {
	tests := []struct {
		name     string
		obj      *corev1.Pod
		expected bool
	}{
		{
			name: "no annotations",
			obj: &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-pod",
				},
			},
			expected: false,
		},
		{
			name: "auto-discovered annotation true",
			obj: &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-pod",
					Annotations: map[string]string{
						agent.AutoDiscoveredAnnotation: agent.AutoDiscoveredValue,
					},
				},
			},
			expected: true,
		},
		{
			name: "auto-discovered annotation false",
			obj: &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-pod",
					Annotations: map[string]string{
						agent.AutoDiscoveredAnnotation: "false",
					},
				},
			},
			expected: false,
		},
		{
			name: "auto-discovered annotation empty",
			obj: &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-pod",
					Annotations: map[string]string{
						agent.AutoDiscoveredAnnotation: "",
					},
				},
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := agent.IsAutoDiscovered(tt.obj)
			assert.Equal(t, tt.expected, result)
		})
	}
}
