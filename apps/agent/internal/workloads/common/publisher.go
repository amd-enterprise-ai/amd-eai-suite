// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"time"

	"github.com/silogen/agent/internal/messaging"
)

// PublishDeletionMessage publishes a deletion status message for a workload component.
func PublishDeletionMessage(ctx context.Context, publisher messaging.MessagePublisher, data *ComponentData) error {
	statusReason := "Resource has been removed from the cluster."
	message := messaging.WorkloadComponentStatusMessage{
		MessageType:  messaging.MessageTypeWorkloadComponentStatusUpdate,
		Name:         data.Name,
		Kind:         messaging.WorkloadComponentKind(data.Kind),
		APIVersion:   data.APIVersion,
		WorkloadID:   data.WorkloadID.String(),
		ID:           data.ComponentID.String(),
		Status:       StatusDeleted,
		StatusReason: &statusReason,
		UpdatedAt:    time.Now().UTC(),
	}

	return publisher.Publish(ctx, message)
}

// PublishWorkloadStatus publishes a high-level workload status update.
func PublishWorkloadStatus(
	ctx context.Context,
	publisher messaging.MessagePublisher,
	workloadID string,
	status messaging.WorkloadStatus,
	reason string,
) error {
	msg := &messaging.WorkloadStatusMessage{
		MessageType:  messaging.MessageTypeWorkloadStatusUpdate,
		Status:       status,
		WorkloadID:   workloadID,
		UpdatedAt:    time.Now().UTC(),
		StatusReason: &reason,
	}
	return publisher.Publish(ctx, msg)
}

// CreateComponentStatusMessage creates a workload component status message.
func CreateComponentStatusMessage(data *ComponentData, status string, statusReason string) *messaging.WorkloadComponentStatusMessage {
	return &messaging.WorkloadComponentStatusMessage{
		MessageType:  messaging.MessageTypeWorkloadComponentStatusUpdate,
		ID:           data.ComponentID.String(),
		Name:         data.Name,
		Kind:         messaging.WorkloadComponentKind(data.Kind),
		APIVersion:   data.APIVersion,
		WorkloadID:   data.WorkloadID.String(),
		Status:       status,
		StatusReason: &statusReason,
		UpdatedAt:    time.Now(),
	}
}

// CreateAutoDiscoveredMessage creates an auto-discovered workload component message.
func CreateAutoDiscoveredMessage(data *ComponentData) *messaging.AutoDiscoveredWorkloadComponentMessage {
	return &messaging.AutoDiscoveredWorkloadComponentMessage{
		MessageType:  messaging.MessageTypeAutoDiscoveredWorkloadComponent,
		ProjectID:    data.ProjectID.String(),
		WorkloadID:   data.WorkloadID.String(),
		ComponentID:  data.ComponentID.String(),
		Name:         data.Name,
		Kind:         messaging.WorkloadComponentKind(data.Kind),
		APIVersion:   data.APIVersion,
		UpdatedAt:    time.Now(),
		Submitter:    data.Submitter,
		WorkloadType: data.WorkloadType,
	}
}

// PublishStatusMessage publishes a workload component status message with logging.
func PublishStatusMessage(
	ctx context.Context,
	publisher messaging.MessagePublisher,
	data *ComponentData,
	status string,
	statusReason string,
) error {
	message := CreateComponentStatusMessage(data, status, statusReason)
	return publisher.Publish(ctx, message)
}

// PublishAutoDiscoveryMessage publishes an auto-discovered workload component message with logging.
func PublishAutoDiscoveryMessage(
	ctx context.Context,
	publisher messaging.MessagePublisher,
	data *ComponentData,
) error {
	message := CreateAutoDiscoveredMessage(data)
	return publisher.Publish(ctx, message)
}
