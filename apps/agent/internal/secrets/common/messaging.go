// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"encoding/json"
	"time"

	"github.com/silogen/agent/internal/messaging"
)

type ProjectSecretStatus string

const (
	ProjectSecretStatusPending      ProjectSecretStatus = "Pending"
	ProjectSecretStatusSynced       ProjectSecretStatus = "Synced"
	ProjectSecretStatusFailed       ProjectSecretStatus = "Failed"
	ProjectSecretStatusSyncedError  ProjectSecretStatus = "SyncedError"
	ProjectSecretStatusDeleteFailed ProjectSecretStatus = "DeleteFailed"
	ProjectSecretStatusDeleted      ProjectSecretStatus = "Deleted"
	ProjectSecretStatusDeleting     ProjectSecretStatus = "Deleting"
	ProjectSecretStatusUnknown      ProjectSecretStatus = "Unknown"
)

type SecretKind string

const (
	SecretKindExternalSecret   SecretKind = "ExternalSecret"
	SecretKindKubernetesSecret SecretKind = "KubernetesSecret"
)

type SecretScope string

const (
	SecretScopeOrganization SecretScope = "Organization"
	SecretScopeProject      SecretScope = "Project"
)

var AllSecretScopes = []SecretScope{
	SecretScopeOrganization,
	SecretScopeProject,
}

type SecretUseCase string

const (
	SecretUseCaseHuggingFace     SecretUseCase = "HuggingFace"
	SecretUseCaseImagePullSecret SecretUseCase = "ImagePullSecret"
	SecretUseCaseS3              SecretUseCase = "S3"
	SecretUseCaseDatabase        SecretUseCase = "Database"
	SecretUseCaseGeneric         SecretUseCase = "Generic"
)

var AllSecretUseCases = []SecretUseCase{
	SecretUseCaseHuggingFace,
	SecretUseCaseImagePullSecret,
	SecretUseCaseS3,
	SecretUseCaseDatabase,
	SecretUseCaseGeneric,
}

type SecretManifestMetadata struct {
	Name        string            `json:"name"`
	Namespace   string            `json:"namespace"`
	Labels      map[string]string `json:"labels,omitempty"`
	Annotations map[string]string `json:"annotations,omitempty"`
}

type KubernetesSecretManifest struct {
	Kind       string                  `json:"kind"`
	Type       string                  `json:"type"`
	Metadata   *SecretManifestMetadata `json:"metadata,omitempty"`
	Data       map[string]string       `json:"data,omitempty"`
	StringData map[string]string       `json:"stringData,omitempty"`
}

type ExternalSecretManifest struct {
	Kind       string                  `json:"kind"`
	APIVersion string                  `json:"apiVersion,omitempty"`
	Metadata   *SecretManifestMetadata `json:"metadata,omitempty"`
	Spec       map[string]interface{}  `json:"spec,omitempty"`
}

type ProjectSecretsUpdateMessage struct {
	MessageType     messaging.MessageType `json:"message_type"`
	ProjectSecretID string                `json:"project_secret_id"`
	SecretScope     *SecretScope          `json:"secret_scope,omitempty"`
	Status          ProjectSecretStatus   `json:"status"`
	StatusReason    *string               `json:"status_reason,omitempty"`
	UpdatedAt       time.Time             `json:"updated_at"`
}

type ProjectSecretsCreateMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	Manifest    json.RawMessage       `json:"manifest"`
	SecretType  SecretKind            `json:"secret_type"`
}

type ProjectSecretsDeleteMessage struct {
	MessageType     messaging.MessageType `json:"message_type"`
	ProjectSecretID string                `json:"project_secret_id"`
	ProjectName     string                `json:"project_name"`
	SecretType      SecretKind            `json:"secret_type"`
	SecretScope     SecretScope           `json:"secret_scope"`
}

type AutoDiscoveredSecretMessage struct {
	MessageType messaging.MessageType `json:"message_type"`
	ProjectID   string                `json:"project_id"`
	SecretID    string                `json:"secret_id"`
	Name        string                `json:"name"`
	Kind        SecretKind            `json:"kind"`
	UseCase     *SecretUseCase        `json:"use_case,omitempty"`
	Submitter   *string               `json:"submitter,omitempty"`
	UpdatedAt   time.Time             `json:"updated_at"`
}
