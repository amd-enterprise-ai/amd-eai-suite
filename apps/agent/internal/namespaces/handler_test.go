// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"

	"github.com/go-logr/logr"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/kubernetes/fake"
	clienttesting "k8s.io/client-go/testing"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func buildUpdatePayload(t *testing.T, ns *corev1.Namespace) []byte {
	t.Helper()
	manifestBytes, err := json.Marshal(ns)
	require.NoError(t, err)
	msg := map[string]json.RawMessage{
		"message_type":       json.RawMessage(`"project_namespace_update"`),
		"namespace_manifest": manifestBytes,
	}
	payload, err := json.Marshal(msg)
	require.NoError(t, err)
	return payload
}

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
	statusMsg, ok := publisher.Published[0].(*ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, NamespaceStatusDeleted, statusMsg.Status)
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
	statusMsg, ok := publisher.Published[0].(*ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, NamespaceStatusFailed, statusMsg.Status)
	assert.Equal(t, "test-project", statusMsg.ProjectID)
	require.NotNil(t, statusMsg.StatusReason)
	assert.Contains(t, *statusMsg.StatusReason, "Failed to create namespace")
}

func TestNamespaceHandler_HandleUpdate_MergesAnnotations(t *testing.T) {
	logger := newTestLogger()
	existingNs := BuildNamespaceManifest("test-ns", "test-project")
	existingNs.Annotations = map[string]string{
		"other.app/key":                "keep",
		KaiwoGpuPreemptionEnabledKey:   "false",
		KaiwoGpuPreemptionThresholdKey: "old",
	}
	clientset := fake.NewSimpleClientset(existingNs)
	publisher := testutils.NewMockPublisher()
	handler := NewNamespaceHandler(clientset, publisher, logger)

	// Manifest carries enabled=true; threshold absent → should be stripped
	incomingNs := BuildNamespaceManifest("test-ns", "test-project")
	incomingNs.Annotations = map[string]string{
		KaiwoGpuPreemptionEnabledKey: "true",
	}
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: buildUpdatePayload(t, incomingNs),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	require.NoError(t, err)

	updated, err := clientset.CoreV1().Namespaces().Get(context.Background(), "test-ns", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, "keep", updated.Annotations["other.app/key"])
	assert.Equal(t, "true", updated.Annotations[KaiwoGpuPreemptionEnabledKey])
	_, hasThresh := updated.Annotations[KaiwoGpuPreemptionThresholdKey]
	assert.False(t, hasThresh)
}

func TestNamespaceHandler_HandleUpdate_ProjectIDMismatch(t *testing.T) {
	logger := newTestLogger()
	existingNs := BuildNamespaceManifest("test-ns", "test-project")
	clientset := fake.NewSimpleClientset(existingNs)
	publisher := testutils.NewMockPublisher()
	handler := NewNamespaceHandler(clientset, publisher, logger)

	// Manifest belongs to a different project
	incomingNs := BuildNamespaceManifest("test-ns", "wrong-project")
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: buildUpdatePayload(t, incomingNs),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	require.NoError(t, err)

	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, NamespaceStatusFailed, statusMsg.Status)
	require.NotNil(t, statusMsg.StatusReason)
	assert.Contains(t, *statusMsg.StatusReason, "project_id label mismatch")
}

func TestNamespaceHandler_HandleUpdate_ConflictReturnsError(t *testing.T) {
	logger := newTestLogger()
	existingNs := BuildNamespaceManifest("test-ns", "test-project")
	existingNs.ResourceVersion = "1"
	clientset := fake.NewSimpleClientset(existingNs)
	clientset.PrependReactor("update", "namespaces", func(action clienttesting.Action) (handled bool, ret runtime.Object, err error) {
		return true, nil, apierrors.NewConflict(schema.GroupResource{Resource: "namespaces"}, "test-ns", fmt.Errorf("rv"))
	})

	publisher := testutils.NewMockPublisher()
	handler := NewNamespaceHandler(clientset, publisher, logger)

	incomingNs := BuildNamespaceManifest("test-ns", "test-project")
	incomingNs.Annotations = map[string]string{KaiwoGpuPreemptionEnabledKey: "true"}
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: buildUpdatePayload(t, incomingNs),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to update namespace annotations")

	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, NamespaceStatusFailed, statusMsg.Status)
}

func TestNamespaceHandler_HandleUpdate_InvalidPayload(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	handler := NewNamespaceHandler(clientset, testutils.NewMockPublisher(), logger)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: []byte(`not json`),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse namespace update message")
}

func TestNamespaceHandler_HandleUpdate_MissingManifest(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	handler := NewNamespaceHandler(clientset, testutils.NewMockPublisher(), logger)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: []byte(`{"message_type":"project_namespace_update"}`),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "missing namespace_manifest")
}

func TestNamespaceHandler_HandleUpdate_ManifestMissingProjectID(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	handler := NewNamespaceHandler(clientset, testutils.NewMockPublisher(), logger)

	// Manifest has a name but no project-id label
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: []byte(`{"message_type":"project_namespace_update","namespace_manifest":{"apiVersion":"v1","kind":"Namespace","metadata":{"name":"test-ns"}}}`),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "missing")
	assert.Contains(t, err.Error(), agent.ProjectIDLabel)
}

func TestNamespaceHandler_HandleUpdate_ManifestMissingName(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	handler := NewNamespaceHandler(clientset, testutils.NewMockPublisher(), logger)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: []byte(`{"message_type":"project_namespace_update","namespace_manifest":{"apiVersion":"v1","kind":"Namespace","metadata":{}}}`),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "missing metadata.name")
}

func TestNamespaceHandler_HandleUpdate_NamespaceNotFound(t *testing.T) {
	logger := newTestLogger()
	clientset := fake.NewSimpleClientset()
	publisher := testutils.NewMockPublisher()
	handler := NewNamespaceHandler(clientset, publisher, logger)

	incomingNs := BuildNamespaceManifest("missing", "test-project")
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: buildUpdatePayload(t, incomingNs),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	require.NoError(t, err)
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, NamespaceStatusDeleted, statusMsg.Status)
}

func TestNamespaceHandler_HandleUpdate_Idempotent(t *testing.T) {
	logger := newTestLogger()
	existingNs := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-ns",
			Labels: map[string]string{
				agent.ProjectIDLabel: "test-project",
				KueueManagedLabel:    "true",
			},
			Annotations: map[string]string{
				KaiwoGpuPreemptionEnabledKey: "true",
			},
		},
	}
	clientset := fake.NewSimpleClientset(existingNs)
	handler := NewNamespaceHandler(clientset, testutils.NewMockPublisher(), logger)

	incomingNs := BuildNamespaceManifest("test-ns", "test-project")
	incomingNs.Annotations = map[string]string{KaiwoGpuPreemptionEnabledKey: "true"}
	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceUpdate,
		Payload: buildUpdatePayload(t, incomingNs),
	}

	err := handler.HandleUpdate(context.Background(), msg)
	require.NoError(t, err)
	err = handler.HandleUpdate(context.Background(), msg)
	require.NoError(t, err)
}
