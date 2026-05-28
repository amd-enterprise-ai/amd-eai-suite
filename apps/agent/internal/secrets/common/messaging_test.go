// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"encoding/json"
	"testing"

	"github.com/silogen/agent/internal/messaging"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestProjectSecretsCreateMessage_MarshalJSON(t *testing.T) {
	manifest := KubernetesSecretManifest{
		Kind: "Secret",
		Type: "Opaque",
		Metadata: &SecretManifestMetadata{
			Name:      "test-secret",
			Namespace: "test-namespace",
		},
		Data: map[string]string{
			"username": "YWRtaW4=",
		},
	}
	manifestBytes, err := json.Marshal(manifest)
	require.NoError(t, err)

	msg := &ProjectSecretsCreateMessage{
		MessageType: messaging.MessageTypeProjectSecretsCreate,
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
		MessageType:     messaging.MessageTypeProjectSecretsDelete,
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
		MessageType:     messaging.MessageTypeProjectSecretsUpdate,
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
		MessageType:     messaging.MessageTypeProjectSecretsUpdate,
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
			"tls.crt": "LS0tLS1CRUdJTi...",
			"tls.key": "LS0tLS1CRUdJTi...",
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
