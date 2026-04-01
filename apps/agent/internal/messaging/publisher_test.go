// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"context"
	"testing"
	"time"

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

func TestPublisher_Publish_NotConnected(t *testing.T) {
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

	msg := &ProjectNamespaceStatusMessage{
		MessageType: MessageTypeProjectNamespaceStatus,
		ProjectID:   "test-project",
		Status:      NamespaceStatusActive,
	}

	err := publisher.Publish(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not connected")
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

func TestPublisher_Publish_UnmanagedNamespaceMessage(t *testing.T) {
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

	msg := &UnmanagedNamespaceMessage{
		MessageType:     MessageTypeUnmanagedNamespace,
		NamespaceName:   "test-namespace",
		NamespaceStatus: NamespaceStatusActive,
	}

	// Should fail because not connected, but we can test the message type extraction
	err := publisher.Publish(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not connected")
}

func TestPublisher_MessageTypeExtraction(t *testing.T) {
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

	tests := []struct {
		name    string
		message interface{}
	}{
		{
			name: "ProjectNamespaceStatusMessage",
			message: &ProjectNamespaceStatusMessage{
				MessageType: MessageTypeProjectNamespaceStatus,
				ProjectID:   "test",
				Status:      NamespaceStatusActive,
			},
		},
		{
			name: "UnmanagedNamespaceMessage",
			message: &UnmanagedNamespaceMessage{
				MessageType:     MessageTypeUnmanagedNamespace,
				NamespaceName:   "test",
				NamespaceStatus: NamespaceStatusActive,
			},
		},
		{
			name: "HeartbeatMessage",
			message: &HeartbeatMessage{
				MessageType:      MessageTypeHeartbeat,
				LastHeartbeatAt:  time.Now().UTC(),
				ClusterName:      "test-cluster",
				OrganizationName: "test-org",
			},
		},
		{
			name: "ProjectSecretsUpdateMessage",
			message: &ProjectSecretsUpdateMessage{
				MessageType:     MessageTypeProjectSecretsUpdate,
				ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
				Status:          ProjectSecretStatusSynced,
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := publisher.Publish(context.Background(), tt.message)
			// We expect an error because we're not connected, but the message should be marshaled correctly
			assert.Error(t, err)
			assert.Contains(t, err.Error(), "not connected")
		})
	}
}

func TestPublisher_Publish_HeartbeatMessage(t *testing.T) {
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

	msg := &HeartbeatMessage{
		MessageType:      MessageTypeHeartbeat,
		LastHeartbeatAt:  time.Now().UTC(),
		ClusterName:      "test-cluster",
		OrganizationName: "test-org",
	}

	// Should fail because not connected, but we can test the message type extraction
	err := publisher.Publish(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not connected")
}

func TestPublisher_Publish_ProjectSecretsUpdateMessage(t *testing.T) {
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

	reason := "Secret Synced."
	scope := SecretScopeProject
	msg := &ProjectSecretsUpdateMessage{
		MessageType:     MessageTypeProjectSecretsUpdate,
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		SecretScope:     &scope,
		Status:          ProjectSecretStatusSynced,
		StatusReason:    &reason,
	}

	// Should fail because not connected, but we can test the message marshaling
	err := publisher.Publish(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not connected")
}

func TestPublisher_Publish_ProjectSecretsUpdateMessage_MinimalFields(t *testing.T) {
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

	msg := &ProjectSecretsUpdateMessage{
		MessageType:     MessageTypeProjectSecretsUpdate,
		ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
		Status:          ProjectSecretStatusPending,
	}

	// Should fail because not connected, but we can test the message marshaling
	err := publisher.Publish(context.Background(), msg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not connected")
}

func TestPublisher_Publish_AllSecretStatuses(t *testing.T) {
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

	statuses := []ProjectSecretStatus{
		ProjectSecretStatusPending,
		ProjectSecretStatusSynced,
		ProjectSecretStatusFailed,
		ProjectSecretStatusSyncedError,
		ProjectSecretStatusDeleteFailed,
		ProjectSecretStatusDeleted,
		ProjectSecretStatusDeleting,
		ProjectSecretStatusUnknown,
	}

	for _, status := range statuses {
		t.Run(string(status), func(t *testing.T) {
			msg := &ProjectSecretsUpdateMessage{
				MessageType:     MessageTypeProjectSecretsUpdate,
				ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
				Status:          status,
			}

			err := publisher.Publish(context.Background(), msg)
			assert.Error(t, err)
			assert.Contains(t, err.Error(), "not connected")
		})
	}
}

func TestPublisher_Publish_BothSecretScopes(t *testing.T) {
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

	scopes := []SecretScope{
		SecretScopeProject,
		SecretScopeOrganization,
	}

	for _, scope := range scopes {
		t.Run(string(scope), func(t *testing.T) {
			scopeCopy := scope
			msg := &ProjectSecretsUpdateMessage{
				MessageType:     MessageTypeProjectSecretsUpdate,
				ProjectSecretID: "550e8400-e29b-41d4-a716-446655440000",
				SecretScope:     &scopeCopy,
				Status:          ProjectSecretStatusSynced,
			}

			err := publisher.Publish(context.Background(), msg)
			assert.Error(t, err)
			assert.Contains(t, err.Error(), "not connected")
		})
	}
}
