// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"time"

	"github.com/silogen/agent/internal/messaging"
)

type ConfigMapStatus string

const (
	ConfigMapStatusAdded   ConfigMapStatus = "Added"
	ConfigMapStatusDeleted ConfigMapStatus = "Deleted"
	ConfigMapStatusFailed  ConfigMapStatus = "Failed"
)

type ProjectS3StorageCreateMessage struct {
	MessageType      messaging.MessageType `json:"message_type"`
	ProjectStorageID string                `json:"project_storage_id"`
	ProjectName      string                `json:"project_name"`
	Manifest         string                `json:"manifest"`
}

type ProjectStorageDeleteMessage struct {
	MessageType      messaging.MessageType `json:"message_type"`
	ProjectStorageID string                `json:"project_storage_id"`
	ProjectName      string                `json:"project_name"`
}

type ProjectStorageUpdateMessage struct {
	MessageType      messaging.MessageType `json:"message_type"`
	ProjectStorageID string                `json:"project_storage_id"`
	Status           ConfigMapStatus       `json:"status"`
	StatusReason     *string               `json:"status_reason,omitempty"`
	UpdatedAt        time.Time             `json:"updated_at"`
}
