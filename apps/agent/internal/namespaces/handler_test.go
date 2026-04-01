// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"testing"

	"github.com/go-logr/logr"
	"k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestLogger() logr.Logger {
	return zap.New()
}

func TestNewNamespaceHandler(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()

	handler := NewNamespaceHandler(clientset, publisher, logger)

	require.NotNil(t, handler)
	assert.Equal(t, clientset, handler.clientset)
	assert.Equal(t, publisher, handler.publisher)
	assert.Equal(t, logger, handler.logger)
}

func TestNamespaceHandler_HandleCreate_Success(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewNamespaceHandler(clientset, publisher, logger)

	// Message with namespace_manifest (K8s Namespace-shaped JSON)
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceCreate,
		Payload: []byte(`{"message_type":"project_namespace_create","namespace_manifest":{"apiVersion":"v1","kind":"Namespace","metadata":{"name":"test-ns","labels":{"airm.silogen.ai/project-id":"test-project"}}}}`),
	}

	err := handler.HandleCreate(context.Background(), msg)

	assert.NoError(t, err)
	// Informer will publish status, but handler should succeed
}

func TestNamespaceHandler_HandleDelete_NamespaceNotFound(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewNamespaceHandler(clientset, publisher, logger)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceDelete,
		Payload: []byte(`{"message_type": "project_namespace_delete", "name": "test-ns", "project_id": "test-project"}`),
	}

	err := handler.HandleDelete(context.Background(), msg)

	assert.NoError(t, err)
	// Should publish DELETED status when namespace not found
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*messaging.ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.NamespaceStatusDeleted, statusMsg.Status)
}

func TestNamespaceHandler_HandleCreate_InvalidPayload(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewNamespaceHandler(clientset, publisher, logger)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceCreate,
		Payload: []byte(`invalid json`),
	}

	err := handler.HandleCreate(context.Background(), msg)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse create message")
}

func TestNamespaceHandler_HandleCreate_AlreadyExists(t *testing.T) {
	logger := newTestLogger()
	publisher := testutils.NewMockPublisher()

	// Pre-create a namespace in the fake clientset
	existingNs := BuildNamespaceManifest("test-ns", "test-project")
	clientset := fake.NewSimpleClientset(existingNs)

	handler := NewNamespaceHandler(clientset, publisher, logger)

	// Message with namespace_manifest (same namespace name so create will conflict)
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceCreate,
		Payload: []byte(`{"message_type":"project_namespace_create","namespace_manifest":{"apiVersion":"v1","kind":"Namespace","metadata":{"name":"test-ns","labels":{"airm.silogen.ai/project-id":"test-project"}}}}`),
	}

	err := handler.HandleCreate(context.Background(), msg)

	// Should return an error when namespace already exists
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to create namespace")

	// Should publish a failure status message
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*messaging.ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.NamespaceStatusFailed, statusMsg.Status)
	assert.Equal(t, "test-project", statusMsg.ProjectID)
	require.NotNil(t, statusMsg.StatusReason)
	assert.Contains(t, *statusMsg.StatusReason, "Failed to create namespace")
}
