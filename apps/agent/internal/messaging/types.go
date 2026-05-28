// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

// MessageType identifies the message for routing.
type MessageType string

const (
	MessageTypeProjectNamespaceCreate          MessageType = "project_namespace_create"
	MessageTypeProjectNamespaceDelete          MessageType = "project_namespace_delete"
	MessageTypeProjectNamespaceUpdate          MessageType = "project_namespace_update"
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
