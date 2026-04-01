// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"testing"

	"github.com/google/uuid"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestCreateComponentStatusMessage(t *testing.T) {
	workloadID := uuid.MustParse("827862af-41b9-4bd6-bd8d-04e4e866dff3")
	componentID := uuid.MustParse("98a47b94-3753-48b7-9b95-0b91f2df27b0")
	projectID := uuid.MustParse("121aede7-b363-4188-8d5a-2e034e4d0b3f")

	tests := []struct {
		name               string
		componentData      *ComponentData
		status             string
		statusReason       string
		expectedStatusKind string
	}{
		{
			name: "pod status message",
			componentData: &ComponentData{
				Name:        "test-pod",
				Kind:        "Pod",
				APIVersion:  "v1",
				WorkloadID:  workloadID,
				ComponentID: componentID,
				ProjectID:   projectID,
			},
			status:             "Running",
			statusReason:       "Pod is running",
			expectedStatusKind: "Pod",
		},
		{
			name: "deployment status message",
			componentData: &ComponentData{
				Name:        "test-deployment",
				Kind:        "Deployment",
				APIVersion:  "apps/v1",
				WorkloadID:  workloadID,
				ComponentID: componentID,
				ProjectID:   projectID,
			},
			status:             "Running",
			statusReason:       "All replicas are running",
			expectedStatusKind: "Deployment",
		},
		{
			name: "cronjob status message",
			componentData: &ComponentData{
				Name:        "test-cronjob",
				Kind:        "CronJob",
				APIVersion:  "batch/v1",
				WorkloadID:  workloadID,
				ComponentID: componentID,
				ProjectID:   projectID,
			},
			status:             "Ready",
			statusReason:       "CronJob is scheduled",
			expectedStatusKind: "CronJob",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			msg := CreateComponentStatusMessage(tt.componentData, tt.status, tt.statusReason)

			assert.NotNil(t, msg)
			assert.Equal(t, messaging.MessageTypeWorkloadComponentStatusUpdate, msg.MessageType)
			assert.Equal(t, tt.componentData.Name, msg.Name)
			assert.Equal(t, messaging.WorkloadComponentKind(tt.expectedStatusKind), msg.Kind)
			assert.Equal(t, tt.componentData.APIVersion, msg.APIVersion)
			assert.Equal(t, tt.componentData.WorkloadID.String(), msg.WorkloadID)
			assert.Equal(t, tt.componentData.ComponentID.String(), msg.ID)
			assert.Equal(t, tt.status, msg.Status)
			assert.NotNil(t, msg.StatusReason)
			assert.Equal(t, tt.statusReason, *msg.StatusReason)
			assert.False(t, msg.UpdatedAt.IsZero())
		})
	}
}

func TestCreateAutoDiscoveredMessage(t *testing.T) {
	workloadID := uuid.MustParse("827862af-41b9-4bd6-bd8d-04e4e866dff3")
	componentID := uuid.MustParse("98a47b94-3753-48b7-9b95-0b91f2df27b0")
	projectID := uuid.MustParse("121aede7-b363-4188-8d5a-2e034e4d0b3f")
	submitter := "user@example.com"
	workloadTypeInference := "INFERENCE"

	tests := []struct {
		name                 string
		componentData        *ComponentData
		expectedKind         string
		expectSubmitter      bool
		expectedSubmitter    string
		expectWorkloadType   bool
		expectedWorkloadType string
	}{
		{
			name: "auto-discovered pod with submitter",
			componentData: &ComponentData{
				Name:           "test-pod",
				Kind:           "Pod",
				APIVersion:     "v1",
				WorkloadID:     workloadID,
				ComponentID:    componentID,
				ProjectID:      projectID,
				AutoDiscovered: true,
				Submitter:      &submitter,
			},
			expectedKind:       "Pod",
			expectSubmitter:    true,
			expectedSubmitter:  submitter,
			expectWorkloadType: false,
		},
		{
			name: "auto-discovered deployment without submitter",
			componentData: &ComponentData{
				Name:           "test-deployment",
				Kind:           "Deployment",
				APIVersion:     "apps/v1",
				WorkloadID:     workloadID,
				ComponentID:    componentID,
				ProjectID:      projectID,
				AutoDiscovered: true,
				Submitter:      nil,
			},
			expectedKind:       "Deployment",
			expectSubmitter:    false,
			expectWorkloadType: false,
		},
		{
			name: "auto-discovered daemonset with submitter",
			componentData: &ComponentData{
				Name:           "test-daemonset",
				Kind:           "DaemonSet",
				APIVersion:     "apps/v1",
				WorkloadID:     workloadID,
				ComponentID:    componentID,
				ProjectID:      projectID,
				AutoDiscovered: true,
				Submitter:      &submitter,
			},
			expectedKind:       "DaemonSet",
			expectSubmitter:    true,
			expectedSubmitter:  submitter,
			expectWorkloadType: false,
		},
		{
			name: "auto-discovered deployment with workload type",
			componentData: &ComponentData{
				Name:           "test-inference",
				Kind:           "Deployment",
				APIVersion:     "apps/v1",
				WorkloadID:     workloadID,
				ComponentID:    componentID,
				ProjectID:      projectID,
				AutoDiscovered: true,
				Submitter:      &submitter,
				WorkloadType:   &workloadTypeInference,
			},
			expectedKind:         "Deployment",
			expectSubmitter:      true,
			expectedSubmitter:    submitter,
			expectWorkloadType:   true,
			expectedWorkloadType: "INFERENCE",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			msg := CreateAutoDiscoveredMessage(tt.componentData)

			assert.NotNil(t, msg)
			assert.Equal(t, messaging.MessageTypeAutoDiscoveredWorkloadComponent, msg.MessageType)
			assert.Equal(t, tt.componentData.ProjectID.String(), msg.ProjectID)
			assert.Equal(t, tt.componentData.WorkloadID.String(), msg.WorkloadID)
			assert.Equal(t, tt.componentData.ComponentID.String(), msg.ComponentID)
			assert.Equal(t, tt.componentData.Name, msg.Name)
			assert.Equal(t, messaging.WorkloadComponentKind(tt.expectedKind), msg.Kind)
			assert.Equal(t, tt.componentData.APIVersion, msg.APIVersion)
			assert.False(t, msg.UpdatedAt.IsZero())

			if tt.expectSubmitter {
				assert.NotNil(t, msg.Submitter)
				assert.Equal(t, tt.expectedSubmitter, *msg.Submitter)
			} else {
				assert.Nil(t, msg.Submitter)
			}

			if tt.expectWorkloadType {
				assert.NotNil(t, msg.WorkloadType)
				assert.Equal(t, tt.expectedWorkloadType, *msg.WorkloadType)
			} else {
				assert.Nil(t, msg.WorkloadType)
			}
		})
	}
}

func TestPublishWorkloadStatus(t *testing.T) {
	pub := testutils.NewMockPublisher()
	reason := "No resources found for deletion"

	err := PublishWorkloadStatus(
		context.Background(),
		pub,
		"11111111-1111-1111-1111-111111111111",
		messaging.WorkloadStatusDeleted,
		reason,
	)
	require.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(*messaging.WorkloadStatusMessage)
	require.True(t, ok, "expected WorkloadStatusMessage, got %T", pub.Published[0])

	assert.Equal(t, messaging.MessageTypeWorkloadStatusUpdate, msg.MessageType)
	assert.Equal(t, messaging.WorkloadStatusDeleted, msg.Status)
	assert.Equal(t, "11111111-1111-1111-1111-111111111111", msg.WorkloadID)
	require.NotNil(t, msg.StatusReason)
	assert.Equal(t, reason, *msg.StatusReason)
	assert.False(t, msg.UpdatedAt.IsZero())
}

func TestPublishDeletionMessage_FromPublisherHelpers(t *testing.T) {
	pub := testutils.NewMockPublisher()
	workloadID := uuid.MustParse("827862af-41b9-4bd6-bd8d-04e4e866dff3")
	componentID := uuid.MustParse("98a47b94-3753-48b7-9b95-0b91f2df27b0")
	projectID := uuid.MustParse("121aede7-b363-4188-8d5a-2e034e4d0b3f")

	data := &ComponentData{
		Name:        "cm1",
		Kind:        "ConfigMap",
		APIVersion:  "v1",
		WorkloadID:  workloadID,
		ComponentID: componentID,
		ProjectID:   projectID,
	}

	err := PublishDeletionMessage(context.Background(), pub, data)
	require.NoError(t, err)

	require.Len(t, pub.Published, 1)
	// Note: PublishDeletionMessage publishes a non-pointer value.
	msg, ok := pub.Published[0].(messaging.WorkloadComponentStatusMessage)
	require.True(t, ok, "expected WorkloadComponentStatusMessage value, got %T", pub.Published[0])

	assert.Equal(t, messaging.MessageTypeWorkloadComponentStatusUpdate, msg.MessageType)
	assert.Equal(t, data.Name, msg.Name)
	assert.Equal(t, messaging.WorkloadComponentKind(data.Kind), msg.Kind)
	assert.Equal(t, data.APIVersion, msg.APIVersion)
	assert.Equal(t, data.WorkloadID.String(), msg.WorkloadID)
	assert.Equal(t, data.ComponentID.String(), msg.ID)
	assert.Equal(t, "Deleted", msg.Status)
	require.NotNil(t, msg.StatusReason)
	assert.Contains(t, *msg.StatusReason, "removed")
	assert.False(t, msg.UpdatedAt.IsZero())
}
