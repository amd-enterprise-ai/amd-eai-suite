// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"encoding/json"

	"github.com/silogen/agent/internal/messaging"
)

type NamespaceStatus string

const (
	NamespaceStatusActive       NamespaceStatus = "Active"
	NamespaceStatusTerminating  NamespaceStatus = "Terminating"
	NamespaceStatusPending      NamespaceStatus = "Pending"
	NamespaceStatusFailed       NamespaceStatus = "Failed"
	NamespaceStatusDeleted      NamespaceStatus = "Deleted"
	NamespaceStatusDeleteFailed NamespaceStatus = "DeleteFailed"
)

type GpuPreemptionPolicy string

const (
	GpuPreemptionPolicyOnPressure GpuPreemptionPolicy = "OnPressure"
	GpuPreemptionPolicyAlways     GpuPreemptionPolicy = "Always"
)

var AllGpuPreemptionPolicies = []GpuPreemptionPolicy{
	GpuPreemptionPolicyOnPressure,
	GpuPreemptionPolicyAlways,
}

type GpuPreemptionStatus struct {
	Enabled     bool                 `json:"enabled"`
	Threshold   *int                 `json:"threshold,omitempty"`
	GracePeriod *int                 `json:"grace_period,omitempty"`
	Policy      *GpuPreemptionPolicy `json:"policy,omitempty"`
}

type ProjectNamespaceStatusMessage struct {
	MessageType   messaging.MessageType `json:"message_type"`
	ProjectID     string                `json:"project_id"`
	Status        NamespaceStatus       `json:"status"`
	StatusReason  *string               `json:"status_reason,omitempty"`
	GpuPreemption *GpuPreemptionStatus  `json:"gpu_preemption,omitempty"`
}

type UnmanagedNamespaceMessage struct {
	MessageType     messaging.MessageType `json:"message_type"`
	NamespaceName   string                `json:"namespace_name"`
	NamespaceStatus NamespaceStatus       `json:"namespace_status"`
}

type ProjectNamespaceCreateMessage struct {
	MessageType       messaging.MessageType `json:"message_type"`
	NamespaceManifest json.RawMessage       `json:"namespace_manifest"`
}

type ProjectNamespaceDeleteMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	Name        string                `json:"name"`
	ProjectID   string                `json:"project_id"`
}

type ProjectNamespaceUpdateMessage struct {
	MessageType       messaging.MessageType `json:"message_type"`
	NamespaceManifest json.RawMessage       `json:"namespace_manifest"`
}

type NamespaceDeletedMessage struct {
	MessageType   messaging.MessageType `json:"message_type"`
	NamespaceName string                `json:"namespace_name"`
}
