// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

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

func TestPublisher_Publish_ProjectSecretsUpdateMessage_WithoutBroker(t *testing.T) {
	publisher := testPublisher(t)
	reason := "Secret Synced."
	scope := SecretScopeProject
	msg := &ProjectSecretsUpdateMessage{
		MessageType:     messaging.MessageTypeProjectSecretsUpdate,
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		SecretScope:     &scope,
		Status:          ProjectSecretStatusSynced,
		StatusReason:    &reason,
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

func TestPublisher_Publish_ProjectSecretsUpdateMessage_MinimalFields_WithoutBroker(t *testing.T) {
	publisher := testPublisher(t)
	msg := &ProjectSecretsUpdateMessage{
		MessageType:     messaging.MessageTypeProjectSecretsUpdate,
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		Status:          ProjectSecretStatusPending,
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
