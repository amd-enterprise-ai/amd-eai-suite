// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"encoding/json"
	"fmt"
	"time"
)

// MessageType identifies the message for routing.
type MessageType string

const (
	MessageTypeProjectNamespaceCreate          MessageType = "project_namespace_create"
	MessageTypeProjectNamespaceDelete          MessageType = "project_namespace_delete"
	MessageTypeProjectNamespaceStatus          MessageType = "project_namespace_status"
	MessageTypeNamespaceDeleted                MessageType = "namespace_deleted"
	MessageTypeClusterQuotasAllocationMessage  MessageType = "cluster_quotas_allocation"
	MessageTypeClusterQuotasFailureMessage     MessageType = "cluster_quotas_failure"
	MessageTypeClusterQuotasStatusMessage      MessageType = "cluster_quotas_status"
	MessageTypeUnmanagedNamespace              MessageType = "unmanaged_namespace"
	MessageTypeHeartbeat                       MessageType = "heartbeat"
	MessageTypeClusterNodes                    MessageType = "cluster_nodes"
	MessageTypeClusterNodeUpdate               MessageType = "cluster_node_update"
	MessageTypeClusterNodeDelete               MessageType = "cluster_node_delete"
	MessageTypeProjectSecretsCreate            MessageType = "project_secrets_create"
	MessageTypeProjectSecretsDelete            MessageType = "project_secrets_delete"
	MessageTypeProjectSecretsUpdate            MessageType = "project_secrets_update"
	MessageTypeProjectS3StorageCreate          MessageType = "project_s3_storage_create"
	MessageTypeProjectStorageDelete            MessageType = "project_storage_delete"
	MessageTypeProjectStorageUpdate            MessageType = "project_storage_update"
	MessageTypeWorkload                        MessageType = "workload"
	MessageTypeDeleteWorkload                  MessageType = "delete_workload"
	MessageTypeWorkloadStatusUpdate            MessageType = "workload_status_update"
	MessageTypeWorkloadComponentStatusUpdate   MessageType = "workload_component_status_update"
	MessageTypeAutoDiscoveredWorkloadComponent MessageType = "auto_discovered_workload_component"
	MessageTypeAutoDiscoveredSecret            MessageType = "auto_discovered_secret"
)

// NamespaceStatus represents the status of a namespace.
type NamespaceStatus string

const (
	NamespaceStatusActive       NamespaceStatus = "Active"
	NamespaceStatusTerminating  NamespaceStatus = "Terminating"
	NamespaceStatusPending      NamespaceStatus = "Pending"
	NamespaceStatusFailed       NamespaceStatus = "Failed"
	NamespaceStatusDeleted      NamespaceStatus = "Deleted"
	NamespaceStatusDeleteFailed NamespaceStatus = "DeleteFailed"
)

// ProjectSecretStatus represents the status of a secret.
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

// TODO: AllSecretScopes and AllSecretUseCases duplicate the const block above.
// Go has no built-in enum iteration, so new values must be added in two places.
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
	Data       map[string]string       `json:"data,omitempty"`       // Base64 encoded in JSON
	StringData map[string]string       `json:"stringData,omitempty"` // Plain text in JSON
}

type ExternalSecretManifest struct {
	Kind       string                  `json:"kind"`
	APIVersion string                  `json:"apiVersion,omitempty"`
	Metadata   *SecretManifestMetadata `json:"metadata,omitempty"`
	Spec       map[string]interface{}  `json:"spec,omitempty"` // Generic spec for flexibility
}

// MessageEnvelope extracts message_type for routing.
type MessageEnvelope struct {
	MessageType MessageType `json:"message_type"`
}

// RawMessage holds type and raw payload for handler parsing.
type RawMessage struct {
	Type    MessageType
	Payload []byte
}

// ParseMessageEnvelope extracts message type from JSON.
func ParseMessageEnvelope(data []byte) (*RawMessage, error) {
	var envelope MessageEnvelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		return nil, fmt.Errorf("failed to parse message: %w", err)
	}

	if envelope.MessageType == "" {
		return nil, fmt.Errorf("message_type is required")
	}

	return &RawMessage{
		Type:    envelope.MessageType,
		Payload: data,
	}, nil
}

// ProjectNamespaceStatusMessage represents a namespace status update for a managed namespace.
type ProjectNamespaceStatusMessage struct {
	MessageType  MessageType     `json:"message_type"`
	ProjectID    string          `json:"project_id"`
	Status       NamespaceStatus `json:"status"`
	StatusReason *string         `json:"status_reason,omitempty"`
}

// UnmanagedNamespaceMessage represents an unmanaged namespace event.
type UnmanagedNamespaceMessage struct {
	MessageType     MessageType     `json:"message_type"`
	NamespaceName   string          `json:"namespace_name"`
	NamespaceStatus NamespaceStatus `json:"namespace_status"`
}

// ProjectNamespaceCreateMessage represents a request to create a namespace.
type ProjectNamespaceCreateMessage struct {
	MessageType       MessageType     `json:"message_type"`
	NamespaceManifest json.RawMessage `json:"namespace_manifest"`
}

// ProjectNamespaceDeleteMessage represents a request to delete a namespace.
type ProjectNamespaceDeleteMessage struct {
	MessageType MessageType `json:"message_type"`
	Name        string      `json:"name"`
	ProjectID   string      `json:"project_id"`
}

// NamespaceDeletedMessage represents a namespace that has been deleted from the cluster.
type NamespaceDeletedMessage struct {
	MessageType   MessageType `json:"message_type"`
	NamespaceName string      `json:"namespace_name"`
}

// HeartbeatMessage represents a heartbeat message sent to the common queue.
type HeartbeatMessage struct {
	MessageType      MessageType `json:"message_type"`
	LastHeartbeatAt  time.Time   `json:"last_heartbeat_at"`
	ClusterName      string      `json:"cluster_name"`
	OrganizationName string      `json:"organization_name"`
}

type GPUVendor string

const (
	GPUVendorNVIDIA GPUVendor = "NVIDIA"
	GPUVendorAMD    GPUVendor = "AMD"
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

// ClusterQuotasAllocationMessage represents a request to update cluster quotas.
type ClusterQuotasAllocationMessage struct {
	MessageType      MessageType              `json:"message_type"`
	GPUVendor        *GPUVendor               `json:"gpu_vendor,omitempty"`
	QuotaAllocations []ClusterQuotaAllocation `json:"quota_allocations"`
	PriorityClasses  []PriorityClass          `json:"priority_classes"`
}

type ClusterQuotasStatusMessage struct {
	MessageType      MessageType              `json:"message_type"`
	UpdatedAt        time.Time                `json:"updated_at"`
	QuotaAllocations []ClusterQuotaAllocation `json:"quota_allocations"`
}

type ClusterQuotaFailureMessage struct {
	MessageType MessageType `json:"message_type"`
	UpdatedAt   time.Time   `json:"updated_at"`
	Reason      string      `json:"reason"`
}

type GPUInformation struct {
	Count              int32     `json:"count"`
	GPUType            string    `json:"type"`
	Vendor             GPUVendor `json:"vendor"`
	VRAMBytesPerDevice int64     `json:"vram_bytes_per_device"`
	ProductName        string    `json:"product_name"`
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
	MessageType  MessageType   `json:"message_type"`
	ClusterNodes []ClusterNode `json:"cluster_nodes"`
	UpdatedAt    time.Time     `json:"updated_at"`
}

type ClusterNodeUpdateMessage struct {
	MessageType MessageType `json:"message_type"`
	ClusterNode ClusterNode `json:"cluster_node"`
	UpdatedAt   time.Time   `json:"updated_at"`
}

type ClusterNodeDeleteMessage struct {
	MessageType MessageType `json:"message_type"`
	Name        string      `json:"name"`
	UpdatedAt   time.Time   `json:"updated_at"`
}

type ProjectSecretsUpdateMessage struct {
	MessageType     MessageType         `json:"message_type"`
	ProjectSecretID string              `json:"project_secret_id"`
	SecretScope     *SecretScope        `json:"secret_scope,omitempty"`
	Status          ProjectSecretStatus `json:"status"`
	StatusReason    *string             `json:"status_reason,omitempty"`
	UpdatedAt       time.Time           `json:"updated_at"`
}

type ProjectSecretsCreateMessage struct {
	MessageType MessageType     `json:"message_type"`
	Manifest    json.RawMessage `json:"manifest"`
	SecretType  SecretKind      `json:"secret_type"`
}

type ProjectSecretsDeleteMessage struct {
	MessageType     MessageType `json:"message_type"`
	ProjectSecretID string      `json:"project_secret_id"`
	ProjectName     string      `json:"project_name"`
	SecretType      SecretKind  `json:"secret_type"`
	SecretScope     SecretScope `json:"secret_scope"`
}

// ConfigMapStatus represents the status of a ConfigMap.
type ConfigMapStatus string

const (
	ConfigMapStatusAdded   ConfigMapStatus = "Added"
	ConfigMapStatusDeleted ConfigMapStatus = "Deleted"
	ConfigMapStatusFailed  ConfigMapStatus = "Failed"
)

// ProjectS3StorageCreateMessage represents a request to create storage ConfigMap.
// The manifest is a fully-built YAML (namespace, labels set by the API).
type ProjectS3StorageCreateMessage struct {
	MessageType      MessageType `json:"message_type"`
	ProjectStorageID string      `json:"project_storage_id"`
	ProjectName      string      `json:"project_name"`
	Manifest         string      `json:"manifest"`
}

// ProjectStorageDeleteMessage represents a request to delete storage ConfigMap.
type ProjectStorageDeleteMessage struct {
	MessageType      MessageType `json:"message_type"`
	ProjectStorageID string      `json:"project_storage_id"`
	ProjectName      string      `json:"project_name"`
}

// ProjectStorageUpdateMessage represents a storage status update.
type ProjectStorageUpdateMessage struct {
	MessageType      MessageType     `json:"message_type"`
	ProjectStorageID string          `json:"project_storage_id"`
	Status           ConfigMapStatus `json:"status"`
	StatusReason     *string         `json:"status_reason,omitempty"`
	UpdatedAt        time.Time       `json:"updated_at"`
}

// WorkloadMessage represents a request to create/apply one or more workload resources (YAML multi-doc supported).
type WorkloadMessage struct {
	MessageType MessageType `json:"message_type"`
	Manifest    string      `json:"manifest"`
	UserToken   string      `json:"user_token"`
	WorkloadID  string      `json:"workload_id"`
}

// DeleteWorkloadMessage represents a request to delete workload resources by workload-id label selector.
type DeleteWorkloadMessage struct {
	MessageType MessageType `json:"message_type"`
	WorkloadID  string      `json:"workload_id"`
}

// WorkloadStatus represents the high-level status of a workload.
type WorkloadStatus string

const (
	WorkloadStatusDeleted WorkloadStatus = "Deleted"
)

// WorkloadStatusMessage represents a high-level workload status update.
type WorkloadStatusMessage struct {
	MessageType  MessageType    `json:"message_type"`
	Status       WorkloadStatus `json:"status"`
	WorkloadID   string         `json:"workload_id"`
	UpdatedAt    time.Time      `json:"updated_at"`
	StatusReason *string        `json:"status_reason,omitempty"`
}

// WorkloadComponentKind represents the kind of workload component.
type WorkloadComponentKind string

const (
	WorkloadComponentKindDeployment   WorkloadComponentKind = "Deployment"
	WorkloadComponentKindJob          WorkloadComponentKind = "Job"
	WorkloadComponentKindStatefulSet  WorkloadComponentKind = "StatefulSet"
	WorkloadComponentKindDaemonSet    WorkloadComponentKind = "DaemonSet"
	WorkloadComponentKindReplicaSet   WorkloadComponentKind = "ReplicaSet"
	WorkloadComponentKindCronJob      WorkloadComponentKind = "CronJob"
	WorkloadComponentKindPod          WorkloadComponentKind = "Pod"
	WorkloadComponentKindKaiwoJob     WorkloadComponentKind = "KaiwoJob"
	WorkloadComponentKindKaiwoService WorkloadComponentKind = "KaiwoService"
	WorkloadComponentKindService      WorkloadComponentKind = "Service"
	WorkloadComponentKindConfigMap    WorkloadComponentKind = "ConfigMap"
	WorkloadComponentKindIngress      WorkloadComponentKind = "Ingress"
	WorkloadComponentKindHTTPRoute    WorkloadComponentKind = "HTTPRoute"
)

// WorkloadComponentStatusMessage represents a workload component status update.
type WorkloadComponentStatusMessage struct {
	MessageType  MessageType           `json:"message_type"`
	ID           string                `json:"id"`
	Name         string                `json:"name"`
	Kind         WorkloadComponentKind `json:"kind"`
	APIVersion   string                `json:"api_version"`
	WorkloadID   string                `json:"workload_id"`
	Status       string                `json:"status"`
	StatusReason *string               `json:"status_reason,omitempty"`
	UpdatedAt    time.Time             `json:"updated_at"`
}

// AutoDiscoveredWorkloadComponentMessage represents an auto-discovered workload component.
type AutoDiscoveredWorkloadComponentMessage struct {
	MessageType  MessageType           `json:"message_type"`
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

// AutoDiscoveredSecretMessage represents an auto-discovered secret or external secret.
type AutoDiscoveredSecretMessage struct {
	MessageType MessageType `json:"message_type"`
	ProjectID   string      `json:"project_id"`
	SecretID    string      `json:"secret_id"`
	Name        string      `json:"name"`
	Kind        SecretKind  `json:"kind"`
	UseCase     *string     `json:"use_case,omitempty"`
	Submitter   *string     `json:"submitter,omitempty"`
	UpdatedAt   time.Time   `json:"updated_at"`
}
