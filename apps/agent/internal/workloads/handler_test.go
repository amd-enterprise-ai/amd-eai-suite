// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"

	"github.com/go-logr/logr"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/runtime/schema"

	"github.com/silogen/agent/internal/messaging"
	common "github.com/silogen/agent/internal/workloads/common"
)

type mockPublisher struct {
	published []any
}

func (m *mockPublisher) Publish(ctx context.Context, message interface{}) error {
	m.published = append(m.published, message)
	return nil
}
func (m *mockPublisher) Connect(ctx context.Context) error { return nil }
func (m *mockPublisher) Close() error                      { return nil }

type alwaysFailMapper struct{}

func (m *alwaysFailMapper) KindFor(resource schema.GroupVersionResource) (schema.GroupVersionKind, error) {
	return schema.GroupVersionKind{}, fmt.Errorf("no kind match for %s", resource.String())
}
func (m *alwaysFailMapper) KindsFor(resource schema.GroupVersionResource) ([]schema.GroupVersionKind, error) {
	return nil, fmt.Errorf("no kinds match for %s", resource.String())
}
func (m *alwaysFailMapper) ResourceFor(input schema.GroupVersionResource) (schema.GroupVersionResource, error) {
	return schema.GroupVersionResource{}, fmt.Errorf("no resource match for %s", input.String())
}
func (m *alwaysFailMapper) ResourcesFor(input schema.GroupVersionResource) ([]schema.GroupVersionResource, error) {
	return nil, fmt.Errorf("no resources match for %s", input.String())
}
func (m *alwaysFailMapper) RESTMapping(gk schema.GroupKind, versions ...string) (*apimeta.RESTMapping, error) {
	return nil, fmt.Errorf("no rest mapping for %s", gk.String())
}
func (m *alwaysFailMapper) RESTMappings(gk schema.GroupKind, versions ...string) ([]*apimeta.RESTMapping, error) {
	return nil, fmt.Errorf("no rest mappings for %s", gk.String())
}
func (m *alwaysFailMapper) ResourceSingularizer(resource string) (string, error) {
	return "", fmt.Errorf("no singularizer for %s", resource)
}

func newEmptyMapper() apimeta.RESTMapper {
	return &alwaysFailMapper{}
}

func TestDecodeYAMLDocuments_MultiDoc(t *testing.T) {
	manifest := `
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm1
  namespace: ns1
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep1
  namespace: ns1
`

	objs, err := common.DecodeYAMLDocuments(manifest)
	require.NoError(t, err)
	require.Len(t, objs, 2)

	assert.Equal(t, "v1", objs[0].GetAPIVersion())
	assert.Equal(t, "ConfigMap", objs[0].GetKind())
	assert.Equal(t, "cm1", objs[0].GetName())
	assert.Equal(t, "ns1", objs[0].GetNamespace())

	assert.Equal(t, "apps/v1", objs[1].GetAPIVersion())
	assert.Equal(t, "Deployment", objs[1].GetKind())
	assert.Equal(t, "dep1", objs[1].GetName())
	assert.Equal(t, "ns1", objs[1].GetNamespace())
}

func TestWorkloadHandler_HandleDelete_NoResourcesPublishesDeletedStatus(t *testing.T) {
	pub := &mockPublisher{}
	h := &Handler{
		publisher: pub,
		logger:    logr.Discard(),
		mapper:    newEmptyMapper(),
		// dynamicClient is intentionally nil; mapping fails so we never call it.
	}

	payload := []byte(`{"message_type":"delete_workload","workload_id":"11111111-1111-1111-1111-111111111111"}`)
	msg := &messaging.RawMessage{Type: messaging.MessageTypeDeleteWorkload, Payload: payload}

	require.NoError(t, h.HandleDelete(context.Background(), msg))

	require.Len(t, pub.published, 1)
	statusMsg, ok := pub.published[0].(*messaging.WorkloadStatusMessage)
	require.True(t, ok, "expected WorkloadStatusMessage, got %T", pub.published[0])

	assert.Equal(t, messaging.MessageTypeWorkloadStatusUpdate, statusMsg.MessageType)
	assert.Equal(t, messaging.WorkloadStatusDeleted, statusMsg.Status)
	assert.Equal(t, "11111111-1111-1111-1111-111111111111", statusMsg.WorkloadID)
	require.NotNil(t, statusMsg.StatusReason)
	assert.Contains(t, *statusMsg.StatusReason, "No resources found for deletion")
}

func TestWorkloadHandler_HandleDelete_InvalidWorkloadID(t *testing.T) {
	pub := &mockPublisher{}
	h := &Handler{
		publisher: pub,
		logger:    logr.Discard(),
		mapper:    newEmptyMapper(),
	}

	payload := []byte(`{"message_type":"delete_workload","workload_id":"not-a-uuid"}`)
	msg := &messaging.RawMessage{Type: messaging.MessageTypeDeleteWorkload, Payload: payload}

	err := h.HandleDelete(context.Background(), msg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "invalid workload_id")
	assert.Empty(t, pub.published)
}

func TestWorkloadHandler_HandleDelete_InvalidJSON(t *testing.T) {
	pub := &mockPublisher{}
	h := &Handler{
		publisher: pub,
		logger:    logr.Discard(),
		mapper:    newEmptyMapper(),
	}

	payload := []byte(`{"message_type":"delete_workload",`) // invalid JSON
	msg := &messaging.RawMessage{Type: messaging.MessageTypeDeleteWorkload, Payload: payload}

	err := h.HandleDelete(context.Background(), msg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse DeleteWorkloadMessage")
	assert.Empty(t, pub.published)
}

func TestWorkloadHandler_HandleCreate_InvalidWorkloadID(t *testing.T) {
	pub := &mockPublisher{}
	h := &Handler{
		publisher: pub,
		logger:    logr.Discard(),
		mapper:    newEmptyMapper(),
	}

	payload := []byte(`{"message_type":"workload","manifest":"apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cm1\n  namespace: ns1\n","user_token":"x","workload_id":"not-a-uuid"}`)
	msg := &messaging.RawMessage{Type: messaging.MessageTypeWorkload, Payload: payload}

	err := h.HandleCreate(context.Background(), msg)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "invalid workload_id")
	assert.Empty(t, pub.published)
}

func TestWorkloadHandler_HandleCreate_MappingErrorPublishesCreateFailedForComponent(t *testing.T) {
	pub := &mockPublisher{}
	h := &Handler{
		publisher: pub,
		logger:    logr.Discard(),
		mapper:    newEmptyMapper(), // forces applyObject to fail before touching dynamic client
	}

	manifest := `
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm1
  labels:
    airm.silogen.ai/component-id: "22222222-2222-2222-2222-222222222222"
    airm.silogen.ai/workload-id: "11111111-1111-1111-1111-111111111111"
    airm.silogen.ai/project-id: "33333333-3333-3333-3333-333333333333"
`

	createMsg := messaging.WorkloadMessage{
		MessageType: messaging.MessageTypeWorkload,
		Manifest:    manifest,
		UserToken:   "x",
		WorkloadID:  "11111111-1111-1111-1111-111111111111",
	}
	payload, err := json.Marshal(createMsg)
	require.NoError(t, err)

	msg := &messaging.RawMessage{Type: messaging.MessageTypeWorkload, Payload: payload}
	require.NoError(t, h.HandleCreate(context.Background(), msg))

	require.Len(t, pub.published, 1)
	compMsg, ok := pub.published[0].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok, "expected WorkloadComponentStatusMessage, got %T", pub.published[0])

	assert.Equal(t, messaging.MessageTypeWorkloadComponentStatusUpdate, compMsg.MessageType)
	assert.Equal(t, "22222222-2222-2222-2222-222222222222", compMsg.ID)
	assert.Equal(t, "cm1", compMsg.Name)
	assert.Equal(t, messaging.WorkloadComponentKindConfigMap, compMsg.Kind)
	assert.Equal(t, "v1", compMsg.APIVersion)
	assert.Equal(t, "11111111-1111-1111-1111-111111111111", compMsg.WorkloadID)
	assert.Equal(t, "CreateFailed", compMsg.Status)
	require.NotNil(t, compMsg.StatusReason)
}

func TestWorkloadHandler_HandleUpdate_NotSupported(t *testing.T) {
	h := &Handler{
		logger: logr.Discard(),
	}

	err := h.HandleUpdate(context.Background(), &messaging.RawMessage{Type: messaging.MessageTypeWorkload})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "update operation not supported")
}
