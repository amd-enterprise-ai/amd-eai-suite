// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package externalsecret

import (
	"testing"

	"github.com/silogen/agent/internal/messaging"
	"github.com/stretchr/testify/assert"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
)

func TestGetExternalSecretGVR(t *testing.T) {
	tests := []struct {
		name       string
		apiVersion string
		wantGroup  string
		wantVer    string
		wantErr    bool
	}{
		{
			name:       "missing apiVersion",
			apiVersion: "",
			wantErr:    true,
		},
		{
			name:       "custom version",
			apiVersion: "external-secrets.io/v1",
			wantGroup:  "external-secrets.io",
			wantVer:    "v1",
			wantErr:    false,
		},
		{
			name:       "invalid api version",
			apiVersion: "group/version/extra",
			wantErr:    true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := GetExternalSecretGVR(tt.apiVersion)
			if tt.wantErr {
				assert.Error(t, err)
				return
			}
			assert.NoError(t, err)
			assert.Equal(t, tt.wantGroup, got.Group)
			assert.Equal(t, tt.wantVer, got.Version)
			assert.Equal(t, "externalsecrets", got.Resource)
		})
	}
}

func TestGetExternalSecretStatus(t *testing.T) {
	tests := []struct {
		name           string
		conditions     []map[string]interface{}
		expectedStatus messaging.ProjectSecretStatus
		expectedReason string
	}{
		{
			name:           "no status field",
			conditions:     nil,
			expectedStatus: "",
			expectedReason: "Secret status could not be determined.",
		},
		{
			name:           "no conditions",
			conditions:     []map[string]interface{}{},
			expectedStatus: "",
			expectedReason: "Secret status could not be determined.",
		},
		{
			name: "Ready True with message",
			conditions: []map[string]interface{}{
				{
					"type":    "Ready",
					"status":  string(corev1.ConditionTrue),
					"reason":  "SecretSynced",
					"message": "Secret was synced",
				},
			},
			expectedStatus: messaging.ProjectSecretStatusSynced,
			expectedReason: "Secret was synced",
		},
		{
			name: "Ready False uses message if present",
			conditions: []map[string]interface{}{
				{
					"type":    "Ready",
					"status":  string(corev1.ConditionFalse),
					"reason":  "SecretNotSynced",
					"message": "sync failed",
				},
			},
			expectedStatus: messaging.ProjectSecretStatusSyncedError,
			expectedReason: "sync failed",
		},
		{
			name: "Ready Unknown",
			conditions: []map[string]interface{}{
				{
					"type":   "Ready",
					"status": string(corev1.ConditionUnknown),
				},
			},
			expectedStatus: messaging.ProjectSecretStatusUnknown,
			expectedReason: "Secret status could not be determined.",
		},
		{
			name: "Ready condition missing",
			conditions: []map[string]interface{}{
				{
					"type":   "Other",
					"status": string(corev1.ConditionTrue),
				},
			},
			expectedStatus: messaging.ProjectSecretStatusUnknown,
			expectedReason: "Secret status could not be determined.",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			u := &unstructured.Unstructured{Object: map[string]interface{}{}}
			if tt.conditions != nil {
				conds := make([]interface{}, 0, len(tt.conditions))
				for _, c := range tt.conditions {
					conds = append(conds, c)
				}
				_ = unstructured.SetNestedSlice(u.Object, conds, "status", "conditions")
			}

			status, reason := GetExternalSecretStatus(u)
			assert.Equal(t, tt.expectedStatus, status)
			assert.Equal(t, tt.expectedReason, reason)
		})
	}
}
