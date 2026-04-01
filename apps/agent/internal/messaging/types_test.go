// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestProjectNamespaceStatusMessage_MarshalJSON(t *testing.T) {
	reason := "Namespace is active"
	msg := &ProjectNamespaceStatusMessage{
		MessageType:  MessageTypeProjectNamespaceStatus,
		ProjectID:    "123e4567-e89b-12d3-a456-426614174000",
		Status:       NamespaceStatusActive,
		StatusReason: &reason,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectNamespaceStatusMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ProjectID, unmarshaled.ProjectID)
	assert.Equal(t, msg.Status, unmarshaled.Status)
	assert.NotNil(t, unmarshaled.StatusReason)
	assert.Equal(t, *msg.StatusReason, *unmarshaled.StatusReason)
}

func TestProjectNamespaceStatusMessage_MarshalJSON_WithoutReason(t *testing.T) {
	msg := &ProjectNamespaceStatusMessage{
		MessageType:  MessageTypeProjectNamespaceStatus,
		ProjectID:    "123e4567-e89b-12d3-a456-426614174000",
		Status:       NamespaceStatusActive,
		StatusReason: nil,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectNamespaceStatusMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ProjectID, unmarshaled.ProjectID)
	assert.Equal(t, msg.Status, unmarshaled.Status)
	assert.Nil(t, unmarshaled.StatusReason)
}

func TestUnmanagedNamespaceMessage_MarshalJSON(t *testing.T) {
	msg := &UnmanagedNamespaceMessage{
		MessageType:     MessageTypeUnmanagedNamespace,
		NamespaceName:   "test-namespace",
		NamespaceStatus: NamespaceStatusActive,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled UnmanagedNamespaceMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.NamespaceName, unmarshaled.NamespaceName)
	assert.Equal(t, msg.NamespaceStatus, unmarshaled.NamespaceStatus)
}

func TestNamespaceStatus_AllValues(t *testing.T) {
	statuses := []NamespaceStatus{
		NamespaceStatusActive,
		NamespaceStatusTerminating,
		NamespaceStatusPending,
		NamespaceStatusFailed,
		NamespaceStatusDeleted,
		NamespaceStatusDeleteFailed,
	}

	for _, status := range statuses {
		t.Run(string(status), func(t *testing.T) {
			data, err := json.Marshal(status)
			require.NoError(t, err)

			var unmarshaled NamespaceStatus
			err = json.Unmarshal(data, &unmarshaled)
			require.NoError(t, err)

			assert.Equal(t, status, unmarshaled)
		})
	}
}

func TestMessageType_Constants(t *testing.T) {
	assert.Equal(t, MessageType("project_namespace_create"), MessageTypeProjectNamespaceCreate)
	assert.Equal(t, MessageType("project_namespace_delete"), MessageTypeProjectNamespaceDelete)
	assert.Equal(t, MessageType("project_namespace_status"), MessageTypeProjectNamespaceStatus)
	assert.Equal(t, MessageType("unmanaged_namespace"), MessageTypeUnmanagedNamespace)
	assert.Equal(t, MessageType("heartbeat"), MessageTypeHeartbeat)
}

func TestHeartbeatMessage_MarshalJSON(t *testing.T) {
	now := time.Now().UTC()
	msg := &HeartbeatMessage{
		MessageType:      MessageTypeHeartbeat,
		LastHeartbeatAt:  now,
		ClusterName:      "test-cluster",
		OrganizationName: "test-org",
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	// Verify JSON structure
	var jsonMap map[string]interface{}
	err = json.Unmarshal(data, &jsonMap)
	require.NoError(t, err)

	assert.Equal(t, "heartbeat", jsonMap["message_type"])
	assert.Equal(t, "test-cluster", jsonMap["cluster_name"])
	assert.Contains(t, jsonMap, "last_heartbeat_at")

	// Verify timestamp is RFC3339 format
	timestampStr, ok := jsonMap["last_heartbeat_at"].(string)
	require.True(t, ok, "last_heartbeat_at should be a string")
	parsedTime, err := time.Parse(time.RFC3339, timestampStr)
	require.NoError(t, err)
	assert.WithinDuration(t, now, parsedTime, time.Second)

	// Test round-trip marshaling/unmarshaling
	var unmarshaled HeartbeatMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ClusterName, unmarshaled.ClusterName)
	assert.WithinDuration(t, msg.LastHeartbeatAt, unmarshaled.LastHeartbeatAt, time.Second)
}

func TestProjectSecretsCreateMessage_MarshalJSON(t *testing.T) {
	manifest := KubernetesSecretManifest{
		Kind: "Secret",
		Type: "Opaque",
		Metadata: &SecretManifestMetadata{
			Name:      "test-secret",
			Namespace: "test-namespace",
		},
		Data: map[string]string{
			"username": "YWRtaW4=", // base64 encoded "admin"
		},
	}
	manifestBytes, err := json.Marshal(manifest)
	require.NoError(t, err)

	msg := &ProjectSecretsCreateMessage{
		MessageType: MessageTypeProjectSecretsCreate,
		Manifest:    manifestBytes,
		SecretType:  SecretKindKubernetesSecret,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectSecretsCreateMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.SecretType, unmarshaled.SecretType)
	assert.Equal(t, string(msg.Manifest), string(unmarshaled.Manifest))
}

func TestProjectSecretsDeleteMessage_MarshalJSON(t *testing.T) {
	msg := &ProjectSecretsDeleteMessage{
		MessageType:     MessageTypeProjectSecretsDelete,
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		ProjectName:     "test-namespace",
		SecretType:      SecretKindKubernetesSecret,
		SecretScope:     SecretScopeProject,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectSecretsDeleteMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ProjectSecretID, unmarshaled.ProjectSecretID)
	assert.Equal(t, msg.ProjectName, unmarshaled.ProjectName)
	assert.Equal(t, msg.SecretType, unmarshaled.SecretType)
	assert.Equal(t, msg.SecretScope, unmarshaled.SecretScope)
}

func TestProjectSecretsUpdateMessage_MarshalJSON(t *testing.T) {
	reason := "Secret has been synced successfully"
	scope := SecretScopeProject
	msg := &ProjectSecretsUpdateMessage{
		MessageType:     MessageTypeProjectSecretsUpdate,
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		SecretScope:     &scope,
		Status:          ProjectSecretStatusSynced,
		StatusReason:    &reason,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectSecretsUpdateMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ProjectSecretID, unmarshaled.ProjectSecretID)
	assert.NotNil(t, unmarshaled.SecretScope)
	assert.Equal(t, *msg.SecretScope, *unmarshaled.SecretScope)
	assert.Equal(t, msg.Status, unmarshaled.Status)
	assert.NotNil(t, unmarshaled.StatusReason)
	assert.Equal(t, *msg.StatusReason, *unmarshaled.StatusReason)
}

func TestProjectSecretsUpdateMessage_MarshalJSON_WithoutOptionalFields(t *testing.T) {
	msg := &ProjectSecretsUpdateMessage{
		MessageType:     MessageTypeProjectSecretsUpdate,
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		Status:          ProjectSecretStatusPending,
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled ProjectSecretsUpdateMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ProjectSecretID, unmarshaled.ProjectSecretID)
	assert.Equal(t, msg.Status, unmarshaled.Status)
	assert.Nil(t, unmarshaled.SecretScope)
	assert.Nil(t, unmarshaled.StatusReason)
}

func TestKubernetesSecretManifest_MarshalJSON(t *testing.T) {
	manifest := KubernetesSecretManifest{
		Kind: "Secret",
		Type: "kubernetes.io/tls",
		Metadata: &SecretManifestMetadata{
			Labels: map[string]string{
				"app": "test-app",
			},
			Annotations: map[string]string{
				"description": "Test secret",
			},
		},
		Data: map[string]string{
			"tls.crt": "LS0tLS1CRUdJTi...", // base64 encoded cert
			"tls.key": "LS0tLS1CRUdJTi...", // base64 encoded key
		},
		StringData: map[string]string{
			"config": "key=value",
		},
	}

	data, err := json.Marshal(manifest)
	require.NoError(t, err)

	var unmarshaled KubernetesSecretManifest
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, manifest.Kind, unmarshaled.Kind)
	assert.Equal(t, manifest.Type, unmarshaled.Type)
	assert.NotNil(t, unmarshaled.Metadata)
	assert.Equal(t, manifest.Metadata.Labels, unmarshaled.Metadata.Labels)
	assert.Equal(t, manifest.Metadata.Annotations, unmarshaled.Metadata.Annotations)
	assert.Equal(t, manifest.Data, unmarshaled.Data)
	assert.Equal(t, manifest.StringData, unmarshaled.StringData)
}

func TestExternalSecretManifest_MarshalJSON(t *testing.T) {
	manifest := ExternalSecretManifest{
		Kind:       "ExternalSecret",
		APIVersion: "external-secrets.io/v1beta1",
		Metadata: &SecretManifestMetadata{
			Labels: map[string]string{
				"app": "test-app",
			},
		},
		Spec: map[string]interface{}{
			"secretStoreRef": map[string]interface{}{
				"name": "vault-backend",
				"kind": "SecretStore",
			},
			"target": map[string]interface{}{
				"name":           "kubernetes-secret-name",
				"creationPolicy": "Owner",
			},
		},
	}

	data, err := json.Marshal(manifest)
	require.NoError(t, err)

	var unmarshaled ExternalSecretManifest
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, manifest.Kind, unmarshaled.Kind)
	assert.Equal(t, manifest.APIVersion, unmarshaled.APIVersion)
	assert.NotNil(t, unmarshaled.Metadata)
	assert.Equal(t, manifest.Metadata.Labels, unmarshaled.Metadata.Labels)
	assert.NotNil(t, unmarshaled.Spec)

	// Verify spec structure
	secretStoreRef, ok := unmarshaled.Spec["secretStoreRef"].(map[string]interface{})
	require.True(t, ok)
	assert.Equal(t, "vault-backend", secretStoreRef["name"])
}

func TestProjectSecretStatus_AllValues(t *testing.T) {
	statuses := []ProjectSecretStatus{
		ProjectSecretStatusPending,
		ProjectSecretStatusSynced,
		ProjectSecretStatusFailed,
		ProjectSecretStatusSyncedError,
		ProjectSecretStatusDeleteFailed,
		ProjectSecretStatusDeleted,
		ProjectSecretStatusDeleting,
		ProjectSecretStatusUnknown,
	}

	for _, status := range statuses {
		t.Run(string(status), func(t *testing.T) {
			data, err := json.Marshal(status)
			require.NoError(t, err)

			var unmarshaled ProjectSecretStatus
			err = json.Unmarshal(data, &unmarshaled)
			require.NoError(t, err)

			assert.Equal(t, status, unmarshaled)
		})
	}
}

func TestSecretKind_AllValues(t *testing.T) {
	kinds := []SecretKind{
		SecretKindExternalSecret,
		SecretKindKubernetesSecret,
	}

	for _, kind := range kinds {
		t.Run(string(kind), func(t *testing.T) {
			data, err := json.Marshal(kind)
			require.NoError(t, err)

			var unmarshaled SecretKind
			err = json.Unmarshal(data, &unmarshaled)
			require.NoError(t, err)

			assert.Equal(t, kind, unmarshaled)
		})
	}
}

func TestSecretScope_AllValues(t *testing.T) {
	scopes := []SecretScope{
		SecretScopeOrganization,
		SecretScopeProject,
	}

	for _, scope := range scopes {
		t.Run(string(scope), func(t *testing.T) {
			data, err := json.Marshal(scope)
			require.NoError(t, err)

			var unmarshaled SecretScope
			err = json.Unmarshal(data, &unmarshaled)
			require.NoError(t, err)

			assert.Equal(t, scope, unmarshaled)
		})
	}
}

func TestSecretMessageType_Constants(t *testing.T) {
	assert.Equal(t, MessageType("project_secrets_create"), MessageTypeProjectSecretsCreate)
	assert.Equal(t, MessageType("project_secrets_delete"), MessageTypeProjectSecretsDelete)
	assert.Equal(t, MessageType("project_secrets_update"), MessageTypeProjectSecretsUpdate)
}

func TestParseMessageEnvelope_SecretMessages(t *testing.T) {
	tests := []struct {
		name        string
		messageType MessageType
		payload     string
	}{
		{
			name:        "project_secrets_create",
			messageType: MessageTypeProjectSecretsCreate,
			payload:     `{"message_type":"project_secrets_create","project_name":"test","secret_name":"test-secret"}`,
		},
		{
			name:        "project_secrets_delete",
			messageType: MessageTypeProjectSecretsDelete,
			payload:     `{"message_type":"project_secrets_delete","project_secret_id":"123"}`,
		},
		{
			name:        "project_secrets_update",
			messageType: MessageTypeProjectSecretsUpdate,
			payload:     `{"message_type":"project_secrets_update","project_secret_id":"123","status":"Synced"}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rawMsg, err := ParseMessageEnvelope([]byte(tt.payload))
			require.NoError(t, err)
			assert.Equal(t, tt.messageType, rawMsg.Type)
			assert.Equal(t, tt.payload, string(rawMsg.Payload))
		})
	}
}
