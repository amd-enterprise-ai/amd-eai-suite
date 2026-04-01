// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package secrets

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/testutils"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	"k8s.io/client-go/kubernetes/fake"
	k8stesting "k8s.io/client-go/testing"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/secrets/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestLogger() logr.Logger {
	return zap.New()
}

func TestNewSecretHandler(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	require.NotNil(t, handler)
	assert.Equal(t, clientset, handler.clientset)
	assert.Equal(t, publisher, handler.publisher)
	assert.Equal(t, logger, handler.logger)
}

func TestSecretHandler_HandleCreate_KubernetesSecret(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	manifest := &messaging.KubernetesSecretManifest{
		Type: "Opaque",
		Metadata: &messaging.SecretManifestMetadata{
			Name:      "test-secret",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: string(messaging.SecretScopeProject),
			},
		},
		StringData: map[string]string{
			"username": "testuser",
			"password": "testpass",
		},
	}

	manifestJSON, _ := json.Marshal(manifest)

	createMsg := messaging.ProjectSecretsCreateMessage{
		SecretType: messaging.SecretKindKubernetesSecret,
		Manifest:   manifestJSON,
	}

	payload, _ := json.Marshal(createMsg)
	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsCreate,
		Payload: payload,
	}

	// Create namespace first
	_, err := clientset.CoreV1().Namespaces().Create(context.Background(),
		&corev1.Namespace{ObjectMeta: metav1.ObjectMeta{Name: "test-namespace"}},
		metav1.CreateOptions{})
	require.NoError(t, err)

	// Handle the create message
	err = handler.HandleCreate(context.Background(), rawMsg)

	assert.NoError(t, err)

	// Verify secret was created
	secret, err := clientset.CoreV1().Secrets("test-namespace").Get(context.Background(), "test-secret", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, "test-secret", secret.Name)
	assert.Equal(t, "550e8400-e29b-41d4-a716-446655440000", secret.Labels[common.ProjectSecretIDLabel])
	assert.Equal(t, "Project", secret.Labels[common.ProjectSecretScopeLabel])
	assert.Equal(t, "testuser", secret.StringData["username"])
}

func TestSecretHandler_HandleCreate_AlreadyExists(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	// Create namespace
	_, err := clientset.CoreV1().Namespaces().Create(context.Background(),
		&corev1.Namespace{ObjectMeta: metav1.ObjectMeta{Name: "test-namespace"}},
		metav1.CreateOptions{})
	require.NoError(t, err)

	// Create existing secret
	existingSecret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-secret",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: "Project",
			},
		},
		Type: corev1.SecretTypeOpaque,
		Data: map[string][]byte{
			"username": []byte("olduser"),
		},
	}
	_, err = clientset.CoreV1().Secrets("test-namespace").Create(context.Background(), existingSecret, metav1.CreateOptions{})
	require.NoError(t, err)

	manifest := &messaging.KubernetesSecretManifest{
		Type: "Opaque",
		Metadata: &messaging.SecretManifestMetadata{
			Name:      "test-secret",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: string(messaging.SecretScopeProject),
			},
		},
		StringData: map[string]string{
			"username": "newuser",
			"password": "newpass",
		},
	}

	manifestJSON, _ := json.Marshal(manifest)

	createMsg := messaging.ProjectSecretsCreateMessage{
		SecretType: messaging.SecretKindKubernetesSecret,
		Manifest:   manifestJSON,
	}

	payload, _ := json.Marshal(createMsg)
	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsCreate,
		Payload: payload,
	}

	// Handle the create message (should warn and return nil)
	err = handler.HandleCreate(context.Background(), rawMsg)

	assert.NoError(t, err)

	// Verify secret was NOT updated (new behavior - just warns)
	secret, err := clientset.CoreV1().Secrets("test-namespace").Get(context.Background(), "test-secret", metav1.GetOptions{})
	require.NoError(t, err)
	// Check that Data is preserved (the fake client converts StringData to Data on create)
	assert.NotEmpty(t, secret.Data, "secret.Data should not be empty")
	assert.Equal(t, "olduser", string(secret.Data["username"]))
	// Controller will handle the status update
}

func TestSecretHandler_HandleCreate_MinimalManifest(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	manifest := &messaging.KubernetesSecretManifest{
		Metadata: &messaging.SecretManifestMetadata{
			Name:      "test-secret",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: "project",
			},
		},
	}
	manifestJSON, err := json.Marshal(manifest)
	require.NoError(t, err)

	createMsg := messaging.ProjectSecretsCreateMessage{
		SecretType: messaging.SecretKindKubernetesSecret,
		Manifest:   manifestJSON,
	}

	payload, err := json.Marshal(createMsg)
	require.NoError(t, err)

	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsCreate,
		Payload: payload,
	}

	err = handler.HandleCreate(context.Background(), rawMsg)

	assert.NoError(t, err)

	// Verify secret was created
	secret, err := clientset.CoreV1().Secrets("test-namespace").Get(context.Background(), "test-secret", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, "test-secret", secret.Name)
	assert.Equal(t, "test-namespace", secret.Namespace)
	assert.Equal(t, "550e8400-e29b-41d4-a716-446655440000", secret.Labels[common.ProjectSecretIDLabel])
}

func TestSecretHandler_HandleCreate_UnsupportedSecretType(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	manifest := &messaging.KubernetesSecretManifest{
		Metadata: &messaging.SecretManifestMetadata{
			Name:      "test-secret",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.ProjectSecretIDLabel: "550e8400-e29b-41d4-a716-446655440000",
			},
		},
	}
	manifestJSON, _ := json.Marshal(manifest)

	createMsg := messaging.ProjectSecretsCreateMessage{
		SecretType: "UnsupportedType",
		Manifest:   manifestJSON,
	}

	payload, _ := json.Marshal(createMsg)
	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsCreate,
		Payload: payload,
	}

	err := handler.HandleCreate(context.Background(), rawMsg)

	// New behavior: returns error for unsupported types
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "unsupported secret type")
}

func TestSecretHandler_HandleDelete_KubernetesSecret(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	// Create namespace and secret
	_, err := clientset.CoreV1().Namespaces().Create(context.Background(),
		&corev1.Namespace{ObjectMeta: metav1.ObjectMeta{Name: "test-namespace"}},
		metav1.CreateOptions{})
	require.NoError(t, err)

	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-secret",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: "Project",
			},
		},
		Type: corev1.SecretTypeOpaque,
	}
	_, err = clientset.CoreV1().Secrets("test-namespace").Create(context.Background(), secret, metav1.CreateOptions{})
	require.NoError(t, err)

	// The client-go fake does not implement DeleteCollection semantics; simulate it.
	clientset.Fake.PrependReactor("delete-collection", "secrets", func(action k8stesting.Action) (bool, runtime.Object, error) {
		// IMPORTANT: do not call back into clientset.CoreV1() here (can deadlock the fake client).
		// Instead, operate directly on the fake client's object tracker.
		ns := action.GetNamespace()
		gvr := schema.GroupVersionResource{Group: "", Version: "v1", Resource: "secrets"}
		gvk := schema.GroupVersionKind{Group: "", Version: "v1", Kind: "Secret"}

		obj, listErr := clientset.Tracker().List(gvr, gvk, ns)
		if listErr != nil {
			return true, nil, listErr
		}
		secretList, ok := obj.(*corev1.SecretList)
		if !ok || secretList == nil {
			return true, nil, nil
		}

		for _, s := range secretList.Items {
			_ = clientset.Tracker().Delete(gvr, ns, s.Name)
		}
		return true, nil, nil
	})

	deleteMsg := messaging.ProjectSecretsDeleteMessage{
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		ProjectName:     "test-namespace",
		SecretType:      messaging.SecretKindKubernetesSecret,
		SecretScope:     messaging.SecretScopeProject,
	}

	payload, _ := json.Marshal(deleteMsg)
	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsDelete,
		Payload: payload,
	}

	err = handler.HandleDelete(context.Background(), rawMsg)

	assert.NoError(t, err)

	// Verify secret was deleted
	_, err = clientset.CoreV1().Secrets("test-namespace").Get(context.Background(), "test-secret", metav1.GetOptions{})
	assert.Error(t, err) // Should not exist
}

func TestSecretHandler_HandleDelete_SecretNotFound(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	// Create namespace but no secret
	_, err := clientset.CoreV1().Namespaces().Create(context.Background(),
		&corev1.Namespace{ObjectMeta: metav1.ObjectMeta{Name: "test-namespace"}},
		metav1.CreateOptions{})
	require.NoError(t, err)

	deleteMsg := messaging.ProjectSecretsDeleteMessage{
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		ProjectName:     "test-namespace",
		SecretType:      messaging.SecretKindKubernetesSecret,
		SecretScope:     messaging.SecretScopeProject,
	}

	payload, _ := json.Marshal(deleteMsg)
	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsDelete,
		Payload: payload,
	}

	err = handler.HandleDelete(context.Background(), rawMsg)

	assert.NoError(t, err)

	// Should publish DELETED status
	require.Len(t, publisher.Published, 1)
	msg, ok := publisher.Published[0].(*messaging.ProjectSecretsUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.ProjectSecretStatusDeleted, msg.Status)
	assert.Contains(t, *msg.StatusReason, "No secrets found")
}

func TestSecretHandler_HandleDelete_UnsupportedSecretType(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	deleteMsg := messaging.ProjectSecretsDeleteMessage{
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		ProjectName:     "test-namespace",
		SecretType:      "UnsupportedType",
		SecretScope:     messaging.SecretScopeProject,
	}

	payload, _ := json.Marshal(deleteMsg)
	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsDelete,
		Payload: payload,
	}

	err := handler.HandleDelete(context.Background(), rawMsg)

	// New behavior: returns error for unsupported types
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "unsupported secret type")
}

func TestSecretHandler_HandleCreate_InvalidJSON(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsCreate,
		Payload: []byte("invalid-json"),
	}

	err := handler.HandleCreate(context.Background(), rawMsg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse")
}

func TestSecretHandler_HandleDelete_InvalidJSON(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	publisher := testutils.NewMockPublisher()

	handler := NewSecretHandler(clientset, dynamicClient, publisher, logger)

	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsDelete,
		Payload: []byte("invalid-json"),
	}

	err := handler.HandleDelete(context.Background(), rawMsg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse")
}
