// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package nodes

import (
	"time"

	"github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
)

type GPUInformation struct {
	Count              int32            `json:"count"`
	GPUType            string           `json:"type"`
	Vendor             common.GPUVendor `json:"vendor"`
	VRAMBytesPerDevice int64            `json:"vram_bytes_per_device"`
	ProductName        string           `json:"product_name"`
}

type ClusterNode struct {
	Name                  string          `json:"name"`
	CPUMilliCores         int64           `json:"cpu_milli_cores"`
	MemoryBytes           int64           `json:"memory_bytes"`
	EphemeralStorageBytes int64           `json:"ephemeral_storage_bytes"`
	GPUInformation        *GPUInformation `json:"gpu_information,omitempty"`
	Status                string          `json:"status"`
	IsReady               bool            `json:"is_ready"`
}

type ClusterNodesMessage struct {
	MessageType  messaging.MessageType `json:"message_type"`
	ClusterNodes []ClusterNode         `json:"cluster_nodes"`
	UpdatedAt    time.Time             `json:"updated_at"`
}

type ClusterNodeUpdateMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	ClusterNode ClusterNode           `json:"cluster_node"`
	UpdatedAt   time.Time             `json:"updated_at"`
}

type ClusterNodeDeleteMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	Name        string                `json:"name"`
	UpdatedAt   time.Time             `json:"updated_at"`
}
