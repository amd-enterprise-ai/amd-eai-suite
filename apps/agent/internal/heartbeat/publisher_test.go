// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package heartbeat

import (
	"context"
	"errors"
	"testing"

	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/messaging"
)

func TestPublisher_Publish_Success(t *testing.T) {
	fakeClientset := fake.NewSimpleClientset()
	k8sClient := &kubernetes.Client{
		Clientset: fakeClientset,
	}
	mockPublisher := testutils.NewMockPublisher()
	logger := zap.New()
	ctx := context.Background()

	publisher := NewPublisher(mockPublisher, k8sClient, "test-cluster", logger)
	err := publisher.Publish(ctx)

	assert.NoError(t, err)
	require.Len(t, mockPublisher.Published, 1)

	msg, ok := mockPublisher.Published[0].(*messaging.HeartbeatMessage)
	require.True(t, ok, "message should be of type *HeartbeatMessage")

	assert.Equal(t, messaging.MessageTypeHeartbeat, msg.MessageType)
	assert.Equal(t, "test-cluster", msg.ClusterName)
	assert.NotZero(t, msg.LastHeartbeatAt)
}

func TestPublisher_Publish_PublishFailure(t *testing.T) {
	logger := zap.New()

	// Create a real kubernetes client with fake clientset (will succeed health check)
	fakeClientset := fake.NewSimpleClientset()
	k8sClient := &kubernetes.Client{
		Clientset: fakeClientset,
	}

	mockMsgPublisher := testutils.NewMockFailingPublisher(errors.New("failed to publish heartbeat"))

	// Publisher fails
	ctx := context.Background()
	publisher := NewPublisher(mockMsgPublisher, k8sClient, "test-cluster", logger)
	err := publisher.Publish(ctx)

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to publish heartbeat")
}
