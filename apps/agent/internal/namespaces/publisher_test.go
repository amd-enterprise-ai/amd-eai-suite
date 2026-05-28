// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"strings"
	"testing"

	"github.com/silogen/agent/internal/config"
	"github.com/silogen/agent/internal/messaging"
	"github.com/stretchr/testify/assert"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func testPublisher(t *testing.T) *messaging.Publisher {
	t.Helper()
	logger := zap.New()
	cfg := config.RabbitMQConfig{
		Host:     "localhost",
		Port:     5672,
		VHost:    "vh_test",
		Queue:    "test_queue",
		User:     "user",
		Password: "pass",
	}
	return messaging.NewPublisher(cfg, logger)
}

func TestPublisher_Publish_ProjectNamespaceStatus_WithoutBroker(t *testing.T) {
	publisher := testPublisher(t)
	msg := &ProjectNamespaceStatusMessage{
		MessageType: messaging.MessageTypeProjectNamespaceStatus,
		ProjectID:   "test-project",
		Status:      NamespaceStatusActive,
	}

	err := publisher.Publish(context.Background(), msg)
	assert.Error(t, err)
	errStr := err.Error()
	assert.True(t,
		strings.Contains(errStr, "connect failed") ||
			strings.Contains(errStr, "queue declare failed") ||
			strings.Contains(errStr, "channel failed"),
		"unexpected error: %s", errStr)
}

func TestPublisher_Publish_UnmanagedNamespaceMessage_WithoutBroker(t *testing.T) {
	publisher := testPublisher(t)
	msg := &UnmanagedNamespaceMessage{
		MessageType:     messaging.MessageTypeUnmanagedNamespace,
		NamespaceName:   "test-namespace",
		NamespaceStatus: NamespaceStatusActive,
	}

	err := publisher.Publish(context.Background(), msg)
	assert.Error(t, err)
	errStr := err.Error()
	assert.True(t,
		strings.Contains(errStr, "connect failed") ||
			strings.Contains(errStr, "queue declare failed") ||
			strings.Contains(errStr, "channel failed"),
		"unexpected error: %s", errStr)
}
