// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"time"

	"github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
)

type PriorityClass struct {
	Name     string `json:"name"`
	Priority int32  `json:"priority"`
}

type ClusterQuotaAllocation struct {
	CPUMilliCores         int64    `json:"cpu_milli_cores"`
	GPUCount              int64    `json:"gpu_count"`
	MemoryBytes           int64    `json:"memory_bytes"`
	EphemeralStorageBytes int64    `json:"ephemeral_storage_bytes"`
	QuotaName             string   `json:"quota_name"`
	Namespaces            []string `json:"namespaces"`
}

type ClusterQuotasAllocationMessage struct {
	MessageType      messaging.MessageType    `json:"message_type"`
	GPUVendor        *common.GPUVendor        `json:"gpu_vendor,omitempty"`
	QuotaAllocations []ClusterQuotaAllocation `json:"quota_allocations"`
	PriorityClasses  []PriorityClass          `json:"priority_classes"`
}

type ClusterQuotasStatusMessage struct {
	MessageType      messaging.MessageType    `json:"message_type"`
	UpdatedAt        time.Time                `json:"updated_at"`
	QuotaAllocations []ClusterQuotaAllocation `json:"quota_allocations"`
}

type ClusterQuotaFailureMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	UpdatedAt   time.Time             `json:"updated_at"`
	Reason      string                `json:"reason"`
}
