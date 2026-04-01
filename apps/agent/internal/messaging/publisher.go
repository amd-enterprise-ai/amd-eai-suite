// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
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
	conn, err := amqp.Dial(p.amqpURL)
	if err != nil {
		return fmt.Errorf("connect failed: %w", err)
	}
	p.conn = conn

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
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
		ch.Close()
		conn.Close()
		return fmt.Errorf("queue declare failed: %w", err)
	}

	p.logger.Info("publisher connected", "queue", p.queueName)
	return nil
}

// Publish publishes a message to the queue.
func (p *Publisher) Publish(ctx context.Context, message interface{}) error {
	if p.channel == nil {
		return fmt.Errorf("not connected, call Connect first")
	}

	msgBytes, err := json.Marshal(message)
	if err != nil {
		return fmt.Errorf("marshal failed: %w", err)
	}

	var envelope MessageEnvelope
	var msgType string
	if err = json.Unmarshal(msgBytes, &envelope); err == nil {
		msgType = string(envelope.MessageType)
	}

	p.logger.Info("publishing message", "type", msgType, "queue", p.queueName)

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
	if err != nil {
		p.logger.Error(err, "publish failed", "type", msgType, "queue", p.queueName)
		return fmt.Errorf("publish failed: %w", err)
	}

	p.logger.Info("message published", "type", msgType, "queue", p.queueName)
	return nil
}

// Close closes the publisher connection.
func (p *Publisher) Close() error {
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
