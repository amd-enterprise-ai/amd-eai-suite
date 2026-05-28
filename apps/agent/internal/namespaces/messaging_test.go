// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"encoding/json"
	"testing"

	"github.com/silogen/agent/internal/messaging"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestProjectNamespaceStatusMessage_MarshalJSON(t *testing.T) {
	reason := "Some reason"
	msg := &ProjectNamespaceStatusMessage{
		MessageType:  messaging.MessageTypeProjectNamespaceStatus,
		ProjectID:    "123e4567-e89b-12d3-a456-426614174000",
		Status:       NamespaceStatusActive,
		StatusReason: &reason,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectNamespaceStatusMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ProjectID, unmarshaled.ProjectID)
	assert.Equal(t, msg.Status, unmarshaled.Status)
	assert.NotNil(t, unmarshaled.StatusReason)
	assert.Equal(t, *msg.StatusReason, *unmarshaled.StatusReason)
}

func TestProjectNamespaceStatusMessage_MarshalJSON_WithoutReason(t *testing.T) {
	msg := &ProjectNamespaceStatusMessage{
		MessageType:  messaging.MessageTypeProjectNamespaceStatus,
		ProjectID:    "123e4567-e89b-12d3-a456-426614174000",
		Status:       NamespaceStatusActive,
		StatusReason: nil,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectNamespaceStatusMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ProjectID, unmarshaled.ProjectID)
	assert.Equal(t, msg.Status, unmarshaled.Status)
	assert.Nil(t, unmarshaled.StatusReason)
}

func TestProjectNamespaceStatusMessage_MarshalJSON_WithGpuPreemption(t *testing.T) {
	threshold := 80
	gracePeriod := 1800
	policy := GpuPreemptionPolicyAlways
	msg := &ProjectNamespaceStatusMessage{
		MessageType: messaging.MessageTypeProjectNamespaceStatus,
		ProjectID:   "123e4567-e89b-12d3-a456-426614174000",
		Status:      NamespaceStatusActive,
		GpuPreemption: &GpuPreemptionStatus{
			Enabled:     true,
			Threshold:   &threshold,
			GracePeriod: &gracePeriod,
			Policy:      &policy,
		},
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectNamespaceStatusMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	require.NotNil(t, unmarshaled.GpuPreemption)
	assert.True(t, unmarshaled.GpuPreemption.Enabled)
	require.NotNil(t, unmarshaled.GpuPreemption.Threshold)
	assert.Equal(t, threshold, *unmarshaled.GpuPreemption.Threshold)
	require.NotNil(t, unmarshaled.GpuPreemption.GracePeriod)
	assert.Equal(t, gracePeriod, *unmarshaled.GpuPreemption.GracePeriod)
	require.NotNil(t, unmarshaled.GpuPreemption.Policy)
	assert.Equal(t, policy, *unmarshaled.GpuPreemption.Policy)

	msgNoPreemption := &ProjectNamespaceStatusMessage{
		MessageType: messaging.MessageTypeProjectNamespaceStatus,
		ProjectID:   "123e4567-e89b-12d3-a456-426614174000",
		Status:      NamespaceStatusActive,
	}
	dataNil, err := json.Marshal(msgNoPreemption)
	require.NoError(t, err)
	assert.NotContains(t, string(dataNil), "gpu_preemption")
}

func TestUnmanagedNamespaceMessage_MarshalJSON(t *testing.T) {
	msg := &UnmanagedNamespaceMessage{
		MessageType:     messaging.MessageTypeUnmanagedNamespace,
		NamespaceName:   "test-namespace",
		NamespaceStatus: NamespaceStatusActive,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled UnmanagedNamespaceMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.NamespaceName, unmarshaled.NamespaceName)
	assert.Equal(t, msg.NamespaceStatus, unmarshaled.NamespaceStatus)
}

func TestNamespaceStatus_AllValues(t *testing.T) {
	statuses := []NamespaceStatus{
		NamespaceStatusActive,
		NamespaceStatusTerminating,
		NamespaceStatusPending,
		NamespaceStatusFailed,
		NamespaceStatusDeleted,
		NamespaceStatusDeleteFailed,
	}

	for _, status := range statuses {
		t.Run(string(status), func(t *testing.T) {
			data, err := json.Marshal(status)
			require.NoError(t, err)

			var unmarshaled NamespaceStatus
			err = json.Unmarshal(data, &unmarshaled)
			require.NoError(t, err)

			assert.Equal(t, status, unmarshaled)
		})
	}
}
