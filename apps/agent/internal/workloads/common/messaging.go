// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"time"

	"github.com/silogen/agent/internal/messaging"
)

type WorkloadMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	Manifest    string                `json:"manifest"`
	UserToken   string                `json:"user_token"`
	WorkloadID  string                `json:"workload_id"`
}

type DeleteWorkloadMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	WorkloadID  string                `json:"workload_id"`
}

type WorkloadStatusMessage struct {
	MessageType  messaging.MessageType `json:"message_type"`
	Status       WorkloadStatus        `json:"status"`
	WorkloadID   string                `json:"workload_id"`
	UpdatedAt    time.Time             `json:"updated_at"`
	StatusReason *string               `json:"status_reason,omitempty"`
}

type WorkloadComponentStatusMessage struct {
	MessageType  messaging.MessageType `json:"message_type"`
	ID           string                `json:"id"`
	Name         string                `json:"name"`
	Kind         WorkloadComponentKind `json:"kind"`
	APIVersion   string                `json:"api_version"`
	WorkloadID   string                `json:"workload_id"`
	Status       string                `json:"status"`
	StatusReason *string               `json:"status_reason,omitempty"`
	UpdatedAt    time.Time             `json:"updated_at"`
}

type AutoDiscoveredWorkloadComponentMessage struct {
	MessageType  messaging.MessageType `json:"message_type"`
	ProjectID    string                `json:"project_id"`
	WorkloadID   string                `json:"workload_id"`
	ComponentID  string                `json:"component_id"`
	Name         string                `json:"name"`
	Kind         WorkloadComponentKind `json:"kind"`
	APIVersion   string                `json:"api_version"`
	UpdatedAt    time.Time             `json:"updated_at"`
	Submitter    *string               `json:"submitter,omitempty"`
	WorkloadType *string               `json:"workload_type,omitempty"`
}
