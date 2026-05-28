// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"context"
	"strings"
	"testing"

	"github.com/silogen/agent/internal/config"
	"github.com/stretchr/testify/assert"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func TestNewPublisher(t *testing.T) {
	logger := zap.New()
	cfg := config.RabbitMQConfig{
		Host:     "localhost",
		Port:     5672,
		VHost:    "vh_test",
		Queue:    "test_queue",
		User:     "user",
		Password: "pass",
	}
	publisher := NewPublisher(cfg, logger)

	assert.NotNil(t, publisher)
	assert.Equal(t, "test_queue", publisher.queueName)
	assert.NotEmpty(t, publisher.amqpURL)
}

func TestPublisher_Close_NoConnection(t *testing.T) {
	logger := zap.New()
	cfg := config.RabbitMQConfig{
		Host:     "localhost",
		Port:     5672,
		VHost:    "vh_test",
		Queue:    "test_queue",
		User:     "user",
		Password: "pass",
	}
	publisher := NewPublisher(cfg, logger)

	err := publisher.Close()
	assert.NoError(t, err)
}

type publishProbe struct {
	MessageType MessageType `json:"message_type"`
}

func TestPublisher_Publish_WithoutBroker(t *testing.T) {
	logger := zap.New()
	cfg := config.RabbitMQConfig{
		Host:     "localhost",
		Port:     5672,
		VHost:    "vh_test",
		Queue:    "test_queue",
		User:     "user",
		Password: "pass",
	}
	publisher := NewPublisher(cfg, logger)

	err := publisher.Publish(context.Background(), publishProbe{MessageType: MessageTypeHeartbeat})
	assert.Error(t, err)
	errStr := err.Error()
	assert.True(t,
		strings.Contains(errStr, "connect failed") ||
			strings.Contains(errStr, "queue declare failed") ||
			strings.Contains(errStr, "channel failed"),
		"unexpected error: %s", errStr)
}
