// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package heartbeat

import (
	"context"
	"fmt"
	"time"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/messaging"
)

// Publisher handles publishing heartbeat messages.
type Publisher struct {
	publisher   messaging.MessagePublisher
	k8sClient   *kubernetes.Client
	clusterName string
	logger      logr.Logger
}

// NewPublisher creates a new heartbeat publisher.
func NewPublisher(
	publisher messaging.MessagePublisher,
	k8sClient *kubernetes.Client,
	clusterName string,
	logger logr.Logger,
) *Publisher {
	return &Publisher{
		publisher:   publisher,
		k8sClient:   k8sClient,
		clusterName: clusterName,
		logger:      logger,
	}
}

// Publish sends a heartbeat message to the queue.
func (p *Publisher) Publish(ctx context.Context) error {
	// Create heartbeat message
	message := &messaging.HeartbeatMessage{
		MessageType:     messaging.MessageTypeHeartbeat,
		LastHeartbeatAt: time.Now().UTC(),
		ClusterName:     p.clusterName,
	}

	// Publish message
	if err := p.publisher.Publish(ctx, message); err != nil {
		p.logger.Error(err, "failed to publish heartbeat")
		return fmt.Errorf("failed to publish heartbeat: %w", err)
	}

	p.logger.Info("heartbeat sent successfully", "cluster", p.clusterName)
	return nil
}
