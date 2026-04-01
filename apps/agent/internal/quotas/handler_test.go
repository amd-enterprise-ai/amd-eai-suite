// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/dynamic/fake"
	fakeclientset "k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/messaging"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
)

func setupQuotaHandler() (*QuotaHandler, *testutils.MockPublisher) {
	scheme := runtime.NewScheme()
	_ = kaiwov1alpha1.AddToScheme(scheme)

	// Create existing KaiwoQueueConfig
	existingConfig := &kaiwov1alpha1.KaiwoQueueConfig{
		TypeMeta: metav1.TypeMeta{
			APIVersion: kaiwov1alpha1.GroupVersion.String(),
			Kind:       "KaiwoQueueConfig",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:            KaiwoQueueConfigDefaultName,
			ResourceVersion: "1",
		},
	}

	unstructuredMap, _ := runtime.DefaultUnstructuredConverter.ToUnstructured(existingConfig)
	unstructuredObj := &unstructured.Unstructured{Object: unstructuredMap}

	dynamicClient := fake.NewSimpleDynamicClient(scheme, unstructuredObj)
	clientset := fakeclientset.NewSimpleClientset()
	mockPub := testutils.NewMockPublisher()
	logger := zap.New()

	handler := NewQuotaHandler(clientset, dynamicClient, mockPub, logger)

	return handler, mockPub
}

func TestQuotaHandler_HandleUpdate_Success(t *testing.T) {
	handler, mockPub := setupQuotaHandler()

	gpuVendor := messaging.GPUVendorAMD
	allocationMsg := messaging.ClusterQuotasAllocationMessage{
		MessageType: messaging.MessageTypeClusterQuotasAllocationMessage,
		GPUVendor:   &gpuVendor,
		QuotaAllocations: []messaging.ClusterQuotaAllocation{
			{
				QuotaName:             "test-quota",
				Namespaces:            []string{"ns1", "ns2"},
				CPUMilliCores:         4000,
				MemoryBytes:           8589934592,
				EphemeralStorageBytes: 10737418240,
				GPUCount:              2,
			},
		},
		PriorityClasses: []messaging.PriorityClass{
			{Name: "high", Priority: 100},
			{Name: "low", Priority: 50},
		},
	}

	payload, err := json.Marshal(allocationMsg)
	require.NoError(t, err)

	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeClusterQuotasAllocationMessage,
		Payload: payload,
	}

	err = handler.HandleUpdate(context.Background(), rawMsg)
	assert.NoError(t, err)

	// Should not publish any failure messages
	assert.Empty(t, mockPub.Published)
}

func TestQuotaHandler_HandleUpdate_InvalidJSON(t *testing.T) {
	handler, mockPub := setupQuotaHandler()

	rawMsg := &messaging.RawMessage{
		Type:    messaging.MessageTypeClusterQuotasAllocationMessage,
		Payload: []byte("invalid json"),
	}

	err := handler.HandleUpdate(context.Background(), rawMsg)
	assert.Error(t, err)

	// Should publish failure message
	require.Len(t, mockPub.Published, 1)
	failureMsg, ok := mockPub.Published[0].(*messaging.ClusterQuotaFailureMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeClusterQuotasFailureMessage, failureMsg.MessageType)
	assert.Contains(t, failureMsg.Reason, "Failed to parse message")
}

func TestQuotaHandler_HandleCreate_NotSupported(t *testing.T) {
	handler, _ := setupQuotaHandler()

	err := handler.HandleCreate(context.Background(), &messaging.RawMessage{})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not supported")
}

func TestQuotaHandler_HandleDelete_NotSupported(t *testing.T) {
	handler, _ := setupQuotaHandler()

	err := handler.HandleDelete(context.Background(), &messaging.RawMessage{})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not supported")
}

func TestPublishFailure(t *testing.T) {
	_, mockPub := setupQuotaHandler()
	handler := &QuotaHandler{
		publisher: mockPub,
		logger:    zap.New(),
	}

	reason := "Test failure reason"
	handler.publishFailure(context.Background(), reason)

	require.Len(t, mockPub.Published, 1)
	failureMsg, ok := mockPub.Published[0].(*messaging.ClusterQuotaFailureMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeClusterQuotasFailureMessage, failureMsg.MessageType)
	assert.Equal(t, reason, failureMsg.Reason)
	assert.WithinDuration(t, time.Now(), failureMsg.UpdatedAt, 2*time.Second)
}
