// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/go-logr/logr"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const testConfigMapManifest = `
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-storage-info-config-map
  namespace: test-project
  labels:
    airm.silogen.ai/project-storage-id: "storage-123"
data:
  BUCKET_URL: "s3://my-bucket"
  ACCESS_KEY_NAME: "access-key"
  SECRET_KEY_NAME: "secret-key"
  SECRET_NAME: "my-secret"
`

func newTestLogger() logr.Logger {
	return zap.New()
}

func TestNewConfigMapHandler(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()

	handler := NewConfigMapHandler(clientset, publisher, logger)

	require.NotNil(t, handler)
	assert.Equal(t, clientset, handler.clientset)
	assert.Equal(t, publisher, handler.publisher)
	assert.Equal(t, logger, handler.logger)
}

func TestConfigMapHandler_HandleCreate_Success(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewConfigMapHandler(clientset, publisher, logger)

	// Manifest with namespace and labels already set by the API.
	createMsg := messaging.ProjectS3StorageCreateMessage{
		MessageType:      messaging.MessageTypeProjectS3StorageCreate,
		ProjectStorageID: "storage-123",
		ProjectName:      "test-project",
		Manifest:         testConfigMapManifest,
	}
	payload, err := json.Marshal(createMsg)
	require.NoError(t, err)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectS3StorageCreate,
		Payload: payload,
	}

	err = handler.HandleCreate(context.Background(), msg)

	assert.NoError(t, err)

	// Verify ConfigMap was created with correct metadata
	cm, err := clientset.CoreV1().ConfigMaps("test-project").Get(context.Background(), "my-storage-info-config-map", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, "my-storage-info-config-map", cm.Name)
	assert.Equal(t, "test-project", cm.Namespace)
	assert.Equal(t, "storage-123", cm.Labels[ProjectStorageIDLabel])
	assert.Equal(t, "s3://my-bucket", cm.Data["BUCKET_URL"])
	assert.Equal(t, "access-key", cm.Data["ACCESS_KEY_NAME"])
	assert.Equal(t, "secret-key", cm.Data["SECRET_KEY_NAME"])
	assert.Equal(t, "my-secret", cm.Data["SECRET_NAME"])
}

func TestConfigMapHandler_HandleCreate_AlreadyExists(t *testing.T) {
	logger := newTestLogger()
	publisher := testutils.NewMockPublisher()

	// Pre-create the ConfigMap
	existingCM := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "my-storage-info-config-map",
			Namespace: "test-project",
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}
	clientset := fake.NewSimpleClientset(existingCM)

	handler := NewConfigMapHandler(clientset, publisher, logger)

	manifest := `
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-storage-info-config-map
data:
  BUCKET_URL: "s3://my-bucket"
`

	createMsg := messaging.ProjectS3StorageCreateMessage{
		MessageType:      messaging.MessageTypeProjectS3StorageCreate,
		ProjectStorageID: "storage-123",
		ProjectName:      "test-project",
		Manifest:         manifest,
	}
	payload, err := json.Marshal(createMsg)
	require.NoError(t, err)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectS3StorageCreate,
		Payload: payload,
	}

	err = handler.HandleCreate(context.Background(), msg)

	// Should succeed (idempotent)
	assert.NoError(t, err)
	// Should NOT publish failure status
	assert.Len(t, publisher.Published, 0)
}

func TestConfigMapHandler_HandleCreate_InvalidPayload(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewConfigMapHandler(clientset, publisher, logger)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectS3StorageCreate,
		Payload: []byte(`invalid json`),
	}

	err := handler.HandleCreate(context.Background(), msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse message")
}

func TestConfigMapHandler_HandleCreate_MissingManifest(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewConfigMapHandler(clientset, publisher, logger)

	createMsg := messaging.ProjectS3StorageCreateMessage{
		MessageType:      messaging.MessageTypeProjectS3StorageCreate,
		ProjectStorageID: "storage-123",
		ProjectName:      "test-project",
		Manifest:         "",
	}
	payload, _ := json.Marshal(createMsg)
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectS3StorageCreate,
		Payload: payload,
	}

	err := handler.HandleCreate(context.Background(), msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "manifest is required")
}

func TestConfigMapHandler_HandleDelete_Success(t *testing.T) {
	logger := newTestLogger()
	publisher := testutils.NewMockPublisher()

	// Pre-create the ConfigMap
	existingCM := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "my-storage-info-config-map",
			Namespace: "test-project",
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}
	clientset := fake.NewSimpleClientset(existingCM)

	handler := NewConfigMapHandler(clientset, publisher, logger)

	msg := &messaging.RawMessage{
		Type: messaging.MessageTypeProjectStorageDelete,
		Payload: []byte(`{
			"message_type": "project_storage_delete",
			"project_storage_id": "storage-123",
			"project_name": "test-project"
		}`),
	}

	err := handler.HandleDelete(context.Background(), msg)

	assert.NoError(t, err)
	// Controller will handle the actual deletion status publishing
}

func TestConfigMapHandler_HandleDelete_NotFound_PublishesDeletedStatus(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset() // No ConfigMaps exist
	publisher := testutils.NewMockPublisher()
	handler := NewConfigMapHandler(clientset, publisher, logger)

	msg := &messaging.RawMessage{
		Type: messaging.MessageTypeProjectStorageDelete,
		Payload: []byte(`{
			"message_type": "project_storage_delete",
			"project_storage_id": "storage-123",
			"project_name": "test-project"
		}`),
	}

	err := handler.HandleDelete(context.Background(), msg)

	assert.NoError(t, err)
	// Should publish Deleted status when ConfigMap doesn't exist
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*messaging.ProjectStorageUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.ConfigMapStatusDeleted, statusMsg.Status)
	assert.Equal(t, "storage-123", statusMsg.ProjectStorageID)
	require.NotNil(t, statusMsg.StatusReason)
	assert.Contains(t, *statusMsg.StatusReason, "already deleted")
}

func TestConfigMapHandler_HandleDelete_InvalidPayload(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewConfigMapHandler(clientset, publisher, logger)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectStorageDelete,
		Payload: []byte(`invalid json`),
	}

	err := handler.HandleDelete(context.Background(), msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse message")
}

func TestConfigMapHandler_HandleUpdate_NotSupported(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewConfigMapHandler(clientset, publisher, logger)

	err := handler.HandleUpdate(context.Background(), nil)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "update operation not supported")
}
