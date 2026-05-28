// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"sync"
	"time"

	"github.com/go-logr/logr"
	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/silogen/agent/internal/config"
)

// MessagePublisher defines the interface for publishing messages.
type MessagePublisher interface {
	Publish(ctx context.Context, message interface{}) error
	Connect(ctx context.Context) error
	Close() error
}

// Publisher publishes messages to RabbitMQ.
type Publisher struct {
	amqpURL   string
	queueName string
	userID    string // User ID to set in message properties (cluster UUID)
	logger    logr.Logger
	// sessionMu: RLock around PublishWithContext on a healthy session (concurrent publishes).
	// Lock for connect and close.
	sessionMu sync.RWMutex
	conn      *amqp.Connection
	channel   *amqp.Channel
}

// NewPublisher creates a new publisher.
func NewPublisher(rabbitMqConfig config.RabbitMQConfig, logger logr.Logger) *Publisher {
	encodedVHost := url.PathEscape(rabbitMqConfig.VHost)
	amqpURL := fmt.Sprintf("amqp://%s:%s@%s:%d/%s", rabbitMqConfig.User, rabbitMqConfig.Password, rabbitMqConfig.Host, rabbitMqConfig.Port, encodedVHost)

	return &Publisher{
		amqpURL:   amqpURL,
		queueName: rabbitMqConfig.Queue,
		userID:    rabbitMqConfig.User, // Store user ID to set in message properties
		logger:    logger,
	}
}

// Connect establishes connection to RabbitMQ.
func (p *Publisher) Connect(ctx context.Context) error {
	p.sessionMu.Lock()
	defer p.sessionMu.Unlock()
	return p.connectLocked(ctx)
}

func (p *Publisher) connectLocked(ctx context.Context) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	p.closeTransportLocked()

	conn, err := amqp.DialConfig(p.amqpURL, amqp.Config{
		Heartbeat: 30 * time.Second,
		Locale:    "en_US",
		Dial:      amqp.DefaultDial(BrokerConnectionTimeout),
	})
	if err != nil {
		return fmt.Errorf("connect failed: %w", err)
	}
	p.conn = conn

	ch, err := conn.Channel()
	if err != nil {
		_ = conn.Close()
		p.conn = nil
		return fmt.Errorf("channel failed: %w", err)
	}
	p.channel = ch

	queueCfg := DefaultQueueConfig()
	_, err = ch.QueueDeclare(
		p.queueName,
		queueCfg.Durable,
		queueCfg.AutoDelete,
		queueCfg.Exclusive,
		queueCfg.NoWait,
		queueCfg.Args,
	)
	if err != nil {
		_ = ch.Close()
		_ = conn.Close()
		p.channel = nil
		p.conn = nil
		return fmt.Errorf("queue declare failed: %w", err)
	}

	p.logger.Info("publisher connected", "queue", p.queueName)
	return nil
}

func (p *Publisher) closeTransportLocked() {
	if p.channel != nil {
		_ = p.channel.Close()
		p.channel = nil
	}
	if p.conn != nil {
		_ = p.conn.Close()
		p.conn = nil
	}
}

func (p *Publisher) isHealthy() bool {
	return p.conn != nil && p.channel != nil &&
		!p.conn.IsClosed() && !p.channel.IsClosed()
}

// Publish publishes a message to the queue.
func (p *Publisher) Publish(ctx context.Context, message interface{}) error {
	msgBytes, err := json.Marshal(message)
	if err != nil {
		return fmt.Errorf("marshal failed: %w", err)
	}

	var envelope MessageEnvelope
	var msgType string
	if err = json.Unmarshal(msgBytes, &envelope); err == nil {
		msgType = string(envelope.MessageType)
	}

	for {
		p.sessionMu.RLock()
		if p.isHealthy() {
			break
		}
		p.sessionMu.RUnlock()

		p.sessionMu.Lock()
		if !p.isHealthy() {
			p.logger.Info("rabbitmq session unhealthy; reconnecting", "queue", p.queueName)
			if connectErr := p.connectLocked(ctx); connectErr != nil {
				p.sessionMu.Unlock()
				return connectErr
			}
		}
		p.sessionMu.Unlock()
	}

	err = p.channel.PublishWithContext(
		ctx,
		"",          // exchange
		p.queueName, // routing key
		false,       // mandatory
		false,       // immediate
		amqp.Publishing{
			ContentType:  "application/json",
			Body:         msgBytes,
			DeliveryMode: amqp.Persistent,
			Timestamp:    time.Now(),
			UserId:       p.userID,
		},
	)
	p.sessionMu.RUnlock()

	if err != nil {
		p.logger.Error(err, "publish failed", "type", msgType, "queue", p.queueName)
		return fmt.Errorf("publish failed: %w", err)
	}

	p.logger.Info("message published", "type", msgType, "queue", p.queueName)
	return nil
}

// Close closes the publisher connection.
func (p *Publisher) Close() error {
	p.sessionMu.Lock()
	defer p.sessionMu.Unlock()

	var errs []error
	if p.channel != nil {
		if err := p.channel.Close(); err != nil {
			errs = append(errs, fmt.Errorf("channel close failed: %w", err))
		}
		p.channel = nil
	}
	if p.conn != nil {
		if err := p.conn.Close(); err != nil {
			errs = append(errs, fmt.Errorf("connection close failed: %w", err))
		}
		p.conn = nil
	}
	if len(errs) > 0 {
		return fmt.Errorf("close errors: %v", errs)
	}
	return nil
}
